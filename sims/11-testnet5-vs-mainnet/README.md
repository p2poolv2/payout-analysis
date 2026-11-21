# 11 · Testnet5 against mainnet

**Question.** The pool finds about 50 blocks a day on testnet5 and about 1 a week on mainnet (a 1 EH/s pool, 0.1% of the network). How differently does the same payout rule behave on the two?

**Sizes.** Shares are of **pool** hashrate, not of the Bitcoin network. On mainnet the pool is 1 EH/s (0.1% of the network): 1% of the pool is 10 PH/s, 0.1% is 1 PH/s, 0.02% is one S21 and 0.0095% is one S19. The same four shares are used on testnet5 so the two can be compared.

**Method.** Closed-form payout distributions on the two synthetic populations at caps of 13 and 60. For each size: mean days between payouts, the chance of no payout in 30 days, and the spread of 30-day income (standard deviation ÷ mean, block luck included).

**Run.** `python3 run.py > output.txt` (a few seconds). Code: [run.py](run.py). Results: [output.txt](output.txt).

## The two settings

| | Testnet5 | Mainnet |
|---|---|---|
| Miners (assumed) | 124 | 1,000 (the p2p network limit), none below one S19 |
| Pool blocks per 30 days | 1,500 | 4.3 |
| Days between pool blocks | 0.02 | 6.94 |
| Spread of 30-day income with no cap | 3% | 48% |

## Result: option 2 adaptive, cap 13

| Share of pool | Testnet5: days between payouts | Testnet5: no payout in 30 days | Testnet5: 30-day spread | Mainnet: days between payouts | Mainnet: no payout in 30 days | Mainnet: 30-day spread |
|---|---|---|---|---|---|---|
| 1% (10 PH/s on mainnet) | 0.09 | 0% | 6% | 45 | 52% | 123% |
| 0.1% (1 PH/s) | 0.93 | 0% | 18% | 451 | 94% | 388% |
| 0.02% (one S21) | 4.6 | 0.2% | 39% | 2,256 | 98.7% | 867% |
| 0.0095% (one S19) | 9.8 | 4.6% | 57% | 4,749 | 99.4% | 1,258% |

## Result: the options compared, 0.1% of the pool, cap 13

| Option | Testnet5: days between payouts | Testnet5: 30-day spread | Mainnet: days between payouts | Mainnet: 30-day spread |
|---|---|---|---|---|
| No cap | 0.02 | 3% | 6.94 | 48% |
| Option 1 | 4.2 | 37% | 2,813 | 968% |
| Option 3, evenly spaced | 1.5 | 23% | 534 | 422% |
| Option 2 adaptive | 0.93 | 18% | 451 | 388% |

At cap 60, option 2 adaptive pays a miner with 0.1% of the pool every 0.04 days on testnet5 and every 56 days on mainnet; one S19 on mainnet waits 588 days.

## How much of the pool is served within 30 days (option 2 adaptive)

| Network | Cap | Miners with at least an even chance of a payout | Their share of hashrate |
|---|---|---|---|
| Testnet5 | 13 | 100% | 100% |
| Testnet5 | 60 | 100% | 100% |
| Mainnet | 13 | 1.6% | 64.4% |
| Mainnet | 60 | 7.3% | 78.5% |

## What it shows

- The ranking of the options is the same on both networks. What differs is how much it matters.
- On testnet5 blocks arrive about 350 times as often, so any unbiased option pays everyone within days. Fairness over time is not a concern there; the reason to run the recommended rule on testnet5 is to exercise the same code mainnet will run.
- On mainnet the same waiting times, counted in blocks, become months or years. For a miner with 0.1% of the pool the choice of option changes the wait from 7.7 years (option 1) to 1.2 years (option 2 adaptive) at cap 13, and the cap matters even more (56 days at cap 60).
- Grinding and splitting gains are relative to revenue and do not depend on the block rate, so the results of [04](../04-splitting/README.md) and [05](../05-grinding/README.md) apply to both networks. Testnet coins have no value, so nobody has a reason to grind there; the code paths can still be tested.
- A testnet5 template has few merkle branches, so it does not load old firmware the way a full mainnet block does. See the note in [09](../09-firmware-caps/README.md).

## Caveats

Both populations are assumptions. The mainnet one is a 1 EH/s pool capped at 1,000 miners with nobody below one S19; [13](../13-miner-count/README.md) compares it with 500 miners. The testnet5 one (four rigs, twenty single ASICs, a hundred small devices) has no miner below 0.01% of its pool, which is why every miner there is served within 30 days.

Back to the [report](../../REPORT.md).
