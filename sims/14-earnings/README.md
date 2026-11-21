# 14 · Earnings: p2poolv2 with a capped coinbase against today's pools

**Question.** What does a miner with one S19, one S21, or a larger operation earn on p2poolv2 under each capped payout scheme, and how does that compare with the pools miners use today?

**Sizes.** The pool is 1 EH/s, which is 0.1% of the Bitcoin network. Shares below are of the **pool** unless a column says "of network".

| Miner | Hashrate | Share of pool | Share of network |
|---|---|---|---|
| One Antminer S19 (the smallest miner) | 95 TH/s | 0.0095% | 0.0000095% |
| One Antminer S21 | 200 TH/s | 0.02% | 0.00002% |
| 0.1% of the pool | 1 PH/s | 0.1% | 0.0001% |
| 1% of the pool | 10 PH/s | 1% | 0.001% |
| 10% of the pool | 100 PH/s | 10% | 0.01% |

## Inputs

| Input | Value used | Source |
|---|---|---|
| Network hashrate | 1,000 EH/s | 7-day averages of 958 EH/s (10 Nov 2026) and 1,069 EH/s (2 Nov 2026); October average 1,024 EH/s (sources 1 and 2) |
| Block reward | 3.125 BTC subsidy + 0.021 BTC fees | fees were 0.66% of block rewards in October 2026 (source 1) |
| BTC price | $75,000 | $74,600 on 10 Nov 2026 (source 2); used only to convert to USD |
| Hashprice implied | $33.98 per PH/s per day | reported: $33.18 to $33.26 (source 1) |
| Pool | 1 EH/s, 52.6 blocks a year, one every 6.9 days | 0.1% of the network |
| S19 / S21 | 95 TH/s at 3,250 W / 200 TH/s at 3,500 W | source 3 |
| p2poolv2 pool fee | none | **assumed** |

Published terms of today's pools. The sources disagree on some fees, so the simulation uses two FPPS levels, 2% and 4%.

| Pool | Payout method | Published fee | Minimum payout |
|---|---|---|---|
| Foundry USA | FPPS | tiered, not public | by account |
| AntPool | FPPS or PPLNS | 2.5% to 4% FPPS; 0% PPLNS | 0.001 BTC |
| F2Pool | FPPS / PPS+ | 2.5% to 4% | 0.001 to 0.005 BTC |
| ViaBTC | PPS+ or PPLNS | 4% PPS+; 2% PPLNS | 0.0001 to 0.001 BTC |
| Braiins Pool | FPPS | 2% | 0.001 BTC on-chain; none over Lightning |
| Luxor | FPPS | 0% to 0.7% | 0.004 BTC |
| OCEAN | TIDES, paid in the coinbase | 2%; 1% with DATUM | about 0.01 BTC on-chain; none over Lightning |
| CKPool solo | solo | 2% | paid only on finding a block |

Sources for the pool terms: 4 and 5 in the list at the end.

**Method.** Expected earnings are hashrate ÷ network hashrate × 144 blocks × reward, less the pool fee. For p2poolv2 a year of pool blocks (Poisson, 52.6 expected) is simulated 400,000 times per case; in each block the miner is paid exactly, or wins a raffle prize with the probability the scheme gives it, on the 1,000-miner mainnet population. FPPS pools pay expected value whatever their luck. OCEAN is modelled as 2% of the network paying on its own luck. Solo pays only when the miner finds a Bitcoin block.

**Run.** `python3 run.py > output.txt` (a few seconds). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result A: what each miner earns before fees

| Miner | Sats a day | USD a day | Sats a year | USD a year | Share of one p2poolv2 block | Break-even power price |
|---|---|---|---|---|---|---|
| One S19 | 4,304 | 3.23 | 1,570,861 | 1,178 | 29,887 sats | $0.041 per kWh |
| One S21 | 9,060 | 6.80 | 3,307,075 | 2,480 | 62,920 sats | $0.081 per kWh |
| 1 PH/s | 45,302 | 33.98 | 16.5 million | 12,402 | 314,600 sats | |
| 10 PH/s | 453,024 | 339.77 | 165 million | 124,015 | 3.146 million sats | |
| 100 PH/s | 4,530,240 | 3,397.68 | 1,654 million | 1,240,153 | 31.46 million sats | |

Power costs the same whichever pool is used, so it does not enter the comparison.

## Result B: expected earnings by pool, sats a day

| Pool | One S19 | One S21 | 1 PH/s | 10 PH/s | 100 PH/s |
|---|---|---|---|---|---|
| FPPS pool, 2% fee | 4,218 | 8,879 | 44,396 | 443,964 | 4,439,635 |
| FPPS pool, 4% fee | 4,132 | 8,698 | 43,490 | 434,903 | 4,349,030 |
| OCEAN (TIDES), 2% fee | 4,218 | 8,879 | 44,396 | 443,964 | 4,439,635 |
| Solo via CKPool, 2% fee | 4,218 | 8,879 | 44,396 | 443,964 | 4,439,635 |
| p2poolv2, any scheme, no fee assumed | 4,304 | 9,060 | 45,302 | 453,024 | 4,530,240 |

Every unbiased scheme pays the same on average, so p2poolv2's expected earnings do not depend on the cap or the option. The difference from an FPPS pool is the fee: 86 to 172 sats a day for an S19.

## Result C: one year on p2poolv2, 1,000 miners

**One S19** (0.0095% of the pool), expected 1,570,861 sats a year:

| Scheme | Payouts a year | Sats per payout | No payout in 1 year | No payout in 3 years | Years to a 90% chance of one payout |
|---|---|---|---|---|---|
| No cap | 52.6 | 29,887 | 0% | 0% | 0 |
| Option 1, cap 13 | 0.01 | 127.3 million | 98.8% | 96.4% | 186.5 |
| Option 3, cap 13 | 0.06 | 24.2 million | 93.7% | 82.3% | 35.5 |
| Option 2 adaptive, cap 13 | 0.08 | 20.4 million | 92.6% | 79.4% | 30.0 |
| Option 1, cap 60 | 0.02 | 73.7 million | 97.9% | 93.8% | 108 |
| Option 3, cap 60 | 0.30 | 5.24 million | 74.1% | 40.7% | 7.7 |
| Option 2 adaptive, cap 60 | 0.62 | 2.53 million | 53.7% | 15.5% | 3.7 |

**One S21** (0.02% of the pool), expected 3,307,075 sats a year:

| Scheme | Payouts a year | Sats per payout | No payout in 1 year | No payout in 3 years | Years to a 90% chance of one payout |
|---|---|---|---|---|---|
| No cap | 52.6 | 62,920 | 0% | 0% | 0 |
| Option 1, cap 13 | 0.03 | 127.3 million | 97.4% | 92.5% | 88.6 |
| Option 3, cap 13 | 0.14 | 24.2 million | 87.2% | 66.4% | 16.8 |
| Option 2 adaptive, cap 13 | 0.16 | 20.4 million | 85.1% | 61.5% | 14.2 |
| Option 1, cap 60 | 0.04 | 73.7 million | 95.6% | 87.4% | 51.3 |
| Option 3, cap 60 | 0.63 | 5.24 million | 53.2% | 15.1% | 3.7 |
| Option 2 adaptive, cap 60 | 1.31 | 2.53 million | 27.0% | 2.0% | 1.8 |

**Larger miners**, option 2 adaptive. Range is the 5th to 95th percentile of a year's income as a share of its expected value.

| Miner | Cap 13: payouts a year | Cap 13: sats per payout | Cap 13: no payout in a year | Cap 13: range | Cap 60: payouts a year | Cap 60: sats per payout | Cap 60: range |
|---|---|---|---|---|---|---|---|
| 1 PH/s (0.1% of pool) | 0.81 | 20.5 million | 44.6% | 0% to 247% | 6.5 | 2.53 million | 46% to 169% |
| 10 PH/s (1% of pool) | 8.0 | 20.6 million | 0% | 50% to 162% | 52.6 (every block) | 3.146 million | 78% to 124% |
| 100 PH/s (10% of pool) | 52.6 (every block) | 31.46 million | 0% | 78% to 124% | 52.6 (every block) | 31.46 million | 78% to 124% |

With no cap every miner's range is 78% to 124%: that is the pool's own block luck at 52.6 blocks a year.

## Result D: the same year on today's pools

| Miner | Pool | Sats a year | Payouts a year | No payout in a year | Range of a year's income |
|---|---|---|---|---|---|
| One S19 | FPPS, 2% fee | 1,539,444 | 15.4 at a 100,000-sat threshold | 0% | 98% |
| One S19 | FPPS, 4% fee | 1,508,026 | 15.1 | 0% | 96% |
| One S19 | OCEAN, 2% fee | 1,539,444 | 1.5 on-chain (no minimum over Lightning) | 0% | 93% to 103% |
| One S19 | Solo, 2% fee | 1,539,444 on average | 0.005 | 99.5% | 0, or 308 million sats |
| One S21 | FPPS, 2% fee | 3,240,934 | 32.4 | 0% | 98% |
| One S21 | OCEAN, 2% fee | 3,240,934 | 3.1 on-chain | 0% | 93% to 103% |
| One S21 | Solo, 2% fee | 3,240,934 on average | 0.0105 | 99.0% | 0, or 308 million sats |
| 10 PH/s | FPPS, 2% fee | 162 million | daily | 0% | 98% |
| 10 PH/s | Solo, 2% fee | 162 million on average | 0.53 | 59.1% | 0% to 373% |
| 100 PH/s | FPPS, 2% fee | 1,620 million | daily | 0% | 98% |
| 100 PH/s | Solo, 2% fee | 1,620 million on average | 5.3 | 0.5% | 37% to 168% |

## Result E: p2poolv2 by miner count (option 2 adaptive)

Payouts a year / chance of no payout in a year / sats per payout.

| Miner | Cap | 500 miners | 1,000 miners |
|---|---|---|---|
| One S19 | 13 | 0.09 / 91.7% / 18.1 million | 0.08 / 92.6% / 20.4 million |
| One S19 | 60 | 0.78 / 45.8% / 2.01 million | 0.62 / 53.7% / 2.53 million |
| One S21 | 13 | 0.18 / 83.3% / 18.1 million | 0.16 / 85.1% / 20.4 million |
| One S21 | 60 | 1.64 / 19.3% / 2.01 million | 1.31 / 27.0% / 2.53 million |
| 1 PH/s | 13 | 0.91 / 40.1% / 18.1 million | 0.81 / 44.6% / 20.5 million |
| 1 PH/s | 60 | 8.2 / 0% / 2.02 million | 6.5 / 0.1% / 2.53 million |

The output has the same table for options 1 and 3.

## Result F: the recommended rule across caps, one S19

Payouts a year / chance of no payout in a year / sats per payout.

| Cap | 500 miners | 1,000 miners |
|---|---|---|
| 13 | 0.09 / 91.7% / 18.1 million | 0.08 / 92.6% / 20.4 million |
| 19 | 0.14 / 86.5% / 10.8 million | 0.13 / 88.0% / 12.3 million |
| 25 | 0.21 / 81.3% / 7.59 million | 0.18 / 83.5% / 8.71 million |
| 60 | 0.78 / 45.8% / 2.01 million | 0.62 / 53.7% / 2.53 million |
| 85 | 1.31 / 26.9% / 1.20 million | 1.01 / 36.4% / 1.55 million |
| 100 | 1.65 / 19.2% / 953,000 | 1.26 / 28.2% / 1.24 million |
| 250 | 6.55 / 0.1% / 240,000 | 4.12 / 1.6% / 381,000 |
| 500 | 52.6 / 0% / 29,887 (paid exactly) | 12.5 / 0% / 125,000 |

## What it shows

- **Expected earnings are the same for every miner size and every scheme.** On p2poolv2 a miner earns full hashprice with no fee assumed, which is 2% to 4% more than an FPPS pool pays. The cap does not change the average; it changes how the money arrives.
- **Large miners get the fee saving with only pool luck.** A miner paid exactly in every block sees a year's income between 78% and 124% of expected, and does better than a 2%-fee FPPS pool in 55% of years. At cap 60 that covers everyone from about 0.8% of the pool (8 PH/s) up; at cap 13, from about 6.7% (67 PH/s) up.
- **For one S19 a small cap turns the pool into a lottery.** At cap 13 under the recommended rule it wins 20.4 million sats, thirteen years of earnings, once in about thirteen years on average. It has a 92.6% chance of no payout in a year and 79% over three years. An FPPS pool pays the same machine about every 24 days.
- **Cap 60 is much better and still not a pool for one machine.** One S19 gets 0.62 payouts a year of 2.53 million sats and has a 54% chance of nothing in a year; one S21 gets 1.31 a year with a 27% chance of nothing.
- **It is still far from solo mining.** Solo, an S19 has a 99.5% chance of nothing in a year.
- **The option matters most at small caps.** For one S19, option 1 gives a 98% to 99% chance of nothing in a year at either cap, because its single prize is 23% to 40% of the block.
- **How large a cap one S19 needs.** To be paid about once a year it needs a cap of about 85 with 1,000 miners; about monthly needs a cap near 500. With 500 miners a cap of 250 gives 6.5 payouts a year.

## Caveats

- p2poolv2 is assumed to take no fee. Any fee or donation reduces every p2poolv2 figure in proportion.
- Published pool fees differ between sources and large miners negotiate their own. Foundry's are not public.
- Hashrate, fees and price move daily. Earnings in sats scale inversely with network hashrate; the comparison between pools does not depend on the price.
- FPPS payout counts assume a 100,000-sat on-chain threshold; several pools pay smaller amounts over Lightning.
- Share-finding luck for small miners is covered in [12](../12-share-luck/README.md) and leaves the averages unchanged.
- The miner population is synthetic. See [13](../13-miner-count/README.md) for 500 against 1,000 miners.

## Sources

1. [Bitcoin Mining Update November 2026, MillionMiner](https://millionminer.com/news/bitcoin-mining-update-november-2026)
2. [Bitcoin difficulty heads for its biggest cut since June, DC Forecasts](https://www.dcforecasts.com/analysis/bitcoin-difficulty-cut-november-2026-hashrate/)
3. [Antminer S19 vs S21 comparison, D-Central](https://d-central.tech/antminer-s19-vs-s21-comparison)
4. [Bitcoin mining pool comparison, Spark](https://www.spark.money/tools/bitcoin-mining-pool-comparison)
5. [Best Bitcoin mining pool 2026, MillionMiner](https://millionminer.com/news/best-bitcoin-mining-pool-2026-comparison)

Back to the [report](../../REPORT.md).
