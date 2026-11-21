#!/usr/bin/env python3
"""Does splitting hashrate across addresses (sock puppets) raise a miner's
expected payout or how often it is paid? And what does a large miner's split
do to everyone else? Part A uses the 168-miner "mainnet_small"
population (every large miner, one in seven of the rest) so that 150,000 blocks per case stay affordable; part B uses the
full population in closed form. Cap 13. Runtime: about 6 minutes."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, with_attacker, spec, marginals, mc,
                          label, CAP_OLD, CAP_NEW)

K, M = CAP_OLD, 6


def part_a():
    w0, _, _ = get_population("mainnet_small")    # 168 honest miners, for speed
    rng = np.random.default_rng(4)
    names = ["opt1", f"opt2_wr:{M}", f"opt2_sys:{M}", f"opt2_wor_equal:{M}",
             f"opt2_wor_prorata:{M}", f"opt2_wor_included:{M}", "opt3_wr",
             "opt3_sys", "adaptive"]
    scen = {
        "0.5% as 1 address": [0.005],
        "0.5% as 10 addresses": [0.0005] * 10,
        "0.5% as 50 addresses": [0.0001] * 50,
        "3% as 1 address": [0.03],
        "3% as 30 addresses": [0.001] * 30,
        "20% as 1 address": [0.20],
        "20% as 20 addresses": [0.01] * 20,
        "20% as 400 addresses": [0.0005] * 400,
    }
    print(f"=== A. the same hashrate held in one address or many, cap {K}, "
          f"{len(w0)} honest miners, 150,000 blocks per case ===")
    print("EV/fair = expected payout / fair share (1.000 = splitting gains "
          "nothing);\nP(paid) = chance of any payout in a block; CV = spread of "
          "the per-block total.")
    for sname, pieces in scen.items():
        w, att = with_attacker(w0, pieces)
        h = sum(pieces)
        print(f"\n miner: {sname}")
        print(f"  {'scheme':40s}{'EV/fair':>9s}{'+-':>7s}{'P(paid)':>9s}{'CV':>7s}")
        for nm in names:
            N, Mm, kind = spec(w, K, nm)
            B = 150_000
            r = mc(w, N, Mm, kind, B, rng, att=att)
            x = r["att"][:, 0]
            print(f"  {label(nm):40s}{x.mean() / h:9.3f}"
                  f"{x.std() / math.sqrt(B) / h:7.3f}"
                  f"{r['att'][:, 1].mean():9.3f}{x.std() / x.mean():7.2f}",
                  flush=True)


def part_b():
    w0, _, _ = get_population("mainnet")
    print("\n=== B. crowd-out: what a 30% miner's split does to honest miners ===")
    print(f"  {'cap':>4s} {'scheme':30s}{'30% miner as':>15s}{'prize%':>8s}"
          f"{'honest paid exactly':>21s}{'honest raffle variance':>24s}")
    for cap in (CAP_OLD, CAP_NEW):
        for nm in ("opt1", f"opt2_sys:{cap // 2}", "opt3_sys", "adaptive"):
            for lab, pieces in (("1 address", [0.30]),
                                (f"{cap} addresses", [0.30 / cap] * cap),
                                ("500 addresses", [0.30 / 500] * 500)):
                w, att = with_attacker(w0, pieces)
                N, Mm, kind = spec(w, cap, nm)
                a = marginals(w, N, Mm, kind)
                hv = float((a["ex2"] - w ** 2)[~att].sum())
                ha = int((a["p_pay"][~att] > 0.999999).sum())
                print(f"  {cap:4d} {label(nm):30s}{lab:>15s}{a['slot'] * 100:8.2f}"
                      f"{ha:21d}{hv:24.5f}")


if __name__ == "__main__":
    part_a()
    part_b()
