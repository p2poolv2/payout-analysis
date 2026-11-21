#!/usr/bin/env python3
"""Alternative seed: the hash of the previous Bitcoin block instead of the
parent share's hash.

Design tested: seed = prev_blockhash of the template; raffle weights = PPLNS
window frozen at the last share mined on the previous Bitcoin tip. Every
template for one Bitcoin height then has the same payouts.

A. tip choice: with the seed fixed, how far does a payout move when the
   frozen window differs by a few shares?
B. block veto: a pool block's hash is the next seed, so its finder can
   discard a block that seeds a bad raffle.
C. steering: what happens if the window is NOT frozen (the attacker credits
   each new share to whichever of its addresses wins most under the seed).
D. conditional hopping (share-level simulation of both seed designs): mine
   here only while the current raffle pays more than your average.
Mainnet population, 10 s shares. Runtime: about 8 minutes."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, with_attacker, spec, sample, marginals,
                          attacker_X, hop_sim, plant_interval, trim, ATTACKERS,
                          UNCLE_PENALTY, SHARE_SECONDS, CAP_OLD, CAP_NEW, MINER_LIMIT, S19)


def part_a(w0, rng):
    K, W = CAP_OLD, 20_000
    print(f"=== A. Bitcoin-hash seed, cap {K}: payout change when the frozen "
          "window differs by d shares ===")
    print(f"  {'attacker':22s}{'d':>3s}{'payout differs':>16s}{'mean |change| %':>17s}"
          f"{'gain after 10% uncle penalty':>30s}")
    for sname in ("20% in 400 addresses", "5% in 50 addresses", "1.5%, 1 address"):
        w, att = with_attacker(w0, ATTACKERS[sname])
        h = w[att].sum()
        base = rng.multinomial(W, w).astype(float)
        for d in (1, 3):
            diffs = []
            for _ in range(2500):
                c2 = base.copy()
                np.add.at(c2, rng.choice(len(w), d, p=w), 1)
                np.add.at(c2, rng.choice(len(w), d, p=base / base.sum()), -1)
                c2 = np.maximum(c2, 0)
                keys = rng.random((1, len(w)))
                u01 = rng.random(1)
                xs = []
                for c in (base, c2):
                    ww = c / c.sum()
                    xs.append(sample(ww, *spec(ww, K, "adaptive"), 1, rng,
                                     keys=keys, u01=u01)[0, att].sum())
                diffs.append(xs[1] - xs[0])
            dx = np.array(diffs)
            print(f"  {sname:22s}{d:3d}{(np.abs(dx) > 1e-9).mean() * 100:15.1f}%"
                  f"{np.abs(dx).mean() * 100:17.3f}"
                  f"{np.maximum(dx - UNCLE_PENALTY, 0).mean() / h * 100:29.3f}%")


def part_b(w0, rng):
    print("\n=== B. Bitcoin-hash seed: discarding a found block to veto the next "
          "seed ===")
    print("  discarding pays when  pi*(E[X] - X_next) > (1-pi)*X_now + pi*share_s/600"
          "\n  (pi = the pool's share of network hashrate)")
    print(f"\n  {'cap':>4s} {'attacker':22s}{'pool share':>11s}{'blocks vetoed':>15s}"
          f"{'revenue gain':>14s}")
    for K in (CAP_OLD, CAP_NEW):
        for sname in ("20% in 400 addresses", "5% in 50 addresses", "1.5%, 1 address"):
            w, att = with_attacker(w0, ATTACKERS[sname])
            X = attacker_X(w, att, *spec(w, K, "adaptive"), 30_000, rng)
            for pi in (0.0015, 0.35):
                xn, xx = rng.choice(X, 400_000), rng.choice(X, 400_000)
                G = pi * (X.mean() - xx) - (1 - pi) * xn - pi * SHARE_SECONDS / 600
                print(f"  {K:4d} {sname:22s}{pi * 100:10.2f}%"
                      f"{(G > 0).mean() * 100:14.2f}%"
                      f"{np.maximum(G, 0).mean() * 100:13.4f}%", flush=True)
    print("\n  share of pool blocks discarded if every single-address tail miner "
          "plays it")
    print(f"  {'network':10s}{'cap':>4s}{'prize%':>8s}"
          + "".join(f"{f'{s:.0f} s shares':>14s}" for s in (5, 10, 20, 40)))
    for net in ("mainnet", "testnet5"):
        w, _, _ = get_population(net)
        for K in (CAP_OLD, 19, CAP_NEW):
            a = marginals(w, *spec(w, K, "adaptive"))
            tau, tail = a["slot"], w[~a["is_top"]]
            line = f"  {net:10s}{K:4d}{tau * 100:8.2f}"
            for s in (5, 10, 20, 40):
                elig = tail[tail > s / 600]
                line += f"{(elig * (1 - elig / tau) ** 2).sum() * 100:13.2f}%"
            print(line)


def part_c(w_main, rng):
    print("\n=== C. Bitcoin-hash seed WITHOUT a frozen window: steering new "
          "shares onto winning addresses ===")
    # two farms and 998 miners with 1 to 20 S19s each, in a 1 EH/s pool
    tail = S19 * np.round(np.exp(rng.uniform(0.0, np.log(20.0), 998)))
    home = np.concatenate([[(1 - tail.sum()) / 2] * 2, tail])
    pops = {"mainnet": w_main, "mostly small miners": home / home.sum()}
    K = CAP_OLD
    print(f"  {'population':20s}{'attacker':>22s}{'slots won, fair':>17s}"
          f"{'steered':>9s}{'prize%':>8s}{'revenue gain':>14s}")
    for pname, pop in pops.items():
        for a, n_addr in ((0.05, 50), (0.20, 400)):
            honest = trim(pop, MINER_LIMIT - n_addr)      # total stays at 1,000
            res = {}
            for optimise in (False, True):
                r2 = np.random.default_rng(1000 + K)      # same events for both
                runs = [plant_interval(r2, honest, a, K, 20_000, optimise, n_addr)
                        for _ in range(300)]
                res[optimise] = (np.mean([r[0] for r in runs]),
                                 np.mean([r[1] for r in runs]))
            gain = (res[True][0] - res[False][0]) * res[True][1] / a
            who = f"{a * 100:.0f}% in {n_addr} addresses"
            print(f"  {pname:20s}{who:>22s}{res[False][0]:17.2f}"
                  f"{res[True][0]:9.2f}{res[True][1] * 100:8.2f}{gain * 100:13.1f}%",
                  flush=True)
    print("  With the window frozen before the seed is known this is zero by "
          "construction.")


def part_d(w0, rng):
    print("\n=== D. conditional hopping: revenue gain from mining here only while "
          "the current raffle favours you ===")
    print("  calibration, honest miner (should be 0):")
    for mode in ("share", "btc"):
        g, wa = hop_sim(w0, ATTACKERS["20% in 400 addresses"], CAP_OLD, mode, rng,
                        policy="honest")
        print(f"    {'per-share' if mode == 'share' else 'Bitcoin-hash'} seed: "
              f"{g * 100:+.2f}%   (window weight {wa * 100:.1f}%)", flush=True)
    print(f"\n  {'cap':>4s} {'attacker':22s}{'per-share seed':>16s}"
          f"{'Bitcoin-hash seed':>19s}{'same, 2% fee elsewhere':>24s}"
          f"{'weight left':>13s}")
    for K in (CAP_OLD, CAP_NEW):
        names = list(ATTACKERS) if K == CAP_OLD else ["20% in 400 addresses"]
        for sname in names:
            pieces = ATTACKERS[sname]
            tail_single = sname == "1.5%, 1 address"
            stays = (0.0, 0.35) if tail_single else (0.0,)
            n_btc = 200_000 if tail_single else 90_000
            sh = max(hop_sim(w0, pieces, K, "share", rng, stay=st, n_units=160_000)
                     for st in stays)
            bt = max(hop_sim(w0, pieces, K, "btc", rng, stay=st, n_units=n_btc)
                     for st in stays)
            fee = max(hop_sim(w0, pieces, K, "btc", rng, stay=st, cost=0.02,
                              n_units=n_btc) for st in stays)
            print(f"  {K:4d} {sname:22s}{sh[0] * 100:15.2f}%{bt[0] * 100:18.2f}%"
                  f"{fee[0] * 100:23.2f}%{bt[1] * 100:12.1f}%", flush=True)
    print("\n  Bitcoin-hash seed: hopping plus rented hashrate while in the money "
          "(rental priced 5% above fair value)")
    print(f"  {'cap':>4s} {'attacker':22s}{'rent 1x own':>13s}{'rent 3x own':>13s}")
    for sname in ("20% in 400 addresses", "5% in 50 addresses"):
        g1 = hop_sim(w0, ATTACKERS[sname], CAP_OLD, "btc", rng, rent=1.0)[0]
        g3 = hop_sim(w0, ATTACKERS[sname], CAP_OLD, "btc", rng, rent=3.0)[0]
        print(f"  {CAP_OLD:4d} {sname:22s}{g1 * 100:12.2f}%{g3 * 100:12.2f}%",
              flush=True)


if __name__ == "__main__":
    pop, _, _ = get_population("mainnet")
    gen = np.random.default_rng(104)
    part_a(pop, gen)
    part_b(pop, gen)
    part_c(pop, gen)
    part_d(pop, gen)
