# 10 · Count cap or byte budget?

**Question.** The firmware limit is in bytes and payout scripts range from 31 bytes (P2WPKH) to 43 (P2TR, P2WSH). Is it worth making the rule spend a byte budget instead of counting outputs?

**Method.** A count cap of 13 taproot-size outputs is 559 bytes. This compares that count cap with a 559-byte budget under several mixes of script types, on the synthetic 1,000-miner mainnet population, 20,000 simulated blocks per row.

The byte-budget rule ("per-byte"):

1. Pay a miner exactly while its weight ÷ output size exceeds remaining weight ÷ remaining bytes.
2. Raffle the remaining bytes. A miner wins with probability proportional to weight ÷ size and is then paid in proportion to its output size, so its expected payout is still its weight.
3. Draw the winners in (output size, hash(seed ‖ address)) order with one evenly spaced draw, and reserve the difference between the largest and smallest tail script. That keeps the bytes used at or under the budget in every block.

"Equal-prize" is the same budget with one prize for every script type.

**Run.** `python3 run.py > output.txt` (about 20 seconds). Code: [run.py](run.py); the rule is `byte_rule()` in [../../lib/payout_model.py](../../lib/payout_model.py). Results: [output.txt](output.txt).

## Result: mean days between payouts for a miner with 0.1% of the pool (1 PH/s)

| Rule and script mix | Miner on P2WPKH | Miner on taproot |
|---|---|---|
| Count cap 13, any mix | 451 | 451 |
| Byte budget, everyone on P2WPKH | 290 | n/a |
| Byte budget, 60% P2WPKH / 15% P2SH / 10% P2PKH / 15% taproot | 320 | 444 |
| Byte budget, 30% of miners on taproot | 333 | 462 |
| Byte budget, top 10 miners on 43-byte multisig | 343 | 476 |
| Byte budget, everyone on taproot | n/a | 451 |

Every row was unbiased (paid ÷ fair share between 0.995 and 1.000 for miners on 43-byte scripts) and no block used more than 559 bytes.

## What it shows

- A count cap must assume the largest script for every output, so it wastes room whenever miners use smaller scripts. With a realistic mix, the byte budget cuts a P2WPKH miner's wait by about 29% (320 days against 451).
- With the per-byte rule a miner on a larger script is paid less often and more each time: 39% larger payouts, 28% less often. That gives miners a reason to choose the small script without forcing them to.
- Large scripts still cost other miners. A miner paid exactly bears none of the cost of its own 43-byte output: with the ten largest miners on multisig a small P2WPKH miner waits 343 days instead of 290.
- When every address is P2WPKH the byte rule is the count rule with K = budget ÷ 31.

## Caveats

- This is more consensus code than a count: sizes, a per-byte comparison, a size-ordered draw.
- Use integer arithmetic. A floating-point floor silently dropped one slot in an early version of this script.
- The budget must be a consensus constant. If it varied with the template's merkle depth, the finder would be choosing the cap (see [06](../06-dynamic-cap/README.md)).
- Splitting was not re-simulated for the byte rule. The win probability is still proportional to weight, so the argument of [04](../04-splitting/README.md) should carry over.

Back to the [report](../../REPORT.md).
