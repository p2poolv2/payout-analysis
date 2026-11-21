# 02 · Waiting time and raffle variance by option

**Question.** For a given cap, how long does a miner of a given size wait between payouts under each option, and how much variance does the raffle add?

**Sizes.** Every share here is a share of **pool** hashrate, not of the Bitcoin network. The mainnet pool is 1 EH/s (0.1% of a 1,000 EH/s network), so 1% of the pool is 10 PH/s, 0.1% is 1 PH/s, one S21 (200 TH/s) is 0.02% and one S19 (95 TH/s) is 0.0095%. Nobody in the pool is smaller than one S19.

**Method.** Closed-form payout distributions on the two synthetic populations (mainnet: 1,000 miners, about 1 pool block a week; testnet5: 124 miners at 50 pool blocks a day), at caps of 13 and 60 outputs. Three parts:

- **A.** Per-option table: split into exact and raffle slots, prize size, miners paid in every block, mean days between payouts for the four reference sizes, total raffle variance, and a cap sweep for the adaptive rule.
- **B.** Robustness: the same variance comparison on 300 random populations per cap (Zipf and log-normal shapes, up to 1,000 miners, none smaller than one S19 in a 1 EH/s pool).
- **C.** Monte Carlo of income over 7 days (testnet5) and 365 days (mainnet), 40,000 paths.

**Run.** `python3 run.py > output.txt` (a few seconds). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result: mainnet, mean days between payouts

With no cap every miner is paid every 6.9 days.

| Option | Cap 13: 0.1% of pool | Cap 13: one S21 | Cap 13: one S19 | Cap 60: 0.1% of pool | Cap 60: one S21 | Cap 60: one S19 |
|---|---|---|---|---|---|---|
| Option 1 (top + 1 random) | 2,813 | 14,048 | 29,571 | 1,631 | 8,133 | 17,116 |
| Option 2 fixed, K/5 raffle slots | 1,469 | 7,335 | 15,440 | 145 | 725 | 1,525 |
| Option 2 fixed, K/2 raffle slots | 582 | 2,906 | 6,118 | 65 | 325 | 684 |
| Option 3, evenly spaced draw | 534 | 2,671 | 5,623 | 116 | 579 | 1,218 |
| Option 2 adaptive | 451 | 2,256 | 4,749 | 56 | 279 | 588 |

Prize sizes at cap 13: option 1 pays one prize of 40.5% of the block, option 3 pays 7.7% per slot, option 2 adaptive pays 6.5% per slot. At cap 60: 23.4%, 1.7% and 0.80%.

## Result: chance of no payout in a year on mainnet (Monte Carlo)

| Option | Cap 13: 0.1% of pool | Cap 13: one S21 | Cap 13: one S19 | Cap 60: 0.1% of pool | Cap 60: one S21 | Cap 60: one S19 |
|---|---|---|---|---|---|---|
| Option 1 | 88% | 97% | 99% | 80% | 96% | 98% |
| Option 3, evenly spaced draw | 51% | 87% | 94% | 4% | 53% | 74% |
| Option 2 adaptive | 45% | 85% | 93% | 0.1% | 27% | 54% |

## Result: option 2 adaptive across caps (mainnet)

Mean days between payouts.

| Cap | Exact + raffle | Prize | 0.1% of pool | One S21 | One S19 | Miners with an even chance of a payout in a year |
|---|---|---|---|---|---|---|
| 13 | 4 + 9 | 6.50% | 451 | 2,256 | 4,749 | 10.2% |
| 19 | 4 + 15 | 3.90% | 271 | 1,354 | 2,850 | 16.8% |
| 25 | 6 + 19 | 2.77% | 192 | 961 | 2,023 | 21.6% |
| 60 | 19 + 41 | 0.80% | 56 | 279 | 588 | 56.1% |
| 85 | 24 + 61 | 0.49% | 34 | 172 | 361 | 100% |
| 100 | 26 + 74 | 0.40% | 27.5 | 137 | 289 | 100% |
| 250 | 85 + 165 | 0.12% | 8.4 | 42 | 89 | 100% |
| 500 | 191 + 309 | 0.04% | 6.9 | 13.9 | 29 | 100% |

## Result: robustness over 300 random populations per cap

Raffle variance relative to option 2 adaptive (1.00 = same):

| Option | Cap 13 median | Cap 13 worst | Cap 60 median | Cap 60 worst | Prize above 10% of block (cap 13 / cap 60) |
|---|---|---|---|---|---|
| Option 1 | 4.35 | 10.6 | 16.0 | 37.5 | 89% / 68% of populations |
| Option 2 fixed, K/5 raffle slots | 2.35 | 5.4 | 1.70 | 3.3 | 74% / 0% |
| Option 2 fixed, K/2 raffle slots | 1.12 | 2.3 | 1.05 | 1.5 | 26% / 0% |
| Option 3, evenly spaced draw | 1.58 | 942 | 2.43 | 118 | 0% / 0% |
| Option 2 adaptive | 1.00 | 1.00 | 1.00 | 1.00 | 0% / 0% |

## What it shows

- Option 2 with the adaptive split has the lowest raffle variance in every one of the 600 populations. Simulation [07](../07-optimality-and-reference/README.md) shows this is the theoretical minimum.
- A fixed split can come close (K/2 raffle slots is within about 12% at the median) but is up to 2.3 times worse when the population differs from the one it suits.
- Option 1's single prize grows with the tail. With no miner below an S19 the tail is heavy: the prize is 40.5% of the block at cap 13 and still 23.4% at cap 60. It exceeds 10% of the block in most populations, which is the threshold that makes seed grinding pay (see [05](../05-grinding/README.md)).
- Option 3 never has a large prize but gives up the exact payouts of large miners, and its variance is very large in top-heavy populations.
- At cap 60 option 1 pays any miner above about 0.14% of the pool (1.4 PH/s) exactly, but everyone below shares one prize of 23.4% of the block, so a miner with one S19 waits 29 times longer than under the adaptive rule.
- For one S19 the wait is long under every option: 13 years on average at cap 13 and 1.6 years at cap 60 under the adaptive rule. It falls to about three months at cap 250 and one month at cap 500.

## Caveats

Waits for the reference sizes are for a miner of that size put into the population in place of its smallest member, so the miner count stays at 1,000. Simulation [03](../03-variance-by-hashrate-share/README.md) covers shares up to 30% of the pool, [13](../13-miner-count/README.md) compares 500 miners with 1,000, and [14](../14-earnings/README.md) turns the waits into earnings.

Back to the [report](../../REPORT.md).
