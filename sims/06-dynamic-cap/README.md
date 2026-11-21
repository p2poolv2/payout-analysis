# 06 · Option 4: coinbase size chosen by the finder's hardware

**Question.** If a block finder may use 13 outputs (old firmware) or 60 outputs (newer firmware), what is gained, what can be gamed, and who pays?

**Why it can be gamed.** Hardware cannot be verified. A miner able to hash the large coinbase can always claim the small one. It sees the raffle seed before building the template, so it can work out its payout under both sizes and use the better one.

**Method.** Synthetic 1,000-miner mainnet population (attacker addresses take the place of the smallest honest miners), option 2 adaptive under both sizes, with the same seed driving both raffles.

- **A.** Revenue gain from choosing the size, from tip choice alone (see [05](../05-grinding/README.md)), and from both together; 24,000 blocks per attacker.
- **B.** Who pays: payouts to everyone else on the blocks the choosing miner finds; 60,000 blocks.
- **C.** Honest use: waiting times when 0%, 20%, 50% or 100% of blocks carry 60 outputs.

**Run.** `python3 run.py > output.txt` (about 4 minutes). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result A: relative revenue gain

Miner sizes are shares of **pool** hashrate.

| Miner | Size choice only | Tip choice only (fixed cap 13) | Both |
|---|---|---|---|
| 20% in one address | 0 | 0 | 0 |
| 20% in 400 addresses | 4.15% | 4.3% | 5.9% |
| 5% in 50 addresses | 2.4% | 1.1% | 2.8% |
| 1.5% in one address | 1.14% | 0 | 1.14% |

With option 1 as the base rule the size choice is worth 11.7% to the miner with 20% of the pool in 400 addresses.

## Result B: who pays

Blocks found by the single-address miner with 1.5% of the pool. It uses the small size on 22.8% of them.

| Group | Fair share | Collects |
|---|---|---|
| The miner choosing | 1.50% | 2.66% |
| Paid exactly at both sizes | 34.38% | 34.38% |
| Exact at 60, raffled at 13 | 31.66% | 31.25% |
| Raffled at both sizes | 32.45% | 31.71% |
| Total | 100% | 100% |

Blocks found by the miner with 20% of the pool in 400 addresses. It uses the small size on 49.3% of them.

| Group | Fair share | Collects |
|---|---|---|
| The miner choosing | 20.00% | 24.10% |
| Paid exactly at both sizes | 29.03% | 29.03% |
| Exact at 60, raffled at 13 | 21.55% | 20.29% |
| Raffled at both sizes | 29.43% | 26.58% |
| Total | 100% | 100% |

## Result C: honest use, mean days between payouts (mainnet)

| Blocks carrying 60 outputs | 1% of pool | 0.1% of pool | One S21 | One S19 | Variance vs no cap, 0.1% of pool | Variance vs no cap, one S19 |
|---|---|---|---|---|---|---|
| 0% | 45 | 451 | 2,256 | 4,749 | 65× | 684× |
| 20% | 21.5 | 187 | 934 | 1,965 | 54× | 564× |
| 50% | 12.0 | 99.5 | 497 | 1,046 | 36.5× | 384× |
| 100% | 6.9 | 56 | 279 | 588 | 8.1× | 85× |

## What it shows

- **Gain.** If a fifth of blocks carry 60 outputs, small miners are paid about 2.4 times as often (one S19 every 1,965 days instead of 4,749). Their income variance improves much less, because the large prizes on small blocks still dominate.
- **Loss.** This is the one option under which an ordinary single-address miner can gain by gaming under the recommended rule (about 1.1%), and it adds about 1.6 points to what a large sock-puppet miner can already take.
- **Who pays.** Every coinbase pays out exactly the reward, so the gain comes from the other miners in the raffle on those blocks. Miners paid exactly at both sizes lose nothing.
- Most of the benefit survives gaming: a small miner usually loses the 13-output raffle, so it prefers the large size anyway.

## Caveats

Two sizes only; each further allowed size gives the finder another option to pick from. The gains are per block found by the choosing miner and therefore scale with its hashrate.

Back to the [report](../../REPORT.md).
