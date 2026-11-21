# 15 · Testnet: a 250 TH/s pool of a few S19s and many Bitaxes

**Question.** On a testnet pool of about 250 TH/s made of a couple of S19s and a lot of Bitaxes, how do the capped payout options behave, and which should be used?

**Sizes.** Shares are of **pool** hashrate. In a 250 TH/s pool one S19 (95 TH/s) is 38% of the pool and the smallest Bitaxe (0.5 TH/s) is 0.2%.

**The pool assumed.** 250 TH/s cannot hold more than two S19s at full power, so the base case is 2 S19s and Bitaxes making up the other 60 TH/s. Bitaxe hashrates are stock figures (source 3). The pool finds 50 blocks a day, the project's testnet5 figure.

| Device | Count | TH/s each | Share of pool each | Class share of pool |
|---|---|---|---|---|
| Antminer S19 | 2 | 95 | 38% | 76.0% |
| Bitaxe Hex | 2 | 3.2 | 1.28% | 2.6% |
| Bitaxe GT | 4 | 2.1 | 0.84% | 3.4% |
| Bitaxe Gamma | 27 | 1.2 | 0.48% | 13.0% |
| Bitaxe Supra | 12 | 0.7 | 0.28% | 3.4% |
| Bitaxe Ultra | 9 | 0.5 | 0.20% | 1.8% |

56 miners in all. Two variants bracket "a handful of S19s and a lot of Bitaxes": 1 S19 with 155 TH/s of Bitaxes (150 miners), and 2 S19s with 120 Bitaxe Ultras (122 miners).

**Method.** Closed-form payout distributions for options 1, 2 (adaptive) and 3 at caps of 13, 20 and 60, per device type; the finder-sized coinbase (option 4) as a blend of two caps; a 200,000-block Monte Carlo check of fairness.

**Run.** `python3 run.py > output.txt` (about 20 seconds). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Result B: what each device's firmware takes

Taproot-size outputs beside a witness commitment. S19 figures use the job-message caps measured in [09](../09-firmware-caps/README.md); fewer merkle branches leave more room, and testnet blocks are nearly empty.

| Transactions in the block | S19, 3,072-byte build | S19, 5,120-byte build |
|---|---|---|
| 1 (coinbase only) | 23 | 71 |
| up to 16 | 20 | 68 |
| up to 64 | 19 | 67 |
| up to 8,192 (a full mainnet block) | 14 | 61 |

**Bitaxe (ESP-Miner).** The stock firmware has a 16 KiB limit on a stratum line. A coinb2 of about 5 KB is reported to work, which is about 115 taproot-size outputs; a job line of 14 to 15.5 KB is reported to stall the miner without disconnecting. A fix raising the limit is in draft (sources 1 and 2). So on this testnet the Bitaxes are not the constraint; the S19s are.

## Result C: each option, base pool

Payouts a day / hours between payouts. With no cap every miner is paid 50 times a day.

Cap 13:

| Option | Exact + raffle | Prize | S19 | Gamma (1.2 TH/s) | Supra (0.7 TH/s) | Ultra (0.5 TH/s) | Ultra: chance of a day with no payout |
|---|---|---|---|---|---|---|---|
| Option 1 | 12 + 1 | 16.2% | 50 / 0.5 h | 1.5 / 16.2 h | 0.9 / 27.8 h | 0.6 / 38.9 h | 54% |
| Option 3, evenly spaced | 0 + 13 | 7.7% | 50 / 0.5 h | 3.1 / 7.7 h | 1.8 / 13.2 h | 1.3 / 18.5 h | 27% |
| Option 2 adaptive | 2 + 11 | 2.18% | 50 / 0.5 h | 11.0 / 2.2 h | 6.4 / 3.7 h | 4.6 / 5.2 h | 1.0% |

Cap 20:

| Option | Exact + raffle | Prize | S19 | Gamma (1.2 TH/s) | Supra (0.7 TH/s) | Ultra (0.5 TH/s) | Ultra: chance of a day with no payout |
|---|---|---|---|---|---|---|---|
| Option 1 | 19 + 1 | 12.8% | 50 / 0.5 h | 1.9 / 12.8 h | 1.1 / 22.0 h | 0.8 / 30.8 h | 46% |
| Option 3, evenly spaced | 0 + 20 | 5.0% | 50 / 0.5 h | 4.8 / 5.0 h | 2.8 / 8.6 h | 2.0 / 12.0 h | 13.5% |
| Option 2 adaptive | 2 + 18 | 1.34% | 50 / 0.5 h | 18.0 / 1.3 h | 10.5 / 2.3 h | 7.5 / 3.2 h | 0.06% |

Cap 60: the pool has 56 miners, so options 1 and 2 pay everyone exactly in every block and there is no raffle.

Under option 1 the Gamma rows are for a Gamma left in the raffle: it pays 4 of the 27 identical Gammas exactly at cap 13 (11 at cap 20) and raffles the rest.

Spread of one week's income (standard deviation ÷ mean) under option 2 adaptive, against 5% with no cap:

| Cap | S19 | Hex | GT | Gamma | Supra | Ultra |
|---|---|---|---|---|---|---|
| 13 | 5% | 7% | 9% | 11% | 15% | 18% |
| 20 | 5% | 5% | 7% | 9% | 12% | 14% |
| 60 | 5% | 5% | 5% | 5% | 5% | 5% |

## Result D: coinbase sized by the finder

Bitaxes find 24% of the blocks and can carry all 56 outputs. If their blocks pay everyone exactly and only S19-found blocks are capped (option 2 adaptive on those):

| S19-found blocks capped at | Gamma | Supra | Ultra |
|---|---|---|---|
| 13, same cap on every block | 11.0 / 2.2 h | 6.4 / 3.7 h | 4.6 / 5.2 h |
| 13, Bitaxe blocks carry everyone | 20.4 / 1.2 h | 16.9 / 1.4 h | 15.5 / 1.5 h |
| 20, same cap on every block | 18.0 / 1.3 h | 10.5 / 2.3 h | 7.5 / 3.2 h |
| 20, Bitaxe blocks carry everyone | 25.7 / 0.9 h | 20.0 / 1.2 h | 17.7 / 1.4 h |

## Result E: variants, smallest Bitaxe (0.5 TH/s, 0.2% of pool)

Payouts a day / hours between payouts.

| Pool | Option | Cap 13 | Cap 20 | Cap 60 | Cap 110 |
|---|---|---|---|---|---|
| 1 S19 + 155 TH/s of Bitaxes (150 miners) | Option 1 | 0.2 / 125 h | 0.2 / 117 h | 0.3 / 71 h | 1.1 / 22.6 h |
| | Option 3 | 1.3 / 18.5 h | 2.0 / 12.0 h | 6.0 / 4.0 h | 11.0 / 2.2 h |
| | Option 2 adaptive | 1.9 / 12.4 h | 3.1 / 7.8 h | 9.7 / 2.5 h | 18.8 / 1.3 h |
| 2 S19s + 120 Bitaxe Ultras (122 miners) | Option 1 | 0.5 / 52.8 h | 0.5 / 49.4 h | 0.8 / 30.2 h | 3.8 / 6.2 h |
| | Option 3 | 1.3 / 18.5 h | 2.0 / 12.0 h | 6.0 / 4.0 h | 11.0 / 2.2 h |
| | Option 2 adaptive | 4.6 / 5.2 h | 7.5 / 3.2 h | 24.2 / 1.0 h | 45.0 / 0.5 h |

## Result F: fairness check

Over 200,000 simulated blocks at cap 13, paid ÷ fair share was between 0.999 and 1.004 for S19s, Gammas, Ultras and all Bitaxes together under each of the three options.

## What it shows

- **On this testnet a capped coinbase with a raffle works.** At 50 blocks a day a 13-output cap still makes 650 payouts a day for 56 miners. Under option 2 adaptive the smallest Bitaxe is paid 4.6 times a day and has a 1% chance of a day with no payout.
- **Option 2 adaptive is clearly best for a pool this top-heavy.** The two S19s hold 76% of the hashrate and are paid exactly; the other 11 slots share the remaining 24%, so the prize is 2.2% of the block. Option 3 spends about ten of its 13 slots on the S19s and pays an Ultra 1.3 times a day. Option 1 pays an Ultra 0.6 times a day.
- **Option 1 treats identical devices differently.** It pays four of the 27 Gammas in every block and the other 23 about every 16 hours, with the tie broken arbitrarily.
- **The cap comes from the S19s, not the Bitaxes.** On near-empty testnet blocks the old S19 build fits about 20 taproot-size outputs instead of 13, and the newer builds fit 68 or more, which is more than the pool has miners.
- **The result holds across the variants.** With one S19 and about 150 Bitaxes the smallest Bitaxe is still paid 1.9 times a day at cap 13 and 3.1 times at cap 20.
- **This says nothing about mainnet.** It works because of the block rate: the same 13 outputs make 650 payouts a day here and 683 a year in the 1 EH/s mainnet pool of the [report](../../REPORT.md).

## Caveats

- The pool composition is assumed. "A handful of S19s" is read as two, the most that fit in 250 TH/s at full power.
- 50 pool blocks a day is the project's testnet5 figure; payouts a day scale with it.
- The S19 output counts are derived from the job-message caps in the firmware report, which itself says they need a bench test. The Bitaxe figures come from an open issue and a draft fix, not from a specification.
- A cap of 20 fits the old S19 build only while its template holds at most 16 transactions.
- Gaming is not modelled here: testnet coins have no value.

## Sources

1. [ESP-Miner issue 2081: raise or remove the line-length limit for stratum messages](https://github.com/bitaxeorg/ESP-Miner/issues/2081)
2. [ESP-Miner pull request 2082: support coinbase jobs with 10,000 payouts](https://github.com/bitaxeorg/ESP-Miner/pull/2082)
3. [Bitaxe Supra vs Gamma vs Hex vs GT, D-Central](https://d-central.tech/bitaxe-supra-vs-gamma-vs-hex-vs-gt/)

Back to the [testnet report](../../TESTNET-REPORT.md) or the [main report](../../REPORT.md).
