#!/usr/bin/env python3
"""500 miners against 1,000 miners.

The p2p network is expected to carry at most about 1,000 miners, so every
simulation in this bundle uses a population of at most 1,000. This one asks
what changes if the pool has 500 miners instead.

Both pools are 1 EH/s (0.1% of the network) and hold 4 farms, 25 small farms
and 250 miners with 2 to 20 machines; the 1,000-miner pool adds 721 miners with
one machine (an S19 or an S21) and the 500-miner pool 221, with the farms
making up the difference. Nobody is smaller than one S19. In attacker scenarios the attacker's addresses take the place of the
smallest honest miners, so the total stays at 500 or 1,000.

Part H checks both of those assumptions: a 500-miner pool built instead from
every second miner of the 1,000 (same mix of sizes, each miner with twice the
hashrate), and attacker addresses that do not count toward the limit.
Runtime: about 30 seconds."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, miner_stats, spec, marginals, label,
                          with_attacker, attacker_X, stale_tip_gain, withhold_gain,
                          ATTACKERS, BLOCKS_PER_DAY, UNCLE_PENALTY, SHARE_SECONDS,
                          CAP_OLD, CAP_NEW, S19, S21, SIZES, size_label, SIZE_NOTE)

POPS = (("500", "mainnet_500"), ("1,000", "mainnet"))
LAM = BLOCKS_PER_DAY["mainnet"]
YEAR = LAM * 365
SHARES = [S19, S21, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30]   # of the pool


def lab(x):
    return size_label(x) if x in (S19, S21) else f"{x * 100:.1f}%"
OPTIONS = ("opt1", "adaptive", "opt3_sys")
SHORT = {"opt1": "option 1", "adaptive": "option 2", "opt3_sys": "option 3"}
WINDOW_SHARES = 14 * 86400 / SHARE_SECONDS


def part_a(pops):
    print(SIZE_NOTE)
    print("=== A. the two populations (both pools are 1 EH/s) ===")
    print(f"  {'':36s}" + "".join(f"{n + ' miners':>16s}" for n, _ in POPS))
    rows = [
        ("largest miner", lambda w: f"{w[0] * 100:.1f}%"),
        ("hashrate of the 29 largest", lambda w: f"{w[:29].sum() * 100:.1f}%"),
        ("hashrate of the smallest half", lambda w: f"{w[len(w) // 2:].sum() * 100:.3f}%"),
        ("hashrate outside the 29 largest", lambda w: f"{w[29:].sum() * 100:.1f}%"),
        ("miners at or below 200 TH/s", lambda w: f"{(w < 2.05e-4).sum()}"),
        ("their share of pool hashrate", lambda w: f"{w[w < 2.05e-4].sum() * 100:.1f}%"),
        ("miners with one S19", lambda w: f"{(w < 1.0e-4).sum()}"),
    ]
    for name, f in rows:
        print(f"  {name:36s}" + "".join(f"{f(pops[n]):>16s}" for n, _ in POPS))
    print("  share of pool hashrate by class:")
    names = {"farm": "4 farms", "mid": "25 small farms (3-30 PH/s)",
             "small": "250 miners with 2-20 machines", "single": "miners with one machine"}
    full = {n: get_population(name) for n, name in POPS}
    for c, cname in names.items():
        print(f"  {'  ' + cname:36s}" + "".join(
            f"{f'{full[n][0][full[n][1] == c].sum() * 100:.1f}% ({(full[n][1] == c).sum()})':>16s}"
            for n, _ in POPS))
    w = full["1,000"][0]
    print(f"  the four farms of the 1,000-miner pool hold "
          + ", ".join(f"{x * 100:.1f}%" for x in w[:4]) + " of the pool")


def part_b(pops):
    print("\n=== B. each option, by miner count (mainnet block rate) ===")
    print("  days = mean days between payouts for a miner with that share; "
          "spread = sd / mean of a year's income")
    for K in (CAP_OLD, CAP_NEW):
        print(f"\n cap {K}")
        print(f"  {'scheme':30s}{'miners':>8s}{'N+M':>8s}{'prize%':>8s}{'exact':>6s}"
              f"{'days 1%':>9s}{'days 0.1%':>11s}{'days S21':>10s}{'days S19':>10s}"
              f"{'spread 0.1%':>13s}{'spread S19':>12s}{'spread 2%':>11s}{'raffle var':>12s}")
        for nm in OPTIONS:
            for n, _ in POPS:
                w = pops[n]
                N, M, kind = spec(w, K, nm)
                a = marginals(w, N, M, kind)
                st = {x: miner_stats(w, x, K, nm) for x in (0.01, 0.001, S21, S19, 0.02)}
                print(f"  {label(nm):30s}{n:>8s}{N:>4d}+{M:<3d}{a['slot'] * 100:8.2f}"
                      f"{int((a['p_pay'] > 0.999999).sum()):6d}"
                      + "".join(f"{1 / (LAM * st[x]['p_pay']):{wd}.1f}"
                                for x, wd in ((0.01, 9), (0.001, 11), (S21, 10), (S19, 10)))
                      + f"{math.sqrt(st[0.001]['infl'] / YEAR) * 100:12.0f}%"
                      f"{math.sqrt(st[S19]['infl'] / YEAR) * 100:11.0f}%"
                      f"{math.sqrt(st[0.02]['infl'] / YEAR) * 100:10.1f}%"
                      f"{(a['ex2'] - w ** 2).sum():12.5f}")


def part_c(pops):
    print("\n=== C. payout variance by hashrate share and miner count ===")
    measures = (
        ("variance of income relative to an uncapped coinbase (1.0 = no added variance)",
         lambda q: f"{q['infl']:.1f}"),
        (f"spread of one year's income, sd / mean (no cap: {math.sqrt(1 / YEAR) * 100:.1f}%)",
         lambda q: f"{math.sqrt(q['infl'] / YEAR) * 100:.1f}%"),
        (f"mean days between payouts (no cap: {1 / LAM:.1f})",
         lambda q: f"{1 / (LAM * q['p_pay']):.1f}"),
    )
    for K in (CAP_OLD, CAP_NEW):
        st = {(x, nm, n): miner_stats(pops[n], x, K, nm)
              for x in SHARES for nm in OPTIONS for n, _ in POPS}
        for title, f in measures:
            print(f"\n cap {K}: {title}")
            print(f"  {'share':>7s}" + "".join(
                f"{SHORT[nm] + ', ' + n:>20s}" for nm in OPTIONS for n, _ in POPS))
            for x in SHARES:
                print(f"  {lab(x):>7s}" + "".join(
                    f"{f(st[x, nm, n]):>20s}" for nm in OPTIONS for n, _ in POPS))


def part_d(pops):
    print("\n=== D. how many miners are served (option 2 adaptive) ===")
    print(f"  {'cap':>4s}{'miners':>8s}{'paid exactly':>14s}{'raffle prizes a year':>22s}"
          f"{'tail miners':>13s}{'>=50% chance of a payout in a year':>36s}"
          f"{'in 30 days':>22s}")
    for K in (CAP_OLD, CAP_NEW):
        for n, _ in POPS:
            w = pops[n]
            N, M, kind = spec(w, K, "adaptive")
            a = marginals(w, N, M, kind)
            cells = []
            for days in (365.0, 30.0):
                ok = 1 - np.exp(-LAM * days * a["p_pay"]) >= 0.5
                cells.append(f"{ok.sum()} ({ok.mean() * 100:.1f}% of miners, "
                             f"{w[ok].sum() * 100:.1f}% of hashrate)")
            print(f"  {K:4d}{n:>8s}{N:14d}{M * YEAR:22.0f}{len(w) - N:13d}"
                  f"{cells[0]:>48s}{cells[1]:>48s}")


def part_e(pops):
    blocks = LAM * 14
    print(f"\n=== E. one share on mainnet (2-week window, {blocks:.0f} pool blocks "
          "expected) ===")
    print(f"  {'cap':>4s}{'miners':>8s}{'prize%':>8s}{'chance the share ever pays':>28s}")
    for K in (CAP_OLD, CAP_NEW):
        for n, _ in POPS:
            tau = marginals(pops[n], *spec(pops[n], K, "adaptive"))["slot"]
            ever = 1 - math.exp(-blocks * (1 / WINDOW_SHARES) / tau)
            print(f"  {K:4d}{n:>8s}{tau * 100:8.2f}{ever * 100:27.3f}%")


def part_f(pops):
    print("\n=== F. seed grinding by miner count (tip choice among 3 older tips + "
          "withholding, 10% uncle penalty) ===")
    rng = np.random.default_rng(13)
    print(f"  {'cap':>4s}{'attacker':>24s}{'scheme':>30s}"
          + "".join(f"{n + ' miners':>22s}" for n, _ in POPS))
    for K in (CAP_OLD, CAP_NEW):
        for sname in ("20% in 400 addresses", "5% in 50 addresses"):
            for nm in ("opt1", "adaptive"):
                cells = []
                for n, _ in POPS:
                    w, att = with_attacker(pops[n], ATTACKERS[sname], limit=len(pops[n]))
                    X = attacker_X(w, att, *spec(w, K, nm), 30_000, rng)
                    cells.append(
                        f"{stale_tip_gain(X, 3, UNCLE_PENALTY, rng) * 100:.2f}% + "
                        f"{withhold_gain(X, sum(ATTACKERS[sname]), UNCLE_PENALTY, rng) * 100:.2f}%")
                print(f"  {K:4d}{sname:>24s}{label(nm):>30s}"
                      + "".join(f"{c:>22s}" for c in cells), flush=True)
    rng3 = np.random.default_rng(131)            # option 3, own random stream
    for K in (CAP_OLD, CAP_NEW):
        for sname in ("20% in 400 addresses", "5% in 50 addresses"):
            cells = []
            for n, _ in POPS:
                w, att = with_attacker(pops[n], ATTACKERS[sname], limit=len(pops[n]))
                X = attacker_X(w, att, *spec(w, K, "opt3_sys"), 30_000, rng3)
                cells.append(
                    f"{stale_tip_gain(X, 3, UNCLE_PENALTY, rng3) * 100:.2f}% + "
                    f"{withhold_gain(X, sum(ATTACKERS[sname]), UNCLE_PENALTY, rng3) * 100:.2f}%")
            print(f"  {K:4d}{sname:>24s}{label('opt3_sys'):>30s}"
                  + "".join(f"{c:>22s}" for c in cells), flush=True)


def part_g(pops):
    print("\n=== G. option 2 adaptive, small miners: mean days between payouts / "
          "chance of no payout in 30 days ===")
    blocks = LAM * 30
    head = "".join(f"{f'cap {K}, {n} miners':>26s}" for K in (CAP_OLD, CAP_NEW) for n, _ in POPS)
    print(f"  {'share':>8s}{head}")
    for x in SIZES:
        cells = []
        for K in (CAP_OLD, CAP_NEW):
            for n, _ in POPS:
                s = miner_stats(pops[n], x, K, "adaptive")
                cells.append(f"{1 / (LAM * s['p_pay']):9.1f} /{math.exp(-blocks * s['p_pay']) * 100:5.1f}%")
        print(f"  {size_label(x):>8s}" + "".join(f"{c:>26s}" for c in cells))


def part_h(pops):
    print("\n=== H. sensitivity to the two modelling assumptions ===")
    print("\n H1. which miners make up a 500-miner pool")
    mix = get_population("mainnet_500_mix")[0]
    cases = (("500, fewer single machines", pops["500"]),
             ("500, every second miner", mix),
             ("1,000", pops["1,000"]))
    print(f"  {'population':26s}{'largest':>9s}{'top 29':>8s}{'cap':>5s}{'scheme':>30s}"
          f"{'N+M':>8s}{'prize%':>8s}{'days 1%':>9s}{'days 0.1%':>11s}"
          f"{'days S19':>12s}{'spread 0.1%':>13s}")
    for K in (CAP_OLD, CAP_NEW):
        for nm in OPTIONS:
            for name, w in cases:
                N, M, kind = spec(w, K, nm)
                a = marginals(w, N, M, kind)
                st = {x: miner_stats(w, x, K, nm) for x in (0.01, 0.001, S19)}
                print(f"  {name:26s}{w[0] * 100:8.1f}%{w[:29].sum() * 100:7.1f}%{K:5d}"
                      f"{label(nm):>30s}{N:>4d}+{M:<3d}{a['slot'] * 100:8.2f}"
                      + "".join(f"{1 / (LAM * st[x]['p_pay']):{wd}.1f}"
                                for x, wd in ((0.01, 9), (0.001, 11), (S19, 12)))
                      + f"{math.sqrt(st[0.001]['infl'] / YEAR) * 100:12.0f}%")
    print("\n  miners with >= 50% chance of a payout in a year (option 2 adaptive)")
    for K in (CAP_OLD, CAP_NEW):
        for name, w in cases:
            a = marginals(w, *spec(w, K, "adaptive"))
            ok = 1 - np.exp(-YEAR * a["p_pay"]) >= 0.5
            print(f"  cap {K:3d}  {name:26s}{ok.sum():5d} ({ok.mean() * 100:.1f}% of miners, "
                  f"{w[ok].sum() * 100:.1f}% of hashrate)")

    print("\n H2. do the attacker's addresses count toward the 1,000-miner limit?")
    print("  (tip choice among 3 older tips + withholding, 10% uncle penalty; "
          "option 2 adaptive, 1,000 honest miners)")
    rng = np.random.default_rng(113)
    w0 = pops["1,000"]
    print(f"  {'cap':>4s}{'attacker':>24s}{'counted: 1,000 addresses':>28s}"
          f"{'not counted: 1,000 + attacker':>32s}")
    for K in (CAP_OLD, CAP_NEW):
        for sname in ("20% in 400 addresses", "5% in 50 addresses"):
            cells = []
            for limit in (len(w0), len(w0) + len(ATTACKERS[sname])):
                w, att = with_attacker(w0, ATTACKERS[sname], limit=limit)
                X = attacker_X(w, att, *spec(w, K, "adaptive"), 30_000, rng)
                cells.append(
                    f"{len(w)} addr: "
                    f"{stale_tip_gain(X, 3, UNCLE_PENALTY, rng) * 100:.2f}% + "
                    f"{withhold_gain(X, sum(ATTACKERS[sname]), UNCLE_PENALTY, rng) * 100:.2f}%")
            print(f"  {K:4d}{sname:>24s}{cells[0]:>28s}{cells[1]:>32s}", flush=True)
    print("\n  prize and waits for honest miners when a 20% miner in 400 addresses is present "
          "(option 2 adaptive)")
    print(f"  {'cap':>4s}{'addresses':>11s}{'N+M':>8s}{'prize%':>8s}{'days 0.1%':>11s}{'days S19':>10s}")
    for K in (CAP_OLD, CAP_NEW):
        for limit in (len(w0), len(w0) + 400):
            w, att = with_attacker(w0, ATTACKERS["20% in 400 addresses"], limit=limit)
            N, M, kind = spec(w, K, "adaptive")
            tau = marginals(w, N, M, kind)["slot"]
            print(f"  {K:4d}{len(w):11d}{N:>4d}+{M:<3d}{tau * 100:8.2f}"
                  f"{tau / 0.001 / LAM:11.1f}{tau / S19 / LAM:10.1f}")


if __name__ == "__main__":
    populations = {n: get_population(name)[0] for n, name in POPS}
    part_a(populations)
    part_b(populations)
    part_c(populations)
    part_d(populations)
    part_e(populations)
    part_g(populations)
    part_f(populations)
    part_h(populations)
