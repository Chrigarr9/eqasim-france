#!/bin/bash
export JAVA_HOME="C:/Users/VWAUCCY/dev/msf/.jdk/jdk-21.0.2+13"
export PATH="$JAVA_HOME/bin:$PATH"
cd "C:/Users/VWAUCCY/dev/msf/projects/Dissertation/matsim_scenarios/eqasim-france"
LOG_FILE="logs/matsim_output_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs
.venv/Scripts/python -m synpp config_100pct.yml 2>&1 | tee "$LOG_FILE"
