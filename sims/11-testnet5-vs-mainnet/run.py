#!/usr/bin/env python3
"""Testnet5 against mainnet. The pool finds about 50 blocks a day on testnet5
and about 1.5 a week on mainnet, a ratio of roughly 230. The same payout rule
therefore behaves very differently over calendar time. Closed forms on the two
synthetic populations. Runtime: a few seconds."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, miner_stats, spec, marginals, label,
                          BLOCKS_PER_DAY, CAP_OLD, CAP_NEW, SIZES, SIZE_NOTE)

SHARES = SIZES          # share of POOL: 1%, 0.1%, 0.02% (one S21), 0.0095% (one S19)
DAYS = 30.0


def main():
    pops = {net: get_population(net)[0] for net in ("testnet5", "mainnet")}
    print("Shares are of pool hashrate. On mainnet: " + SIZE_NOTE.split(": ", 1)[1])
    print("=== A. the two settings ===")
    print(f"  {'':22s}{'testnet5':>12s}{'mainnet':>12s}")
    print(f"  {'miners (assumed)':22s}{len(pops['testnet5']):12d}{len(pops['mainnet']):12d}")
    print(f"  {'pool blocks per day':22s}{BLOCKS_PER_DAY['testnet5']:12.1f}"
          f"{BLOCKS_PER_DAY['mainnet']:12.2f}")
    print(f"  {'pool blocks per 30 d':22s}{BLOCKS_PER_DAY['testnet5'] * 30:12.0f}"
          f"{BLOCKS_PER_DAY['mainnet'] * 30:12.1f}")
    print(f"  {'days between blocks':22s}{1 / BLOCKS_PER_DAY['testnet5']:12.2f}"
          f"{1 / BLOCKS_PER_DAY['mainnet']:12.2f}")
    print(f"  {'largest miner':22s}{pops['testnet5'][0] * 100:11.1f}%"
          f"{pops['mainnet'][0] * 100:11.1f}%")

    for K in (CAP_OLD, CAP_NEW):
        print(f"\n=== B. cap {K}: what each option does on each network ===")
        for net, pop in pops.items():
            lam = BLOCKS_PER_DAY[net]
            blocks = lam * DAYS
            print(f"\n {net}: mean days between payouts / chance of no payout in "
                  f"{DAYS:.0f} days / spread of {DAYS:.0f}-day income (sd / mean)")
            print(f"  {'scheme':30s}{'exact':>6s}{'prize%':>8s}"
                  + "".join(f"{f'{x * 100:g}% of pool':>26s}" for x in SHARES))
            base = "   ".join(f"{1 / lam:7.2f} /{math.exp(-blocks) * 100:5.1f}% /"
                              f"{math.sqrt(1 / blocks) * 100:5.0f}%" for _ in SHARES)
            print(f"  {'no cap':30s}{len(pop):6d}{'':8s}   {base}")
            for nm in ("opt1", "opt3_sys", "adaptive"):
                N, M, kind = spec(pop, K, nm)
                a = marginals(pop, N, M, kind)
                cells = []
                for x in SHARES:
                    s = miner_stats(pop, x, K, nm)
                    cells.append(f"{1 / (lam * s['p_pay']):7.2f} /"
                                 f"{math.exp(-blocks * s['p_pay']) * 100:5.1f}% /"
                                 f"{math.sqrt(s['infl'] / blocks) * 100:5.0f}%")
                print(f"  {label(nm):30s}{int((a['p_pay'] > 0.999999).sum()):6d}"
                      f"{a['slot'] * 100:8.2f}   " + "   ".join(cells))

    print("\n=== C. option 2 adaptive: how much of the pool is served within "
          f"{DAYS:.0f} days ===")
    print(f"  {'network':10s}{'cap':>5s}{'miners with >=50% chance of a payout':>38s}"
          f"{'their share of hashrate':>26s}")
    for net, pop in pops.items():
        lam = BLOCKS_PER_DAY[net]
        for K in (CAP_OLD, CAP_NEW):
            a = marginals(pop, *spec(pop, K, "adaptive"))
            ok = 1 - np.exp(-lam * DAYS * a["p_pay"]) >= 0.5
            print(f"  {net:10s}{K:5d}{ok.mean() * 100:37.1f}%{pop[ok].sum() * 100:25.1f}%")

    print("\n=== D. smallest cap at which every miner is paid in every block ===")
    for net, pop in pops.items():
        print(f"  {net}: {len(pop)} outputs (one per miner in the window)")


if __name__ == "__main__":
    main()
