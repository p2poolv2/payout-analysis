#!/usr/bin/env python3
"""Small miners: share-finding luck stacked with the raffle.

The share chain has one global difficulty, so a small miner finds a share only
now and then. Under plain PPLNS each share it does find is paid a little by
every block the pool finds while the share is in the 2-week window. With a
capped coinbase and a raffle, that share instead buys a small chance of a
large prize in each of those blocks.

This follows single miners through time with all three sources of luck:
their own shares (Poisson), pool blocks (Poisson) and the raffle (win with
probability weight / prize). The uncapped coinbase is simulated on the same
shares and blocks for comparison. Prize sizes come from option 2 with the
adaptive split on the synthetic populations. Runtime: about 4 minutes."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, spec, marginals, BLOCKS_PER_DAY,
                          SHARE_SECONDS, CAP_OLD, CAP_NEW, S19, S21, REWARD_BTC,
                          size_label, SIZE_NOTE)

WINDOW_DAYS = 14.0
SHARES_PER_DAY = 86400.0 / SHARE_SECONDS
W = WINDOW_DAYS * SHARES_PER_DAY            # 120,960 shares in the window
REWARD_SATS = round(REWARD_BTC * 1e8)       # subsidy + average fees
SHARES = {"mainnet": (1e-3, S21, S19),      # share of POOL hashrate
          "testnet5": (1e-3, 1e-4, 1e-5)}
PATHS = 60_000


def prize(net, K):
    w, _, _ = get_population(net)
    return marginals(w, *spec(w, K, "adaptive"))["slot"]


def one_share(net):
    lam = BLOCKS_PER_DAY[net]
    blocks = lam * WINDOW_DAYS
    print(f"\n=== A. {net}: what ONE share is worth ({blocks:.0f} pool blocks "
          f"expected while it is in the window) ===")
    ev = blocks * REWARD_SATS / W
    print(f"  expected payout from the share, any scheme: {ev:,.0f} sats")
    print(f"  {'scheme':24s}{'chance it ever pays':>21s}{'amount per paying block':>26s}")
    print(f"  {'no cap':24s}{(1 - math.exp(-blocks)) * 100:20.1f}%"
          f"{REWARD_SATS / W:21,.0f} sats")
    for K in (CAP_OLD, CAP_NEW):
        tau = prize(net, K)
        p = (1 / W) / tau                    # chance per block
        ever = 1 - math.exp(-blocks * p)
        print(f"  {f'raffle, cap {K}':24s}{ever * 100:20.3f}%"
              f"{tau * REWARD_SATS:21,.0f} sats")


def over_time(net, horizon):
    lam = BLOCKS_PER_DAY[net]
    rng = np.random.default_rng(12)
    taus = {K: prize(net, K) for K in (CAP_OLD, CAP_NEW)}
    print(f"\n=== B. {net}: a miner followed for {horizon:.0f} days "
          f"({lam * horizon:.0f} pool blocks expected), {PATHS:,} paths ===")
    print("  per scheme: payouts received / chance of none / spread of total "
          "income (sd / mean) / paid vs fair")
    print(f"  {'share':>8s}{'shares in window':>18s}{'window empty':>14s}"
          f"{'no cap':>32s}{f'raffle, cap {CAP_OLD}':>32s}{f'raffle, cap {CAP_NEW}':>32s}")
    for x in SHARES[net]:
        rate = x * SHARES_PER_DAY
        n = PATHS
        inc = {k: np.zeros(n) for k in ("none", CAP_OLD, CAP_NEW)}
        cnt = {k: np.zeros(n) for k in ("none", CAP_OLD, CAP_NEW)}
        for i in range(n):
            tb = rng.uniform(0, horizon, rng.poisson(lam * horizon))
            ts = np.sort(rng.uniform(-WINDOW_DAYS, horizon,
                                     rng.poisson(rate * (horizon + WINDOW_DAYS))))
            c = np.searchsorted(ts, tb) - np.searchsorted(ts, tb - WINDOW_DAYS)
            wgt = c / W
            inc["none"][i] = wgt.sum()
            cnt["none"][i] = (c > 0).sum()
            for K, tau in taus.items():
                exact = wgt >= tau
                win = rng.random(len(tb)) < wgt / tau
                pay = np.where(exact, wgt, np.where(win, tau, 0.0))
                inc[K][i] = pay.sum()
                cnt[K][i] = (pay > 0).sum()
        fair = x * lam * horizon
        cells = []
        for k in ("none", CAP_OLD, CAP_NEW):
            v = inc[k]
            cells.append(f"{cnt[k].mean():9.2f} /{(cnt[k] == 0).mean() * 100:5.1f}% /"
                         f"{v.std() / v.mean() * 100:6.0f}% /{v.mean() / fair:5.2f}")
        print(f"  {size_label(x):>8s}{x * W:18.2f}{math.exp(-x * W) * 100:13.1f}%"
              + "".join(f"{c:>32s}" for c in cells), flush=True)


if __name__ == "__main__":
    print(f"PPLNS window: {WINDOW_DAYS:.0f} days = {W:,.0f} shares at "
          f"{SHARE_SECONDS:.0f} s; block reward {REWARD_SATS / 1e8} BTC")
    print(SIZE_NOTE)
    for network in ("mainnet", "testnet5"):
        print(f"prize, {network}: cap {CAP_OLD}: {prize(network, CAP_OLD) * 100:.2f}% "
              f"of the block, cap {CAP_NEW}: {prize(network, CAP_NEW) * 100:.2f}%")
    one_share("mainnet")
    one_share("testnet5")
    over_time("mainnet", 365.0)
    over_time("testnet5", 30.0)
