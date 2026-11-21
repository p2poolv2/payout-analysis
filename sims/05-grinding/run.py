#!/usr/bin/env python3
"""Grinding the raffle seed. A late share still earns 90% as an uncle, so a
miner can (a) mine on whichever recent tip's raffle pays it most ("tip
choice") or (b) sit on its own share to keep a favourable raffle in play
("withholding"). Both cost 10% of a share and pay only when the better raffle
is worth more than 10% of the block to that miner. Mainnet population.
Runtime: about 6 minutes."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, with_attacker, spec, marginals, label,
                          attacker_X, stale_tip_gain, withhold_gain, ATTACKERS,
                          UNCLE_PENALTY, CAP_OLD, CAP_NEW)

SAMPLES = 30_000


def draws(w0, pieces, K, nm, rng):
    w, att = with_attacker(w0, pieces)
    N, M, kind = spec(w, K, nm)
    X = attacker_X(w, att, N, M, kind, SAMPLES, rng)
    return X, marginals(w, N, M, kind)["slot"]


def main():
    w0, _, _ = get_population("mainnet")
    rng = np.random.default_rng(5)
    print("Relative revenue gain for the attacker. 'tip choice' lets it pick "
          "among the current tip and\n1 or 3 older ones; a share on an older tip "
          f"loses {UNCLE_PENALTY * 100:.0f}% of its value.")
    print("\n=== A. all options at caps 13 and 60 ===")
    keep = {}
    for K in (CAP_OLD, CAP_NEW):
        print(f"\n cap {K}")
        print(f"  {'attacker':22s}{'scheme':30s}{'prize%':>8s}{'tip choice (1)':>16s}"
              f"{'tip choice (3)':>16s}{'withholding':>13s}")
        for sname, pieces in ATTACKERS.items():
            for nm in ("opt1", f"opt2_sys:{K // 2}", "opt3_sys", "adaptive"):
                X, prize = draws(w0, pieces, K, nm, rng)
                keep[K, sname, nm] = X
                print(f"  {sname:22s}{label(nm):30s}{prize * 100:8.2f}"
                      f"{stale_tip_gain(X, 1, UNCLE_PENALTY, rng) * 100:15.2f}%"
                      f"{stale_tip_gain(X, 3, UNCLE_PENALTY, rng) * 100:15.2f}%"
                      f"{withhold_gain(X, sum(pieces), UNCLE_PENALTY, rng) * 100:12.2f}%",
                      flush=True)

    print(f"\n=== A2. a small miner on one address, in the raffle under every "
          f"option (0.5% of the pool, cap {CAP_OLD}) ===")
    print(f"  {'scheme':30s}{'prize%':>8s}{'tip choice (3)':>16s}{'withholding':>13s}")
    for nm in ("opt1", f"opt2_sys:{CAP_OLD // 2}", "opt3_sys", "adaptive"):
        X, prize = draws(w0, [0.005], CAP_OLD, nm, rng)
        print(f"  {label(nm):30s}{prize * 100:8.2f}"
              f"{stale_tip_gain(X, 3, UNCLE_PENALTY, rng) * 100:15.2f}%"
              f"{withhold_gain(X, 0.005, UNCLE_PENALTY, rng) * 100:12.2f}%",
              flush=True)

    print("\n=== B. option 2 adaptive across caps ===")
    print(f"  {'cap':>4s}{'attacker':>24s}{'prize%':>8s}{'extra wins needed':>19s}"
          f"{'tip choice (3)':>16s}{'withholding':>13s}")
    for K in (11, 13, 14, 16, 19, 25, 60, 100):
        for sname in ("20% in 400 addresses", "5% in 50 addresses"):
            pieces = ATTACKERS[sname]
            if (K, sname, "adaptive") in keep:
                X = keep[K, sname, "adaptive"]
                w, _ = with_attacker(w0, pieces)
                N, M, kind = spec(w, K, "adaptive")
                prize = marginals(w, N, M, kind)["slot"]
            else:
                X, prize = draws(w0, pieces, K, "adaptive", rng)
            need = int(np.floor(UNCLE_PENALTY / prize)) + 1
            print(f"  {K:4d}{sname:>24s}{prize * 100:8.2f}{need:19d}"
                  f"{stale_tip_gain(X, 3, UNCLE_PENALTY, rng) * 100:15.2f}%"
                  f"{withhold_gain(X, sum(pieces), UNCLE_PENALTY, rng) * 100:12.2f}%",
                  flush=True)

    print(f"\n=== C. effect of the uncle penalty at cap {CAP_OLD} "
          "(tip choice among 3 older tips + withholding) ===")
    print(f"  {'attacker':22s}{'scheme':30s}"
          + "".join(f"{f'penalty {int(p * 100)}%':>20s}" for p in (0.10, 0.15, 0.20)))
    for sname in ("20% in 400 addresses", "5% in 50 addresses"):
        for nm in ("opt1", "adaptive"):
            X = keep[CAP_OLD, sname, nm]
            cells = []
            for pen in (0.10, 0.15, 0.20):
                a = stale_tip_gain(X, 3, pen, rng)
                b = withhold_gain(X, sum(ATTACKERS[sname]), pen, rng)
                cells.append(f"{a * 100:.2f}% + {b * 100:.2f}%")
            print(f"  {sname:22s}{label(nm):30s}" + "".join(f"{c:>20s}" for c in cells))


if __name__ == "__main__":
    main()
