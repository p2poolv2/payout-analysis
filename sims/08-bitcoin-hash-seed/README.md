# 08 · Alternative seed: the previous Bitcoin block hash

**Question.** Would seeding the raffle from the previous Bitcoin block hash, instead of the parent share's hash, remove seed grinding?

**Design tested.** The seed is the `prev_blockhash` of the template. The raffle weights are the PPLNS window frozen at the last share mined on the previous Bitcoin tip. Every template for one Bitcoin height then has identical payouts.

**Method.** Synthetic 1,000-miner mainnet population (a 1 EH/s pool, nobody below one S19), option 2 adaptive, 10-second shares (60 per Bitcoin block), 20,000-share window. The attacker's addresses count toward the 1,000-miner limit and take the place of the smallest honest miners.

- **A. Tip choice.** With the seed fixed, how far does an attacker's payout move when the frozen window differs by 1 or 3 shares?
- **B. Block veto.** A pool block's hash is the next seed, so its finder knows the next raffle before publishing and could discard the block.
- **C. Steering.** If the window is not frozen: the attacker credits each new share to whichever of its existing addresses then wins the most slots under the known seed. (With the pool at the miner limit it cannot add fresh addresses.)
- **D. Conditional hopping.** A share-by-share simulation of both seed designs in which the attacker mines here only while the current raffle pays it more than its average, and elsewhere otherwise.

**Run.** `python3 run.py > output.txt` (about 8 minutes). Code: [run.py](run.py). Results: [output.txt](output.txt).

## Results (cap 13)

Attacker sizes are shares of **pool** hashrate.

| Channel | Per-share seed | Bitcoin-hash seed |
|---|---|---|
| Tip choice, 20% in 400 addresses | 4.3% (see [05](../05-grinding/README.md)) | 0.1% |
| Withholding, 20% in 400 addresses | 2.2% | none (the seed does not depend on shares) |
| Hopping, 20% in 400 addresses | −0.1% (noise, see below) | 2.7% (2.8% if mining elsewhere costs a 2% fee) |
| Hopping, 5% in 50 addresses | 0.1% (noise) | 0.1% (within noise) |
| Hopping, 1.5% in one address | 0.0% | 0.3% (within noise) |
| Hopping, 20% in one address | 0 | 0 |
| Hopping plus rented hashrate, 20% in 400 addresses | not possible | 5.4% renting 1× own hashrate, 11.0% renting 3× |
| Block veto, revenue gain | not possible | 0.24% at most |
| Block veto, pool blocks lost if every eligible miner did it | none | 7.5% on mainnet, 4.5% on testnet5 |
| Steering if the window is not frozen | not possible | 1.7% to 9.9% (2.6% to 9.3% in a pool of mostly small miners) |

At cap 60 hopping still gives the miner with 20% of the pool in 400 addresses about 1% and the block veto disappears.

**Noise level.** An honest miner in the same simulation scores −0.09% under the per-share seed and +0.36% under the Bitcoin-hash seed, so differences below about 0.4% are noise. Under the per-share seed the expected hopping gain is zero by construction.

## What it shows

- The Bitcoin-hash seed does remove tip choice and withholding.
- It opens **hopping** instead. The raffle is public and fixed for about ten minutes, so pool hashrate present during that time raises the chance that a block lands on that raffle. A miner in the money stays; a miner out of the money leaves. There is no penalty, and rented hashrate multiplies the gain.
- The per-share seed is immune to hopping: each raffle is played by exactly one share whether or not a given miner is present, so presence cannot change which raffle a block lands on.
- The window must be frozen before the seed is known, or a miner with several addresses can steer its new shares onto the ones that win.
- The block veto is individually tiny but destroys pool blocks, and at cap 13 with 10-second shares it is (barely) rational for single-address miners holding more than 1.7% of the pool.

**Conclusion.** Keep the per-share seed.

## Caveats

The hopping gains for the two smaller attackers are within the simulation's noise. Rental is priced 5% above fair mining value. The block-veto analysis assumes a block-solving share cannot be published without revealing the block. Part C assumes the pool is at the 1,000-miner limit; with room for new addresses an attacker could plant fresh ones on winning positions, which is stronger than steering and was not re-run here.

Back to the [report](../../REPORT.md).
