#!/usr/bin/env python3
"""Two checks on the recommended rule (option 2 with the adaptive split).

A. Optimality. Any unbiased scheme with at most K outputs has inclusion
   probabilities p_i with sum(p) <= K, and the variance of miner i's payout is
   at least w_i^2 (1/p_i - 1). Minimise that bound numerically and compare
   with what the adaptive rule achieves.
B. Reference implementation. An integer-only version of the rule (the shape
   consensus code would take) is run on noisy share windows; every block must
   pay out exactly the reward in at most K outputs and stay unbiased.
Runtime: about 1 minute."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from scipy.optimize import minimize
from payout_model import (get_population, adaptive_N, marginals, adaptive_payout,
                          CAP_OLD)


def part_a():
    print("=== A. adaptive rule vs a numerical lower bound on raffle variance ===")
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(40):
        n = int(rng.integers(15, 60))
        K = int(rng.integers(4, n - 2))
        w = np.exp(rng.normal(0, rng.uniform(0.8, 2.5), n))
        w /= w.sum()
        N = adaptive_N(w, K)
        a = marginals(w, N, K - N, "sys")
        v = (a["ex2"] - w ** 2).sum()
        r = minimize(lambda p: (w ** 2 * (1 / p - 1)).sum(), np.full(n, K / n),
                     jac=lambda p: -(w ** 2) / p ** 2, method="SLSQP",
                     bounds=[(1e-9, 1)] * n,
                     constraints=[{"type": "ineq", "fun": lambda p: K - p.sum(),
                                   "jac": lambda p: -np.ones(n)}],
                     options={"maxiter": 2000, "ftol": 1e-15})
        worst = max(worst, abs(v - r.fun) / max(r.fun, 1e-18))
    print(f"  40 random populations and caps: largest relative gap between the "
          f"rule and the bound = {worst:.1e}")


def part_b():
    K = CAP_OLD
    print(f"\n=== B. integer reference implementation, cap {K}, noisy windows ===")
    rng = np.random.default_rng(0)
    hr, _, _ = get_population("mainnet_small")
    addrs = [i.to_bytes(4, "big") for i in range(len(hr))]
    reward, blocks, W = 312_500_000, 240_000, 20_000
    o = np.argsort(-hr)
    groups = [("rank 1-4", o[:4]), ("rank 5-12", o[4:12]),
              ("rank 13-40", o[12:40]), ("rank 41+", o[40:])]
    gid = np.zeros(len(hr), int)
    for g, (_, idx) in enumerate(groups):
        gid[idx] = g
    s1 = np.zeros(len(groups))
    s2 = np.zeros(len(groups))
    most = 0
    for b in range(blocks):
        counts = rng.multinomial(W, hr)            # shares in this block's window
        wts = {a: int(c) for a, c in zip(addrs, counts) if c}
        pay = adaptive_payout(wts, reward, K, b.to_bytes(8, "big"))
        assert sum(pay.values()) == reward and len(pay) <= K
        most = max(most, len(pay))
        tot = np.zeros(len(groups))
        for a, v in pay.items():
            tot[gid[int.from_bytes(a, "big")]] += v
        s1 += tot
        s2 += tot ** 2
    for g, (name, idx) in enumerate(groups):
        fair = reward * hr[idx].sum()
        m = s1[g] / blocks
        se = math.sqrt((s2[g] / blocks - m * m) / blocks)
        print(f"  {name:12s} paid / fair share = {m / fair:.4f} +- {se / fair:.4f}")
    print(f"  {len(hr)} miners, {W:,}-share windows, {blocks:,} blocks: every block "
          f"paid exactly the reward, never more than {most} outputs")


if __name__ == "__main__":
    part_a()
    part_b()
