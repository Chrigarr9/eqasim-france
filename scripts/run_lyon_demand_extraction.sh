#!/usr/bin/env bash
# Lyon DRT demand extraction — eqasim-native.
#
# Invokes org.matsim.contrib.demand_extraction.run.RunLyonEqasimDemandExtraction
# via `mvn exec:java` against the cut scenario for the given sample rate.
# Uses IDF-calibrated mode-choice parameters (Hörl & Balac 2021) unchanged —
# see .project-memory/lyon-calibration-decision-2026-04-19.md for why.
#
# Prerequisites:
#   1. Cut scenario produced by scripts/run_cutter.sh lyon_drt <rate>
#      (lives at output_lyon_drt_<rate>/lyon_drt_area/).
#      100% is a special case — the original full-region run was from 2026-04-19
#      and lives at output_100pct/lyon_drt_area/ instead.
#   2. Congested travel times from the Phase-A 40-iter full-region 10% run:
#      output_fullregion_10pct/travel_times.tsv (already extracted).
#
# Usage:
#   bash scripts/run_lyon_demand_extraction.sh <rate> [<output-dir>]
#
# Examples:
#   bash scripts/run_lyon_demand_extraction.sh 1pct
#   bash scripts/run_lyon_demand_extraction.sh 10pct
#   bash scripts/run_lyon_demand_extraction.sh 25pct
#   bash scripts/run_lyon_demand_extraction.sh 100pct
#   bash scripts/run_lyon_demand_extraction.sh 10pct /tmp/my-run
#
# Output lands at (default):
#   outputs/lyon-eqasim-demand-extraction-<rate>/
#     drt_requests.csv
#     exmas_rides.csv
#     run.log
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <rate> [<output-dir>] [<extra-java-args>...]"
  echo "  rate: 1pct | 5pct | 10pct | 15pct | 25pct | 100pct"
  echo "  extra-java-args: e.g. --max-detour-factor 1.3 --search-horizon 1800"
  exit 1
fi

RATE="$1"
OUT_OVERRIDE="${2:-}"
# Any args beyond the first two are forwarded to the Java main class
EXTRA_ARGS="${@:3}"

# Sample number for qsim flow/storage capacity + sweep-log tagging
case "$RATE" in
  1pct)   SAMPLE=1   ;;
  5pct)   SAMPLE=5   ;;
  10pct)  SAMPLE=10  ;;
  15pct)  SAMPLE=15  ;;
  25pct)  SAMPLE=25  ;;
  100pct) SAMPLE=100 ;;
  *) echo "ERROR: unknown rate '$RATE' (expected 1pct|5pct|10pct|15pct|25pct|100pct)"; exit 1 ;;
esac

REPO_POSIX="$(cd "$(dirname "$0")/../../.." && pwd)"
REPO_WIN="$(cd "$(dirname "$0")/../../.." && pwd -W)"
EQASIM_DIR="$REPO_WIN/matsim_scenarios/eqasim-france"
DE_DIR="$REPO_POSIX/matsim-libs/contribs/drt-demand-extraction"

# 100% was cut from the pre-existing full-region scenario (2026-04-19);
# it lives at output_100pct/lyon_drt_area/, not output_lyon_drt_100pct/.
if [[ "$RATE" == "100pct" ]]; then
  SCENARIO_DIR="$EQASIM_DIR/output_100pct/lyon_drt_area"
else
  SCENARIO_DIR="$EQASIM_DIR/output_lyon_drt_$RATE/lyon_drt_area"
fi

PREFIX="lyon_drt_area_"
TRAVEL_TIMES="$EQASIM_DIR/output_fullregion_10pct/travel_times.tsv"

if [[ -n "$OUT_OVERRIDE" ]]; then
  OUT_DIR="$OUT_OVERRIDE"
else
  OUT_DIR="$REPO_WIN/outputs/lyon-eqasim-demand-extraction-$RATE"
fi

# Sanity checks before firing off mvn
if [[ ! -f "$SCENARIO_DIR/${PREFIX}population.xml.gz" ]]; then
  echo "ERROR: cut scenario missing: $SCENARIO_DIR/${PREFIX}population.xml.gz"
  echo "       Run scripts/run_cutter.sh lyon_drt $RATE first."
  exit 1
fi
if [[ ! -f "$TRAVEL_TIMES" ]]; then
  echo "ERROR: travel times missing: $TRAVEL_TIMES"
  echo "       Run scripts/run_travel_time_extraction.sh first."
  exit 1
fi

# Pre-delete the output directory so the run starts clean.
# RunLyonEqasimDemandExtraction uses overwriteExistingFiles (not deleteDirectoryIfExists)
# to avoid a Windows file-lock issue with exec:java; this rm ensures a clean slate.
OUT_DIR_POSIX="$REPO_POSIX/outputs/lyon-eqasim-demand-extraction-$RATE"
rm -rf "$OUT_DIR_POSIX"
mkdir -p "$OUT_DIR_POSIX"

echo "=== Lyon DRT demand extraction (IDF-calibrated) ==="
echo "  Rate:          $RATE"
echo "  Sample:        $SAMPLE%"
echo "  Scenario dir:  $SCENARIO_DIR"
echo "  Prefix:        $PREFIX"
echo "  Travel times:  $TRAVEL_TIMES"
echo "  Output:        $OUT_DIR"
echo

MAIN="org.matsim.contrib.demand_extraction.run.RunLyonEqasimDemandExtraction"

# JDK 25 is required — eqasim-ile_de_france classes in the local .m2 are v69
# bytecode (compiled by the synpp runtime). JDK 22 (currently the default
# JAVA_HOME on this machine) would reject them with "falsche Version 69.0".
export JAVA_HOME="C:/Users/VWAUCCY/dev/msf/.jdk/jdk-25.0.2+10"
export PATH="$JAVA_HOME/bin:$PATH"

MVN_BIN="C:/Users/VWAUCCY/dev/msf/.maven/maven/bin/mvn.cmd"
if [[ ! -f "$MVN_BIN" ]]; then
  MVN_BIN="mvn"  # fallback for non-Windows dev machines
fi

# Write the tee log OUTSIDE the output directory.
# MATSim uses deleteDirectoryIfExists which deletes $OUT_DIR on startup.
# On Windows, if tee already holds a file open inside that dir, the delete
# fails with "file is used by another process" → Guice injection failure.
# Placing the log alongside (not inside) $OUT_DIR avoids the file-lock clash.
LOG="$REPO_POSIX/outputs/lyon-eqasim-demand-extraction-$RATE.log"

echo "  Log:           $LOG"
echo "  Monitor:       tail -f \"$LOG\""
echo

cd "$DE_DIR"
# exec:java (same JVM as Maven) avoids the Windows 32KB command-line limit that
# exec:exec hits when %classpath expands to hundreds of JARs.
# MATSim's log4j2 FileAppender won't initialise (Maven owns the log4j2 context),
# so ALL output is captured by tee using the POSIX path so git-bash can write it.
# -Xmx100g: 10% Lyon has ~236k agents; 100g gives headroom for 15%+ runs
# (mode-routing cache + pair-gen; previous floor was 64g at 10%).
MAVEN_OPTS="-Djava.awt.headless=true -Xmx100g" "$MVN_BIN" -o compile exec:java \
  "-Dexec.mainClass=$MAIN" \
  "-Dexec.args=--sample $SAMPLE --scenario-dir $SCENARIO_DIR --prefix $PREFIX --travel-times $TRAVEL_TIMES --output-dir $OUT_DIR $EXTRA_ARGS" \
  -Denforcer.skip=true \
  -DskipTests \
  2>&1 | tee "$LOG"

echo
echo "=== Done ==="
echo "Log:      $LOG"
echo "Requests: $OUT_DIR/drt_demand/"
