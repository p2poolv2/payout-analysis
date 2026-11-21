#!/bin/sh
# Re-run every simulation and rewrite each folder's output.txt.
# About 35 minutes if run one after another.
set -e
cd "$(dirname "$0")"
for d in sims/*/; do
    echo "running $d"
    python3 "$d/run.py" > "$d/output.txt" 2>&1
done
python3 sims/04-splitting/recheck.py > sims/04-splitting/recheck_output.txt 2>&1

echo "done"
