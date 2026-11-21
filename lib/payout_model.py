"""
payout_model.py -- shared model for the p2poolv2 coinbase payout analysis.

A block's coinbase can carry at most K miner outputs, but the PPLNS window
holds more miners than that. Each scheme maps the window weights w (sum = 1)
to a payout vector (sum = 1, at most K non-zero entries).

Every scheme is one member of the family (N, M, kind):
    the N largest weights are paid exactly (their PPLNS share),
    the rest ("tail", total weight T) is settled through M raffle slots.

    kind = 'wr'            M independent weighted draws, each pays T/M
           'sys'           one evenly spaced weighted draw: M points spaced T/M
                           apart on the cumulative tail weights, random offset,
                           each pays T/M (M = 1 is a single weighted draw)
           'wor_equal'     M distinct winners (weighted, no replacement), T/M each
           'wor_prorata'   M distinct winners, pot T split pro rata among them
           'wor_included'  M distinct winners, whole reward split pro rata among
                           top N + winners (excluded weight redistributed)

    option 1  = (K-1, 1, sys)                      spec name 'opt1'
    option 2  = (K-M, M, *), fixed split           'opt2_<kind>:<M>'
    option 2  adaptive (recommended)               'adaptive'
                N is set per block: pay a miner exactly while its weight is
                above (remaining weight) / (remaining slots)
    option 3  = (0, K, wr | sys)                   'opt3_wr', 'opt3_sys'
    option 4  = any of the above with K chosen per block by the finder

Assumptions shared by all simulations
    Bitcoin network: 1,000 EH/s, 3.125 BTC subsidy + 0.021 BTC fees a block
    mainnet pool: 1 EH/s (0.1% of the network), so about 1 pool block a week;
    its smallest miner is one Antminer S19 (95 TH/s = 0.0095% of the pool)
    testnet5 finds 50 pool blocks a day
    share chain: 10 s shares, a late share earns 90% as an uncle
    miner populations are synthetic (see get_population) and never exceed
    MINER_LIMIT identities, attacker addresses included

Every "x% miner" in this model is x% of POOL hashrate, not of the network.
"""
import math
import numpy as np

# --- Bitcoin network, November 2026 (sources in sims/14-earnings/README.md) ---
NETWORK_EH = 1000.0           # network hashrate, EH/s (7-day averages 958-1,069)
SUBSIDY_BTC = 3.125
FEES_BTC = 0.021              # average fees per block (0.66% of block rewards)
REWARD_BTC = SUBSIDY_BTC + FEES_BTC
BTC_USD = 75_000.0            # for USD conversions only
# --- the mainnet pool ---
POOL_EH = 1.0                 # pool hashrate: 0.1% of the network
POOL_TH = POOL_EH * 1e6
S19_TH, S21_TH = 95.0, 200.0  # Antminer S19 (3,250 W) and S21 (3,500 W)
S19, S21 = S19_TH / POOL_TH, S21_TH / POOL_TH     # share of POOL: 0.0095%, 0.02%
BLOCKS_PER_DAY = {"testnet5": 50.0, "mainnet": 144.0 * POOL_EH / NETWORK_EH}
UNCLE_PENALTY = 0.10          # a share published late as an uncle keeps 90%
SHARE_SECONDS = 10.0
BTC_SHARES = 600.0 / SHARE_SECONDS    # share intervals per Bitcoin block
CAP_OLD = 13                  # taproot-size outputs that fit a 3,072-byte job
CAP_NEW = 60                  # same, for a 5,120-byte job
MINER_LIMIT = 1000            # most miners the p2p network is expected to carry
SIZES = (1e-2, 1e-3, S21, S19)        # reference miner sizes, share of POOL
SIZE_NOTE = ("shares are of POOL hashrate (mainnet pool = 1 EH/s = 0.1% of the "
             "network): 1% = 10 PH/s, 0.1% = 1 PH/s, S21 = 200 TH/s = 0.02%, "
             "S19 = 95 TH/s = 0.0095%")
SCRIPT_SIZE = dict(P2WPKH=31, P2SH=32, P2PKH=34, P2WSH=43, P2TR=43)

ATTACKERS = {
    "20%, 1 address": [0.20],
    "20% in 400 addresses": [0.0005] * 400,
    "5% in 50 addresses": [0.001] * 50,
    "1.5%, 1 address": [0.015],
}


def size_label(x):
    """Short label for a share of pool hashrate."""
    if abs(x - S19) < 1e-12:
        return "S19"
    if abs(x - S21) < 1e-12:
        return "S21"
    return f"{x * 100:g}%"


def s19_floor(w):
    """Drop miners smaller than one S19 in a 1 EH/s pool and renormalise.
    Shares only grow when miners are dropped, so one pass is enough."""
    w = np.sort(np.asarray(w, float))[::-1]
    for _ in range(50):
        keep = w / w.sum() >= S19 * (1 - 1e-9)
        if keep.all():
            break
        w = w[keep]
    return w / w.sum()


def label(name):
    """Readable name for a scheme spec."""
    if name == "opt1":
        return "option 1 (top + 1 random)"
    if name == "opt3_wr":
        return "option 3, independent draws"
    if name == "opt3_sys":
        return "option 3, evenly spaced draw"
    if name == "adaptive":
        return "option 2 adaptive"
    base, M = name.split(":")
    kind = base.split("_", 1)[1]
    return {"wr": f"option 2 fixed, {M} independent draws",
            "sys": f"option 2 fixed, {M} evenly spaced",
            "wor_equal": f"option 2, {M} distinct, equal prizes",
            "wor_prorata": f"option 2, {M} distinct, pro rata",
            "wor_included": f"option 2, {M} distinct, redistribute"}[kind]


def trim(pop, n):
    """The n largest miners of a population, renormalised."""
    keep = np.sort(pop)[::-1][:n]
    return keep / keep.sum()


def miner_stats(pop, x, K, name):
    """Put a miner holding share x into the population in place of its
    smallest member (so the miner count is unchanged; the others are scaled to
    1 - x) and return its per-block payout statistics under a scheme."""
    w = np.concatenate([trim(pop, len(pop) - 1) * (1 - x), [x]])
    N, M, kind = spec(w, K, name)
    a = marginals(w, N, M, kind)
    i = len(w) - 1
    var = max(a["ex2"][i] - x * x, 0.0)
    return dict(exact=bool(a["is_top"][i]), p_pay=float(a["p_pay"][i]),
                prize=float(a["slot"]), sd=math.sqrt(var), cv=math.sqrt(var) / x,
                infl=float(a["ex2"][i] / (x * x)), N=N, M=M, w=w, kind=kind)


def mainnet_population(rng, n_single, n_small=250, n_mid=25, n_farm=4):
    """A 1 EH/s pool, hashrate in TH/s by class:
      n_mid    small farms of 3 to 30 PH/s,
      n_small  miners with 2 to 20 S19-class machines,
      n_single miners with one machine (60% an S19, 40% an S21),
      n_farm   farms that share the rest of the pool's hashrate.
    Nobody is smaller than one S19. Returns weights sorted descending."""
    mid = np.exp(rng.uniform(np.log(3e3), np.log(30e3), n_mid))
    small = S19_TH * np.round(np.exp(rng.uniform(np.log(2.0), np.log(20.0), n_small)))
    split = rng.uniform(0.6, 1.4, n_farm)
    single = np.where(rng.random(n_single) < 0.6, S19_TH, S21_TH)
    rest = POOL_TH - mid.sum() - small.sum() - single.sum()
    farm = rest * split / split.sum()
    hr = np.concatenate([farm, mid, small, single])
    cls = np.array(["farm"] * n_farm + ["mid"] * n_mid +
                   ["small"] * n_small + ["single"] * n_single)
    o = np.argsort(-hr, kind="stable")
    return hr[o] / hr.sum(), cls[o], hr.sum()


def zipf_population(n, s):
    w = 1.0 / np.arange(1, n + 1) ** s
    return w / w.sum()


def get_population(name, seed=7):
    rng = np.random.default_rng(seed)
    if name == "mainnet":          # 1,000 miners (the network limit), 1 EH/s
        return mainnet_population(rng, 721)
    if name == "mainnet_500":      # 500 miners in the same 1 EH/s pool: fewer
        return mainnet_population(rng, 221)     # single machines, larger farms
    if name == "mainnet_500_mix":  # every second miner of the 1,000 by rank,
        w, cls, tot = mainnet_population(rng, 721)   # each twice the hashrate
        return w[::2] / w[::2].sum(), cls[::2], tot
    if name == "mainnet_small":    # same shape with fewer small miners, for speed:
        w, cls, tot = mainnet_population(rng, 721)
        keep = np.r_[0:29, 29:len(w):7]          # every farm, 1 in 7 of the rest
        return w[keep] / w[keep].sum(), cls[keep], tot
    if name == "testnet5":       # 124 miners: a few rigs, many small devices
        hr = np.concatenate([
            rng.uniform(300.0, 1500.0, 4),
            np.exp(rng.uniform(np.log(50.0), np.log(250.0), 20)),
            np.exp(rng.uniform(np.log(0.5), np.log(20.0), 100))])
        cls = np.array(["small"] * 4 + ["asic"] * 20 + ["home"] * 100)
        o = np.argsort(-hr)
        return hr[o] / hr.sum(), cls[o], hr.sum()
    raise ValueError(name)


def adaptive_N(w, K):
    """Water-filling: number of miners paid exactly under the threshold rule."""
    ws = np.sort(w)[::-1]
    n = len(ws)
    if n <= K:
        return n
    tail = float(ws.sum())
    N = 0
    while N < K - 1 and ws[N] > tail / (K - N):
        tail -= ws[N]
        N += 1
    return N


def spec(w, K, name):
    """-> (N, M, kind)"""
    if name == "opt1":
        return K - 1, 1, "sys"
    if name.startswith("opt2"):
        base, M = name.split(":")
        M = int(M)
        return K - M, M, base.split("_", 1)[1]
    if name == "opt3_wr":
        return 0, K, "wr"
    if name == "opt3_sys":
        return 0, K, "sys"
    if name == "adaptive":
        N = adaptive_N(w, K)
        return N, K - N, "sys"
    raise ValueError(name)


def top_mask(w, N):
    m = np.zeros(len(w), bool)
    m[np.argsort(-w, kind="stable")[:N]] = True
    return m


def marginals(w, N, M, kind):
    """Closed-form per-miner payout moments for the unbiased kinds."""
    n = len(w)
    is_top = top_mask(w, N)
    T = float(w[~is_top].sum())
    p_pay = np.ones(n)
    ex2 = w ** 2
    slot = 0.0
    if T > 0 and M > 0:
        t = ~is_top
        p = w[t] / T
        slot = T / M
        if kind == "wr":
            p_pay[t] = 1 - (1 - p) ** M
            ex2[t] = slot ** 2 * (M * p * (1 - p) + (M * p) ** 2)
        elif kind == "sys":
            mp = M * p
            f = mp - np.floor(mp)
            p_pay[t] = np.minimum(1.0, mp)
            ex2[t] = w[t] ** 2 + slot ** 2 * f * (1 - f)
        else:
            raise ValueError("no closed form for " + kind)
    return dict(is_top=is_top, T=T, slot=slot, p_pay=p_pay, ex2=ex2)


def sys_hits(v, M, B, rng, keys=None, u01=None):
    """Systematic PPS sample: hits per tail miner, order salted per block."""
    nt = len(v)
    step = v.sum() / M
    if keys is None:
        keys = rng.random((B, nt))
    if u01 is None:
        u01 = rng.random(B)
    perm = np.argsort(keys, axis=1)
    cum = np.cumsum(v[perm], axis=1)
    u = (1e-12 + (1 - 2e-12) * u01[:, None]) * step
    hi = np.floor((cum - u) / step)
    hi[:, -1] = M - 1
    lo = np.concatenate([np.full((B, 1), -1.0), hi[:, :-1]], axis=1)
    hits = np.empty((B, nt))
    np.put_along_axis(hits, perm, hi - lo, axis=1)
    return hits


def sample(w, N, M, kind, B, rng, keys=None, u01=None):
    n = len(w)
    is_top = top_mask(w, N)
    pay = np.zeros((B, n))
    pay[:, is_top] = w[is_top]
    tidx = np.where(~is_top)[0]
    v = w[tidx]
    nt = len(v)
    if nt == 0:
        return pay
    T = v.sum()
    if kind == "wr":
        pay[:, tidx] = rng.multinomial(M, v / T, size=B) * (T / M)
    elif kind == "sys":
        k = None if keys is None else keys[:, tidx]
        pay[:, tidx] = sys_hits(v, M, B, rng, k, u01) * (T / M)
    elif kind.startswith("wor"):
        if nt <= M:
            pay[:, tidx] = v
            return pay
        g = np.log(v) + rng.gumbel(size=(B, nt))       # Gumbel top-M trick
        win = np.argpartition(-g, M - 1, axis=1)[:, :M]
        wv = v[win]
        if kind == "wor_equal":
            amt = np.full((B, M), T / M)
        elif kind == "wor_prorata":
            amt = T * wv / wv.sum(1, keepdims=True)
        elif kind == "wor_included":
            denom = w[is_top].sum() + wv.sum(1, keepdims=True)
            amt = wv / denom
            pay[:, is_top] = w[is_top] / denom
        else:
            raise ValueError(kind)
        tp = np.zeros((B, nt))
        np.put_along_axis(tp, win, amt, axis=1)
        pay[:, tidx] = tp
    else:
        raise ValueError(kind)
    return pay


def mc(w, N, M, kind, B, rng, att=None, chunk=2000):
    """Monte Carlo moments; optionally the per-block total of an identity set."""
    n = len(w)
    s1 = np.zeros(n)
    s2 = np.zeros(n)
    pp = np.zeros(n)
    tot = []
    done = 0
    while done < B:
        b = min(chunk, B - done)
        pay = sample(w, N, M, kind, b, rng)
        s1 += pay.sum(0)
        s2 += (pay ** 2).sum(0)
        pp += (pay > 0).sum(0)
        if att is not None:
            a = pay[:, att]
            tot.append(np.stack([a.sum(1), (a > 0).any(1)], axis=1))
        done += b
    out = dict(mean=s1 / B, ex2=s2 / B, p_pay=pp / B)
    if att is not None:
        out["att"] = np.concatenate(tot)
    return out


def with_attacker(w_honest, pieces, limit=MINER_LIMIT):
    """Honest population scaled to 1-h plus attacker identities `pieces`.
    If that would exceed `limit` identities, the attacker's addresses take the
    place of the smallest honest miners."""
    pieces = np.asarray(pieces, float)
    if len(w_honest) + len(pieces) > limit:
        w_honest = trim(w_honest, limit - len(pieces))
    w = np.concatenate([w_honest * (1 - pieces.sum()), pieces])
    att = np.zeros(len(w), bool)
    att[len(w_honest):] = True
    return w, att


def adaptive_payout(weights, reward, K, seed):
    """weights: {address(bytes): int work in window}; reward in sats;
    seed: bytes. Returns {address: sats}, at most K entries, sum == reward."""
    import hashlib
    items = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
    W = sum(v for _, v in items)
    if len(items) <= K:
        N, tail = len(items), []
    else:
        rest, N = W, 0
        # pay exactly while the next miner's share beats an even split of the rest
        while N < K - 1 and items[N][1] * (K - N) > rest:
            rest -= items[N][1]
            N += 1
        tail = items[N:]
    pay = {a: reward * v // W for a, v in items[:N]}
    if tail:
        M = K - N
        T = sum(v for _, v in tail)
        tail.sort(key=lambda kv: hashlib.sha256(seed + kv[0]).digest())
        U = 1 + int.from_bytes(hashlib.sha256(seed + b"offset").digest(), "big") % T
        prize = reward * T // (W * M)
        cum = 0
        for a, v in tail:                 # winners: points U + j*T on a line of length M*T
            hits = (M * (cum + v) - U) // T - (M * cum - U) // T
            cum += v
            if hits:
                pay[a] = prize * hits
    dust = reward - sum(pay.values())     # rounding remainder
    first = items[0][0] if N else max(pay, key=pay.get)
    pay[first] = pay.get(first, 0) + dust
    return pay


def size_stats(w, N, M, kind, a, x):
    """(P(paid per block), variance inflation) for a miner holding share x."""
    ws = np.sort(w)[::-1]
    exact = N >= len(w) or (N > 0 and x >= ws[N - 1])
    if exact or a["T"] <= 0:
        return 1.0, 1.0
    p, slot = x / a["T"], a["slot"]
    if kind == "wr":
        return 1 - (1 - p) ** M, 1 + (a["T"] - x) / (M * x)
    mp = M * p
    f = mp - math.floor(mp)
    return min(1.0, mp), 1 + slot ** 2 * f * (1 - f) / x ** 2


def fairness_row(w, K, nm, lam, horizon):
    """Summary of one scheme on a population. Waits and variance for the
    reference sizes are for a miner of that size put into the population in
    place of its smallest member (see miner_stats)."""
    N, M, kind = spec(w, K, nm)
    a = marginals(w, N, M, kind)
    p_any = 1 - np.exp(-lam * horizon * a["p_pay"])
    st = [miner_stats(w, x, K, nm) for x in SIZES]
    return dict(
        scheme=nm, N=N, M=M, prize=a["slot"],
        assured=int((a["p_pay"] > 0.999999).sum()),
        tot_var=float((a["ex2"] - w ** 2).sum()),
        paid_half=float((p_any >= 0.5).mean()),
        wait=[1 / (lam * q["p_pay"]) for q in st],
        infl=[q["infl"] for q in st],
    )


def attacker_X(w, att, N, M, kind, S, rng, chunk=2000):
    xs = []
    done = 0
    while done < S:
        b = min(chunk, S - done)
        xs.append(sample(w, N, M, kind, b, rng)[:, att].sum(1))
        done += b
    return np.concatenate(xs)


def stale_tip_gain(X, c, pen, rng, S=400_000):
    """Mine on whichever of the last c+1 tips pays you most; a non-block share
    on a stale tip is an uncle and loses `pen` of its value. Relative revenue
    gain = E[(max_j X_j - pen - X_0)+]."""
    d = rng.choice(X, size=(S, c + 1))
    return float(np.maximum(d[:, 1:].max(1) - pen - d[:, 0], 0).mean())


def withhold_gain(X, h, pen, rng, chains=20_000, steps=400):
    """Sit on a favourable seed: withhold own shares whose seed pays less.
    Estimated against honest play on the same random draws."""
    best = 0.0
    for theta in (pen, 0.75 * pen, 0.5 * pen):
        cur = rng.choice(X, chains)
        gain = 0.0
        for _ in range(steps):
            new = rng.choice(X, chains)
            hold = (rng.random(chains) < h) & (cur - new > theta)
            cur = np.where(hold, cur, new)
            gain += (cur - new).mean() - pen * hold.mean()
        best = max(best, gain / steps / X.mean())
    return float(best)


def k_choice_gain(w, att, base, Ks, rng, B=30_000, chunk=1500):
    """Relative revenue gain when the finder picks the cap per template."""
    h, n, acc, done = w[att].sum(), len(w), 0.0, 0
    while done < B:
        keys = rng.random((chunk, n))
        u01 = rng.random(chunk)
        xs = []
        for K in Ks:
            if K is None:
                xs.append(np.full(chunk, h))
            else:
                N, M, kind = spec(w, K, base)
                xs.append(sample(w, N, M, kind, chunk, rng,
                                 keys=keys, u01=u01)[:, att].sum(1))
        acc += np.max(xs, axis=0).sum()
        done += chunk
    return float(acc / B - h)


# ---- Bitcoin-hash seed helpers -------------------------------------------
def raffle_X(counts, n_h, K, rng):
    """One adaptive raffle on integer share counts; attacker ids are >= n_h.
    Returns the attacker's payout as a fraction of the block."""
    idx = np.nonzero(counts)[0]
    c = counts[idx].astype(float)
    tot = c.sum()
    if len(c) <= K:
        return c[idx >= n_h].sum() / tot
    o = np.argsort(-c, kind="stable")
    cs = c[o]
    tail, N = tot, 0
    while N < K - 1 and cs[N] * (K - N) > tail:
        tail -= cs[N]
        N += 1
    M = K - N
    att_sorted = idx[o] >= n_h
    x = cs[:N][att_sorted[:N]].sum()
    v, av = cs[N:], att_sorted[N:]
    p = rng.permutation(len(v))
    step = tail / M
    hi = np.floor((np.cumsum(v[p]) - rng.random() * step) / step)
    hi[-1] = M - 1
    hits = np.diff(hi, prepend=-1.0)
    return (x + hits[av[p]].sum() * step) / tot


def hop_sim(pop, pieces, K, mode, rng, W=20_000, policy="hop", stay=0.0,
            cost=0.0, rent=0.0, rent_premium=0.05, n_units=None):
    """Attacker revenue per unit of own hashrate, relative to fair (= 1).
    mode 'share': a new raffle with every share (per-share seed).
    mode 'btc'  : one raffle per Bitcoin block, window frozen at its start.
    policy 'hop': mine here only while the current raffle pays at least the
    attacker's window weight minus `cost`; otherwise mine elsewhere for
    (1 - cost) of fair value, staying anyway with probability `stay`.
    `rent` > 0 adds rented hashrate (multiple of own) while in the money by
    more than `rent_premium`, bought at fair value times (1 + rent_premium)."""
    g = float(sum(pieces))
    if len(pop) + len(pieces) > MINER_LIMIT:      # attacker addresses displace
        pop = trim(pop, MINER_LIMIT - len(pieces))  # the smallest honest miners
    hr_h = pop * (1 - g)
    n_h, n_a = len(pop), len(pieces)
    cdf = np.cumsum(hr_h) / hr_h.sum()
    H_o = 1 - g
    win = np.empty(W, np.int64)
    k0 = rng.random(W) < g
    win[k0] = n_h + rng.integers(0, n_a, k0.sum())
    win[~k0] = np.searchsorted(cdf, rng.random((~k0).sum()))
    counts = np.bincount(win, minlength=n_h + n_a).astype(np.int64)
    cA = int(counts[n_h:].sum())
    ptr = 0
    luck = mined = outside = rentc = tm = 0.0
    if n_units is None:
        n_units = 260_000 if mode == "share" else 90_000
    burn = 3 * W if mode == "share" else int(3 * W / BTC_SHARES)
    for t in range(burn + n_units):
        X = raffle_X(counts, n_h, K, rng)
        wA = cA / W
        here = True
        if policy == "hop" and X - wA < -cost and rng.random() >= stay:
            here = False
        r = rent * g if (rent > 0 and X - wA > rent_premium) else 0.0
        g_here = g if here else 0.0
        H = H_o + g_here + r
        if mode == "share":
            dur, n_sh = 1.0 / H, 1
        else:
            dur = rng.exponential(BTC_SHARES)
            n_sh = rng.poisson(H * dur)
        if t >= burn:
            # Revenue = shares found in this raffle state * X. Split it into the
            # fair value of the attacker's own window weight (wA, which in a
            # steady state equals the shares it mines) and the part that comes
            # from timing: H * dur * (X - wA). Using the expected shares mined
            # instead of the realised weight path removes the slow random walk
            # of the window weight from the estimate.
            luck += H * dur * (X - wA)
            mined += (g_here + r) * dur
            outside += (g - g_here) * (1 - cost) * dur
            rentc += r * (1 + rent_premium) * dur
            tm += dur
        if n_sh:
            ka = rng.random(n_sh) < (g_here + r) / H
            new = np.where(ka, n_h + rng.integers(0, n_a, n_sh),
                           np.searchsorted(cdf, rng.random(n_sh)))
            if n_sh >= W:
                new = new[-W:]
            pos = (ptr + np.arange(len(new))) % W
            old = win[pos]
            np.subtract.at(counts, old, 1)
            np.add.at(counts, new, 1)
            cA += int((new >= n_h).sum() - (old >= n_h).sum())
            win[pos] = new
            ptr = (ptr + len(new)) % W
    return (luck + mined + outside - rentc) / tm / g - 1, cA / W


def plant_interval(rng, honest_hr, a, K, W, optimise, n_addr):
    """One Bitcoin interval, seed known, window NOT frozen. The attacker holds
    its weight in `n_addr` addresses and may credit each new share to any of
    them. With `optimise` it credits the address that wins most raffle slots
    under the known seed; otherwise a random one. Returns time-averaged slots
    won and the prize as a share of the block."""
    n_h = len(honest_hr)
    cnt = rng.multinomial(int(W * (1 - a)), honest_hr)
    per = W * a / n_addr
    allw = np.concatenate([cnt, np.full(n_addr, per)]).astype(float)
    N = adaptive_N(allw / allw.sum(), K)
    order = np.argsort(-cnt, kind="stable")
    exact = set(order[:N].tolist())
    M = K - N
    ids = np.array([i for i in range(n_h) if cnt[i] > 0 and i not in exact]
                   + [-1] * n_addr)
    width = np.array([cnt[i] for i in ids if i >= 0] + [per] * n_addr, float)
    perm = rng.permutation(len(ids))                 # seed-salted order
    ids, width = ids[perm], width[perm]
    cand = np.where(ids < 0)[0] + 1                  # boundary after each own address
    u01 = rng.random()
    n_ev = max(1, rng.poisson(BTC_SHARES))
    who = rng.random(n_ev) < a
    hon = rng.choice(n_h, n_ev, p=honest_hr)
    drop = rng.choice(n_h, n_ev, p=cnt / cnt.sum())
    rpick = rng.integers(0, n_addr, n_ev)
    wins_t = []
    for e in range(n_ev):
        T = width.sum()
        if who[e]:
            k = int(cand[rpick[e]])
            if optimise:
                # crediting the address before boundary k gives it the unit
                # [S_k, S_k + 1) and shifts every later address by one share
                g = (u01 + np.arange(M)) * (T + 1) / M
                ends = np.cumsum(width)
                S = (ends - width)[cand - 1] + width[cand - 1]
                is_att = np.concatenate([ids < 0, [False]])
                i0 = np.minimum(np.searchsorted(ends, g, side="right"), len(ids))
                i1 = np.minimum(np.searchsorted(ends, g - 1, side="right"), len(ids))
                before = g[:, None] < S[None, :]
                inside = (~before) & (g[:, None] < S[None, :] + 1)
                wins = (before * is_att[i0][:, None] + inside
                        + (~before & ~inside) * is_att[i1][:, None]).sum(0)
                k = int(cand[np.argmax(wins)])
            width[k - 1] += 1
        else:
            j = np.where(ids == hon[e])[0]
            if len(j):
                width[j[0]] += 1
        j = np.where(ids == drop[e])[0]              # oldest share leaves
        if len(j) and width[j[0]] > 1:
            width[j[0]] -= 1
        T = width.sum()
        g = (u01 + np.arange(M)) * T / M
        win = np.minimum(np.searchsorted(np.cumsum(width), g, side="right"),
                         len(ids) - 1)
        wins_t.append((ids[win] < 0).sum())
    return float(np.mean(wins_t)), T / M / W


# ---- byte-budget rule -----------------------------------------------------
def byte_rule(w, s, B, per_byte=True):
    """-> (exact mask, p inclusion prob, prize share of reward when paid)."""
    n = len(w)
    key = w / s if per_byte else w            # what is compared to the threshold
    order = np.argsort(-key, kind="stable")
    exact = np.zeros(n, bool)
    if s.sum() <= B:                          # everyone fits
        return np.ones(n, bool), np.ones(n), w.copy()
    rest_b = float(B)
    i = 0
    while True:
        tail = order[i:]
        wt, st = w[tail], s[tail]
        spread = st.max() - st.min()
        # expected bytes per winner: sum(p*s)/sum(p), p proportional to key
        per_win = (wt.sum() / (wt / st).sum()) if per_byte \
            else ((wt * st).sum() / wt.sum())
        M = int((rest_b - spread) / per_win + 1e-9)   # integers in real code
        thr = key[tail].sum() / M if M > 0 else np.inf
        nxt = order[i]
        # can the next miner be paid exactly and still leave one raffle slot?
        after = order[i + 1:]
        room = rest_b - s[nxt] - (s[after].max() - s[after].min()) >= s[after].max()
        if key[nxt] > thr and room:
            exact[nxt] = True
            rest_b -= s[nxt]
            i += 1
        else:
            break
    p = np.ones(n)
    prize = w.copy()
    t = ~exact
    p[t] = np.minimum(1.0, key[t] / thr)
    prize[t] = w[t] / p[t]
    return exact, p, prize


def byte_draw(w, s, exact, p, prize, blocks, rng):
    """Monte Carlo of the systematic draw; returns payouts and bytes used."""
    tail = np.where(~exact)[0]
    keys = s[tail][None, :] * 10.0 + rng.random((blocks, len(tail)))
    perm = np.argsort(keys, axis=1)           # by size, then salted order
    cum = np.cumsum(p[tail][perm], axis=1)
    u = rng.random((blocks, 1))
    hi = np.floor(cum - u)
    lo = np.concatenate([np.full((blocks, 1), -1.0), hi[:, :-1]], axis=1)
    hits = np.empty_like(hi)
    np.put_along_axis(hits, perm, hi - lo, axis=1)
    pay = np.zeros((blocks, len(w)))
    pay[:, exact] = w[exact]
    pay[:, tail] = hits * prize[tail]
    used = s[exact].sum() + (hits * s[tail]).sum(1)
    return pay, used
