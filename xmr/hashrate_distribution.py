# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy", "matplotlib"]
# ///
"""Distribution of miner hashrate on the Monero P2Pool sidechains.

Fetches the recent share history of each P2Pool sidechain (main, mini, nano)
from the p2pool.observer API, estimates each miner's hashrate, prints summary
statistics, fits candidate distributions and plots the result.

Hashrate estimate: a share of difficulty D represents D expected hashes, so a
miner's hashrate is the sum of the difficulty of their shares (uncles included,
since an uncle is real work) divided by the length of the period. Miners are
identified by payout address.

Why the fit is done on share counts. The per-miner estimate is noisy for small
miners (k shares give a relative error of about 1/sqrt(k)), and a miner whose
hashrate is well below share_difficulty / period finds no share and is
invisible. Fitting a distribution directly to the estimates rewards models
that pile mass on the detection floor. Instead each candidate is fitted to the
observed share counts with the measurement built in:

    true hashrate h ~ candidate distribution
    shares k | h    ~ Poisson(h * period / mean_share_difficulty)
    only miners with k >= 1 are observed

and the candidates are compared by AIC on that likelihood, with a chi-square
test of observed against predicted share-count histograms as an absolute check.

Usage:
    uv run xmr/hashrate_distribution.py                 # all pools, last 24 h
    uv run xmr/hashrate_distribution.py --hours 72 --pools mini nano
"""

import argparse
import csv
import json
import math
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import optimize, stats
from scipy.special import gammaln

POOLS = {
    "main": "https://p2pool.observer",
    "mini": "https://mini.p2pool.observer",
    "nano": "https://nano.p2pool.observer",
}

# Candidate distributions of true hashrate. All have location 0; each is
# described by its positive parameters in scipy order (shapes..., scale).
CANDIDATES = {
    "lognormal": (stats.lognorm, ("sigma", "scale")),
    "pareto": (stats.pareto, ("alpha", "x_min")),
    "weibull": (stats.weibull_min, ("shape", "scale")),
    "gamma": (stats.gamma, ("shape", "scale")),
    "log-logistic": (stats.fisk, ("shape", "scale")),
    "exponential": (stats.expon, ("scale",)),
}
SCALE_PARAMS = {"scale", "x_min"}  # parameters measured in hashrate units

USER_AGENT = "p2pool-hashrate-analysis/1.0"
MAX_WINDOW = 60000  # larger windows make the observer API silently return ~1 h of data
MIN_SHAPE = 0.05    # shape parameters below this describe a degenerate mass at zero


# ---------------------------------------------------------------- data

def fetch_json(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_shares(base, hours):
    """Shares (including uncles) from the last `hours` hours."""
    info = fetch_json(f"{base}/api/pool_info")["sidechain"]
    # The window is counted in sidechain heights and uncles come on top, so
    # ask for a little more than needed and trim by timestamp.
    window = min(MAX_WINDOW, int(hours * 3600 / info["block_time"] * 1.1) + 10)
    shares = fetch_json(f"{base}/api/side_blocks_in_window?window={window}&noMainStatus")
    newest = max(s["timestamp"] for s in shares)
    covered = (newest - min(s["timestamp"] for s in shares)) / 3600
    if covered < 0.95 * hours:
        print(f"  warning: the API returned only {covered:.1f} h of the {hours:g} h asked for",
              file=sys.stderr)
    return info, [s for s in shares if s["timestamp"] >= newest - hours * 3600]


def miner_stats(shares):
    """Per-miner hashrate estimates and share counts, largest first."""
    ts = [s["timestamp"] for s in shares]
    period = max(ts) - min(ts)
    work, count = defaultdict(int), defaultdict(int)
    for s in shares:
        work[s["miner_address"]] += s["difficulty"]
        count[s["miner_address"]] += 1
    addrs = sorted(work, key=work.get, reverse=True)
    hr = np.array([work[a] / period for a in addrs], dtype=float)
    k = np.array([count[a] for a in addrs])
    # Hashrate that yields one expected share over the period.
    unit = sum(work.values()) / len(shares) / period
    return addrs, hr, k, period, unit


def gini(x):
    x = np.sort(x)
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def nakamoto(x, frac=0.5):
    """Smallest number of miners that together hold more than `frac`."""
    c = np.cumsum(np.sort(x)[::-1]) / x.sum()
    return int(np.searchsorted(c, frac, side="right") + 1)


# ---------------------------------------------------------------- fitting

class CountModel:
    """Zero-truncated Poisson mixture likelihood for observed share counts.

    Works in units of expected shares (lambda = h / unit). The mixing integral
    is a sum over a fine log-spaced lambda grid using exact CDF differences.
    """

    def __init__(self, k):
        self.k = k
        self.n = len(k)
        self.kmax = int(k.max())
        self.edges = np.logspace(-4, math.log10(self.kmax * 100), 3000)
        mids = np.sqrt(self.edges[:-1] * self.edges[1:])
        self.mids = mids
        ks = np.arange(1, self.kmax + 1)[:, None]
        self.pois = np.exp(ks * np.log(mids) - mids - gammaln(ks + 1))  # P(k|lam)
        self.p_hit = -np.expm1(-mids)                                   # P(k>=1|lam)
        self.freq = np.bincount(k, minlength=self.kmax + 1)[1:]

    def probs(self, dist, args):
        """P(k) for k = 1..kmax, P(k >= 1), and P(k = 0)."""
        cdf = dist.cdf(self.edges, *args)
        w = np.diff(cdf)
        p_k = self.pois @ w
        p_seen = w @ self.p_hit + (1 - cdf[-1])  # mass above grid always seen
        p_zero = cdf[0] + w @ np.exp(-self.mids)
        return p_k, p_seen, p_zero

    def loglik(self, dist, args):
        p_k, p_seen, _ = self.probs(dist, args)
        used = self.freq > 0
        if p_seen <= 0 or np.any(p_k[used] <= 0):
            return -np.inf
        return float(self.freq[used] @ np.log(p_k[used]) - self.n * math.log(p_seen))


def scipy_args(theta):
    """Positive parameters (shapes..., scale) -> scipy args with loc=0."""
    p = np.exp(theta)
    return (*p[:-1], 0.0, p[-1])


def fit_counts(k, unit):
    model = CountModel(k)
    results = []
    for name, (dist, pnames) in CANDIDATES.items():
        # Start from a naive fit to the share counts themselves.
        try:
            naive = dist.fit(k.astype(float), floc=0)
            start = np.log([*naive[:-2], naive[-1]])
        except Exception:
            start = np.zeros(len(pnames))
        start = np.where(np.isfinite(start), start, 0.0)
        start[:-1] = np.maximum(start[:-1], math.log(MIN_SHAPE) + 0.5)

        def nll(theta):
            if len(theta) > 1 and np.any(theta[:-1] < math.log(MIN_SHAPE)):
                return 1e12
            ll = model.loglik(dist, scipy_args(theta))
            return 1e12 if not math.isfinite(ll) else -ll

        best = None
        for s in (start, start + 0.5, start - 0.5):
            r = optimize.minimize(nll, s, method="Nelder-Mead",
                                  options={"xatol": 1e-4, "fatol": 1e-4, "maxiter": 4000})
            if best is None or r.fun < best.fun:
                best = r
        if best.fun >= 1e12:
            print(f"    fit failed for {name}", file=sys.stderr)
            continue
        args = scipy_args(best.x)
        p_k, p_seen, p_zero = model.probs(dist, args)
        chi2, dof, pval = chi_square(model.freq, model.n * p_k / p_seen, len(pnames))
        params = dict(zip(pnames, np.exp(best.x)))
        for pn in SCALE_PARAMS & params.keys():
            params[pn] *= unit  # expected shares -> H/s
        results.append({
            "name": name, "dist": dist, "args": args, "params": params,
            "aic": 2 * len(pnames) + 2 * best.fun,
            "chi2": chi2, "dof": dof, "p": pval,
            "hidden": model.n * p_zero / p_seen,
            "at_bound": len(pnames) > 1 and bool(np.any(best.x[:-1] < math.log(MIN_SHAPE) + 0.01)),
            "p_k": p_k / p_seen,
        })
    results.sort(key=lambda r: r["aic"])
    return model, results


def count_bins(kmax):
    """Share-count bins 1, 2, 3-4, 5-8, 9-16, ... as (lo, hi) inclusive."""
    bins, lo = [], 1
    while lo <= kmax:
        hi = max(lo, 2 * lo - 2) if lo > 2 else lo
        bins.append((lo, min(hi, kmax)))
        lo = hi + 1
    return bins


def chi_square(freq, expected, nparams):
    """Chi-square of observed vs expected miners per share-count bin.

    The last bin is open-ended (its expectation includes counts above kmax),
    and bins are merged from the tail until each expects at least 5 miners.
    """
    obs, exp = [], []
    for lo, hi in count_bins(len(freq)):
        obs.append(freq[lo - 1:hi].sum())
        exp.append(expected[lo - 1:hi].sum())
    exp[-1] += max(0.0, freq.sum() - sum(exp))  # tail beyond kmax
    while len(exp) > 1 and exp[-1] < 5:
        o, e = obs.pop(), exp.pop()
        obs[-1] += o
        exp[-1] += e
    obs, exp = np.array(obs, float), np.array(exp, float)
    chi2 = float(((obs - exp) ** 2 / exp).sum())
    dof = len(obs) - 1 - nparams
    return chi2, dof, float(stats.chi2.sf(chi2, dof)) if dof > 0 else float("nan")


# ---------------------------------------------------------------- output

def fmt_hr(h):
    for unit, scale in (("GH/s", 1e9), ("MH/s", 1e6), ("kH/s", 1e3)):
        if h >= scale:
            return f"{h / scale:.2f} {unit}"
    return f"{h:.0f} H/s"


def describe(params):
    return " ".join(f"{k}={fmt_hr(v) if k in SCALE_PARAMS else f'{v:.3f}'}"
                    for k, v in params.items())


def report(pool, info, shares, hr, k, period, unit):
    pool_hr = info["difficulty"] / info["block_time"]
    print(f"\n=== {pool} ({len(shares)} shares over {period / 3600:.1f} h) ===")
    print(f"  miners seen           {len(hr)}")
    print(f"  pool hashrate         {fmt_hr(hr.sum())} from shares, "
          f"{fmt_hr(pool_hr)} from current difficulty")
    print(f"  one-share hashrate    {fmt_hr(unit)} (one expected share in the period)")
    print(f"  mean / median         {fmt_hr(hr.mean())} / {fmt_hr(np.median(hr))}")
    pct = np.percentile(hr, [10, 25, 75, 90, 99])
    print("  p10 p25 p75 p90 p99   " + "  ".join(fmt_hr(v) for v in pct))
    print(f"  min / max             {fmt_hr(hr.min())} / {fmt_hr(hr.max())}")
    print(f"  largest miner         {100 * hr[0] / hr.sum():.1f}% of pool")
    print(f"  top 10 miners         {100 * hr[:10].sum() / hr.sum():.1f}% of pool")
    print(f"  miners for >50%       {nakamoto(hr)}")
    print(f"  gini (seen miners)    {gini(hr):.3f}")
    print(f"  miners with 1 share   {int((k == 1).sum())} ({100 * (k == 1).mean():.0f}%)")


def report_fits(fits):
    print("  fits to share counts (Poisson noise, unseen miners modelled; lower AIC is better):")
    print(f"    {'model':<13}{'AIC':>10}{'dAIC':>8}{'chi2':>9}{'dof':>5}{'p':>10}"
          f"{'unseen':>10}  params")
    best = fits[0]["aic"]
    for r in fits:
        print(f"    {r['name']:<13}{r['aic']:>10.1f}{r['aic'] - best:>8.1f}"
              f"{r['chi2']:>9.1f}{r['dof']:>5}{r['p']:>10.3g}{r['hidden']:>10.3g}"
              f"  {describe(r['params'])}{'  (shape at lower bound)' if r['at_bound'] else ''}")
    b = fits[0]
    tied = [r for r in fits if r["aic"] - b["aic"] <= 2]
    gof = ("its predicted share-count histogram is consistent with the data"
           if b["p"] > 0.05 else "the chi-square test rejects it at 5%")
    if len(tied) == 1:
        margin = fits[1]["aic"] - b["aic"] if len(fits) > 1 else float("inf")
        strength = "decisively" if margin > 10 else "clearly" if margin > 4 else "narrowly"
        print(f"  best fit: {b['name']} ({describe(b['params'])}), {strength} "
              f"(dAIC {margin:.1f} to the next); {gof}")
    else:
        names = ", ".join(r["name"] for r in tied)
        print(f"  best fit: no clear winner; {names} are within dAIC 2 of each other.")
        print(f"    They agree above the one-share hashrate and differ only below it,")
        print(f"    where miners are invisible. Lowest AIC: {b['name']}; {gof}")
    lo, hi = min(r["hidden"] for r in tied), max(r["hidden"] for r in tied)
    span = f"~{lo:.0f}" if len(tied) == 1 else f"between {lo:.0f} and {hi:.0f}"
    print(f"  unseen miners (too small to find a share in the period): {span}")


def plot(results, path):
    fig, axes = plt.subplots(len(results), 2, figsize=(13, 4.2 * len(results)),
                             squeeze=False)
    colors = ["#d1495b", "#00798c", "#edae49"]
    for row, (pool, k, unit, period, model, fits) in enumerate(results):
        ax_h, ax_c = axes[row]
        n = len(k)

        # Left: miners per share-count bin, observed vs each model's prediction.
        bins = count_bins(model.kmax)
        lo = np.array([b[0] for b in bins]) - 0.5
        hi = np.array([b[1] for b in bins]) + 0.5
        obs = [model.freq[a - 1:b].sum() for a, b in bins]
        ax_h.bar(lo * unit, obs, width=(hi - lo) * unit, align="edge",
                 color="#bcc9d1", edgecolor="white", label=f"observed ({n} miners)")
        mid = np.sqrt(lo * hi) * unit
        for r, c in zip(fits[:3], colors):
            exp = [n * r["p_k"][a - 1:b].sum() for a, b in bins]
            ax_h.plot(mid, exp, "o-", color=c, ms=4, lw=1.3,
                      label=f"{r['name']} (dAIC {r['aic'] - fits[0]['aic']:.0f})")
        ax_h.set_xscale("log")
        ax_h.set_yscale("log")
        ax_h.set_xlabel("miner hashrate estimate (H/s)")
        ax_h.set_ylabel("miners per bin")
        ax_h.set_title(f"{pool}: miners by hashrate ({period / 3600:.0f} h)")
        ax_h.legend(fontsize=8)

        # Right: CCDF of observed estimates vs the best model, both as it would
        # be observed (with Poisson noise) and as true hashrate.
        ks = np.arange(1, model.kmax + 1)
        xs = np.sort(k)
        ax_c.loglog(xs * unit, 1 - np.arange(n) / n, ".", color="#333", ms=4,
                    label="observed")
        for r, c in zip(fits[:3], colors):
            ccdf = 1 - np.concatenate([[0], np.cumsum(r["p_k"])[:-1]])
            ax_c.loglog(ks * unit, ccdf, "-", color=c, lw=1.4,
                        label=f"{r['name']}, as observed")
        b = fits[0]
        lam = np.logspace(math.log10(0.05), math.log10(model.kmax * 3), 300)
        seen_frac = n / (n + b["hidden"])
        ax_c.loglog(lam * unit, b["dist"].sf(lam, *b["args"]) / seen_frac, "--",
                    color=colors[0], lw=1.2, label=f"{b['name']}, true hashrate")
        ax_c.axvline(unit, color="#999", lw=0.8, ls=":")
        ax_c.set_ylim(0.5 / n, 1.5)
        ax_c.set_xlabel("miner hashrate (H/s)   [dotted: one expected share]")
        ax_c.set_ylabel("fraction of seen miners >= x")
        ax_c.set_title(f"{pool}: CCDF")
        ax_c.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def write_csv(path, addrs, hr, k):
    total = hr.sum()
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["miner_address", "hashrate_hs", "shares", "pool_fraction"])
        for a, h, n in zip(addrs, hr, k):
            w.writerow([a, f"{h:.1f}", int(n), f"{h / total:.6f}"])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pools", nargs="+", choices=POOLS, default=list(POOLS))
    ap.add_argument("--hours", type=float, default=24,
                    help="length of share history to use (default 24; about a week is available)")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "output",
                    help="directory for the plot and per-miner CSVs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())

    results = []
    for pool in args.pools:
        print(f"fetching {pool} ...", file=sys.stderr)
        info, shares = fetch_shares(POOLS[pool], args.hours)
        addrs, hr, k, period, unit = miner_stats(shares)
        write_csv(args.out / f"{pool}-{stamp}.csv", addrs, hr, k)
        report(pool, info, shares, hr, k, period, unit)
        model, fits = fit_counts(k, unit)
        report_fits(fits)
        results.append((pool, k, unit, period, model, fits))

    png = args.out / f"hashrate-distribution-{stamp}.png"
    plot(results, png)
    print(f"\nplot: {png}")
    print(f"per-miner CSVs: {args.out}/<pool>-{stamp}.csv")


if __name__ == "__main__":
    main()
