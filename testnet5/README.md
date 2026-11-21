# Testnet5 hashrate distribution from coinbases

How miner hashrate is distributed on Bitcoin testnet5, worked out from the coinbase of every block.

```
export BITCOIN_RPC_URL=http://minis:18352 BITCOIN_RPC_USER=p2pool BITCOIN_RPC_PASSWORD=...
uv run testnet5/coinbase_distribution.py --epochs 1            # current difficulty, with fits
uv run testnet5/coinbase_distribution.py                       # whole chain, no fits
uv run testnet5/coinbase_distribution.py --epochs 1 --by tag   # group by pool tag
uv run testnet5/coinbase_distribution.py --by outputs          # split p2pool coinbases by payout
```

- **Connection:** the script talks to `bitcoind` over JSON-RPC. It authenticates with `--rpc-cookie`, or with a user and password. Each option can also be set by environment variable (`BITCOIN_RPC_URL`, `_USER`, `_PASSWORD`, `_COOKIE`). Use the variable for the password, so it doesn't show up in the process list.
- **Cache:** coinbases are cached in `testnet5/data/<chain>-coinbases.jsonl`. Later runs fetch only new blocks and drop cached blocks that a reorg replaced. `--no-sync` analyses the cache without contacting the node.
- **Outputs:** each run writes a plot and a per-miner CSV to `testnet5/output/`.

## Method

- **Data:** for each block, the script fetches `getblock` (verbosity 1) and then the coinbase with `getrawtransaction <txid> true <blockhash>`. This works without `-txindex`.
- **Attribution** (`--by`):
  - `address` (the default): the output address paid the most.
  - `tag`: the ASCII tag in the coinbase scriptSig, such as `ckpool` or `P2Poolv2`.
  - `outputs`: splits each block across its output addresses by value. That gives each p2poolv2 miner's share of the pool's blocks.
- **Hashrate:** a block of difficulty D is D·2³² expected hashes, so a miner's hashrate is the work of their blocks divided by the period.
- **Minimum-difficulty blocks:** testnets let anyone mine a minimum-difficulty block after 20 minutes without a block. The script flags blocks over 100 times easier than the hardest block in their retarget epoch, reports them separately and leaves them out of the distribution. Testnet5 has had none so far.
- **Fits:** the lognormal and log-logistic count models from `lib/hashrate_fit.py`, the same ones used in [../xmr](../xmr/README.md).
  - **Single difficulty only.** Under a changing difficulty, block counts don't measure hashrate: an easy early block counts as much as a hard late one. So the script fits only when the selected blocks share one difficulty, which `--epochs 1` ensures.
  - **Whole chain:** over the whole chain, the stats are still computed from work, but no fit is made.

## Findings (to height 7,848, 2026-11-21)

### The chain is still ramping up

Testnet5 started on 2026-11-14. Difficulty has risen 4× at each retarget, which is the maximum step, and blocks still come about 3.6 times faster than the 10-minute target.

| Epoch | Heights | Difficulty | Days | Blocks per day |
|---|---|---|---|---|
| 0 | 1–2,015 | 1.05 M | 0.6 | 3,413 |
| 1 | 2,016–4,031 | 4.19 M | 0.4 | 4,800 |
| 2 | 4,032–6,047 | 16.8 M | 3.0 | 671 |
| 3 | 6,048–7,848 | 67.1 M | 3.4 | 524 |

This is why fits need `--epochs 1`. Over the whole chain, P2Poolv2's main address found the most blocks (1,938) but did only 10% of the work, because most of those blocks were easy early ones.

### The current epoch (3.4 days, 1,801 blocks)

Network hashrate is 1.75 PH/s: about 18 S19s, or 1,460 Bitaxe Gammas.

| | |
|---|---|
| Miners (addresses) | 21 |
| Largest miner | 38.6% (ckpool, 676 TH/s) |
| Two largest | 76% (ckpool and Testnet5.com Pool) |
| Top 10 | 98.7% |
| Bottom half | 1.3% |
| Miners for >50% | 2 |
| Gini | 0.83 |
| Largest ÷ smallest seen | ~700× |

| Pool tag | Blocks | Share | Hashrate |
|---|---|---|---|
| ckpool | 718 | 39.9% | 697 TH/s |
| Testnet5.com Pool | 674 | 37.4% | 655 TH/s |
| P2Poolv2 | 133 | 7.4% | 129 TH/s |
| ckpool/@jaonoctus/casa21 | 93 | 5.2% | 90 TH/s |
| (no tag) | 89 | 4.9% | 86 TH/s |
| P2Poolv2-21m.dev | 34 | 1.9% | 33 TH/s |
| plebhash (Sv2) | 22 | 1.2% | 21 TH/s |
| 7 others | 18 | 1.0% | |

- **Testnet5 is more head-heavy than any of the Monero pools.** Two pools do three quarters of the work, and the bottom half of addresses holds about 1%. That puts it closest to Monero's main sidechain, which has a tail index of about 0.5.
- **Fits:** lognormal (σ = 3.9) and log-logistic (c = 0.50) fit equally well, and both pass the chi-square test (p ≈ 0.55). The log-logistic tail index of about 0.5 is the infinite-mean regime: the largest miners keep a fixed share however many small miners join.
  - **Small sample:** with 21 miners, the parameters are loose.
  - **Unseen miners:** the fits imply roughly 20 to 30 further miners too small to have found a block in 3.4 days. That is below about 1 TH/s, which covers most Bitaxes.
- **P2Poolv2's own payouts:** most of its blocks pay 8 outputs. With `--by outputs`, its largest payees receive the equivalent of 131, 73 and 30 TH/s of network hashrate, followed by a tail of small miners.

### Caveats

- **Addresses are not people.** One pool pays many miners from one coinbase address, and one miner can use several addresses. `--by outputs` breaks down only the pools that pay miners directly in the coinbase, such as p2poolv2.
- **The chain is a week old.** Hashrate nearly tripled from week 45 to week 46. Rerun as it settles; later runs fetch only the new blocks.
