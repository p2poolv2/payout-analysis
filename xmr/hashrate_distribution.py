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
import json
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from hashrate_fit import fit_models, fmt_hr, plot, report_distribution, report_fits, write_csv

POOLS = {
    "main": "https://p2pool.observer",
    "mini": "https://mini.p2pool.observer",
    "nano": "https://nano.p2pool.observer",
}

USER_AGENT = "p2pool-hashrate-analysis/1.0"
MAX_WINDOW = 60000  # larger windows make the observer API silently return ~1 h of data

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
        print(f"\n=== {pool} ({len(shares)} shares over {period / 3600:.1f} h) ===")
        print(f"  pool hashrate         {fmt_hr(hr.sum())} from shares, "
              f"{fmt_hr(info['difficulty'] / info['block_time'])} from current difficulty")
        report_distribution(hr, k, unit)
        fits = fit_models(k, unit)
        report_fits(fits)
        results.append((pool, k, unit, period, fits))

    png = args.out / f"hashrate-distribution-{stamp}.png"
    plot(results, png)
    print(f"\nplot: {png}")
    print(f"per-miner CSVs: {args.out}/<pool>-{stamp}.csv")


if __name__ == "__main__":
    main()
