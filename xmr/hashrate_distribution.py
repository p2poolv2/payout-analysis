# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy", "matplotlib"]
# ///
"""Distribution of miner hashrate on the Monero P2Pool sidechains.

Fetches the recent share history of each P2Pool sidechain (main, mini, nano)
from the p2pool.observer API, estimates each miner's hashrate, prints summary
and concentration statistics, fits a lognormal and a log-logistic and plots the result.

Hashrate estimate: a share of difficulty D represents D expected hashes, so a
miner's hashrate is the sum of the difficulty of their shares (uncles included,
since an uncle is real work) divided by the length of the period. Miners are
identified by payout address.

Why the fit is done on share counts. The per-miner estimate is noisy for small
miners (k shares give a relative error of about 1/sqrt(k)), and a miner whose
hashrate is well below share_difficulty / period finds no share and is
invisible. Fitting directly to the estimates would put the distribution's mass
on that detection floor. Instead each model is fitted to the observed share
counts with the measurement built in:

    true hashrate h ~ lognormal(mu, sigma) or log-logistic(mu, c)
    shares k | h    ~ Poisson(h * period / mean_share_difficulty)
    only miners with k >= 1 are observed

so the fitted parameters describe true hashrate. Both models are symmetric in
log hashrate around mu = log(median): the lognormal has a normal shape there,
the log-logistic a logistic one, which gives it a power-law tail
P(h > x) ~ x^-c. The models are compared by AIC (both have two parameters), and
a chi-square test of observed against predicted share-count histograms checks
each fit.

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
from scipy.special import expit, gammaln

POOLS = {
    "main": "https://p2pool.observer",
    "mini": "https://mini.p2pool.observer",
    "nano": "https://nano.p2pool.observer",
}

USER_AGENT = "p2pool-hashrate-analysis/1.0"
MAX_WINDOW = 60000  # larger windows make the observer API silently return ~1 h of data

# Each model is a CDF of z = log(x) with location mu = log(median) and a
# spread parameter; both are fitted as (mu, log spread).
MODELS = {
    "lognormal": {"spread": "sigma", "cdf": lambda z, mu, s: stats.norm.cdf((z - mu) / s),
                  "color": "#00798c"},
    "log-logistic": {"spread": "c", "cdf": lambda z, mu, c: expit(c * (z - mu)),
                     "color": "#d1495b"},
}


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


def top_share(hr, frac):
    """Fraction of hashrate held by the largest `frac` of miners (hr sorted desc)."""
    return hr[:max(1, round(len(hr) * frac))].sum() / hr.sum()


# ---------------------------------------------------------------- fitting

class CountModel:
    """Zero-truncated Poisson-mixture likelihood for observed share counts.

    Works in units of expected shares (lambda = h / unit). The mixing integral
    is a sum over a fine log-spaced lambda grid using exact CDF differences.
    """

    def __init__(self, k):
        self.n = len(k)
        self.kmax = int(k.max())
        self.edges = np.logspace(-4, math.log10(self.kmax * 100), 3000)
        self.log_edges = np.log(self.edges)
        self.mids = np.sqrt(self.edges[:-1] * self.edges[1:])
        ks = np.arange(1, self.kmax + 1)[:, None]
        self.pois = np.exp(ks * np.log(self.mids) - self.mids - gammaln(ks + 1))
        self.p_hit = -np.expm1(-self.mids)
        self.freq = np.bincount(k, minlength=self.kmax + 1)[1:]

    def probs(self, cdf_fn, mu, spread):
        """P(k) for k = 1..kmax, P(k >= 1) and P(k = 0) for lambda ~ model."""
        cdf = cdf_fn(self.log_edges, mu, spread)
        w = np.diff(cdf)
        p_k = self.pois @ w
        p_seen = w @ self.p_hit + (1 - cdf[-1])  # mass above the grid is always seen
        p_zero = cdf[0] + w @ np.exp(-self.mids)
        return p_k, p_seen, p_zero

    def nll(self, theta, cdf_fn):
        mu, log_spread = theta
        p_k, p_seen, _ = self.probs(cdf_fn, mu, math.exp(log_spread))
        used = self.freq > 0
        if p_seen <= 0 or np.any(p_k[used] <= 0):
            return 1e12
        return -float(self.freq[used] @ np.log(p_k[used]) - self.n * math.log(p_seen))


def fit_models(k, unit):
    """Fit each model's true hashrate to the share counts; best AIC first."""
    model = CountModel(k)
    logk = np.log(k)
    fits = []
    for name, m in MODELS.items():
        # sigma ~ std(log k); a logistic with the same spread has c ~ 1.8 / sigma.
        s0 = logk.std() + 0.1
        s0 = s0 if m["spread"] == "sigma" else 1.8 / s0
        best = None
        for start in ([logk.mean(), math.log(s0)], [logk.mean() - 1, math.log(s0) + 0.5],
                      [logk.mean() - 1, math.log(s0) - 0.5]):
            r = optimize.minimize(model.nll, start, args=(m["cdf"],), method="Nelder-Mead",
                                  options={"xatol": 1e-5, "fatol": 1e-5, "maxiter": 4000})
            if best is None or r.fun < best.fun:
                best = r
        mu_l, spread = best.x[0], math.exp(best.x[1])
        p_k, p_seen, p_zero = model.probs(m["cdf"], mu_l, spread)
        chi2, dof, pval = chi_square(model.freq, model.n * p_k / p_seen, 2)
        fits.append({
            "name": name, "cdf": m["cdf"], "color": m["color"], "model": model,
            "spread_name": m["spread"], "spread": spread,
            "mu_lambda": mu_l,                 # in log expected shares
            "mu": mu_l + math.log(unit),       # in log H/s
            "aic": 4 + 2 * best.fun,
            "chi2": chi2, "dof": dof, "p": pval,
            "unseen": model.n * p_zero / p_seen,
            "p_k": p_k / p_seen,
        })
    fits.sort(key=lambda f: f["aic"])
    return fits


def model_summary(f):
    """Median, mean and Gini of the fitted true-hashrate distribution."""
    med = math.exp(f["mu"])
    if f["name"] == "lognormal":
        s = f["spread"]
        return med, med * math.exp(s * s / 2), 2 * stats.norm.cdf(s / math.sqrt(2)) - 1
    c = f["spread"]
    mean = med * (math.pi / c) / math.sin(math.pi / c) if c > 1 else math.inf
    return med, mean, min(1.0, 1 / c)  # gini is 1 once the mean is infinite


def count_bins(kmax):
    """Share-count bins 1, 2, 3-4, 5-8, 9-16, ... as (lo, hi) inclusive."""
    bins, lo = [], 1
    while lo <= kmax:
        hi = 2 * lo - 2 if lo > 2 else lo
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


def report(pool, info, shares, hr, k, period, unit):
    pool_hr = info["difficulty"] / info["block_time"]
    n = len(hr)
    print(f"\n=== {pool} ({len(shares)} shares over {period / 3600:.1f} h) ===")
    print(f"  miners seen           {n}")
    print(f"  pool hashrate         {fmt_hr(hr.sum())} from shares, "
          f"{fmt_hr(pool_hr)} from current difficulty")
    print(f"  one-share hashrate    {fmt_hr(unit)} (one expected share in the period)")
    print(f"  mean / median         {fmt_hr(hr.mean())} / {fmt_hr(np.median(hr))}")
    pct = np.percentile(hr, [10, 25, 75, 90, 99])
    print("  p10 p25 p75 p90 p99   " + "  ".join(fmt_hr(v) for v in pct))
    print(f"  min / max             {fmt_hr(hr.min())} / {fmt_hr(hr.max())}")
    print(f"  largest / smallest    {hr[0] / hr[-1]:.0f}x  (smallest is at the detection floor)")
    print(f"  largest / median      {hr[0] / np.median(hr):.0f}x")
    print(f"  concentration")
    print(f"    largest miner       {100 * hr[0] / hr.sum():.1f}% of pool")
    print(f"    top 10 miners       {100 * hr[:10].sum() / hr.sum():.1f}%")
    print(f"    top 1% of miners    {100 * top_share(hr, 0.01):.1f}%")
    print(f"    top 10% of miners   {100 * top_share(hr, 0.10):.1f}%")
    print(f"    bottom 50%          {100 * (1 - top_share(hr, 0.5)):.1f}%")
    print(f"    miners for >50%     {nakamoto(hr)}")
    print(f"    gini                {gini(hr):.3f}")
    print(f"  miners with 1 share   {int((k == 1).sum())} ({100 * (k == 1).mean():.0f}%)")


def report_fits(fits):
    print("  fits to share counts (Poisson noise and unseen miners modelled; lower AIC is better)")
    best = fits[0]["aic"]
    for f in fits:
        med, mean, g = model_summary(f)
        gof = "consistent with the data" if f["p"] > 0.05 else "rejected at 5%"
        print(f"    {f['name']:<13} mu={f['mu']:.3f} {f['spread_name']}={f['spread']:.3f}  "
              f"AIC={f['aic']:.1f} (dAIC {f['aic'] - best:.1f})")
        print(f"      median {fmt_hr(med)}, mean "
              f"{fmt_hr(mean) if math.isfinite(mean) else 'infinite'}, "
              f"gini incl. unseen {g:.3f}, unseen miners ~{f['unseen']:.0f}")
        print(f"      chi2={f['chi2']:.1f} dof={f['dof']} p={f['p']:.3g} -> {gof}")
        if f["name"] == "log-logistic":
            c = f["spread"]
            tail = ("finite mean and variance" if c > 2 else
                    "finite mean, infinite variance" if c > 1 else "infinite mean")
            print(f"      power-law tail P(h > x) ~ x^-{c:.2f}: {tail}")
    margin = fits[1]["aic"] - best
    verdict = (f"{fits[0]['name']} fits better (dAIC {margin:.1f})" if margin > 2
               else f"the two fit about equally well (dAIC {margin:.1f})")
    print(f"  {verdict}")


def plot(results, path):
    fig, axes = plt.subplots(len(results), 2, figsize=(13, 4.2 * len(results)),
                             squeeze=False)
    for row, (pool, k, unit, period, fits) in enumerate(results):
        ax_h, ax_c = axes[row]
        model, n = fits[0]["model"], len(k)

        # Left: miners per share-count bin, observed vs each model's prediction.
        bins = count_bins(model.kmax)
        lo = np.array([b[0] for b in bins]) - 0.5
        hi = np.array([b[1] for b in bins]) + 0.5
        obs = [model.freq[a - 1:b].sum() for a, b in bins]
        ax_h.bar(lo * unit, obs, width=(hi - lo) * unit, align="edge",
                 color="#bcc9d1", edgecolor="white", label=f"observed ({n} miners)")
        for f in fits:
            exp = [n * f["p_k"][a - 1:b].sum() for a, b in bins]
            ax_h.plot(np.sqrt(lo * hi) * unit, exp, "o-", color=f["color"], ms=4, lw=1.4,
                      label=f"{f['name']} (mu={f['mu']:.2f}, {f['spread_name']}="
                            f"{f['spread']:.2f}, dAIC {f['aic'] - fits[0]['aic']:.0f})")
        ax_h.set_xscale("log")
        ax_h.set_yscale("log")
        ax_h.set_xlabel("miner hashrate estimate (H/s)")
        ax_h.set_ylabel("miners per bin")
        ax_h.set_title(f"{pool}: miners by hashrate ({period / 3600:.0f} h)")
        ax_h.legend(fontsize=8)

        # Right: CCDF of observed estimates vs each model, both as it would be
        # observed (with Poisson noise) and as true hashrate.
        ks = np.arange(1, model.kmax + 1)
        ax_c.loglog(np.sort(k) * unit, 1 - np.arange(n) / n, ".", color="#333", ms=4,
                    label="observed")
        lam = np.logspace(math.log10(0.05), math.log10(model.kmax * 3), 300)
        for f in fits:
            ccdf = 1 - np.concatenate([[0], np.cumsum(f["p_k"])[:-1]])
            ax_c.loglog(ks * unit, ccdf, "-", color=f["color"], lw=1.4,
                        label=f"{f['name']}, as observed")
            sf = 1 - f["cdf"](np.log(lam), f["mu_lambda"], f["spread"])
            ax_c.loglog(lam * unit, sf * (n + f["unseen"]) / n, "--", color=f["color"],
                        lw=1.1, label=f"{f['name']}, true hashrate")
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
        fits = fit_models(k, unit)
        report_fits(fits)
        results.append((pool, k, unit, period, fits))

    png = args.out / f"hashrate-distribution-{stamp}.png"
    plot(results, png)
    print(f"\nplot: {png}")
    print(f"per-miner CSVs: {args.out}/<pool>-{stamp}.csv")


if __name__ == "__main__":
    main()
