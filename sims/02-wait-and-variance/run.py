#!/usr/bin/env python3
"""How long do miners wait between payouts, and how much raffle variance does
each option add? Closed-form results for both networks at caps 13 and 60, a
robustness check over 300 random populations per cap (never more than 1,000
miners, none smaller than one S19 in a 1 EH/s pool), and a Monte Carlo of
income over a horizon. Runtime: a few seconds."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, spec, marginals, fairness_row, label,
                          zipf_population, BLOCKS_PER_DAY, CAP_OLD, CAP_NEW, SIZES,
                          MINER_LIMIT, S19, S21, size_label, s19_floor, SIZE_NOTE)


def schemes(K):
    return ["opt1", f"opt2_wr:{max(2, K // 5)}", f"opt2_sys:{max(2, K // 5)}",
            f"opt2_sys:{K // 2}", "opt3_wr", "opt3_sys", "adaptive"]


def part_a():
    for net, horizon in (("testnet5", 1.0), ("mainnet", 365.0)):
        w, _, _ = get_population(net)
        lam = BLOCKS_PER_DAY[net]
        print(f"\n=== A. {net}: {len(w)} miners, {lam * 7:.1f} pool blocks a week, "
              f"largest {w[0] * 100:.1f}%, median {np.median(w) * 100:.4f}% ===")
        print(f" {SIZE_NOTE}" if net == "mainnet" else
              " shares are of pool hashrate; S21 and S19 here mean 0.02% and 0.0095% of the pool")
        for K in (CAP_OLD, CAP_NEW):
            print(f"\n cap {K}: mean days between payouts by pool share "
                  f"(with no cap: {1 / lam:.2f} days)")
            print(f"  {'scheme':38s}{'N+M':>7s}{'prize%':>8s}{'exact':>6s}"
                  + "".join(f"{size_label(x):>11s}" for x in SIZES)
                  + f"{'raffle var':>11s}{'paid>=50%':>10s}")
            for nm in schemes(K):
                r = fairness_row(w, K, nm, lam, horizon)
                print(f"  {label(nm):38s}{r['N']:>3d}+{r['M']:<3d}"
                      f"{r['prize'] * 100:8.2f}{r['assured']:6d}"
                      + "".join(f"{x:11.1f}" for x in r["wait"])
                      + f"{r['tot_var']:11.5f}{r['paid_half'] * 100:9.1f}%")
        print(f"\n cap sweep, option 2 adaptive, {net}")
        print(f"  {'cap':>6s}{'N+M':>10s}{'prize%':>9s}"
              + "".join(f"{size_label(x):>11s}" for x in SIZES) + f"{'paid>=50%':>10s}")
        for K in (11, 13, 14, 19, 25, 60, 85, 100, 250, 500):
            r = fairness_row(w, K, "adaptive", lam, horizon)
            print(f"  {K:6d}{r['N']:>6d}+{r['M']:<3d}{r['prize'] * 100:9.3f}"
                  + "".join(f"{x:11.1f}" for x in r["wait"])
                  + f"{r['paid_half'] * 100:9.1f}%")
    print("\n 'exact' = miners paid in every block; 'raffle var' = sum over miners "
          "of the variance the raffle adds;\n 'paid>=50%' = share of miners with at "
          "least an even chance of one payout in the horizon\n (1 day on testnet5, "
          "365 days on mainnet).")


def part_b():
    print("\n=== B. robustness: raffle variance relative to option 2 adaptive "
          "(= 1.00), 300 random populations per cap ===")
    rng = np.random.default_rng(8)
    for K in (CAP_OLD, CAP_NEW):
        names = ["opt1", f"opt2_sys:{max(2, K // 5)}", f"opt2_sys:{K // 2}",
                 "opt3_wr", "opt3_sys", "adaptive"]
        ratio = {nm: [] for nm in names}
        prize = {nm: [] for nm in names}
        done = 0
        while done < 300:
            n = int(np.exp(rng.uniform(np.log(2 * K), np.log(MINER_LIMIT))))
            if rng.random() < 0.5:
                w = zipf_population(n, rng.uniform(0.5, 1.6))
            else:
                w = np.exp(rng.normal(0, rng.uniform(1.0, 3.5), n))
                w = w / w.sum()
            w = s19_floor(w)            # nobody below one S19 in a 1 EH/s pool
            if len(w) < 2 * K:
                continue
            done += 1
            var = {}
            for nm in names:
                N, M, kind = spec(w, K, nm)
                a = marginals(w, N, M, kind)
                var[nm] = float((a["ex2"] - w ** 2).sum())
                prize[nm].append(a["slot"])
            for nm in names:
                ratio[nm].append(var[nm] / var["adaptive"])
        print(f"\n cap {K}")
        print(f"  {'scheme':38s}{'min':>8s}{'median':>8s}{'p90':>8s}{'max':>10s}"
              f"{'prize>10%':>11s}")
        for nm in names:
            r, p = np.array(ratio[nm]), np.array(prize[nm])
            print(f"  {label(nm):38s}{r.min():8.2f}{np.median(r):8.2f}"
                  f"{np.percentile(r, 90):8.2f}{r.max():10.1f}"
                  f"{(p > 0.10).mean() * 100:10.0f}%")
    print("\n 'prize>10%' = share of populations where one raffle prize exceeds "
          "10% of the block,\n the uncle penalty that grinding has to beat.")


def part_c():
    print("\n=== C. income over a horizon, realised / expected "
          "(Monte Carlo, 40,000 paths) ===")
    rng = np.random.default_rng(3)
    for net, horizon in (("testnet5", 7.0), ("mainnet", 365.0)):
        w, _, _ = get_population(net)
        lam = BLOCKS_PER_DAY[net]
        for x in ((1e-3, S21, S19) if net == "mainnet" else (1e-3, 1e-4)):
            who = {S21: "one S21 (0.02% of the pool)",
                   S19: "one S19 (0.0095% of the pool)"}.get(x, f"miner with {x * 100:g}% of the pool")
            print(f"\n {net}, {horizon:.0f} days, {who}")
            print(f"  {'scheme':30s}{'cap':>5s}{'P(nothing)':>11s}{'p5':>7s}"
                  f"{'median':>8s}{'p95':>7s}{'CV':>7s}")
            for K in (CAP_OLD, CAP_NEW):
                for nm in ("ideal", "opt1", "opt3_sys", "adaptive"):
                    nb = rng.poisson(lam * horizon, 40_000)
                    inc = nb * x
                    if nm != "ideal":
                        N, M, kind = spec(w, K, nm)
                        a = marginals(w, N, M, kind)
                        ws = np.sort(w)[::-1]
                        if not (N > 0 and x >= ws[N - 1]):
                            mp = M * x / a["T"]
                            base, f = math.floor(mp), mp - math.floor(mp)
                            inc = a["slot"] * (nb * base + rng.binomial(nb, f))
                    r = inc / (lam * horizon * x)
                    name = "no cap (ideal)" if nm == "ideal" else label(nm)
                    print(f"  {name:30s}{K:5d}{(inc == 0).mean():11.3f}"
                          f"{np.percentile(r, 5):7.2f}{np.percentile(r, 50):8.2f}"
                          f"{np.percentile(r, 95):7.2f}{r.std():7.2f}")


if __name__ == "__main__":
    part_a()
    part_b()
    part_c()
