#!/usr/bin/env python3
"""From firmware byte caps to an output count.

Source: "Bitmain firmware coinbase output limits" (rkuester), which measures
the stratum job-message cap on three bmminer builds (3,072 or 5,120 bytes)
and tabulates how many outputs of each script type fit with 0 and with 12
merkle branches, before a witness commitment.
https://gist.github.com/rkuester/3a9378ea3a3fef898b732b294146afeb

This script (A) backs out the byte budget those tables imply, (B) recomputes
the counts next to a 47-byte witness commitment for 11-14 merkle branches,
and (C) runs the payout model at the resulting caps.
Runtime: about 2 minutes."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, with_attacker, spec, fairness_row,
                          attacker_X, stale_tip_gain, withhold_gain, ATTACKERS,
                          BLOCKS_PER_DAY, UNCLE_PENALTY, SCRIPT_SIZE,
                          SIZES, size_label, SIZE_NOTE)

# outputs that fit with 0 merkle branches, as tabulated in the report
REPORT = {3072: dict(P2WPKH=34, P2SH=33, P2PKH=31, P2TR=25),
          5120: dict(P2WPKH=100, P2SH=97, P2PKH=91, P2TR=72)}
WITNESS_COMMITMENT = 47       # 8 value + 1 length + 38 script
BRANCH = 32


def budget(row):
    """Range of output-byte budgets consistent with one row of the report."""
    lo = max(n * SCRIPT_SIZE[k] for k, n in row.items())
    hi = min((n + 1) * SCRIPT_SIZE[k] for k, n in row.items())
    return lo, hi


def part_a():
    b1, b2 = budget(REPORT[3072]), budget(REPORT[5120])
    lo = max(b1[0], b2[0] - 2048)
    hi = min(b1[1], b2[1] - 2048)
    print("=== A. output-byte budget implied by the report (0 merkle branches, "
          "before the witness commitment) ===")
    print(f"  3,072-byte cap: {lo} to {hi - 1} bytes    5,120-byte cap: "
          f"{lo + 2048} to {hi + 2047} bytes")
    print("  (the two caps differ by exactly 2,048 bytes, which narrows the range; "
          "the low end is used below)")
    return lo


def part_b(base):
    print("\n=== B. miner outputs that fit beside a witness commitment ===")
    print(f"  {'job cap':>8s}{'branches':>9s}{'max txs':>9s}"
          f"{'P2WPKH':>8s}{'spare':>7s}{'P2TR':>6s}{'spare':>7s}"
          f"{'spare at one fewer P2TR':>25s}")
    for cap, b0 in ((3072, base), (5120, base + 2048)):
        for br in (11, 12, 13, 14):
            b = b0 - WITNESS_COMMITMENT - BRANCH * br
            kw, kt = b // 31, b // 43
            print(f"  {cap:8,d}{br:9d}{2 ** br:9,d}{kw:8d}{b - 31 * kw:7d}"
                  f"{kt:6d}{b - 43 * kt:7d}{b - 43 * (kt - 1):25d}")
    print("  'spare' = bytes left under the cap. The report notes a job right at "
          "the boundary split in a\n  measured run, and the job id and pool URL also "
          "count against the cap, so thin margins are risky.")
    print("\n  testnet5 blocks are nearly empty (few merkle branches). Outputs "
          "needed there to put the same\n  byte load on a 3,072-byte build as 13 "
          "taproot-size outputs with 13 branches on mainnet:")
    load = 13 * 43 + BRANCH * 13
    print("   " + ", ".join(f"{br} branches: {(load - BRANCH * br) // 43}"
                            for br in (0, 2, 4, 6)))


def part_c():
    w0, _, _ = get_population("mainnet")
    lam = BLOCKS_PER_DAY["mainnet"]
    rng = np.random.default_rng(43)
    print("\n=== C. the model at those caps (mainnet, option 2 adaptive) ===")
    print(f"  {'cap':>4s}{'meaning':>34s}{'N+M':>8s}{'prize%':>8s}"
          + "".join(f"{size_label(x):>9s}" for x in SIZES) +
          f"{'20% in 400: tip + hold':>25s}{'5% in 50: tip + hold':>23s}")
    meaning = {13: "taproot size, old builds", 14: "taproot size, <= 8,192 txs",
               19: "P2WPKH only, old builds", 20: "P2WPKH only, <= 4,096 txs",
               60: "taproot size, new builds", 61: "taproot size, <= 8,192 txs",
               85: "P2WPKH only, new builds", 86: "P2WPKH only, <= 4,096 txs"}
    for K in (13, 14, 19, 20, 60, 61, 85, 86):
        r = fairness_row(w0, K, "adaptive", lam, 365.0)
        g = []
        for sname in ("20% in 400 addresses", "5% in 50 addresses"):
            w, att = with_attacker(w0, ATTACKERS[sname])
            X = attacker_X(w, att, *spec(w, K, "adaptive"), 30_000, rng)
            g.append(f"{stale_tip_gain(X, 3, UNCLE_PENALTY, rng) * 100:.2f}% + "
                     f"{withhold_gain(X, sum(ATTACKERS[sname]), UNCLE_PENALTY, rng) * 100:.2f}%")
        print(f"  {K:4d}{meaning[K]:>34s}{r['N']:>4d}+{r['M']:<3d}{r['prize'] * 100:8.2f}"
              + "".join(f"{x:9.1f}" for x in r["wait"])
              + f"{g[0]:>25s}{g[1]:>23s}", flush=True)
    print("  waits are mean days between payouts for a miner with that share of "
          f"the pool (no cap: {1 / lam:.1f} days)")
    print(f"  {SIZE_NOTE}")


if __name__ == "__main__":
    part_b(part_a())
    part_c()
