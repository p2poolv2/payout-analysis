#!/usr/bin/env python3
"""Earnings on p2poolv2 with a capped coinbase against today's pools.

Miners: one Antminer S19 (95 TH/s), one S21 (200 TH/s), and miners holding
0.1%, 1% and 10% of the POOL (1, 10 and 100 PH/s). The pool is 1 EH/s, 0.1% of
a 1,000 EH/s network, and finds about one block a week.

A. the inputs and what each machine earns before fees
B. expected earnings by pool type (fees only; no luck)
C. one year on p2poolv2 under each capped scheme: how often a miner is paid,
   how large a payout is, the chance of no payout, and the range of income
D. the same year on today's pools (FPPS, OCEAN, solo)
E. p2poolv2 by miner count, 500 against 1,000
F. the recommended rule across caps from 13 to 500

Expected earnings are the same under every unbiased scheme; what differs is
how they arrive. p2poolv2 is assumed to take no pool fee.
Runtime: about 20 seconds."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, miner_stats, label, BLOCKS_PER_DAY,
                          NETWORK_EH, POOL_EH, POOL_TH, REWARD_BTC, SUBSIDY_BTC,
                          FEES_BTC, BTC_USD, S19_TH, S21_TH, CAP_OLD, CAP_NEW)

LAM = BLOCKS_PER_DAY["mainnet"]
YEAR = LAM * 365.0                        # pool blocks a year
NET_BLOCKS_YEAR = 144 * 365.0
MINERS = (("one S19", S19_TH), ("one S21", S21_TH), ("1 PH/s", 1e3),
          ("10 PH/s", 1e4), ("100 PH/s", 1e5))
WATTS = {"one S19": 3250.0, "one S21": 3500.0}
POOLS = (("FPPS pool, 2% fee", 0.02), ("FPPS pool, 4% fee", 0.04),
         ("OCEAN (TIDES), 2% fee", 0.02), ("solo via CKPool, 2% fee", 0.02),
         ("p2poolv2, no fee assumed", 0.0))
SCHEMES = (("no cap", None, None), ("option 1", "opt1", CAP_OLD),
           ("option 3", "opt3_sys", CAP_OLD), ("option 2 adaptive", "adaptive", CAP_OLD),
           ("option 1", "opt1", CAP_NEW), ("option 3", "opt3_sys", CAP_NEW),
           ("option 2 adaptive", "adaptive", CAP_NEW))
FPPS_FLOOR = 0.98                         # income of a 2%-fee FPPS pool / fair
PAYOUT_MIN_SATS = 100_000                 # a typical on-chain payout threshold
OCEAN_MIN_SATS = 1_048_576                # OCEAN's on-chain threshold
OCEAN_SHARE = 0.02                        # OCEAN's share of network hashrate
PATHS = 400_000


def sats_day(th):
    return th * 1e12 / (NETWORK_EH * 1e18) * 144 * REWARD_BTC * 1e8


def part_a():
    print("=== A. inputs ===")
    print(f"  network hashrate {NETWORK_EH:,.0f} EH/s; block reward {SUBSIDY_BTC} BTC + "
          f"{FEES_BTC} BTC fees = {REWARD_BTC:.3f} BTC; BTC at ${BTC_USD:,.0f}")
    hp = sats_day(1e3) / 1e8 * BTC_USD
    print(f"  hashprice implied: {sats_day(1e3):,.0f} sats = ${hp:.2f} per PH/s per day")
    print(f"  pool {POOL_EH:g} EH/s = {POOL_EH / NETWORK_EH * 100:.2f}% of the network: "
          f"{LAM * 7:.2f} blocks a week, {YEAR:.1f} a year, one every {1 / LAM:.1f} days")
    print(f"\n  {'miner':10s}{'TH/s':>10s}{'% of pool':>11s}{'% of network':>14s}"
          f"{'sats/day':>11s}{'USD/day':>10s}{'sats/year':>16s}{'USD/year':>11s}"
          f"{'per pool block':>16s}{'break-even power':>18s}")
    for name, th in MINERS:
        d = sats_day(th)
        be = (f"${d / 1e8 * BTC_USD / (WATTS[name] * 24 / 1000):.3f}/kWh"
              if name in WATTS else "")
        print(f"  {name:10s}{th:10,.0f}{th / POOL_TH * 100:10.4f}%"
              f"{th / (NETWORK_EH * 1e6) * 100:13.7f}%{d:11,.0f}"
              f"{d / 1e8 * BTC_USD:10.2f}{d * 365:16,.0f}{d * 365 / 1e8 * BTC_USD:11,.0f}"
              f"{th / POOL_TH * REWARD_BTC * 1e8:13,.0f} sats{be:>18s}")
    print("  'per pool block' = the miner's PPLNS share of one p2poolv2 block; "
          "earnings are before fees and power")


def part_b():
    print("\n=== B. expected earnings by pool type, sats per day (fees only) ===")
    print(f"  {'pool':28s}" + "".join(f"{n:>12s}" for n, _ in MINERS)
          + f"{'pool fee':>10s}")
    for pname, fee in POOLS:
        print(f"  {pname:28s}"
              + "".join(f"{sats_day(th) * (1 - fee):12,.0f}" for _, th in MINERS)
              + f"{fee * 100:9.0f}%")
    print("  in USD per year:")
    for pname, fee in POOLS:
        print(f"  {pname:28s}" + "".join(
            f"{sats_day(th) * 365 * (1 - fee) / 1e8 * BTC_USD:12,.0f}" for _, th in MINERS))


def year_on_p2pool(pop, x, nm, K, rng):
    """One year of income / fair income under a scheme, plus summary figures."""
    nb = rng.poisson(YEAR, PATHS)
    if nm is None:                                    # uncapped: paid every block
        rel, per_year, size, p_block = nb / YEAR, YEAR, x, 1.0
    else:
        s = miner_stats(pop, x, K, nm)
        if s["exact"]:
            rel, per_year, size, p_block = nb / YEAR, YEAR, x, 1.0
        else:
            mp = x / s["prize"]                       # expected slots per block
            base, f = math.floor(mp), mp - math.floor(mp)
            wins = nb * base + rng.binomial(nb, f)
            rel = wins * s["prize"] / (x * YEAR)
            p_block = min(1.0, mp)
            per_year = YEAR * p_block
            size = s["prize"] if base == 0 else x
    return dict(rel=rel, per_year=per_year, size=size,
                none1=math.exp(-per_year), none3=math.exp(-3 * per_year),
                y90=math.log(10) / per_year)


def row(name, r, th):
    rel = r["rel"]
    return (f"  {name:26s}{r['per_year']:11.2f}{r['size'] * REWARD_BTC * 1e8:15,.0f}"
            f"{r['none1'] * 100:11.1f}%{r['none3'] * 100:11.1f}%{r['y90']:9.1f}"
            f"{np.median(rel) * 100:9.0f}%{np.percentile(rel, 5) * 100:7.0f}%"
            f"{np.percentile(rel, 95) * 100:7.0f}%{(rel >= FPPS_FLOOR).mean() * 100:10.1f}%")


HEAD = (f"  {'scheme':26s}{'payouts/yr':>11s}{'sats/payout':>15s}{'none in 1 y':>12s}"
        f"{'none in 3 y':>12s}{'y to 90%':>9s}{'median':>10s}{'p5':>8s}{'p95':>8s}"
        f"{'beats FPPS':>11s}")
NOTE = ("  payouts/yr = expected number of payouts in a year; sats/payout = size of "
        "one payout;\n  none in 1 y / 3 y = chance of no payout at all; y to 90% = "
        "years until a 90% chance of at least one payout;\n  median, p5, p95 = one "
        "year's income as a share of its expected value; beats FPPS = chance that "
        "the year's\n  income exceeds what a 2%-fee FPPS pool pays (98% of expected)")


def part_c(pop, rng):
    print(f"\n=== C. one year on p2poolv2, {len(pop):,} miners, "
          f"{YEAR:.1f} pool blocks expected ({PATHS:,} paths) ===")
    for name, th in MINERS:
        x = th / POOL_TH
        print(f"\n {name} ({x * 100:g}% of the pool), expected "
              f"{sats_day(th) * 365:,.0f} sats a year")
        print(HEAD)
        for sname, nm, K in SCHEMES:
            r = year_on_p2pool(pop, x, nm, K, rng)
            tag = sname if K is None else f"{sname}, cap {K}"
            print(row(tag, r, th))
    print(NOTE)


def part_d(rng):
    print("\n=== D. the same year on today's pools ===")
    ocean_blocks = OCEAN_SHARE * NET_BLOCKS_YEAR
    print(f"  FPPS: the pool pays expected value less its fee whatever its luck; "
          f"payout when the balance passes {PAYOUT_MIN_SATS:,} sats")
    print(f"  OCEAN: {OCEAN_SHARE * 100:.0f}% of the network assumed, "
          f"{ocean_blocks:,.0f} blocks a year, paid on pool luck; on-chain payout "
          f"when the balance passes {OCEAN_MIN_SATS:,} sats (no minimum over Lightning)")
    print(f"  solo: paid only when the miner itself finds a Bitcoin block "
          f"({REWARD_BTC * 0.98:.3f} BTC after the fee)")
    print(f"\n  {'miner':10s}{'pool':28s}{'expected sats/yr':>18s}{'payouts/yr':>12s}"
          f"{'none in 1 y':>12s}{'median':>9s}{'p5':>7s}{'p95':>7s}")
    for name, th in MINERS:
        e = sats_day(th) * 365
        for fee in (0.02, 0.04):
            n_pay = min(365.0, e * (1 - fee) / PAYOUT_MIN_SATS)
            print(f"  {name:10s}{f'FPPS pool, {fee * 100:.0f}% fee':28s}{e * (1 - fee):18,.0f}"
                  f"{n_pay:12.1f}{0.0:11.1f}%{(1 - fee) * 100:8.0f}%"
                  f"{(1 - fee) * 100:6.0f}%{(1 - fee) * 100:6.0f}%")
        rel = rng.poisson(ocean_blocks, PATHS) / ocean_blocks * 0.98
        print(f"  {name:10s}{'OCEAN (TIDES), 2% fee':28s}{e * 0.98:18,.0f}"
              f"{min(ocean_blocks, e * 0.98 / OCEAN_MIN_SATS):12.1f}{0.0:11.1f}%{np.median(rel) * 100:8.0f}%"
              f"{np.percentile(rel, 5) * 100:6.0f}%{np.percentile(rel, 95) * 100:6.0f}%")
        mu = th * 1e12 / (NETWORK_EH * 1e18) * NET_BLOCKS_YEAR      # own blocks a year
        rel = rng.poisson(mu, PATHS) / mu * 0.98
        print(f"  {name:10s}{'solo via CKPool, 2% fee':28s}{e * 0.98:18,.0f}"
              f"{mu:12.4f}{math.exp(-mu) * 100:11.1f}%{np.median(rel) * 100:8.0f}%"
              f"{np.percentile(rel, 5) * 100:6.0f}%{np.percentile(rel, 95) * 100:6.0f}%")


def part_e(pops, rng):
    print("\n=== E. p2poolv2 by miner count: payouts a year / chance of no payout "
          "in a year / sats per payout ===")
    print(f"  {'miner':10s}{'scheme':26s}" + "".join(f"{n + ' miners':>36s}" for n in pops))
    for name, th in MINERS[:3]:
        x = th / POOL_TH
        for sname, nm, K in SCHEMES[1:]:
            cells = []
            for pop in pops.values():
                r = year_on_p2pool(pop, x, nm, K, rng)
                cells.append(f"{r['per_year']:7.2f} /{r['none1'] * 100:6.1f}% /"
                             f"{r['size'] * REWARD_BTC * 1e8:13,.0f}")
            print(f"  {name:10s}{f'{sname}, cap {K}':26s}" + "".join(f"{c:>36s}" for c in cells))


def part_f(pops, rng):
    print("\n=== F. option 2 adaptive across caps: payouts a year / chance of no "
          "payout in a year / sats per payout ===")
    for n, pop in pops.items():
        print(f"\n {n} miners")
        print(f"  {'cap':>5s}{'prize%':>8s}" + "".join(f"{m:>36s}" for m, _ in MINERS[:3])
              + f"{'miners paid exactly':>21s}")
        for K in (13, 19, 25, 60, 85, 100, 250, 500):
            cells, exact = [], 0
            for _, th in MINERS[:3]:
                r = year_on_p2pool(pop, th / POOL_TH, "adaptive", K, rng)
                cells.append(f"{r['per_year']:7.2f} /{r['none1'] * 100:6.1f}% /"
                             f"{r['size'] * REWARD_BTC * 1e8:13,.0f}")
            s = miner_stats(pop, MINERS[0][1] / POOL_TH, K, "adaptive")
            print(f"  {K:5d}{s['prize'] * 100:8.3f}" + "".join(f"{c:>36s}" for c in cells)
                  + f"{s['N']:21d}")


if __name__ == "__main__":
    gen = np.random.default_rng(14)
    populations = {"500": get_population("mainnet_500")[0],
                   "1,000": get_population("mainnet")[0]}
    part_a()
    part_b()
    part_c(populations["1,000"], gen)
    part_d(gen)
    part_e(populations, gen)
    part_f(populations, gen)
