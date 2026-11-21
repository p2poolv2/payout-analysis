# 01 · Expected payout: is each variant fair on average?

**Question.** Does every miner receive, on average, the same share of the reward as its share of the work?

**Method.** 400,000 simulated blocks per variant on a 168-miner population (every farm and small farm of the synthetic 1,000-miner mainnet population and one in seven of the rest, to keep the run short; nobody is smaller than one S19), with a cap of 13 outputs. The fixed-split variants of option 2 use 7 miners paid exactly and 6 raffle slots. The output is the amount paid divided by the fair share, grouped by rank. A value of 1.000 means unbiased.

**Run.** `python3 run.py > output.txt` (about 30 seconds). Code: [run.py](run.py), shared model in [../../lib/payout_model.py](../../lib/payout_model.py). Results: [output.txt](output.txt).

## Result

| Variant | Rank 1–4 | Rank 5–12 | Rank 13–40 | Rank 41+ |
|---|---|---|---|---|
| Option 1 (12 top + 1 random) | 1.000 | 1.000 | 0.999 | 1.007 ± 0.004 |
| Option 2 fixed, 6 independent draws | 1.000 | 1.000 | 1.000 | 1.000 ± 0.002 |
| Option 2 fixed, 6 evenly spaced draws | 1.000 | 1.001 | 0.999 | 1.001 ± 0.002 |
| Option 2, 6 **distinct** winners, equal prizes | 1.000 | 0.951 | 1.040 | 1.127 |
| Option 2, 6 **distinct** winners, pot split pro rata | 1.000 | 1.302 | 0.784 | 0.046 |
| Option 2, 6 **distinct** winners, excluded weight redistributed | 1.347 | 0.914 | 0.248 | 0.012 |
| Option 3, independent draws | 1.000 | 1.000 | 1.001 | 1.002 ± 0.002 |
| Option 3, evenly spaced draw | 1.000 | 1.000 | 1.000 | 0.997 ± 0.002 |
| Option 2 adaptive (recommended) | 1.000 | 1.000 | 0.999 | 1.001 ± 0.002 |

## What it shows

- Options 1, 2 and 3 are all unbiased when each raffle slot is an independent weighted draw, or when the slots come from one evenly spaced draw.
- Forcing the winners to be distinct addresses breaks fairness in every form tried:
  - with equal prizes, the smallest miners are overpaid by 13% and mid-sized raffle miners underpaid by 5%;
  - with the pot split pro rata among the winners, the smallest miners receive under 5% of their fair share;
  - with the excluded miners' weight redistributed to those included, the four largest miners collect 35% more than their share.

## Caveats

The population is synthetic. The bias of the broken variants depends on the population; the direction does not.

Back to the [report](../../REPORT.md).
