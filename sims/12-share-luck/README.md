# 12 · Small miners: share-finding luck stacked with the raffle

**Question.** The share chain has one global difficulty, so a small miner finds a share only now and then. Plain PPLNS pays that share a little from every block found while it sits in the 2-week window. Under a capped coinbase the share instead buys a chance in a raffle. What does that do to a small miner?

**Sizes.** Shares are of **pool** hashrate. The mainnet pool is 1 EH/s (0.1% of the network): 0.1% of the pool is 1 PH/s, one S21 is 0.02% and one S19, the smallest miner, is 0.0095%.

**Method.** Single miners are followed through time with three sources of luck together: their own shares (Poisson arrivals, 14-day window of 120,960 shares at 10 seconds each), pool blocks (Poisson) and the raffle (win with probability window weight ÷ prize). The uncapped coinbase is run on the same shares and blocks. Prize sizes come from option 2 with the adaptive split on the synthetic populations: 6.50% of the block at cap 13 and 0.80% at cap 60 on the 1,000-miner mainnet population.

**Run.** `python3 run.py > output.txt` (about 2 minutes). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result A: what one share is worth

Its expected payout is the same under every scheme: 5,243 sats on mainnet (2 pool blocks while it is in the window, at 3.146 BTC).

| One share on mainnet | Chance it ever pays | Amount per paying block |
|---|---|---|
| No cap | 86.7% | 2,601 sats |
| Raffle, cap 13 | 0.026% | 20.4 million sats |
| Raffle, cap 60 | 0.21% | 2.53 million sats |

On testnet5 about 700 pool blocks are found while a share is in the window, so the same share ever pays with 12% probability at cap 13 and 95% at cap 60.

## Result B: a miner followed for a year on mainnet

Payouts received in the year / chance of receiving none / spread of the year's income (standard deviation ÷ mean).

| Miner | Shares in window (mean) | Window empty | No cap | Raffle, cap 13 | Raffle, cap 60 |
|---|---|---|---|---|---|
| 0.1% of pool (1 PH/s) | 121 | never | 52.5 / 0% / 14% | 0.81 / 44.5% / 111% | 6.5 / 0.1% / 39% |
| One S21 | 24 | never | 52.6 / 0% / 15% | 0.16 / 85.3% / 250% | 1.31 / 27.0% / 87% |
| One S19 | 11.5 | never | 52.6 / 0% / 16% | 0.08 / 92.5% / 358% | 0.62 / 54.0% / 128% |

Total paid ÷ fair share was between 0.98 and 1.02 in every cell.

## What it shows

- **Expected income is unchanged.** The raffle pays a small miner the same on average as plain PPLNS would, with or without lumpy share counts.
- **The regular small payouts are gone.** With no cap one S19 is paid in every pool block, about 52 times a year. At cap 13 it is paid once in thirteen years on average, and has a 92.5% chance of nothing in a given year.
- **This comes from the cap, not from the choice of a raffle.** At cap 13 with four miners paid exactly there are 9 prizes per block, about 470 a year, for 996 other miners. No rule limited to 13 outputs can pay more often than that. The alternative to a raffle under the same cap is that miners left out of the coinbase get nothing; see the "redistribute" variant in [01](../01-expected-payout/README.md).
- **Share luck is minor once nobody is smaller than an S19.** An S19 holds 11.5 shares in the window on average and its window is never empty; share luck lifts its yearly spread from 14% to 16% with no cap. Once a raffle is in place the raffle dominates: the capped figures match the steady-weight results in [03](../03-variance-by-hashrate-share/README.md).
- **A larger cap helps a great deal.** At cap 60 one S19 receives 0.62 payouts a year instead of 0.08. [14](../14-earnings/README.md) carries this through to earnings and compares with other pools.

## Caveats

The window is taken as exactly 14 days of 10-second shares. Prize sizes are held fixed at their population values; a single small miner does not move them. The miner's hashrate is constant.

Back to the [report](../../REPORT.md).
