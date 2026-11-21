#!/usr/bin/env python3
"""Payout variance as a function of hashrate share, from 0.1% to 30% of the
pool. A miner of each size is inserted into the mainnet (or testnet5)
population and its per-block payout distribution is computed in closed form,
then checked by Monte Carlo. Writes two charts next to this file.
Runtime: about 1 minute."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import (get_population, miner_stats, sample, label,
                          BLOCKS_PER_DAY, CAP_OLD, CAP_NEW, S19, S21, size_label,
                          SIZE_NOTE)

HERE = pathlib.Path(__file__).resolve().parent
CHART_SHARES = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30]   # of the pool
SMALL = [S19, S21]                      # one S19, one S21 (mainnet only)


def lab(x):
    return size_label(x) if x in SMALL else f"{x * 100:.1f}%"
SCHEMES = ["opt1", "adaptive", "opt3_sys", "opt3_wr"]
SHORT = {"opt1": "option 1", "adaptive": "option 2 adaptive",
         "opt3_sys": "option 3 (spaced)", "opt3_wr": "option 3 (indep.)"}


def tables(net, horizon, horizon_name):
    SHARES = (SMALL if net == "mainnet" else []) + CHART_SHARES
    pop, _, _ = get_population(net)
    blocks = BLOCKS_PER_DAY[net] * horizon
    out = {}
    for K in (CAP_OLD, CAP_NEW):
        st = {nm: [miner_stats(pop, x, K, nm) for x in SHARES] for nm in SCHEMES}
        out[K] = st
        print(f"\n--- {net}, cap {K} ---")
        print(" spread of ONE block's payout: standard deviation / mean")
        print(f"  {'share':>7s}{'no cap':>9s}" + "".join(f"{SHORT[n]:>20s}" for n in SCHEMES))
        for i, x in enumerate(SHARES):
            print(f"  {lab(x):>7s}{0.0:9.2f}"
                  + "".join(f"{st[n][i]['cv']:20.2f}" for n in SCHEMES))
        print(f"\n variance of income relative to an uncapped coinbase (1.0 = no "
              f"added variance)")
        print(f"  {'share':>7s}{'no cap':>9s}" + "".join(f"{SHORT[n]:>20s}" for n in SCHEMES))
        for i, x in enumerate(SHARES):
            print(f"  {lab(x):>7s}{1.0:9.1f}"
                  + "".join(f"{st[n][i]['infl']:20.1f}" for n in SCHEMES))
        print(f"\n spread of income over {horizon_name} ({blocks:.0f} pool blocks "
              f"expected): standard deviation / mean, block luck included")
        print(f"  {'share':>7s}{'no cap':>9s}" + "".join(f"{SHORT[n]:>20s}" for n in SCHEMES))
        for i, x in enumerate(SHARES):
            print(f"  {lab(x):>7s}{math.sqrt(1 / blocks) * 100:8.1f}%"
                  + "".join(f"{math.sqrt(st[n][i]['infl'] / blocks) * 100:19.1f}%"
                            for n in SCHEMES))
        print(f"\n option 2 adaptive in detail (N+M shown for the population with "
              f"this miner added)")
        print(f"  {'share':>7s}{'N+M':>8s}{'paid':>8s}{'chance/block':>13s}"
              f"{'payout if paid':>15s}{'sd/block':>10s}{'days between':>13s}"
              f"{'P(none in ' + horizon_name + ')':>22s}")
        lam = BLOCKS_PER_DAY[net]
        for i, x in enumerate(SHARES):
            s = st["adaptive"][i]
            paid = x if s["exact"] else s["prize"]
            print(f"  {lab(x):>7s}{s['N']:>4d}+{s['M']:<3d}"
                  f"{'exactly' if s['exact'] else 'raffle':>8s}"
                  f"{s['p_pay'] * 100:12.1f}%{paid * 100:14.2f}%"
                  f"{s['sd'] * 100:9.2f}%{1 / (lam * s['p_pay']):13.1f}"
                  f"{math.exp(-blocks * s['p_pay']) * 100:21.1f}%")
    return out


def monte_carlo_check():
    print("\n--- Monte Carlo check of the closed forms (mainnet, cap 13, "
          "40,000 blocks) ---")
    pop, _, _ = get_population("mainnet")
    rng = np.random.default_rng(33)
    print(f"  {'share':>7s}{'scheme':>22s}{'sd closed form':>16s}{'sd simulated':>14s}"
          f"{'mean / fair':>13s}")
    for x in (0.001, 0.01, 0.05):
        for nm in ("opt1", "adaptive", "opt3_sys"):
            s = miner_stats(pop, x, CAP_OLD, nm)
            pays = np.concatenate([
                sample(s["w"], s["N"], s["M"], s["kind"], 2000, rng)[:, -1]
                for _ in range(20)])
            print(f"  {lab(x):>7s}{SHORT[nm]:>22s}{s['sd'] * 100:15.3f}%"
                  f"{pays.std() * 100:13.3f}%{pays.mean() / x:13.3f}")


def charts(st_main):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    surface, ink, ink2, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
    colour = {"opt1": "#2a78d6", "adaptive": "#eb6834", "opt3_sys": "#1baf7a"}
    name = {"opt1": "Option 1", "adaptive": "Option 2 adaptive", "opt3_sys": "Option 3"}
    xs = [x * 100 for x in CHART_SHARES]
    blocks = BLOCKS_PER_DAY["mainnet"] * 365

    def frame(fig, axes, title, ylab):
        fig.patch.set_facecolor(surface)
        for ax, K in zip(axes, (CAP_OLD, CAP_NEW)):
            ax.set_facecolor(surface)
            ax.set_xscale("log")
            ax.set_xticks([0.1, 0.3, 1, 3, 10, 30])
            ax.set_xticklabels(["0.1%", "0.3%", "1%", "3%", "10%", "30%"])
            ax.minorticks_off()
            ax.grid(True, axis="y", color=grid, linewidth=1)
            ax.set_axisbelow(True)
            for sp in ("top", "right", "left"):
                ax.spines[sp].set_visible(False)
            ax.spines["bottom"].set_color(grid)
            ax.tick_params(colors=ink2, length=0, labelsize=10)
            ax.set_title(f"Cap of {K} outputs", color=ink, fontsize=12, loc="left")
            ax.set_xlabel("Miner's share of pool hashrate", color=ink2, fontsize=10)
        axes[0].set_ylabel(ylab, color=ink2, fontsize=10)
        fig.suptitle(title, color=ink, fontsize=13, x=0.01, ha="left", y=0.99)

    def lines(ax, K, value, fmt, top, ideal=None):
        ends = {}
        for nm in ("opt1", "adaptive", "opt3_sys"):
            ys = [value(s) for s in st_main[K][nm][len(SMALL):]]
            ends[nm] = ys[0]
            ax.plot(xs, ys, color=colour[nm], linewidth=2, solid_capstyle="round",
                    marker="o", markersize=6, markeredgecolor=surface,
                    markeredgewidth=1.5, label=name[nm], zorder=3)
        # label the left ends, recommended option first; skip a label that
        # would sit on top of one already placed (the legend still names it)
        placed = []
        for nm in ("adaptive", "opt3_sys", "opt1"):
            if all(abs(ends[nm] - y) > 0.07 * top for y in placed):
                ax.annotate(fmt(ends[nm]), (xs[0], ends[nm]),
                            textcoords="offset points", xytext=(8, 5),
                            color=ink, fontsize=9)
                placed.append(ends[nm])
        if ideal is not None:
            ax.plot(xs, [ideal] * len(xs), color="#8a8983", linewidth=2,
                    label="No cap (block luck only)", zorder=2)
        ax.set_ylim(0, top)

    def top_of(value):
        return 1.1 * max(value(s) for K in (CAP_OLD, CAP_NEW)
                         for nm in ("opt1", "adaptive", "opt3_sys")
                         for s in st_main[K][nm][len(SMALL):])

    def yearly(s):
        return math.sqrt(s["infl"] / blocks) * 100

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True, dpi=150)
    frame(fig, axes, "Spread of one block's payout by hashrate share "
          "(standard deviation ÷ mean; 0 = paid exactly)", "Standard deviation ÷ mean")
    for ax, K in zip(axes, (CAP_OLD, CAP_NEW)):
        lines(ax, K, lambda s: s["cv"], lambda v: f"{v:.1f}", top_of(lambda s: s["cv"]))
    axes[1].legend(frameon=False, fontsize=10, labelcolor=ink2, loc="upper right")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(HERE / "spread_per_block.png", facecolor=surface)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True, dpi=150)
    frame(fig, axes, "Spread of one year's income on mainnet by hashrate share "
          "(standard deviation ÷ mean, block luck included)",
          "Standard deviation ÷ mean")
    for ax, K in zip(axes, (CAP_OLD, CAP_NEW)):
        lines(ax, K, yearly, lambda v: f"{v:.0f}%", top_of(yearly),
              ideal=math.sqrt(1 / blocks) * 100)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    axes[1].legend(frameon=False, fontsize=10, labelcolor=ink2, loc="upper right")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(HERE / "spread_per_year_mainnet.png", facecolor=surface)
    print("\ncharts written: spread_per_block.png, spread_per_year_mainnet.png")


if __name__ == "__main__":
    print("Payout variance by hashrate share. A miner of the given size is put "
          "into the population in place\nof its smallest member; the other miners "
          "are scaled down to make room.")
    print(SIZE_NOTE)
    main_stats = tables("mainnet", 365.0, "a year")
    tables("testnet5", 7.0, "a week")
    monte_carlo_check()
    charts(main_stats)
