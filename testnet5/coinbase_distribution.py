# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scipy", "matplotlib"]
# ///
"""Distribution of miner hashrate on Bitcoin testnet5, from block coinbases.

Talks to a bitcoind over JSON-RPC, fetches the coinbase of every block, caches
them locally (later runs fetch only new blocks and handle reorgs), attributes
each block to a miner, prints summary and concentration statistics, fits the
same lognormal and log-logistic models as xmr/hashrate_distribution.py and
plots the result.

Attribution (--by):
    address   the coinbase output address receiving the most value (default)
    tag       the ASCII tag in the coinbase scriptSig, e.g. a pool name
    outputs   split each block across all coinbase output addresses by value,
              as a pool paying its miners in the coinbase would (p2poolv2).
              Block counts become fractional, so no distribution is fitted.

Hashrate: a block of difficulty D represents D * 2^32 expected hashes, so a
miner's hashrate is the work of their blocks divided by the length of the
period. Testnets let anyone mine a minimum-difficulty block when no block has
been found for 20 minutes; those blocks carry almost no work, are won by
whoever is fastest to submit rather than by hashrate, and are reported
separately and left out of the distribution.

Fitting needs a single difficulty: under a changing difficulty a block count
does not measure hashrate (an easy early block counts as much as a hard late
one). When the selection spans more than one difficulty the statistics are
still computed from work, but no distribution is fitted; --epochs 1 restricts
the analysis to the current retarget epoch.

Connection: --rpc-url, plus either --rpc-cookie or a user and password. The
password is best given in the BITCOIN_RPC_PASSWORD environment variable, so it
does not appear in the process list. Every option also reads an environment
variable: BITCOIN_RPC_URL, BITCOIN_RPC_USER, BITCOIN_RPC_PASSWORD,
BITCOIN_RPC_COOKIE.

Usage:
    export BITCOIN_RPC_URL=http://127.0.0.1:48332 BITCOIN_RPC_COOKIE=~/.bitcoin/testnet5/.cookie
    uv run testnet5/coinbase_distribution.py                    # whole chain
    uv run testnet5/coinbase_distribution.py --epochs 1          # current difficulty, with fits
    uv run testnet5/coinbase_distribution.py --days 30 --by tag
"""

import argparse
import base64
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from hashrate_fit import (fit_models, fmt_hr, gini, nakamoto, plot, report_distribution,
                          report_fits, write_csv)  # also selects the Agg backend
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
BATCH = 250             # RPC calls per HTTP request
MIN_DIFF_RATIO = 100    # a block this many times easier than its epoch's hardest is min-difficulty
EPOCH = 2016            # difficulty retarget interval
MIN_MINERS_TO_FIT = 8
S19_TH = 95.0           # Antminer S19, as in lib/payout_model.py
BITAXE_TH = 1.2         # Bitaxe Gamma, as in TESTNET-REPORT.md


# ---------------------------------------------------------------- RPC

class RPC:
    def __init__(self, url, user=None, password=None, cookie=None, timeout=300):
        self.url = url
        self.timeout = timeout
        if cookie:
            auth = Path(cookie).expanduser().read_text().strip()
        elif user is not None:
            auth = f"{user}:{password or ''}"
        else:
            auth = None
        self.headers = {"Content-Type": "application/json"}
        if auth:
            self.headers["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()

    def _post(self, payload):
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(),
                                     headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                sys.exit("RPC: authentication failed (check the cookie or user and password)")
            body = e.read().decode(errors="replace")
            try:  # bitcoind reports RPC errors with HTTP 500 and a JSON body
                return json.loads(body)
            except ValueError:
                sys.exit(f"RPC: HTTP {e.code}: {body[:200]}")
        except urllib.error.URLError as e:
            sys.exit(f"RPC: cannot reach {self.url}: {e.reason}")

    def call(self, method, *params):
        r = self._post({"jsonrpc": "1.0", "id": 0, "method": method, "params": list(params)})
        if r.get("error"):
            raise RuntimeError(f"{method}: {r['error']}")
        return r["result"]

    def batch(self, calls):
        """Run [(method, params), ...] and return results in order."""
        out = []
        for i in range(0, len(calls), BATCH):
            chunk = calls[i:i + BATCH]
            resp = self._post([{"jsonrpc": "1.0", "id": j, "method": m, "params": list(p)}
                               for j, (m, p) in enumerate(chunk)])
            resp = sorted(resp, key=lambda r: r["id"])
            for (m, p), r in zip(chunk, resp):
                if r.get("error"):
                    raise RuntimeError(f"{m}{tuple(p)}: {r['error']}")
                out.append(r["result"])
        return out


# ---------------------------------------------------------------- coinbases

def coinbase_tag(script_hex):
    """Printable ASCII in a coinbase scriptSig, after the BIP34 height push.

    Keeps runs of 4+ printable characters that contain 3+ letters in a row, so
    extranonce bytes that happen to be printable are not mistaken for text.
    """
    b = bytes.fromhex(script_hex)
    if b and 1 <= b[0] <= 8:          # push of the block height
        b = b[1 + b[0]:]
    runs, cur = [], bytearray()
    for c in b:
        if 32 <= c < 127:
            cur.append(c)
        else:
            if len(cur) >= 4:
                runs.append(cur.decode())
            cur = bytearray()
    if len(cur) >= 4:
        runs.append(cur.decode())
    runs = [r.strip() for r in runs if re.search(r"[A-Za-z]{3}", r)]
    return " ".join(runs).strip()


def block_record(block, cb):
    outs = []
    for o in cb["vout"]:
        spk = o["scriptPubKey"]
        if spk.get("type") == "nulldata":
            continue  # witness commitment and other OP_RETURN data
        sats = round(o["value"] * 1e8)
        who = spk.get("address") or (spk.get("addresses") or [None])[0] \
            or f"script:{spk['hex'][:40]}"
        outs.append([sats, who])
    return {
        "height": block["height"], "hash": block["hash"], "time": block["time"],
        "difficulty": block["difficulty"], "bits": block["bits"], "ntx": block["nTx"],
        "coinbase": cb["vin"][0].get("coinbase", ""), "outputs": outs,
    }


def load_cache(path):
    if not path.exists():
        return []
    with open(path) as f:
        records = [json.loads(line) for line in f if line.strip()]
    for r in records:
        r.pop("tag", None)  # computed on load, not stored
    return records


def save_cache(path, records):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        for r in records:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    tmp.replace(path)


def sync(rpc, cache_path):
    """Bring the local cache up to the node's tip; return all block records."""
    records = load_cache(cache_path)
    tip = rpc.call("getblockcount")

    # Drop cached blocks that are no longer on the node's best chain.
    records = [r for r in records if r["height"] <= tip]
    while records:
        h = records[-1]["height"]
        if h <= tip and rpc.call("getblockhash", h) == records[-1]["hash"]:
            break
        back = min(len(records), max(1, len(records) // 64), 100)
        print(f"  reorg or different chain at height {h}: dropping {back} cached blocks",
              file=sys.stderr)
        del records[-back:]

    # The genesis coinbase cannot be fetched over RPC and pays no miner.
    start = records[-1]["height"] + 1 if records else 1
    if start > tip:
        return records
    print(f"  fetching coinbases for heights {start}..{tip} ({tip - start + 1} blocks)",
          file=sys.stderr)
    t0, step = time.time(), 2000
    for lo in range(start, tip + 1, step):
        heights = range(lo, min(tip, lo + step - 1) + 1)
        hashes = rpc.batch([("getblockhash", [h]) for h in heights])
        blocks = rpc.batch([("getblock", [bh, 1]) for bh in hashes])
        cbs = rpc.batch([("getrawtransaction", [b["tx"][0], True, b["hash"]]) for b in blocks])
        records.extend(block_record(b, cb) for b, cb in zip(blocks, cbs))
        save_cache(cache_path, records)
        done = heights[-1] - start + 1
        rate = done / max(time.time() - t0, 1e-9)
        print(f"    {heights[-1]}/{tip}  ({rate:.0f} blocks/s)", file=sys.stderr)
    return records


# ---------------------------------------------------------------- analysis

def flag_min_difficulty(records):
    """Mark blocks far easier than the hardest block in their retarget epoch."""
    hardest = defaultdict(float)
    for r in records:
        e = r["height"] // EPOCH
        hardest[e] = max(hardest[e], r["difficulty"])
    for r in records:
        r["min_diff"] = r["difficulty"] * MIN_DIFF_RATIO < hardest[r["height"] // EPOCH]


def attribute(r, by):
    """[(miner, fraction of the block)] for one block."""
    outs = [(s, who) for s, who in r["outputs"] if s > 0]
    if by == "tag":
        return [(r["tag"] or "(no tag)", 1.0)]
    if not outs:
        return [("(no outputs)", 1.0)]
    if by == "address":
        return [(max(outs)[1], 1.0)]
    total = sum(s for s, _ in outs)
    share = defaultdict(float)
    for s, who in outs:
        share[who] += s / total
    return list(share.items())


def miner_table(blocks, by, period):
    """Per-miner work, block counts and most common tag, largest first."""
    work, count, tags = defaultdict(float), defaultdict(float), defaultdict(Counter)
    for r in blocks:
        w = r["difficulty"] * 2.0 ** 32
        for who, frac in attribute(r, by):
            work[who] += w * frac
            count[who] += frac
            tags[who][r["tag"]] += 1
    names = sorted(work, key=work.get, reverse=True)
    hr = np.array([work[n] / period for n in names])
    k = np.array([count[n] for n in names])
    top_tag = {n: tags[n].most_common(1)[0][0] for n in names}
    return names, hr, k, top_tag


def short(name, width=44):
    return name if len(name) <= width else name[:width - 3] + "..."


def report_header(info, records, blocks, mind, period):
    first, last = blocks[0], blocks[-1]
    fmt = lambda t: time.strftime("%Y-%m-%d %H:%M", time.gmtime(t))
    work = sum(r["difficulty"] for r in blocks) * 2.0 ** 32
    print(f"\n=== {info['chain']} ===")
    print(f"  chain tip             height {info['blocks']}, difficulty {info['difficulty']:.6g}")
    print(f"  analysed              heights {first['height']}..{last['height']}, "
          f"{fmt(first['time'])} to {fmt(last['time'])} UTC ({period / 86400:.1f} days)")
    n_all = len(blocks) + len(mind)
    print(f"  blocks                {n_all} ({len(mind)} min-difficulty, "
          f"{100 * len(mind) / max(n_all, 1):.0f}%)")
    print(f"  network hashrate      {fmt_hr(work / period)} (work of full-difficulty blocks "
          f"over the period)")
    print(f"                        = {work / period / 1e12 / S19_TH:.1f} S19s or "
          f"{work / period / 1e12 / BITAXE_TH:.0f} Bitaxe Gammas")


def report_min_diff(mind, by, n_all):
    if not mind:
        return
    c = Counter(who for r in mind for who, _ in attribute(r, by))
    print(f"  min-difficulty blocks: {len(mind)} by {len(c)} miners "
          f"(won by submitting first after 20 minutes, not by hashrate)")
    for who, n in c.most_common(5):
        print(f"    {n:>7} ({100 * n / len(mind):4.1f}%)  {short(who)}")


def report_top(names, hr, k, top_tag, n=15):
    total = hr.sum()
    print(f"  top miners")
    print(f"    {'miner':<46}{'blocks':>8}{'share':>8}{'hashrate':>13}{'S19s':>8}  tag")
    for name, h, b in list(zip(names, hr, k))[:n]:
        print(f"    {short(name):<46}{b:>8.4g}{100 * h / total:>7.1f}%{fmt_hr(h):>13}"
              f"{h / 1e12 / S19_TH:>8.2f}  {short(top_tag[name], 30)}")


def report_periods(blocks, by):
    """Miner count and concentration per month (or per week for short spans)."""
    span = blocks[-1]["time"] - blocks[0]["time"]
    weekly = span < 90 * 86400
    fmt = "%Y-W%W" if weekly else "%Y-%m"
    groups = defaultdict(list)
    for r in blocks:
        groups[time.strftime(fmt, time.gmtime(r["time"]))].append(r)
    if len(groups) < 2:
        return
    print(f"  by {'week' if weekly else 'month'}")
    print(f"    {'period':<10}{'blocks':>8}{'miners':>8}{'hashrate':>13}{'largest':>9}"
          f"{'for >50%':>10}{'gini':>7}")
    for p, rs in sorted(groups.items()):
        t = max(rs[-1]["time"] - rs[0]["time"], 1)
        _, hr, _, _ = miner_table(rs, by, t)
        print(f"    {p:<10}{len(rs):>8}{len(hr):>8}{fmt_hr(hr.sum()):>13}"
              f"{100 * hr[0] / hr.sum():>8.1f}%{nakamoto(hr):>10}{gini(hr):>7.3f}")


def plot_simple(title, hr, path):
    """Hashrate histogram and CCDF without fitted models."""
    fig, (ax_h, ax_c) = plt.subplots(1, 2, figsize=(13, 4.2))
    bins = np.logspace(np.log10(hr.min()) - 0.1, np.log10(hr.max()) + 0.1, 25)
    ax_h.hist(hr, bins=bins, color="#bcc9d1", edgecolor="white", label=f"{len(hr)} miners")
    ax_h.set_xscale("log")
    ax_h.set_xlabel("miner hashrate (H/s)")
    ax_h.set_ylabel("miners")
    ax_h.set_title(f"{title}: miners by hashrate")
    ax_h.legend(fontsize=8)
    xs = np.sort(hr)
    ax_c.loglog(xs, 1 - np.arange(len(xs)) / len(xs), ".", color="#333", ms=4)
    ax_c.set_xlabel("miner hashrate (H/s)")
    ax_c.set_ylabel("fraction of miners >= x")
    ax_c.set_title(f"{title}: CCDF")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- main

def main():
    env = os.environ.get
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rpc-url", default=env("BITCOIN_RPC_URL"),
                    help="e.g. http://127.0.0.1:48332 (env BITCOIN_RPC_URL)")
    ap.add_argument("--rpc-user", default=env("BITCOIN_RPC_USER"))
    ap.add_argument("--rpc-password", default=env("BITCOIN_RPC_PASSWORD"),
                    help="prefer the BITCOIN_RPC_PASSWORD environment variable")
    ap.add_argument("--rpc-cookie", default=env("BITCOIN_RPC_COOKIE"),
                    help="path to bitcoind's .cookie file (env BITCOIN_RPC_COOKIE)")
    ap.add_argument("--by", choices=("address", "tag", "outputs"), default="address",
                    help="how blocks are attributed to miners (default address)")
    ap.add_argument("--days", type=float, help="analyse only the last N days")
    ap.add_argument("--epochs", type=int,
                    help="analyse only the last N difficulty retarget epochs (2016 blocks)")
    ap.add_argument("--from-height", type=int)
    ap.add_argument("--to-height", type=int)
    ap.add_argument("--top", type=int, default=15, help="miners to list (default 15)")
    ap.add_argument("--no-sync", action="store_true",
                    help="analyse the local cache without contacting the node")
    ap.add_argument("--data", type=Path, default=HERE / "data", help="coinbase cache directory")
    ap.add_argument("--out", type=Path, default=HERE / "output",
                    help="directory for the plot and per-miner CSV")
    args = ap.parse_args()
    args.data.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)

    if args.no_sync:
        caches = sorted(args.data.glob("*-coinbases.jsonl"))
        if len(caches) != 1:
            sys.exit(f"--no-sync needs exactly one cache in {args.data}, found {len(caches)}")
        cache = caches[0]
        records = load_cache(cache)
        info = {"chain": cache.name.split("-coinbases")[0], "blocks": records[-1]["height"],
                "difficulty": records[-1]["difficulty"]}
    else:
        if not args.rpc_url:
            sys.exit("give --rpc-url or set BITCOIN_RPC_URL")
        rpc = RPC(args.rpc_url, args.rpc_user, args.rpc_password, args.rpc_cookie)
        info = rpc.call("getblockchaininfo")
        if info["chain"] != "testnet5":
            print(f"  note: the node is on '{info['chain']}', not testnet5", file=sys.stderr)
        cache = args.data / f"{info['chain']}-coinbases.jsonl"
        records = sync(rpc, cache)
    if not records:
        sys.exit("no blocks")

    flag_min_difficulty(records)
    for r in records:
        r["tag"] = coinbase_tag(r["coinbase"])
    sel = records
    if args.from_height is not None:
        sel = [r for r in sel if r["height"] >= args.from_height]
    if args.to_height is not None:
        sel = [r for r in sel if r["height"] <= args.to_height]
    if args.epochs and sel:
        first_epoch = sel[-1]["height"] // EPOCH - args.epochs + 1
        sel = [r for r in sel if r["height"] // EPOCH >= first_epoch]
    if args.days and sel:
        cutoff = sel[-1]["time"] - args.days * 86400
        sel = [r for r in sel if r["time"] >= cutoff]
    sel = [r for r in sel if r["height"] > 0]  # the genesis coinbase is not a miner
    blocks = [r for r in sel if not r["min_diff"]]
    mind = [r for r in sel if r["min_diff"]]
    if len(blocks) < 2:
        sys.exit("fewer than two full-difficulty blocks in the selection")
    period = blocks[-1]["time"] - blocks[0]["time"]

    report_header(info, records, blocks, mind, period)
    names, hr, k, top_tag = miner_table(blocks, args.by, period)
    unit = hr.sum() / len(blocks)  # hashrate that finds one expected block in the period
    print(f"  attribution           by {args.by}")
    report_distribution(hr, np.round(k) if args.by == "outputs" else k, unit,
                        event="block", whole="network")
    report_min_diff(mind, args.by, len(sel))
    report_top(names, hr, k, top_tag, args.top)
    report_periods(blocks, args.by)

    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    title = f"{info['chain']} by {args.by}"
    png = args.out / f"{info['chain']}-{args.by}-{stamp}.png"
    diffs = [r["difficulty"] for r in blocks]
    mixed = max(diffs) > 1.05 * min(diffs)
    if args.by != "outputs" and len(hr) >= MIN_MINERS_TO_FIT and not mixed:
        fits = fit_models(k.astype(int), unit)
        report_fits(fits, event="block")
        plot([(title, k.astype(int), unit, period, fits)], png, event="block")
    else:
        why = ("block counts are fractional when blocks are split across outputs"
               if args.by == "outputs" else
               f"fewer than {MIN_MINERS_TO_FIT} miners" if len(hr) < MIN_MINERS_TO_FIT else
               f"difficulty varies {min(diffs):.3g} to {max(diffs):.3g} in the selection, so "
               "block counts do not track hashrate; use --epochs 1 (one difficulty)")
        print(f"  no distribution fitted: {why}")
        plot_simple(title, hr, png)
    csv_path = args.out / f"{info['chain']}-{args.by}-{stamp}.csv"
    write_csv(csv_path, names, hr, k, event="block")
    print(f"\nplot: {png}\nper-miner CSV: {csv_path}\ncache: {cache}")


if __name__ == "__main__":
    main()
