"""Shared statistics, distribution fitting and plots for miner hashrate.

Used by xmr/hashrate_distribution.py (Monero P2Pool shares) and
testnet5/coinbase_distribution.py (Bitcoin blocks). Both observe each miner as
a count k of events (shares or blocks) over a period; `unit` is the hashrate
that yields one expected event in the period.

Model, fitted to the counts so that Poisson noise and miners with no event are
accounted for:

    true hashrate h ~ lognormal(mu, sigma) or log-logistic(mu, c)
    events k | h    ~ Poisson(h / unit)
    only miners with k >= 1 are observed
"""

import csv
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import optimize, stats
from scipy.special import expit, gammaln

# Each model is a CDF of z = log(x) with location mu = log(median) and a
# spread parameter; both are fitted as (mu, log spread).
MODELS = {
    "lognormal": {"spread": "sigma", "cdf": lambda z, mu, s: stats.norm.cdf((z - mu) / s),
                  "color": "#00798c"},
    "log-logistic": {"spread": "c", "cdf": lambda z, mu, c: expit(c * (z - mu)),
                     "color": "#d1495b"},
}



# ---------------------------------------------------------------- statistics

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
    """Zero-truncated Poisson-mixture likelihood for observed event counts.

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
    """Fit each model's true hashrate to the event counts; best AIC first."""
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
            "mu_lambda": mu_l,                 # in log expected events
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
    """Event-count bins 1, 2, 3-4, 5-8, 9-16, ... as (lo, hi) inclusive."""
    bins, lo = [], 1
    while lo <= kmax:
        hi = 2 * lo - 2 if lo > 2 else lo
        bins.append((lo, min(hi, kmax)))
        lo = hi + 1
    return bins


def chi_square(freq, expected, nparams):
    """Chi-square of observed vs expected miners per event-count bin.

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
    for unit, scale in (("EH/s", 1e18), ("PH/s", 1e15), ("TH/s", 1e12),
                        ("GH/s", 1e9), ("MH/s", 1e6), ("kH/s", 1e3)):
        if h >= scale:
            return f"{h / scale:.2f} {unit}"
    return f"{h:.0f} H/s"


def report_distribution(hr, k, unit, event="share", whole="pool"):
    """Print size and concentration statistics. hr must be sorted descending."""
    n = len(hr)
    print(f"  miners seen           {n}")
    print(f"  one-{event} hashrate    {fmt_hr(unit)} (one expected {event} in the period)")
    print(f"  mean / median         {fmt_hr(hr.mean())} / {fmt_hr(np.median(hr))}")
    pct = np.percentile(hr, [10, 25, 75, 90, 99])
    print("  p10 p25 p75 p90 p99   " + "  ".join(fmt_hr(v) for v in pct))
    print(f"  min / max             {fmt_hr(hr.min())} / {fmt_hr(hr.max())}")
    print(f"  largest / smallest    {hr[0] / hr[-1]:.0f}x  (smallest is at the detection floor)")
    print(f"  largest / median      {hr[0] / np.median(hr):.0f}x")
    print(f"  concentration")
    print(f"    largest miner       {100 * hr[0] / hr.sum():.1f}% of {whole}")
    print(f"    top 10 miners       {100 * hr[:10].sum() / hr.sum():.1f}%")
    print(f"    top 1% of miners    {100 * top_share(hr, 0.01):.1f}%")
    print(f"    top 10% of miners   {100 * top_share(hr, 0.10):.1f}%")
    print(f"    bottom 50%          {100 * (1 - top_share(hr, 0.5)):.1f}%")
    print(f"    miners for >50%     {nakamoto(hr)}")
    print(f"    gini                {gini(hr):.3f}")
    print(f"  miners with 1 {event}   {int((k == 1).sum())} ({100 * (k == 1).mean():.0f}%)")


def report_fits(fits, event="share"):
    print(f"  fits to {event} counts (Poisson noise and unseen miners modelled; lower AIC is better)")
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


def plot(results, path, event="share"):
    """results: list of (title, k, unit, period_seconds, fits)."""
    fig, axes = plt.subplots(len(results), 2, figsize=(13, 4.2 * len(results)),
                             squeeze=False)
    for row, (pool, k, unit, period, fits) in enumerate(results):
        ax_h, ax_c = axes[row]
        model, n = fits[0]["model"], len(k)

        # Left: miners per event-count bin, observed vs each model's prediction.
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
        span = f"{period / 3600:.0f} h" if period < 4 * 86400 else f"{period / 86400:.0f} days"
        ax_h.set_title(f"{pool}: miners by hashrate ({span})")
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
        ax_c.set_xlabel(f"miner hashrate (H/s)   [dotted: one expected {event}]")
        ax_c.set_ylabel("fraction of seen miners >= x")
        ax_c.set_title(f"{pool}: CCDF")
        ax_c.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def write_csv(path, addrs, hr, k, event="share"):
    total = hr.sum()
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["miner", "hashrate_hs", f"{event}s", "fraction"])
        for a, h, n in zip(addrs, hr, k):
            w.writerow([a, f"{h:.1f}", round(float(n), 4), f"{h / total:.6f}"])
