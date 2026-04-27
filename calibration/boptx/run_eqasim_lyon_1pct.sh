#!/usr/bin/env bash
# Run eqasim-ile-de-france simulation for Lyon 1% scenario with calibrated ASCs.
#
# Reads ASC overrides from calibrated_asc.yml (produced by export_calibrated_asc.py
# after calibrate_lyon_1pct.py converges). Runs a full MATSim loop with DMC
# replanning for `iterations` iters.
#
# Usage:
#   bash run_eqasim_lyon_1pct.sh [iterations]
#
# Output: outputs/eqasim-lyon-1pct/
set -euo pipefail

ITERATIONS="${1:-100}"

# pwd -W gives Windows-native C:/... path for child java processes
REPO="$(cd "$(dirname "$0")/../../../.." && pwd -W)"
SCENARIO_DIR="$REPO/matsim_scenarios/eqasim-france/output_1pct"
CONFIG_PATH="$SCENARIO_DIR/lyon_1pct_config.xml"
POPULATION_PATH="$SCENARIO_DIR/lyon_1pct_population.xml.gz"
OUTPUT_DIR="$REPO/outputs/eqasim-lyon-1pct"
ASC_YAML="$REPO/matsim_scenarios/eqasim-france/calibration/boptx/calibrated_asc.yml"
JAR_PATH="$SCENARIO_DIR/lyon_1pct_run.jar"
JAVA_BINARY="C:/Users/VWAUCCY/dev/msf/.jdk/jdk-25.0.2+10/bin/java.exe"
PYTHON_BINARY="$REPO/matsim_scenarios/eqasim-france/.venv/Scripts/python.exe"

# Read calibrated ASCs from YAML (if present) and build --mode-choice-parameter flags
ASC_ARGS=""
if [[ -f "$ASC_YAML" ]]; then
  ASC_ARGS=$("$PYTHON_BINARY" -c "
import yaml
with open(r'$ASC_YAML') as f:
    d = yaml.safe_load(f) or {}
for k, v in d.items():
    if k.startswith('#') or not isinstance(v, (int, float)):
        continue
    print(f'--mode-choice-parameter:{k}={v:+.6f}')
" | tr '\n' ' ')
else
  echo "NOTE: $ASC_YAML not found — running with IDF defaults."
fi

mkdir -p "$OUTPUT_DIR"

echo "=== Eqasim Lyon 1% base simulation ==="
echo "  Scenario:    $SCENARIO_DIR"
echo "  Population:  $POPULATION_PATH"
echo "  Output:      $OUTPUT_DIR"
echo "  Iterations:  $ITERATIONS"
echo "  ASC YAML:    $ASC_YAML"
echo "  ASC args:    $ASC_ARGS"

"$JAVA_BINARY" -Xmx12g -Djava.awt.headless=true \
  -cp "$JAR_PATH" org.eqasim.ile_de_france.RunSimulation \
  --config-path "$CONFIG_PATH" \
  --config:plans.inputPlansFile "$POPULATION_PATH" \
  --config:controler.outputDirectory "$OUTPUT_DIR" \
  --config:controler.lastIteration "$ITERATIONS" \
  --config:controler.overwriteFiles deleteDirectoryIfExists \
  --config:controler.writeEventsInterval "$ITERATIONS" \
  --config:controler.writePlansInterval "$ITERATIONS" \
  --config:controler.writeTripsInterval 0 \
  --config:qsim.flowCapacityFactor 0.01 \
  --config:qsim.storageCapacityFactor 0.01 \
  --config:controler.createGraphsInterval 0 \
  $ASC_ARGS

echo "=== Done ==="
echo "Events:  $OUTPUT_DIR/output_events.xml.gz"
echo "Trips:   $OUTPUT_DIR/output_trips.csv.gz"
