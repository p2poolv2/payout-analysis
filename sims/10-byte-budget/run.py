#!/usr/bin/env python3
"""Count cap or byte budget? The firmware limit is in bytes and payout scripts
differ in size (31 to 43 bytes), so a count cap has to assume the largest
script for every output. This compares a count of 13 taproot-size outputs
with a byte budget of the same size (559 bytes) under several script mixes.

Byte-budget rule ("per-byte"): pay a miner exactly while weight / output size
exceeds remaining weight / remaining bytes; raffle the remaining bytes, with
win probability proportional to weight / size and a prize proportional to
size, so the expected payout is still the miner's weight. The tail is drawn
in (size, hash(seed || address)) order so the bytes used never exceed the
budget. "Equal-prize" is the same budget with one prize for every script
type. Mainnet population. Runtime: about 20 s."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, adaptive_N, marginals, byte_rule,
                          byte_draw, BLOCKS_PER_DAY, CAP_OLD)

BUDGET = CAP_OLD * 43          # 559 bytes


def wait(w, s, exact, p, lam, x, size, per_byte):
    """Mean days between payouts for a hypothetical tail miner."""
    t = ~exact
    if per_byte:
        thr = ((w[t] / s[t]) / p[t]).max()      # weight per byte at the threshold
        return 1 / (lam * min(1.0, (x / size) / thr))
    thr = (w[t] / p[t]).max()
    return 1 / (lam * min(1.0, x / thr))


def sizes(rng, w, name):
    s = np.full(len(w), 31.0)
    order = np.argsort(-w)
    if name == "top 10 on 43-byte multisig, rest P2WPKH":
        s[order[:10]] = 43
    elif name == "30% of miners on taproot, rest P2WPKH":
        s[rng.random(len(w)) < 0.30] = 43
    elif name == "60% P2WPKH, 15% P2SH, 10% P2PKH, 15% taproot":
        r = rng.random(len(w))
        s[r > 0.60] = 32
        s[r > 0.75] = 34
        s[r > 0.85] = 43
    elif name == "everyone on taproot":
        s[:] = 43
    return s


def main():
    rng = np.random.default_rng(77)
    w, _, _ = get_population("mainnet")
    lam = BLOCKS_PER_DAY["mainnet"]
    N = adaptive_N(w, CAP_OLD)
    a = marginals(w, N, CAP_OLD - N, "sys")
    print(f"count cap {CAP_OLD} (every output assumed taproot size): prize "
          f"{a['slot'] * 100:.2f}% of the block, a 0.1% miner is paid every "
          f"{1 / (lam * 1e-3 / a['slot']):.0f} days whatever scripts are in use")
    print(f"\nbyte budget {BUDGET} bytes: mean days between payouts for a 0.1% "
          "miner, by its own script type")
    print(f"  {'script mix':46s}{'rule':>12s}{'exact':>6s}{'winners':>8s}"
          f"{'P2WPKH':>8s}{'taproot':>9s}{'max bytes used':>16s}{'paid/fair':>10s}")
    for nm in ("everyone on P2WPKH", "top 10 on 43-byte multisig, rest P2WPKH",
               "30% of miners on taproot, rest P2WPKH",
               "60% P2WPKH, 15% P2SH, 10% P2PKH, 15% taproot",
               "everyone on taproot"):
        s = sizes(rng, w, nm)
        for lab, per_byte in (("per-byte", True), ("equal-prize", False)):
            ex, p, prize = byte_rule(w, s, BUDGET, per_byte)
            pay, used = byte_draw(w, s, ex, p, prize, 20_000, rng)
            t = ~ex
            big = t & (s == 43)
            grp = big if big.any() else t
            bias = pay[:, grp].sum() / (20_000 * w[grp].sum())
            assert used.max() <= BUDGET, (nm, lab, used.max())
            print(f"  {nm:46s}{lab:>12s}{ex.sum():6d}{p[t].sum():8.1f}"
                  f"{wait(w, s, ex, p, lam, 1e-3, 31, per_byte):8.0f}"
                  f"{wait(w, s, ex, p, lam, 1e-3, 43, per_byte):9.0f}"
                  f"{used.max():16.0f}{bias:10.3f}")
    print("  'paid/fair' is for tail miners on 43-byte scripts where there are "
          "any (1.000 = unbiased);\n  20,000 simulated blocks per row; the run "
          "aborts if any block uses more than the budget.")


if __name__ == "__main__":
    main()
