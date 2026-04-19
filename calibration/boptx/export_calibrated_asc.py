"""
Export best-so-far calibrated ASCs from the boptx optimization pickle.

Reads `optimization_lyon_1pct.p`, finds the evaluation with the lowest
objective value, and writes `calibrated_asc.yml` with the corresponding
parameter values. `run_eqasim_lyon_1pct.sh` reads this YAML and applies
the ASCs as `--mode-choice-parameter:X` overrides on top of the IDF
defaults.

Usage:
    cd matsim_scenarios/eqasim-france/calibration/boptx
    ../../.venv/Scripts/python export_calibrated_asc.py
"""
import pickle
import pathlib
import datetime


PICKLE_PATH = pathlib.Path("optimization_lyon_1pct.p")
OUT_YAML = pathlib.Path("calibrated_asc.yml")


def main():
    if not PICKLE_PATH.exists():
        raise SystemExit(f"No calibration pickle found: {PICKLE_PATH.resolve()}")

    with open(PICKLE_PATH, "rb") as f:
        state = pickle.load(f)

    # boptx PickleTracker stores a dict with 'evaluations' list.
    evaluations = state.get("evaluations") if isinstance(state, dict) else None
    if evaluations is None:
        # Fallback: object form
        evaluations = getattr(state, "evaluations", None)
    if not evaluations:
        raise SystemExit("No evaluations in pickle — calibration hasn't produced any finished evals.")

    best = None
    for ev in evaluations:
        try:
            obj = ev.get_objective() if callable(getattr(ev, "get_objective", None)) else ev["objective"]
        except Exception:
            continue
        if obj is None:
            continue
        if best is None or obj < best[0]:
            best = (obj, ev)

    if best is None:
        raise SystemExit("No evaluation had a finite objective.")

    obj, ev = best
    try:
        values = ev.get_values()
        param_names = [p.parameter for p in ev.get_problem().parameters]
    except Exception:
        values = ev["values"]
        param_names = ev["parameters"]

    lines = [
        "# calibrated_asc.yml - exported from boptx pickle",
        f"# Source:    {PICKLE_PATH.resolve()}",
        f"# Best objective (L1): {obj:.6f}",
        f"# Generated: {datetime.date.today().isoformat()}",
        "",
        "# Reference alternative is PT — pt.alpha_u is pinned at 0 in the",
        "# calibration (not varied). Motorcycle pinned at IDF default (+1.35).",
        "# Applied via CLI in the run script.",
        "pt.alpha_u: 0.0",
        "motorcycle.alpha_u: 1.35",
        "",
    ]
    for name, val in zip(param_names, values):
        lines.append(f"{name}: {val:+.6f}")

    OUT_YAML.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT_YAML.resolve()}")
    print(f"Best objective: {obj:.6f}")
    for name, val in zip(param_names, values):
        print(f"  {name:40s} = {val:+.6f}")


if __name__ == "__main__":
    main()
