# Monero P2Pool hashrate distribution

How miner hashrate is distributed on the three Monero P2Pool sidechains (main, mini, nano): how concentrated each pool is, how far apart the largest and smallest miners are, and lognormal and log-logistic models of each pool for use in simulations.

```
uv run xmr/hashrate_distribution.py                       # all pools, last 24 h
uv run xmr/hashrate_distribution.py --hours 72 --pools mini nano
```

`uv run` installs numpy, scipy and matplotlib from the inline script metadata. Each run prints the statistics below and writes a plot and per-miner CSVs to `xmr/output/`. The files are timestamped, so repeated runs track the distribution over time.

## Method

- **Data**: the share history from the p2pool.observer API (`/api/side_blocks_in_window`), with uncles included. The API returns up to about 60,000 shares, which is a week on main and mini. Above that it silently returns about an hour, so the script caps the request and warns if coverage falls short.
- **Hashrate**: a miner's hashrate is the sum of the difficulty of their shares divided by the length of the period. Miners are identified by payout address.
- **Fits**: small miners are measured badly. A miner with k shares has a relative error of about 1/√k, and miners below one expected share are often not seen at all. Fitting straight to the estimates would put the distribution's mass on that detection floor. Instead each model is fitted to the share counts:

  `h ~ lognormal(mu, sigma)` or `h ~ log-logistic(mu, c)`, `k | h ~ Poisson(h · period / mean share difficulty)`, observed only if `k ≥ 1`

  The fitted parameters therefore describe true hashrate in H/s, and can be used directly to generate miner populations. In both models `mu` is the log of the median hashrate, and both are symmetric in log hashrate. The difference is in the tail:
  - **lognormal**: has a normal shape in log hashrate. Its tail thins out quickly and every moment is finite.
  - **log-logistic**: has a logistic shape in log hashrate, which gives it a power-law tail, P(h > x) ~ x^−c.

  Both have two parameters and are compared by AIC. A chi-square test of observed against predicted share-count histograms checks each fit.
- **Sampling**: draw a miner's hashrate as `exp(mu + sigma·Z)` with Z standard normal (lognormal), or as `exp(mu) · (u/(1−u))^(1/c)` with u uniform on (0, 1) (log-logistic).

## Findings (24 h to 2026-11-21)

### Head-heavy in hashrate, tail-heavy in headcount

The answer to "head-heavy or tail-heavy?" depends on what you count:

- **Statistically, all three pools are heavy-tailed.** The right tail, the big miners, falls off far more slowly than an exponential would.
- **In hashrate, they are head-heavy.** A few large miners hold most of the hashrate.
- **In headcount, they are tail-heavy.** Most miners are small and together hold very little.

|                        | main            | mini             | nano            |
|------------------------|-----------------|------------------|-----------------|
| Miners seen            | 168             | 1,124            | 574             |
| Pool hashrate          | 448 MH/s        | 37.5 MH/s        | 5.5 MH/s        |
| Median miner           | 152 kH/s        | 12.8 kH/s        | 5.7 kH/s        |
| Largest miner          | 74 MH/s (16.6%) | 4.9 MH/s (13.2%) | 186 kH/s (3.4%) |
| Top 10 miners hold     | 70.5%           | 24.3%            | 20.0%           |
| Top 1% of miners hold  | 30.4%           | 25.1%            | 14.2%           |
| Top 10% of miners hold | 83.5%           | 57.7%            | 46.1%           |
| Bottom 50% hold        | 1.4%            | 10.1%            | 15.5%           |
| Miners for >50%        | 5               | 72               | 70              |
| Gini (seen miners)     | 0.88            | 0.67             | 0.56            |

- **main is the most head-heavy.** 17 miners hold 83% of the hashrate and 5 hold over half. The bottom half of its miners holds 1.4% between them.
- **mini sits in between.** It has a real middle class: the bottom half holds 10% and it takes 72 miners to reach 50%. One miner still holds 13%, and a handful of large miners sit above the fitted curve.
- **nano is the flattest.** Its largest miner holds 3.4% and is only 33 times the median. It is the closest of the three to "everyone is roughly the same size".

### Largest against smallest miners

|                                 | main    | mini     | nano     |
|---------------------------------|---------|----------|----------|
| Largest ÷ smallest seen         | 1,510×  | 1,242×   | 100×     |
| Largest ÷ median                | 488×    | 388×     | 33×      |
| Smallest seen (detection floor) | 49 kH/s | 4.0 kH/s | 1.9 kH/s |

- **The gap is large, and larger than it looks.** The smallest visible miner sits at the detection floor (one share in the period), so the ratios above are lower bounds. Smaller miners exist but found no share; the fits put a few hundred of them on each pool.
- **Across all three pools together**, hashrate runs from about 1.9 kH/s to 74 MH/s, roughly 40,000 times. That is about one CPU against a sizeable farm.

### The pools sort miners by size

Each pool covers a band of miner sizes, and the bands overlap:

| Pool | Smallest seen | Largest  |
|------|---------------|----------|
| main | 49 kH/s       | 74 MH/s  |
| mini | 4 kH/s        | 4.9 MH/s |
| nano | 1.9 kH/s      | 186 kH/s |

Miners choose a pool where they can find shares often enough, which puts small miners on nano and mini. Large miners have no reason to stay on nano, so its top is cut off, which is why nano looks flat. Each pool's distribution is one slice of a single, much wider Monero P2Pool population.

### Fitted distributions

| Pool | Model        | mu   | Spread   | Median   | Gini incl. unseen | ΔAIC | Chi-square p | Unseen miners |
|------|--------------|------|----------|----------|-------------------|------|--------------|---------------|
| main | lognormal    | 6.24 | σ = 4.20 | 511 H/s  | 0.997             | 0    | 0.08         | ~772          |
| main | log-logistic | 9.06 | c = 0.56 | 8.6 kH/s | 1.0               | 1.0  | 0.11         | ~316          |
| mini | log-logistic | 8.98 | c = 1.27 | 7.9 kH/s | 0.79              | 0    | 0.59         | ~405          |
| mini | lognormal    | 8.79 | σ = 1.51 | 6.6 kH/s | 0.71              | 2.1  | 0.44         | ~516          |
| nano | log-logistic | 8.24 | c = 1.65 | 3.8 kH/s | 0.61              | 0    | 0.36         | ~162          |
| nano | lognormal    | 8.10 | σ = 1.19 | 3.3 kH/s | 0.60              | 9.7  | 0.007        | ~205          |

- **mini and nano: log-logistic fits best.** On nano the margin is decisive and the chi-square test rejects the lognormal. The difference is all at the top: the lognormal tail falls away from the largest miners, while the log-logistic's power-law tail follows them.
- **main: the two fit equally well, and neither is pinned down.** Most of main's miners sit near the detection floor, so the data say little about what lies below it. Both fits put the median well below the floor, and their counts of unseen miners differ by more than double. Use the fits for main's tail and the per-miner CSV for anything else.
- **Tail index c.** The log-logistic tail gets lighter down the pools: 0.56 on main, 1.27 on mini, 1.65 on nano. This matches the concentration figures above.
  - Below 1 (main), the model's mean is infinite. The largest miners hold a fixed share of the pool however many small miners join.
  - Between 1 and 2 (mini, nano), the mean is finite but the variance is infinite.
  - For simulations that need variances, cap the distribution at a maximum hashrate, such as the largest miner seen.
- **Which to use:**
  - **Lognormal** for the body of the distribution, and when finite moments make the analysis easier.
  - **Log-logistic** for anything that depends on the largest miners: their share of the pool, how many miners make up 50%, or crowding-out.
  - If a conclusion changes between the two models, it depends on the tail.
- The tables in this README come from runs a few minutes apart, so miner counts differ by one or two between sections.

### Caveats

- Miners are counted by payout address. One address can be a farm, or many users behind a proxy, and one person can use several addresses. That can make the head look bigger or smaller than it is.
- This is one 24-hour window. Large miners come and go, so the top-1% figures in particular move from day to day. Repeated runs show how stable they are.

### For p2poolv2

A Bitcoin pool will likely look like main or mini. A few miners would hold most of the hashrate, with a long tail of small miners. Those small miners are the ones a capped coinbase struggles to pay, and they are the population the payout options in [REPORT.md](../REPORT.md) are designed for.
