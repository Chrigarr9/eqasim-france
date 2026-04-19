#!/usr/bin/env bash
# Phase A — full-region travel-time extraction via multi-iteration MATSim.
#
# Consumes the prepared scenario XMLs produced by
#   synpp config_lyon_fullregion_10pct.yml
# and runs org.eqasim.ile_de_france.RunSimulation for N iterations (default 40)
# to let mode choice and network travel times converge.
#
# Output: output_fullregion_10pct/simulation_output/output_events.xml.gz
# and output_fullregion_10pct/simulation_output/output_trips.csv.gz — these feed
# downstream DRT demand extraction with realistic congested travel times.
#
# Iterations:
# - 40 is the eqasim-ile-de-france paper default (Hörl & Balac 2021).
# - 100 gives tighter convergence at 2.5x the cost.
# - Less than 20 produces noisy travel times.
#
# Usage:
#   bash scripts/run_travel_time_extraction.sh              # 40 iterations
#   bash scripts/run_travel_time_extraction.sh 100          # 100 iterations
set -euo pipefail

ITERATIONS="${1:-40}"
WRITE_EVERY="${2:-$ITERATIONS}"  # only write full events on last iter by default

REPO="$(cd "$(dirname "$0")/../../.." && pwd -W)"
SCENARIO_DIR="$REPO/matsim_scenarios/eqasim-france/output_fullregion_10pct"
CONFIG_PATH="$SCENARIO_DIR/lyon_fullregion_10pct_config.xml"
POPULATION_PATH="$SCENARIO_DIR/lyon_fullregion_10pct_population.xml.gz"
JAR_PATH="$SCENARIO_DIR/lyon_fullregion_10pct_run.jar"
OUTPUT_DIR="$SCENARIO_DIR/simulation_output"
JAVA_BINARY="C:/Users/VWAUCCY/dev/msf/.jdk/jdk-25.0.2+10/bin/java.exe"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "ERROR: missing $CONFIG_PATH"
  echo "       Run synpp config_lyon_fullregion_10pct.yml first to produce the prepared XMLs."
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "=== Phase A travel-time extraction ==="
echo "  Scenario:    $SCENARIO_DIR"
echo "  Config:      $CONFIG_PATH"
echo "  Iterations:  $ITERATIONS"
echo "  Events @:    every $WRITE_EVERY iters"
echo "  Output:      $OUTPUT_DIR"

"$JAVA_BINARY" -Xmx48g -Djava.awt.headless=true \
  -cp "$JAR_PATH" org.eqasim.ile_de_france.RunSimulation \
  --config-path "$CONFIG_PATH" \
  --config:plans.inputPlansFile "$POPULATION_PATH" \
  --config:controler.outputDirectory "$OUTPUT_DIR" \
  --config:controler.lastIteration "$ITERATIONS" \
  --config:controler.overwriteFiles deleteDirectoryIfExists \
  --config:controler.writeEventsInterval "$WRITE_EVERY" \
  --config:controler.writePlansInterval "$WRITE_EVERY" \
  --config:controler.writeTripsInterval 0 \
  --config:qsim.flowCapacityFactor 0.10 \
  --config:qsim.storageCapacityFactor 0.10 \
  --config:controler.createGraphsInterval 0 \
  --config:planCalcScore.writeExperiencedPlans true

echo "=== Done ==="
echo "Events:  $OUTPUT_DIR/output_events.xml.gz"
echo "Trips:   $OUTPUT_DIR/output_trips.csv.gz"
echo "Plans:   $OUTPUT_DIR/output_plans.xml.gz"
echo
echo "Next: extract travel_times.tsv from output_events.xml.gz for downstream"
echo "      DRT demand extraction."
