# 05 · Grinding the raffle seed (tip choice and withholding)

**Question.** The raffle seed is the hash of the parent share, so every share-chain tip has its own raffle. Can a miner profit by steering which raffle is in play when a block is found?

**Two strategies are modelled.** Both rest on the fact that a share published late still earns 90% as an uncle.

- **Tip choice.** Mine on whichever of the last few tips has the raffle that pays you most. A share on an older tip costs 10% of that share's value; if it happens to be a Bitcoin block, the block pays out under the raffle you chose.
- **Withholding.** When you find a share whose raffle is worse for you than the current one, sit on it so the current raffle stays in play for one more share. The withheld share later becomes an uncle.

Either one pays only when the better raffle is worth more than 10% of the block reward to the miner. So the size of a prize, and how many prizes one entity can win at once, decide everything.

**Sizes.** Attacker sizes are shares of **pool** hashrate (the mainnet pool is 1 EH/s, 0.1% of the network): 20% is 200 PH/s, 5% is 50 PH/s, 1.5% is 15 PH/s. Each sock-puppet address holds at least five S19s' worth of hashrate.

**Method.** For each attacker and option, 30,000 raffle outcomes are sampled on the synthetic 1,000-miner mainnet population. The attacker's addresses count toward the 1,000-miner limit and take the place of the smallest honest miners. Tip choice is evaluated over the current tip plus 1 or 3 older ones; withholding by a Markov simulation of 20,000 chains. Gains are relative to the attacker's honest revenue. Each figure is a separate Monte Carlo estimate, so the same case can differ by a few hundredths of a point between tables.

**Run.** `python3 run.py > output.txt` (about 6 minutes). Code: [run.py](run.py). Results: [output.txt](output.txt). The same comparison for a 500-miner pool is in [13](../13-miner-count/README.md).

## Result: cap 13, relative revenue gain (tip choice among 3 older tips + withholding)

| Attacker (share of pool) | Option 1 | Option 2 fixed (7 + 6) | Option 3 | Option 2 adaptive |
|---|---|---|---|---|
| 20% in one address | 0 | 0 | 0 | 0 |
| 20% in 400 addresses | 19.1% + 11.0% | 5.3% + 2.8% | 4.8% + 2.5% | 4.3% + 2.2% |
| 5% in 50 addresses | 9.1% + 3.6% | 1.4% + 0.5% | 1.4% + 0.5% | 1.1% + 0.4% |
| 1.5% in one address | 3.2% + 1.1% | 0 | 0 | 0 |
| 0.5% in one address | 1.0% + 0.4% | 0 | 0 | 0 |

At cap 60 only option 1 still leaks: 10.75% + 7.2% for the miner with 20% of the pool in 400 addresses and 6.3% + 2.7% for the miner with 5% of the pool in 50. Option 3 is at 0.35% + 0.15% and option 2 adaptive at 0.07% + 0.03% for the 20% miner.

## Result: option 2 adaptive across caps (20% of the pool in 400 addresses)

| Cap | Prize | Extra wins needed to beat the 10% penalty | Tip choice | Withholding |
|---|---|---|---|---|
| 11 | 8.9% | 2 | 5.25% | 2.67% |
| 13 | 7.1% | 2 | 4.30% | 2.21% |
| 14 | 6.5% | 2 | 3.88% | 1.99% |
| 16 | 5.5% | 2 | 3.07% | 1.55% |
| 19 | 4.4% | 3 | 2.31% | 1.12% |
| 25 | 3.1% | 4 | 1.39% | 0.64% |
| 60 | 1.05% | 10 | 0.07% | 0.03% |
| 100 | 0.55% | 19 | 0 | 0 |

The prize is larger here than on the honest population (7.1% against 6.5% at cap 13) because the attacker's 400 small addresses enlarge the tail.

## Result: uncle penalty at cap 13 (20% of the pool in 400 addresses)

| Uncle penalty | Option 1 | Option 2 adaptive |
|---|---|---|
| 10% (current) | 19.1% + 11.0% | 4.3% + 2.2% |
| 15% | 16.7% + 9.65% | 2.3% + 1.0% |
| 20% | 14.4% + 8.3% | 1.2% + 0.5% |

In total: 6.5%, 3.3% and 1.7% for option 2 adaptive.

## What it shows

- A miner on a single address gains nothing under option 2 adaptive, at any cap above 10: it can win at most one prize, and a prize is never more than 1/K of the block.
- Grinding needs sock puppets and scale. Even then the gain falls quickly with the cap and is close to zero at 60 outputs.
- Option 1 is the weak one: its single prize is the whole tail (34% to 50% of the block here), so even a single-address miner with 0.5% of the pool gains 1.4%, one with 1.5% gains 4.3%, and a large sock-puppet miner gains up to 30%.
- With no miner below an S19 the tail is heavier than in a pool full of tiny devices, so prizes are larger and every option leaks more than it would there.
- Raising the uncle penalty is a direct lever, at the cost of penalising honest miners with slow links.

## Caveats

Tip choice assumes a share up to three behind the tip still counts as an uncle. The two gains are computed separately; adding them is an upper estimate of doing both. The withholding policy is a simple threshold rule, so its figure is a lower bound on the best possible policy.

Back to the [report](../../REPORT.md).
