# Testnet payouts: a 250 TH/s pool of a few S19s and many Bitaxes

**p2poolv2 payout analysis · 17 November 2026**

The mainnet analysis is in [REPORT.md](REPORT.md). This note asks the same question for a testnet pool of about 250 TH/s. Figures come from [simulation 15](sims/15-testnet-bitaxe/README.md).

## Recommendation

**On this testnet, cap the coinbase at what the S19s can hash and use option 2 with the adaptive split.** A cap that fails on mainnet works here, because the pool finds 50 blocks a day instead of one a week.

- **If the S19s run the old 3,072-byte firmware:** use a cap of 13, or 20 if S19 templates are kept to 16 transactions. The smallest Bitaxe (0.5 TH/s) is paid 4.6 times a day at cap 13 and 7.5 times at cap 20.
- **If the S19s run a 5,120-byte build:** a cap of 60 holds every one of the 56 miners, so nobody is raffled.
- **Do not use option 1.** It pays the smallest Bitaxe 0.6 times a day at cap 13 and treats identical Bitaxes differently.
- **Option 3 is the fallback if the least code matters most.** It pays the smallest Bitaxe 1.3 times a day at cap 13.

This is a workable stopgap for testnet. It is not evidence for mainnet, where the same cap leaves a 1 PH/s miner waiting over a year.

## The pool assumed

Every percentage is a share of the **pool**. 250 TH/s cannot hold more than two S19s at full power, so the base case is 2 S19s and 54 Bitaxes.

| Device | Count | TH/s each | Share of pool each | Class share of pool |
|---|---|---|---|---|
| Antminer S19 | 2 | 95 | 38% | 76.0% |
| Bitaxe Hex | 2 | 3.2 | 1.28% | 2.6% |
| Bitaxe GT | 4 | 2.1 | 0.84% | 3.4% |
| Bitaxe Gamma | 27 | 1.2 | 0.48% | 13.0% |
| Bitaxe Supra | 12 | 0.7 | 0.28% | 3.4% |
| Bitaxe Ultra | 9 | 0.5 | 0.20% | 1.8% |

The pool finds 50 blocks a day, the project's testnet5 figure. Both the device mix and the reading of "a handful of S19s" as two are assumptions.

## What the firmware takes

Taproot-size outputs beside a witness commitment:

| Device | Near-empty testnet block (up to 16 transactions) | Full mainnet block |
|---|---|---|
| S19, 3,072-byte build | 20 | 13 to 14 |
| S19, 5,120-byte build | 68 | 60 to 61 |
| Bitaxe, stock ESP-Miner | about 115 reported working | same |

The Bitaxe firmware has a 16 KiB limit on a stratum line and stalls on larger jobs; a fix is in draft. At these caps the Bitaxes are not the constraint. The S19s are.

## How often each device is paid

Payouts a day / hours between payouts. With no cap every miner is paid 50 times a day.

Cap 13:

| Option | Prize | S19 | Gamma (1.2 TH/s) | Supra (0.7 TH/s) | Ultra (0.5 TH/s) | Ultra: chance of a day with no payout |
|---|---|---|---|---|---|---|
| Option 1 | 16.2% | 50 / 0.5 h | 1.5 / 16.2 h | 0.9 / 27.8 h | 0.6 / 38.9 h | 54% |
| Option 3, evenly spaced | 7.7% | 50 / 0.5 h | 3.1 / 7.7 h | 1.8 / 13.2 h | 1.3 / 18.5 h | 27% |
| Option 2 adaptive | 2.18% | 50 / 0.5 h | 11.0 / 2.2 h | 6.4 / 3.7 h | 4.6 / 5.2 h | 1.0% |

Cap 20:

| Option | Prize | S19 | Gamma (1.2 TH/s) | Supra (0.7 TH/s) | Ultra (0.5 TH/s) | Ultra: chance of a day with no payout |
|---|---|---|---|---|---|---|
| Option 1 | 12.8% | 50 / 0.5 h | 1.9 / 12.8 h | 1.1 / 22.0 h | 0.8 / 30.8 h | 46% |
| Option 3, evenly spaced | 5.0% | 50 / 0.5 h | 4.8 / 5.0 h | 2.8 / 8.6 h | 2.0 / 12.0 h | 13.5% |
| Option 2 adaptive | 1.34% | 50 / 0.5 h | 18.0 / 1.3 h | 10.5 / 2.3 h | 7.5 / 3.2 h | 0.06% |

Cap 60: all 56 miners are paid exactly in every block under options 1 and 2.

Under option 2 adaptive the spread of a week's income for the smallest Bitaxe is 18% at cap 13 and 14% at cap 20, against 5% with no cap.

## Why option 2 adaptive wins by so much here

The pool is top-heavy: two S19s hold 76% of the hashrate.

- **Option 2 adaptive** pays the two S19s exactly and gives the other 11 outputs to the Bitaxes, who share 24% of the block. The prize is 2.2% of the block, so Bitaxes win often.
- **Option 3** spends about ten of its 13 slots on the S19s, leaving about three for 54 Bitaxes.
- **Option 1** pays the S19s and the ten largest Bitaxes exactly and leaves one prize for the other 44. Four of the 27 identical Gammas are paid in every block and the other 23 about every 16 hours, with the tie broken arbitrarily.

## If the mix is different

Smallest Bitaxe (0.5 TH/s), payouts a day / hours between payouts under option 2 adaptive:

| Pool | Cap 13 | Cap 20 | Cap 60 |
|---|---|---|---|
| 2 S19s + 54 mixed Bitaxes (56 miners) | 4.6 / 5.2 h | 7.5 / 3.2 h | paid exactly |
| 2 S19s + 120 Bitaxe Ultras (122 miners) | 4.6 / 5.2 h | 7.5 / 3.2 h | 24.2 / 1.0 h |
| 1 S19 + 155 TH/s of Bitaxes (150 miners) | 1.9 / 12.4 h | 3.1 / 7.8 h | 9.7 / 2.5 h |

The ranking of the options is the same in all three pools.

## Sizing the coinbase by the finder

Bitaxes find 24% of the blocks and can carry all 56 outputs. If their blocks paid everyone exactly and only S19-found blocks were capped at 13, the smallest Bitaxe would be paid 15.5 times a day instead of 4.6. Testnet coins have no value, so the gaming cost found on mainnet does not apply. It still means two valid coinbases per tip, which is extra consensus code for a stopgap; the plain cap already pays every device several times a day.

## Why this works on testnet and not on mainnet

A pool can make at most cap × blocks payouts.

| | Blocks | Cap 13 gives | Miners |
|---|---|---|---|
| This testnet pool | 50 a day | 650 payouts a day | 56 |
| Mainnet pool of 1 EH/s | 1 a week | 683 payouts a year | 1,000 |

## Limits

- The device mix, the two S19s and the 50 blocks a day are assumptions; payouts a day scale with the block rate.
- The S19 output counts are derived from measured job-message caps and have not been bench-tested. The Bitaxe figures come from an open issue and a draft fix in ESP-Miner.
- A cap of 20 fits the old S19 build only while its template holds at most 16 transactions.
- Gaming is not modelled: testnet coins have no value.

Sources are listed in the [simulation README](sims/15-testnet-bitaxe/README.md).
