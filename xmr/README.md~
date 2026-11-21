# Monero P2Pool hashrate distribution

How miner hashrate is distributed on the three Monero P2Pool sidechains (main, mini, nano), and which distribution best describes it.

```
uv run xmr/hashrate_distribution.py                       # all pools, last 24 h
uv run xmr/hashrate_distribution.py --hours 72 --pools mini nano
```

`uv run` installs numpy, scipy and matplotlib from the inline script metadata. Each run writes a plot and per-miner CSVs to `xmr/output/`; the files are timestamped, so repeated runs track the distribution over time.

## Method

- **Data**: the share history from the p2pool.observer API (`/api/side_blocks_in_window`), with uncles included. The API returns up to about 60,000 shares, which is a week on main and mini.
- **Hashrate**: a miner's hashrate is the sum of the difficulty of their shares divided by the length of the period. Miners are identified by payout address.
- **Stats**: miner count, pool hashrate, mean, median and percentiles, the share held by the largest miner and by the top 10, the number of miners holding more than 50%, and the Gini coefficient.
- **Fitting**: small miners are measured badly. A miner with k shares has a relative error of about 1/√k, and miners below one expected share are often not seen at all. Fitting a distribution straight to the estimates rewards models that put their mass on that detection floor. Instead each candidate (lognormal, Pareto, Weibull, gamma, log-logistic, exponential) is fitted to the share counts:

  `h ~ distribution`, `k | h ~ Poisson(h · period / mean share difficulty)`, observed only if `k ≥ 1`

  The candidates are ranked by AIC. A chi-square test of observed against predicted share-count histograms checks each fit in absolute terms. Models within 2 AIC of the best are reported as tied.

## Findings (24 h to 2026-11-21)

| Pool | Miners seen | Best fit | Notes |
|---|---|---|---|
| main | 169 | no clear winner: Weibull, lognormal, Pareto and log-logistic are tied | Top 10 miners hold 70%; 5 miners hold over half. Too few miners above the one-share floor (51 kH/s) to tell the tails apart. |
| mini | 1,124 | log-logistic (shape 1.26, scale 7.8 kH/s), lognormal close behind | Chi-square p = 0.52. Power-law tail with index ≈ 1.3. |
| nano | 576 | log-logistic (shape 1.64, scale 3.8 kH/s), Pareto next (ΔAIC 3.9) | Chi-square p = 0.28. Flattest distribution: the largest miner holds 3%. |

The exponential and gamma distributions are rejected on every pool. The distribution is heavy-tailed: roughly lognormal in the body with a power-law tail. The number of miners too small to find a share in the period depends on which model is chosen, so the data cannot settle it.
