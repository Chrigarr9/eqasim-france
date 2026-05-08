#!/usr/bin/env bash
# Scaling law study: R2 baseline extractions at 1%, 5%, 10%, 15%.
# Runs sequentially to avoid memory pressure (10pct alone needs 64g).
#
# Step 1: generate 5% and 15% scenario directories from 100% population
# Step 2: run R2 (no gate, no pruning) at each rate in ascending size order
#
# Log: each extraction logs to outputs/lyon-eqasim-demand-extraction-<rate>.log
# Monitor: tail -f outputs/lyon-eqasim-demand-extraction-<rate>.log
#
# Usage: bash scripts/run_scaling_study.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EQASIM_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$EQASIM_DIR/.venv/Scripts/python.exe"

echo "======================================================"
echo " Lyon scaling law study — R2 baseline extractions"
echo " $(date)"
echo "======================================================"
echo

# --- Step 1: generate 5% and 15% populations ---
echo "[Step 1] Generating 5% and 15% scenario populations ..."
"$VENV_PYTHON" "$SCRIPT_DIR/create_scaling_populations.py" --rates 5,15
echo "[Step 1] Done."
echo

# --- Step 2: R2 extractions in ascending size order ---
for RATE in 1pct 5pct 10pct 15pct; do
  echo "======================================================"
  echo " Starting R2 extraction: $RATE  ($(date))"
  echo "======================================================"
  # Pass "" as output-dir override so it uses the default path,
  # then --profile r2 as the extra Java arg.
  bash "$SCRIPT_DIR/run_lyon_demand_extraction.sh" "$RATE" "" --profile r2
  echo
  echo "[Done] $RATE  ($(date))"
  echo
done

echo "======================================================"
echo " All scaling study extractions complete  ($(date))"
echo "======================================================"
