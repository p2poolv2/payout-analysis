# 07 · Optimality of the adaptive split, and an integer reference implementation

**Questions.**

1. Is there any unbiased rule with the same cap that adds less variance than option 2 with the adaptive split?
2. Does the rule survive being written in integer arithmetic, the way consensus code would have to write it?

**Method.**

- **A. Lower bound.** Any unbiased scheme with at most K outputs gives miner *i* some probability *p_i* of being paid, with the *p_i* summing to at most K. The variance of that miner's payout is then at least *w_i² (1/p_i − 1)*. The script minimises the sum of those bounds numerically (SLSQP) for 40 random populations and caps and compares the minimum with what the adaptive rule achieves.
- **B. Reference implementation.** `adaptive_payout()` in [../../lib/payout_model.py](../../lib/payout_model.py) takes integer share counts, a reward in satoshis, the cap and a seed, and returns at most K outputs using integers and SHA-256 only. It is run for 240,000 blocks on share windows of 20,000 shares drawn at random from 168 miners' hashrates (every farm and small farm of the synthetic mainnet population and one in seven of the rest).

**Run.** `python3 run.py > output.txt` (about 1 minute; needs scipy). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result

- **A.** Across 40 random populations and caps the largest relative gap between the adaptive rule and the numerical lower bound is 1.0e-04, which is the optimiser's tolerance. The adaptive split is the minimum-variance unbiased rule for a given cap.
- **B.** Every block paid exactly the reward in at most 13 outputs. Paid ÷ fair share by rank:

| Rank 1–4 | Rank 5–12 | Rank 13–40 | Rank 41+ |
|---|---|---|---|
| 1.0000 | 0.9993 ± 0.0005 | 1.0005 ± 0.0007 | 1.002 ± 0.002 |

## The rule in the reference implementation

1. Sort miners by weight, largest first (ties by address).
2. Pay a miner exactly while its weight × remaining slots exceeds the remaining weight. This sets N, the number paid exactly.
3. The other M = K − N slots each pay the remaining weight ÷ M.
4. Order the remaining miners by SHA-256(seed ‖ address). Draw one offset from the seed and place M evenly spaced points along their cumulative weights; each point pays the miner it lands on.
5. Rounding remainders go to the largest output.

## Caveats

The lower bound in A is on the sum of per-miner variances. A rule could trade variance between miners (option 1 does, see [03](../03-variance-by-hashrate-share/README.md)) but cannot reduce the total. B tests arithmetic and fairness, not adversarial inputs.

Back to the [report](../../REPORT.md).
