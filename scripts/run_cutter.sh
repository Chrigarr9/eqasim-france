#!/usr/bin/env bash
# Apply the DRT-area polygon cut to a prepared scenario.
#
# Invokes org.eqasim.core.scenario.cutter.RunScenarioCutter manually with
# absolute paths and the Lambert-93 companion shapefile produced by
# scenario-selection/build_cutter_polygon.py. Bypasses the synpp
# `matsim.simulation.cutter.cut` stage, which has two bugs in this fork:
# relative-path handling under cwd=output_path, and WGS84 extent vs L93
# network.
#
# Usage:
#   bash scripts/run_cutter.sh <scenario-name> <rate-label>
#
# Examples:
#   bash scripts/run_cutter.sh lyon_drt 1pct
#   bash scripts/run_cutter.sh lyon_drt 10pct
#
# Output lands at:
#   output_<scenario-name>_<rate-label>/<scenario-name>_area/
#     <scenario-name>_area_config.xml
#     <scenario-name>_area_network.xml.gz
#     <scenario-name>_area_population.xml.gz
#     <scenario-name>_area_households.xml.gz
#     <scenario-name>_area_facilities.xml.gz
#     <scenario-name>_area_vehicles.xml.gz
#     <scenario-name>_area_transit_{schedule,vehicles}.xml.gz
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <scenario-name> <rate-label>"
  echo "Example: $0 lyon_drt 1pct"
  exit 1
fi

NAME="$1"
RATE="$2"

REPO_POSIX="$(cd "$(dirname "$0")/../../.." && pwd)"
REPO_WIN="$(cd "$(dirname "$0")/../../.." && pwd -W)"
SCENARIO_DIR="$REPO_WIN/matsim_scenarios/eqasim-france/output_${NAME}_${RATE}"
POLY_SHP="$REPO_WIN/matsim_scenarios/eqasim-france/data/cutter/${NAME}_area.shp"
CONFIG="${NAME}_${RATE}_config.xml"
PREFIX="${NAME}_area_"
OUT_SUBDIR="${NAME}_area"

JAR="C:/matsim_cache_lyon/matsim.runtime.eqasim__8b47747b574715b5fcb5abf827714fb3.cache/eqasim-java/ile_de_france/target/ile_de_france-2.1.0.jar"
JAVA="C:/Users/VWAUCCY/dev/msf/.jdk/jdk-25.0.2+10/bin/java.exe"

if [[ ! -d "$SCENARIO_DIR" ]]; then
  echo "ERROR: scenario directory not found: $SCENARIO_DIR"
  echo "       Run synpp config_${NAME}_${RATE}.yml first."
  exit 1
fi

if [[ ! -f "$POLY_SHP" ]]; then
  echo "ERROR: Lambert-93 cutter shapefile not found: $POLY_SHP"
  echo "       Run scripts/setup_drt_scenario.py to regenerate (it produces"
  echo "       both .geojson WGS84 and .shp L93 companions)."
  exit 1
fi

cd "$SCENARIO_DIR"
mkdir -p "$OUT_SUBDIR"

echo "=== Cutting ${NAME}_${RATE} ==="
echo "  Scenario: $SCENARIO_DIR"
echo "  Config:   $CONFIG"
echo "  Extent:   $POLY_SHP"
echo "  Output:   $SCENARIO_DIR/$OUT_SUBDIR"

"$JAVA" -Xmx16G -cp "$JAR" org.eqasim.core.scenario.cutter.RunScenarioCutter \
  --config-path "$CONFIG" \
  --output-path "$OUT_SUBDIR" \
  --extent-path "$POLY_SHP" \
  --prefix "$PREFIX"

echo "=== Done ==="
ls -la "$OUT_SUBDIR/"
