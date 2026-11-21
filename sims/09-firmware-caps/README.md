# 09 · From firmware byte caps to an output count

**Question.** What cap should the payout rule use, given what deployed ASIC firmware accepts?

**Source.** ["Bitmain firmware coinbase output limits"](https://gist.github.com/rkuester/3a9378ea3a3fef898b732b294146afeb) (rkuester). It measures the stratum job-message cap on three bmminer builds and tabulates how many outputs of each script type fit:

| Build | Job-message cap |
|---|---|
| S19j Pro, A113D, 2021-11-19 | 3,072 bytes |
| S19j Pro, Xilinx, 2022-03-29 | 5,120 bytes |
| S21 Pro+, A113D, 2026-04-29 | 5,120 bytes |

The limit is on bytes, not on output count. Each merkle branch costs 32 bytes, so the room left for outputs depends on how many transactions the template holds.

**Method.**

- **A.** Back out the output-byte budget from the report's tables. The counts for four script sizes pin it to 1,075–1,079 bytes at the 3,072-byte cap with no merkle branches (the low end is used).
- **B.** Recompute how many outputs fit beside a 47-byte witness commitment for 11 to 14 merkle branches.
- **C.** Run the payout model (option 2 adaptive, 1,000-miner mainnet population) at the resulting caps.

**Run.** `python3 run.py > output.txt` (about 2 minutes). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result B: miner outputs beside a witness commitment, 3,072-byte builds

| Merkle branches | Transactions | P2WPKH (31 bytes) | Spare bytes | Taproot size (43 bytes) | Spare bytes |
|---|---|---|---|---|---|
| 12 | up to 4,096 | 20 | 24 | 14 | 42 |
| 13 | up to 8,192 | 19 | 23 | 14 | 10 |
| 14 | up to 16,384 | 18 | 22 | 13 | 21 |

On the 5,120-byte builds the same arithmetic gives 86 / 85 / 84 P2WPKH outputs, or 62 / 61 / 61 at taproot size.

**Chosen caps.** With users on mixed script types and a count rule, every output must be assumed taproot size. 13 fits any block on the oldest build and leaves 53 bytes spare at 13 branches; 14 fits up to 8,192 transactions with only 10 bytes spare. On the newer builds, 60 fits any block.

## Result C: the model at those caps (mainnet, 1,000 miners, option 2 adaptive)

Waits are mean days between payouts. Shares are of the pool (1 EH/s): 0.1% is 1 PH/s and one S19 is 0.0095%.

| Cap | Meaning | Exact + raffle | Prize | 0.1% of pool paid every | One S19 paid every | Grinding gain, 20% in 400 addresses |
|---|---|---|---|---|---|---|
| 13 | taproot size, old builds | 4 + 9 | 6.50% | 451 days | 4,749 days | 4.30% + 2.20% |
| 14 | taproot size, ≤ 8,192 txs | 4 + 10 | 5.85% | 406 days | 4,274 days | 3.87% + 1.98% |
| 19 | P2WPKH only, old builds | 4 + 15 | 3.90% | 271 days | 2,850 days | 2.33% + 1.13% |
| 60 | taproot size, new builds | 19 + 41 | 0.80% | 56 days | 588 days | 0.07% + 0.03% |
| 85 | P2WPKH only, new builds | 24 + 61 | 0.49% | 34 days | 361 days | 0.01% |

Grinding gain is tip choice + withholding (see [05](../05-grinding/README.md)).

## Testnet5 note

Testnet5 blocks are nearly empty, so their templates have few merkle branches and sit about 400 bytes further from the cap than a full mainnet block with the same coinbase. To put the same byte load on a 3,072-byte build as 13 taproot-size outputs with 13 branches, a testnet5 template needs about 22 outputs with no branches, or 19 with 4.

## Caveats

- The report covers three builds only and gives no share of deployed hashrate for each cap.
- Its counts are derived from the socket cap; the report itself says the hashing block's own ceiling is unproven until a bench test.
- It observed a job right at the boundary being split, and the job id and pool URL also count against the cap, so the spare bytes above are a real safety margin, not slack to use up.
- The 47-byte witness commitment is the only non-miner output assumed. Any further pool or commitment output costs one count per 43 bytes.

Back to the [report](../../REPORT.md).
