# p2poolv2 coinbase payout analysis

How to pay every miner fairly when a block's coinbase can only carry a limited number of outputs.

Start with the **[report](REPORT.md)**. It compares four options, recommends option 2 with an adaptive split, compares earnings with today's pools, and links each claim to the simulation behind it.

## Layout

```
REPORT.md                     the report (mainnet and the options)
TESTNET-REPORT.md             the same question for a 250 TH/s testnet pool of S19s and Bitaxes
lib/payout_model.py           shared model: populations, payout rules, samplers,
                              grinding helpers, integer reference implementation
sims/NN-name/README.md        what the simulation asks, how to run it, what it found
sims/NN-name/run.py           the simulation
sims/NN-name/output.txt       its output, as used in the report
run_all.sh                    re-run everything
```

## Simulations

| Folder | Question | Runtime |
|---|---|---|
| [01-expected-payout](sims/01-expected-payout/README.md) | Is each variant fair on average? | 30 s |
| [02-wait-and-variance](sims/02-wait-and-variance/README.md) | Waiting times and raffle variance by option | seconds |
| [03-variance-by-hashrate-share](sims/03-variance-by-hashrate-share/README.md) | Payout variance from one S19 to 30% of the pool | 1 min |
| [04-splitting](sims/04-splitting/README.md) | Do sock puppets gain? Can a large miner crowd out others? | 6 min |
| [05-grinding](sims/05-grinding/README.md) | Tip choice and withholding with a 90% uncle credit | 6 min |
| [06-dynamic-cap](sims/06-dynamic-cap/README.md) | Option 4: finder-chosen coinbase size | 4 min |
| [07-optimality-and-reference](sims/07-optimality-and-reference/README.md) | Variance lower bound; integer reference implementation | 1 min |
| [08-bitcoin-hash-seed](sims/08-bitcoin-hash-seed/README.md) | Seeding from the previous Bitcoin block hash | 8 min |
| [09-firmware-caps](sims/09-firmware-caps/README.md) | From firmware byte caps to an output count | 2 min |
| [10-byte-budget](sims/10-byte-budget/README.md) | Count cap or byte budget | 20 s |
| [11-testnet5-vs-mainnet](sims/11-testnet5-vs-mainnet/README.md) | The same rule on the two networks | seconds |
| [12-share-luck](sims/12-share-luck/README.md) | Small miners: share-finding luck stacked with the raffle | 2 min |
| [13-miner-count](sims/13-miner-count/README.md) | 500 miners against 1,000 | 30 s |
| [14-earnings](sims/14-earnings/README.md) | Earnings for an S19, an S21 and large miners against today's pools | seconds |
| [15-testnet-bitaxe](sims/15-testnet-bitaxe/README.md) | Testnet: a 250 TH/s pool of a few S19s and many Bitaxes | 20 s |

## Running

Requires Python 3 with numpy; scipy for simulation 07 and matplotlib for the charts in simulation 03.

```
python3 sims/05-grinding/run.py > sims/05-grinding/output.txt     # one simulation
./run_all.sh                                                       # all of them, about 35 minutes
```

Random seeds are fixed, so a re-run reproduces the output files.

## Assumptions to keep in mind

- Every hashrate percentage is a share of the **pool**, not of the Bitcoin network. The mainnet pool is 1 EH/s, 0.1% of a 1,000 EH/s network, and finds about one block a week. Its smallest miner is one Antminer S19 (95 TH/s, 0.0095% of the pool). The network constants are at the top of `lib/payout_model.py`; their sources are in simulation 14.
- The miner populations are synthetic; see `get_population()` in the model.
- No population has more than 1,000 miners, the scale limit of the p2p network (`MINER_LIMIT` in the model). A sock-puppet miner's addresses count toward that limit and take the place of the smallest honest miners. Simulation 13 compares 500 miners with 1,000 and tests both assumptions.
- The caps (13 and 60 taproot-sized outputs) are derived from a firmware report that covers three builds and has not been bench-tested; see simulation 09.
- A late share earns 90% as an uncle; shares are 10 seconds apart.
- p2poolv2 is assumed to take no pool fee.
