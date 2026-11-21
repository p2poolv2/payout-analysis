#!/usr/bin/env python3
"""Is the expected payout proportional to work? Monte Carlo of every scheme
variant on one population, reporting paid / fair share by miner group.
A value of 1.000 means unbiased. Runtime: about 30 s."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import get_population, spec, sample, label, CAP_OLD

K, M = CAP_OLD, 6            # fixed-split variants use 7 top + 6 raffle slots
BLOCKS, CHUNK = 400_000, 2000


def main():
    w, _, _ = get_population("mainnet_small")     # 168 miners, same shape
    rng = np.random.default_rng(1)
    names = ["opt1", f"opt2_wr:{M}", f"opt2_sys:{M}", f"opt2_wor_equal:{M}",
             f"opt2_wor_prorata:{M}", f"opt2_wor_included:{M}", "opt3_wr",
             "opt3_sys", "adaptive"]
    order = np.argsort(-w)
    groups = {"rank 1-4": order[:4], "rank 5-12": order[4:12],
              "rank 13-40": order[12:40], "rank 41+": order[40:]}
    print(f"expected payout / fair share, {len(w)} miners, cap {K}, "
          f"{BLOCKS:,} blocks (+- one standard error)")
    print(f"{'scheme':40s}" + "".join(f"{g:>16s}" for g in groups))
    for nm in names:
        N, Mm, kind = spec(w, K, nm)
        g1 = {g: 0.0 for g in groups}
        g2 = {g: 0.0 for g in groups}
        for _ in range(BLOCKS // CHUNK):
            pay = sample(w, N, Mm, kind, CHUNK, rng)
            for g, i in groups.items():
                t = pay[:, i].sum(1)
                g1[g] += t.sum()
                g2[g] += (t ** 2).sum()
        cells = []
        for g, i in groups.items():
            m = g1[g] / BLOCKS
            se = math.sqrt(max(g2[g] / BLOCKS - m * m, 0) / BLOCKS)
            cells.append(f"{m / w[i].sum():9.3f}+-{se / w[i].sum():.3f}")
        print(f"{label(nm):40s}" + "".join(f"{c:>16s}" for c in cells))


if __name__ == "__main__":
    main()
