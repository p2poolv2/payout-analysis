#!/usr/bin/env python3
"""Testnet pool of 250 TH/s: a couple of S19s and many Bitaxes.

Base case: 2 Antminer S19s (95 TH/s each) and Bitaxes making up the other
60 TH/s, at 50 pool blocks a day. Two variants bracket "a handful of S19s and
a lot of Bitaxes": 1 S19 with 155 TH/s of Bitaxes, and 2 S19s with 120 of the
smallest Bitaxe (0.5 TH/s).

A. the pool
B. how many outputs each device's firmware takes on a near-empty testnet block
C. each option at caps 13, 20 and 60: how often each device is paid
D. coinbase sized by the finder: Bitaxe-found blocks carry everyone
E. the two variants
F. Monte Carlo check that payouts are unbiased
Runtime: about 20 seconds."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import spec, marginals, sample, label, S19_TH

POOL_TH = 250.0
LAM = 50.0                                   # pool blocks a day on testnet5
BITAXE = {"Hex": 3.2, "GT": 2.1, "Gamma": 1.2, "Supra": 0.7, "Ultra": 0.5}   # TH/s
MIX = {"Hex": 0.03, "GT": 0.07, "Gamma": 0.50, "Supra": 0.25, "Ultra": 0.15}
OPTIONS = ("opt1", "opt3_sys", "adaptive")
CAPS = (13, 20, 60)
BITAXE_CAP = 110          # taproot-size outputs in a coinb2 of about 5 KB


def pool(n_s19, rng, only=None):
    """n_s19 S19s plus Bitaxes filling the pool up to 250 TH/s."""
    room = POOL_TH - n_s19 * S19_TH
    names, hr = ["S19"] * n_s19, [S19_TH] * n_s19
    models, probs = list(MIX), list(MIX.values())
    while room > 0.25:
        m = only or models[rng.choice(len(models), p=probs)]
        if BITAXE[m] > room + 0.25:
            m = "Ultra"
        names.append(m)
        hr.append(BITAXE[m])
        room -= BITAXE[m]
    hr = np.array(hr)
    o = np.argsort(-hr, kind="stable")
    return hr[o] / hr.sum(), np.array(names)[o], hr.sum()


def firmware_caps():
    print("\n=== B. outputs that fit, by device (taproot-size outputs of 43 bytes "
          "beside a 47-byte witness commitment) ===")
    print("  S19-class firmware, from the job-message caps in simulation 09:")
    print(f"  {'merkle branches':>17s}{'transactions':>14s}{'3,072-byte build':>18s}"
          f"{'5,120-byte build':>18s}")
    for b in (0, 2, 4, 6, 13):
        txs = "1" if b == 0 else f"up to {2 ** b:,}"
        print(f"  {b:17d}{txs:>14s}{(1075 - 47 - 32 * b) // 43:18d}"
              f"{(3123 - 47 - 32 * b) // 43:18d}")
    print("  Bitaxe (ESP-Miner): stratum line limit 16 KiB; a coinb2 of about 5 KB is "
          "reported to work,\n  a job line of 14-15.5 KB to stall. 5 KB is about "
          f"{(5000 - 47) // 43} taproot-size outputs; this run uses {BITAXE_CAP}.")


def device_rows(w, names, a, q_all=0.0, a_big=None):
    """Per device type: chance per block, payouts a day, hours between payouts,
    chance of none in a day, spread of a day's and a week's income.
    With q_all > 0, that share of blocks uses the big-coinbase marginals.
    The device shown is the last of its class in rank order, so where a rule
    pays only some of a set of identical devices exactly (option 1 breaks the
    tie arbitrarily), the row is for one left in the raffle."""
    out = {}
    for dev in ["S19"] + list(BITAXE):
        idx = np.where(names == dev)[0]
        if not len(idx):
            continue
        i = idx[-1]
        p, ex2 = a["p_pay"][i], a["ex2"][i]
        if q_all > 0:
            p = q_all * a_big["p_pay"][i] + (1 - q_all) * p
            ex2 = q_all * a_big["ex2"][i] + (1 - q_all) * ex2
        infl = ex2 / w[i] ** 2
        out[dev] = (p, LAM * p, 24 / (LAM * p), math.exp(-LAM * p),
                    math.sqrt(infl / LAM), math.sqrt(infl / (7 * LAM)))
    return out


def show(rows, devs):
    return "".join(f"{rows[d][1]:8.1f} /{rows[d][2]:5.1f} h /{rows[d][4] * 100:4.0f}%"
                   for d in devs if d in rows)


def part_a(w, names, tot):
    print(f"=== A. the pool: {len(w)} miners, {tot:.0f} TH/s, {LAM:.0f} pool blocks a day ===")
    print(f"  {'device':8s}{'count':>7s}{'TH/s each':>11s}{'share of pool each':>20s}"
          f"{'class share of pool':>21s}{'blocks found a day':>20s}")
    for dev in ["S19"] + list(BITAXE):
        m = names == dev
        if m.any():
            th = S19_TH if dev == "S19" else BITAXE[dev]
            print(f"  {dev:8s}{m.sum():7d}{th:11.1f}{w[m][0] * 100:19.2f}%"
                  f"{w[m].sum() * 100:20.1f}%{w[m].sum() * LAM:20.1f}")
    print(f"  Bitaxes together: {(names != 'S19').sum()} devices, "
          f"{w[names != 'S19'].sum() * 100:.1f}% of the pool")


def part_c(w, names, title="C"):
    devs = [d for d in ["S19", "Hex", "GT", "Gamma", "Supra", "Ultra"] if (names == d).any()]
    print(f"\n=== {title}. each option: payouts a day / hours between payouts / spread of "
          "one day's income (sd / mean) ===")
    print(f"  no cap: every miner is paid {LAM:.0f} times a day; spread of a day's income "
          f"{math.sqrt(1 / LAM) * 100:.0f}%, of a week's {math.sqrt(1 / (7 * LAM)) * 100:.0f}%")
    for K in CAPS:
        print(f"\n cap {K}")
        print(f"  {'scheme':30s}{'N+M':>8s}{'prize%':>8s}{'exact':>6s}"
              + "".join(f"{d:>23s}" for d in devs) + f"{'raffle var':>12s}")
        for nm in OPTIONS:
            N, M, kind = spec(w, K, nm)
            a = marginals(w, N, M, kind)
            rows = device_rows(w, names, a)
            print(f"  {label(nm):30s}{N:>4d}+{M:<3d}{a['slot'] * 100:8.2f}"
                  f"{int((a['p_pay'] > 0.999999).sum()):6d}" + show(rows, devs)
                  + f"{(a['ex2'] - w ** 2).sum():12.5f}")
            split = [f"{int(a['is_top'][names == d].sum())} of {(names == d).sum()} {d}"
                     for d in devs if 0 < a["is_top"][names == d].sum() < (names == d).sum()]
            if split:
                print(f"  {'':30s}paid exactly: only {', '.join(split)}; the rows show "
                      "one left in the raffle")
    print("\n  spread of one week's income (sd / mean), option 2 adaptive:")
    for K in CAPS:
        rows = device_rows(w, names, marginals(w, *spec(w, K, "adaptive")))
        print(f"  cap {K:3d}  " + "  ".join(f"{d} {rows[d][5] * 100:.0f}%" for d in devs))
    print("  chance of no payout in a day, smallest Bitaxe present:")
    for K in CAPS:
        cells = []
        for nm in OPTIONS:
            rows = device_rows(w, names, marginals(w, *spec(w, K, nm)))
            cells.append(f"{label(nm)} {rows[devs[-1]][3] * 100:.2f}%")
        print(f"  cap {K:3d}  " + ";  ".join(cells))


def part_d(w, names):
    devs = [d for d in ["S19", "Hex", "GT", "Gamma", "Supra", "Ultra"] if (names == d).any()]
    q = w[names != "S19"].sum()                      # blocks found by Bitaxes
    Kb = min(BITAXE_CAP, len(w))
    a_big = marginals(w, *spec(w, Kb, "adaptive"))
    print(f"\n=== D. coinbase sized by the finder: Bitaxes find {q * 100:.1f}% of blocks "
          f"and carry {Kb} outputs; S19-found blocks are capped ===")
    print(f"  {'S19 blocks capped at':24s}" + "".join(f"{d:>23s}" for d in devs))
    for K in (13, 20):
        a = marginals(w, *spec(w, K, "adaptive"))
        print(f"  {f'{K}, every block (no choice)':24s}" + show(device_rows(w, names, a), devs))
        print(f"  {f'{K}, Bitaxe blocks carry all':24s}"
              + show(device_rows(w, names, a, q, a_big), devs))


def part_e(rng):
    print("\n=== E. variants: payouts a day / hours between payouts / spread of one "
          "day's income, smallest Bitaxe ===")
    cases = (("1 S19 + 155 TH/s of Bitaxes", pool(1, rng)),
             ("2 S19s + 120 Bitaxe Ultras", pool(2, rng, only="Ultra")))
    for title, (w, names, tot) in cases:
        small = "Ultra"
        print(f"\n {title}: {len(w)} miners, S19s hold {w[names == 'S19'].sum() * 100:.0f}% "
              f"of the pool, smallest Bitaxe {w[-1] * 100:.2f}%")
        print(f"  {'scheme':30s}" + "".join(f"{f'cap {K}':>34s}" for K in (13, 20, 60, 110)))
        for nm in OPTIONS:
            cells = []
            for K in (13, 20, 60, 110):
                N, M, kind = spec(w, K, nm)
                a = marginals(w, N, M, kind)
                r = device_rows(w, names, a)[small]
                cells.append(f"{N}+{M}: {r[1]:5.1f} /{r[2]:5.1f} h /{r[4] * 100:4.0f}%")
            print(f"  {label(nm):30s}" + "".join(f"{c:>34s}" for c in cells))


def part_f(w, names, rng):
    print("\n=== F. Monte Carlo check, base pool, cap 13, 200,000 blocks: "
          "paid / fair share by class ===")
    B = 200_000
    for nm in OPTIONS:
        N, M, kind = spec(w, 13, nm)
        tot = np.zeros(len(w))
        for _ in range(B // 2000):
            tot += sample(w, N, M, kind, 2000, rng).sum(0)
        cells = []
        for dev in ("S19", "Gamma", "Ultra"):
            m = names == dev
            cells.append(f"{dev} {tot[m].sum() / B / w[m].sum():.3f}")
        print(f"  {label(nm):30s}" + "   ".join(cells)
              + f"   all Bitaxes {tot[names != 'S19'].sum() / B / w[names != 'S19'].sum():.3f}")


if __name__ == "__main__":
    gen = np.random.default_rng(15)
    weights, kinds, total = pool(2, gen)
    part_a(weights, kinds, total)
    firmware_caps()
    part_c(weights, kinds)
    part_d(weights, kinds)
    part_e(gen)
    part_f(weights, kinds, gen)
