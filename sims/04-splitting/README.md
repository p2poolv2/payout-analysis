# 04 · Splitting hashrate across addresses (sock puppets)

**Question.** Can a miner raise its expected payout, or be paid more often, by mining to many addresses instead of one? And what does a large miner's split do to everyone else?

**Sizes.** Shares are of **pool** hashrate (the mainnet pool is 1 EH/s, 0.1% of the network). No address in these scenarios is smaller than one S19 (0.0095% of the pool).

**Method.**

- **A.** The same hashrate (0.5%, 3% or 20% of the pool) is held in 1, 10 to 30, or 50 to 400 addresses. For each variant, 150,000 simulated blocks give the expected payout ÷ fair share, the chance of any payout in a block, and the spread of the per-block total. Honest population: 168 miners (every farm and small farm of the synthetic mainnet population, one in seven of the rest, to keep the run short), cap 13.
- **B.** Crowd-out, in closed form on the 1,000-miner mainnet population: a miner with 30% of the pool as one address, as one address per coinbase slot, or as 500 addresses. Its addresses count toward the 1,000-miner limit and take the place of the smallest honest miners. Reported: prize size, number of honest miners paid exactly, and the raffle variance borne by honest miners.

**Run.** `python3 run.py > output.txt` (about 6 minutes). Code: [run.py](run.py), re-check of four cells in [recheck.py](recheck.py). Results: [output.txt](output.txt), [recheck_output.txt](recheck_output.txt).

## Result A: expected payout ÷ fair share

| Variant | 0.5% as 1 address | 0.5% as 50 addresses | 3% as 1 address | 3% as 30 addresses | 20% as 1 address | 20% as 400 addresses |
|---|---|---|---|---|---|---|
| Option 1 | 0.991 ± 0.017 | 0.966 ± 0.017 | 1.000 | 0.984 ± 0.007 | 1.000 | 1.001 |
| Option 2 fixed, independent draws | 1.012 | 1.001 | 1.000 | 1.002 | 1.000 | 0.999 |
| Option 2 fixed, evenly spaced | 1.002 | 0.999 | 1.001 | 0.998 | 1.000 | 1.000 |
| Option 2, distinct winners, equal prizes | **1.09** | **1.13** | **0.89** | **1.10** | 1.000 | **1.04** |
| Option 2, distinct winners, pro rata | **0.45** | **0.010** | **1.65** | **0.11** | 1.000 | **0.14** |
| Option 2, distinct winners, redistributed | **0.13** | **0.003** | **0.60** | **0.03** | **1.29** | **0.01** |
| Option 3, independent draws | 0.989 | 1.011 | 0.997 | 0.999 | 1.000 | 1.000 |
| Option 3, evenly spaced | 0.996 | 0.998 | 0.992 ± 0.003 | 1.002 | 1.000 | 1.001 |
| Option 2 adaptive | 1.005 | 1.001 | 1.003 | 1.003 | 1.000 | 0.998 |

Standard errors are 0.001 to 0.017; the full table with errors is in the output.

Four unbiased cells came out two or more standard errors low (three under option 1 and option 3 evenly spaced for 3% as one address). Re-running those four with 600,000 blocks and a fresh seed gave 0.996 ± 0.003, 1.014 ± 0.009, 1.001 ± 0.008 and 1.001 ± 0.002, so they were noise.

## Result A: being paid more often

Under option 2 adaptive, splitting makes a miner's payouts less regular, not more:

| Miner | Chance of a payout per block | Spread of per-block total |
|---|---|---|
| 3% of pool as 1 address | 58% | 0.86 |
| 3% of pool as 30 addresses | 46% | 1.25 |
| 20% of pool as 1 address | 100% | 0 |
| 20% of pool as 400 addresses | 98.6% | 0.43 |

## Result B: crowd-out by a miner with 30% of the pool (1,000-miner mainnet population)

Each cell gives the miner with 30% of the pool as one address / as one address per coinbase slot / as 500 addresses.

| Cap | Option | Prize, share of block | Raffle variance borne by honest miners |
|---|---|---|---|
| 13 | Option 1 | 29.6% / 52.4% / 56.0% | 0.0866 / 0.2118 / 0.1445 |
| 13 | Option 3, evenly spaced | 7.7% / 7.7% / 7.7% | 0.0312 / 0.0312 / 0.0304 |
| 13 | Option 2 adaptive | 5.06% / 7.55% / 7.42% | 0.0182 / 0.0296 / 0.0274 |
| 60 | Option 1 | 16.5% / 32.8% / 43.4% | 0.0271 / 0.0746 / 0.0578 |
| 60 | Option 3, evenly spaced | 1.7% / 1.7% / 1.7% | 0.0045 / 0.0045 / 0.0041 |
| 60 | Option 2 adaptive | 0.58% / 1.21% / 1.17% | 0.0011 / 0.0028 / 0.0023 |

In the worst case the split multiplies honest miners' raffle variance by 2.4 under option 1 and by 1.6 under option 2 adaptive at cap 13.

## What it shows

- With independent or evenly spaced weighted draws, splitting never changes the expected payout, under any option.
- Splitting does pay when the winners are forced to be distinct addresses with equal prizes: a miner with 3% of the pool collects 0.89 of its share as one address and 1.10 as 30 addresses.
- The other two "distinct winner" variants punish small addresses instead, which pays miners to merge and leaves small miners with a fraction of their share.
- A large miner can make honest miners' payouts more variable by splitting (it gains nothing itself). Option 3 is immune. Under option 2 adaptive the damage is bounded, because a prize can never exceed 1/K of the block, and even the attacked case is better for honest miners than option 1 or option 3 without any attack.

Back to the [report](../../REPORT.md).
