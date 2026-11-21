# 13 · Miner count: 500 against 1,000

**Question.** The p2p network is expected to carry at most about 1,000 miners, so every simulation in this bundle uses a mainnet population of at most 1,000. What changes if the pool has 500 miners instead?

**Sizes.** Shares are of **pool** hashrate, not of the Bitcoin network. Both pools are 1 EH/s (0.1% of the network): 1% of the pool is 10 PH/s, 0.1% is 1 PH/s, one S21 is 0.02% and one S19 is 0.0095%. Nobody is smaller than one S19.

**Method.** Two populations with the same total hashrate and block rate (about 1 pool block a week):

- **1,000 miners**: 4 farms, 25 small farms (3 to 30 PH/s), 250 miners with 2 to 20 machines, 721 miners with one machine (an S19 or an S21).
- **500 miners**: the same small farms and multi-machine miners, 221 single-machine miners, and larger farms making up the difference.

Two assumptions are built in, and part H tests both:

1. A smaller pool has fewer single-machine miners. The alternative tested is every second miner of the 1,000 by rank, each with twice the hashrate.
2. A sock-puppet miner's addresses count toward the limit and take the place of the smallest honest miners. The alternative tested is 1,000 honest miners plus the attacker's addresses.

Parts: **A** the populations, **B** each option at both counts, **C** payout variance by hashrate share (one S19 to 30% of the pool), **D** how many miners are served, **E** what one share is worth, **G** small miners, **F** seed grinding, **H** the two assumptions.

**Run.** `python3 run.py > output.txt` (about 30 seconds). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result A: the two populations

| | 500 miners | 1,000 miners |
|---|---|---|
| Largest miner, share of pool | 13.9% | 11.9% |
| Hashrate of the 29 largest | 78.5% | 71.8% |
| Hashrate outside the 29 largest | 21.5% | 28.2% |
| Miners at or below 200 TH/s | 246 | 746 |
| Their share of pool hashrate | 3.5% | 10.3% |
| Miners with one S19 | 129 | 439 |
| Hashrate held by the 4 farms | 48.3% | 41.5% |
| Hashrate held by the 25 small farms | 30.2% | 30.2% |
| Hashrate held by the 250 miners with 2 to 20 machines | 18.4% | 18.4% |
| Hashrate held by single-machine miners | 3.1% (221 miners) | 9.8% (721 miners) |

## Result B: each option at both counts

Mean days between payouts.

| Option | Miners | Cap 13: prize | Cap 13: 0.1% of pool | Cap 13: one S19 | Cap 60: prize | Cap 60: 0.1% of pool | Cap 60: one S19 |
|---|---|---|---|---|---|---|---|
| Option 1 | 500 | 33.7% | 2,345 | 24,640 | 16.7% | 1,163 | 12,185 |
| Option 1 | 1,000 | 40.5% | 2,813 | 29,571 | 23.4% | 1,631 | 17,116 |
| Option 2 adaptive | 500 | 5.75% | 400 | 4,202 | 0.64% | 44.5 | 467 |
| Option 2 adaptive | 1,000 | 6.50% | 451 | 4,749 | 0.80% | 56 | 588 |
| Option 3, evenly spaced | 500 | 7.69% | 534 | 5,623 | 1.67% | 116 | 1,218 |
| Option 3, evenly spaced | 1,000 | 7.69% | 534 | 5,623 | 1.67% | 116 | 1,218 |

The split into exact and raffle slots is the same at both counts: 12 + 1, 4 + 9 and 0 + 13 at cap 13; 59 + 1, 19 + 41 and 0 + 60 at cap 60.

## Result C: spread of one year's income by hashrate share (standard deviation ÷ mean)

Block luck alone gives 13.8% at 52.6 blocks a year. Cap 13:

| Share of pool | Option 1: 500 | Option 1: 1,000 | Option 2 adaptive: 500 | Option 2 adaptive: 1,000 | Option 3: 500 | Option 3: 1,000 |
|---|---|---|---|---|---|---|
| One S19 (0.0095%) | 822% | 900% | 339% | 361% | 392% | 392% |
| One S21 (0.02%) | 566% | 620% | 234% | 249% | 270% | 270% |
| 0.1% | 253% | 278% | 105% | 111% | 121% | 121% |
| 0.2% | 179% | 196% | 74% | 79% | 85.5% | 85.5% |
| 0.5% | 114% | 124.5% | 47% | 50% | 54% | 54% |
| 1% | 81% | 88% | 33% | 35% | 38% | 38% |
| 2% | 13.8% | 13.8% | 23.6% | 25.0% | 27.1% | 27.1% |
| 5% | 13.8% | 13.8% | 15.1% | 15.9% | 17.1% | 17.1% |
| 10% | 13.8% | 13.8% | 13.8% | 13.8% | 14.6% | 14.6% |
| 20% | 13.8% | 13.8% | 13.8% | 13.8% | 14.0% | 14.0% |
| 30% | 13.8% | 13.8% | 13.8% | 13.8% | 13.8% | 13.8% |

Cap 60:

| Share of pool | Option 1: 500 | Option 1: 1,000 | Option 2 adaptive: 500 | Option 2 adaptive: 1,000 | Option 3: 500 | Option 3: 1,000 |
|---|---|---|---|---|---|---|
| One S19 (0.0095%) | 578% | 685% | 113% | 127% | 183% | 183% |
| One S21 (0.02%) | 398% | 472% | 78% | 87% | 126% | 126% |
| 0.1% | 178.5% | 211% | 35% | 39% | 56% | 56% |
| 0.2% | 13.8% | 13.8% | 24.7% | 27.7% | 39.8% | 39.8% |
| 0.5% | 13.8% | 13.8% | 15.7% | 17.6% | 25.2% | 25.2% |
| 1% | 13.8% | 13.8% | 13.8% | 13.8% | 17.8% | 17.8% |
| 2% | 13.8% | 13.8% | 13.8% | 13.8% | 14.5% | 14.5% |
| 5% to 30% | 13.8% | 13.8% | 13.8% | 13.8% | 13.8% | 13.8% |

The output also gives the variance relative to an uncapped coinbase and the days between payouts in the same layout.

## Result D: how many miners are served (option 2 adaptive)

| Cap | Miners | Paid exactly | In the raffle | Raffle prizes a year | At least an even chance of a payout in a year | Same, in 30 days |
|---|---|---|---|---|---|---|
| 13 | 500 | 4 | 496 | 473 | 137 miners (27.4%), 91.4% of hashrate | 17 miners (3.4%), 72.1% of hashrate |
| 13 | 1,000 | 4 | 996 | 473 | 102 miners (10.2%), 81.8% of hashrate | 16 miners (1.6%), 64.4% of hashrate |
| 60 | 500 | 19 | 481 | 2,155 | 500 miners (100%), 100% of hashrate | 98 miners (19.6%), 88.1% of hashrate |
| 60 | 1,000 | 19 | 981 | 2,155 | 561 miners (56.1%), 95.8% of hashrate | 73 miners (7.3%), 78.5% of hashrate |

## Results E and G: small miners (option 2 adaptive)

Chance that a single share ever pays (2-week window, 2 pool blocks expected): 0.029% with 500 miners and 0.026% with 1,000 at cap 13; 0.26% and 0.21% at cap 60.

Mean days between payouts / chance of no payout in 30 days:

| Miner | Cap 13: 500 miners | Cap 13: 1,000 miners | Cap 60: 500 miners | Cap 60: 1,000 miners |
|---|---|---|---|---|
| 1% of pool (10 PH/s) | 40 / 47.5% | 45 / 51.7% | 6.9 / 1.3% | 6.9 / 1.3% |
| 0.1% of pool (1 PH/s) | 400 / 92.8% | 451 / 93.6% | 44.5 / 51.0% | 56 / 58.5% |
| One S21 | 1,996 / 98.5% | 2,256 / 98.7% | 222 / 87.4% | 279 / 89.8% |
| One S19 | 4,202 / 99.3% | 4,749 / 99.4% | 467 / 93.8% | 588 / 95.0% |

## Result F: seed grinding (tip choice among 3 older tips + withholding)

| Cap | Attacker | Option | 500 miners | 1,000 miners |
|---|---|---|---|---|
| 13 | 20% in 400 addresses | Option 1 | 13.2% + 8.4% | 19.1% + 11.1% |
| 13 | 20% in 400 addresses | Option 3, evenly spaced | 4.6% + 2.3% | 4.9% + 2.5% |
| 13 | 20% in 400 addresses | Option 2 adaptive | 3.2% + 1.7% | 4.3% + 2.2% |
| 13 | 5% in 50 addresses | Option 1 | 8.2% + 3.3% | 9.2% + 3.6% |
| 13 | 5% in 50 addresses | Option 3, evenly spaced | 1.4% + 0.5% | 1.4% + 0.5% |
| 13 | 5% in 50 addresses | Option 2 adaptive | 0.9% + 0.3% | 1.1% + 0.4% |
| 60 | 20% in 400 addresses | Option 1 | 2.7% + 2.3% | 10.7% + 7.1% |
| 60 | 20% in 400 addresses | Option 3, evenly spaced | 0.2% + 0.1% | 0.35% + 0.15% |
| 60 | 20% in 400 addresses | Option 2 adaptive | 0 | 0.07% + 0.03% |
| 60 | 5% in 50 addresses | Option 1 | 4.5% + 2.0% | 6.3% + 2.7% |
| 60 | 5% in 50 addresses | Options 2 adaptive and 3 | 0 | 0 |

## Result H1: which miners make up a 500-miner pool

Option 2 adaptive.

| Population | Largest miner | Cap 13: exact + raffle | Cap 13: prize | Cap 13: one S19 paid every | Cap 60: prize | Cap 60: one S19 paid every |
|---|---|---|---|---|---|---|
| 1,000 | 11.9% | 4 + 9 | 6.50% | 4,749 days | 0.80% | 588 days |
| 500, fewer single machines | 13.9% | 4 + 9 | 5.75% | 4,202 days | 0.64% | 467 days |
| 500, every second miner | 22.4% | 3 + 10 | 5.05% | 3,690 days | 0.59% | 429.5 days |

"One S19" here means a miner with 0.0095% of the pool; in the every-second-miner pool the smallest miner is twice that. Miners with at least an even chance of a payout in a year at cap 13: 102 of 1,000, 137 of 500 and 108 of 500 in the same order; at cap 60, 561 of 1,000 and all 500 in both smaller pools.

## Result H2: do the attacker's addresses count toward the limit?

Option 2 adaptive, a miner with 20% of the pool in 400 addresses, cap 13:

| | Addresses in the window | Tip choice + withholding | Prize | Honest S19 paid every |
|---|---|---|---|---|
| Counted (600 honest + 400) | 1,000 | 4.30% + 2.19% | 7.10% | 5,188 days |
| Not counted (1,000 honest + 400) | 1,400 | 4.44% + 2.28% | 7.21% | 5,269 days |

At cap 60: 0.07% + 0.03% counted and 0.10% + 0.04% not counted.

## What it shows

- **With no miner below an S19, the count matters.** Small miners now hold real hashrate: the 746 smallest miners hold 10.3% of the 1,000-miner pool and the 246 smallest hold 3.5% of the 500-miner pool. More small miners means a heavier tail and a larger prize, so everyone in the raffle waits longer: one S19 is paid every 467 days in the 500-miner pool and every 588 days in the 1,000-miner pool at cap 60.
- **At cap 60 a 500-miner pool serves everyone within a year; a 1,000-miner pool does not.** All 500 miners have at least an even chance of a payout in a year, against 561 of 1,000.
- **Option 1 is hit hardest by more miners.** Its single prize is the whole tail: 33.7% of the block with 500 miners and 40.5% with 1,000 at cap 13.
- **Option 3 does not depend on the count** for a miner in the raffle; its prize is always 1/K.
- **Grinding grows with the tail.** The 400-address miner gains 3.2% + 1.7% with 500 miners and 4.3% + 2.2% with 1,000 at cap 13 under option 2 adaptive, which stays the least exposed at both counts.
- **The composition of a 500-miner pool matters less than its size**: the two 500-miner pools are within about 12% of each other.
- **Whether sock-puppet addresses count toward the limit barely matters**: the 400 displaced miners hold 3.8% of hashrate, and the results differ by a few percent.

## Caveats

- Both pools are 1 EH/s with about one block a week. A smaller pool in hashrate would find blocks less often; that is not modelled here.
- Both populations are synthetic, and which miners a real pool would hold is unknown. H1 brackets two cases.

Back to the [report](../../REPORT.md).
