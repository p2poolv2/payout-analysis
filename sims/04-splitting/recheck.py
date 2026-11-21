#!/usr/bin/env python3
"""Re-check of the four unbiased cells of part A that came out two or more
standard errors low in the main run: 600,000 blocks each with a fresh random
seed. Runtime: about 1 minute."""
import sys
import pathlib
import math
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "lib"))
import numpy as np
from payout_model import get_population, with_attacker, spec, mc, label, CAP_OLD

B = 600_000
w0 = get_population("mainnet_small")[0]
rng = np.random.default_rng(2024)
for scheme, name, pieces in (("opt1", "3% as 30 addresses", [0.001] * 30),
                             ("opt1", "0.5% as 50 addresses", [0.0001] * 50),
                             ("opt1", "0.5% as 10 addresses", [0.0005] * 10),
                             ("opt3_sys", "3% as 1 address", [0.03])):
    w, att = with_attacker(w0, pieces)
    h = sum(pieces)
    x = mc(w, *spec(w, CAP_OLD, scheme), B, rng, att=att)["att"][:, 0]
    print(f"{label(scheme)}, {name}: expected payout / fair share = "
          f"{x.mean() / h:.4f} +- {x.std() / math.sqrt(B) / h:.4f}")
