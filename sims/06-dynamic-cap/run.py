#!/usr/bin/env python3
"""Option 4: the block finder uses whatever coinbase size its hardware takes
(13 outputs on old firmware, 60 on newer). Hardware cannot be verified, so a
miner that can use the large size can also choose the small one after seeing
the raffle seed. This measures what that choice is worth, who pays for it,
and what honest use of the large size buys. Mainnet population.
Runtime: about 4 minutes."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, with_attacker, spec, sample, marginals,
                          top_mask, miner_stats, k_choice_gain, ATTACKERS,
                          BLOCKS_PER_DAY, UNCLE_PENALTY, CAP_OLD, CAP_NEW, SIZES,
                          size_label, SIZE_NOTE)

KS, KB, OLDER_TIPS = CAP_OLD, CAP_NEW, 3


def part_a(w0, rng):
    print(f"=== A. gain for a miner that picks {KS} or {KB} outputs per template "
          "(option 2 adaptive) ===")
    print("relative revenue gain; 'tip choice' = also choosing among the 3 "
          "previous tips at a 10% uncle penalty")
    print(f"  {'attacker':22s}{'size choice only':>18s}"
          f"{f'tip choice only, {KS}':>22s}{'both together':>15s}")
    for name, pieces in ATTACKERS.items():
        w, att = with_attacker(w0, pieces)
        h, n = sum(pieces), len(w)
        sp = {K: spec(w, K, "adaptive") for K in (KS, KB)}
        acc = np.zeros(3)
        B, chunk, done = 24_000, 1500, 0
        while done < B:
            X = {}
            for j in range(OLDER_TIPS + 1):          # current tip and older tips
                keys = rng.random((chunk, n))
                u01 = rng.random(chunk)
                for K in (KS, KB):
                    X[j, K] = sample(w, *sp[K], chunk, rng,
                                     keys=keys, u01=u01)[:, att].sum(1)
            size = np.maximum(X[0, KS], X[0, KB])
            older_s = np.max([X[j, KS] for j in range(1, OLDER_TIPS + 1)], axis=0)
            older_b = np.max([np.maximum(X[j, KS], X[j, KB])
                              for j in range(1, OLDER_TIPS + 1)], axis=0)
            tip = np.maximum(X[0, KS], older_s - UNCLE_PENALTY)
            both = np.maximum(size, older_b - UNCLE_PENALTY)
            acc += [size.sum(), tip.sum(), both.sum()]
            done += chunk
        g = acc / B - h
        print(f"  {name:22s}{g[0] * 100:17.2f}%{g[1] * 100:21.2f}%{g[2] * 100:14.2f}%",
              flush=True)
    print("\n same size choice with option 1 as the base rule:")
    for name in ("20% in 400 addresses", "5% in 50 addresses", "1.5%, 1 address"):
        w, att = with_attacker(w0, ATTACKERS[name])
        print(f"  {name:22s}{k_choice_gain(w, att, 'opt1', [KS, KB], rng) * 100:17.2f}%",
              flush=True)


def part_b(w0, rng):
    print("\n=== B. who pays: payouts on the blocks the choosing miner finds ===")
    for name in ("1.5%, 1 address", "20% in 400 addresses"):
        w, att = with_attacker(w0, ATTACKERS[name])
        h, n = w[att].sum(), len(w)
        sp = {K: spec(w, K, "adaptive") for K in (KS, KB)}
        ts, tb = top_mask(w, sp[KS][0]), top_mask(w, sp[KB][0])
        groups = {"paid exactly at both sizes": ts & tb & ~att,
                  f"exact at {KB}, raffled at {KS}": tb & ~ts & ~att,
                  "raffled at both sizes": ~tb & ~att}
        tot = {g: 0.0 for g in groups}
        a_tot, small = 0.0, 0
        B, chunk, done = 60_000, 1500, 0
        while done < B:
            keys = rng.random((chunk, n))
            u01 = rng.random(chunk)
            P = {K: sample(w, *sp[K], chunk, rng, keys=keys, u01=u01)
                 for K in (KS, KB)}
            pick = P[KS][:, att].sum(1) > P[KB][:, att].sum(1)
            chosen = np.where(pick[:, None], P[KS], P[KB])
            assert np.allclose(chosen.sum(1), 1.0)
            a_tot += chosen[:, att].sum()
            small += pick.sum()
            for g, m in groups.items():
                tot[g] += chosen[:, m].sum()
            done += chunk
        print(f"\n chooser: {name} (uses the small size on {small / B * 100:.1f}% "
              "of the blocks it finds)")
        print(f"  {'group':30s}{'fair share':>12s}{'collects':>10s}{'change':>9s}")
        print(f"  {'the miner choosing':30s}{h * 100:11.2f}%{a_tot / B * 100:9.2f}%"
              f"{(a_tot / B - h) * 100:+9.2f}")
        for g, m in groups.items():
            fair = w[m].sum()
            print(f"  {g:30s}{fair * 100:11.2f}%{tot[g] / B * 100:9.2f}%"
                  f"{(tot[g] / B - fair) * 100:+9.2f}")
        print(f"  {'total':30s}{100.0:11.2f}%"
              f"{(a_tot + sum(tot.values())) / B * 100:9.2f}%")


def part_c(w0):
    lam = BLOCKS_PER_DAY["mainnet"]
    print(f"\n=== C. honest use: mean days between payouts when a share of blocks "
          f"carries {KB} outputs ===")
    st = {}
    for K in (KS, KB):
        st[K] = [(q["p_pay"], q["infl"])
                 for q in (miner_stats(w0, x, K, "adaptive") for x in SIZES)]
    print(f"  {f'blocks at {KB} outputs':>22s}"
          + "".join(f"{size_label(x):>11s}" for x in SIZES)
          + f"{'variance vs no cap: 0.1% of pool':>35s}{'one S19':>10s}")
    for share in (0.0, 0.2, 0.5, 1.0):
        mix = [1 / (lam * ((1 - share) * p1 + share * p2))
               for (p1, _), (p2, _) in zip(st[KS], st[KB])]
        infl = [(1 - share) * st[KS][i][1] + share * st[KB][i][1] for i in (1, 3)]
        print(f"  {share * 100:21.0f}%" + "".join(f"{x:11.1f}" for x in mix)
              + f"{infl[0]:34.1f}x{infl[1]:9.0f}x")
    print(f"  {SIZE_NOTE}")


if __name__ == "__main__":
    pop, _, _ = get_population("mainnet")
    gen = np.random.default_rng(51)
    part_a(pop, gen)
    part_b(pop, gen)
    part_c(pop)
