"""
Produce a `lyon_1pct_asc_only_config.xml` with DiscreteModeChoice strategy
weight = 1.0 (100% replanning) so that every agent undergoes mode choice
exactly once per single-iteration calibration evaluation.

The default generated config has DMC at 0.05 and KeepLastSelected at 0.95,
suitable for warm-start multi-iteration simulations — but wrong for single-
iter ASC calibration where we want every agent to pick a fresh mode each
trial. Without this fix, only ~5% of agents produce the calibration signal;
the other 95% contribute noise from their initialization-random modes.

This is the eqasim/Bavaria-v4 pattern. Idempotent: can safely be re-run.

Usage:
    cd matsim_scenarios/eqasim-france/calibration/boptx
    ../../.venv/Scripts/python make_asc_only_config.py
"""
import pathlib
import xml.etree.ElementTree as ET


INPUT = pathlib.Path("../../output_1pct/lyon_1pct_config.xml")
OUTPUT = pathlib.Path("../../output_1pct/lyon_1pct_asc_only_config.xml")


def set_weight(tree, strategy_name: str, new_weight: float) -> bool:
    """Find the strategysettings parameterset for `strategy_name` and set its weight.

    Returns True if the strategy was found and modified.
    """
    for parameterset in tree.iter("parameterset"):
        if parameterset.attrib.get("type") != "strategysettings":
            continue
        name_param = None
        weight_param = None
        for p in parameterset.findall("param"):
            if p.attrib.get("name") == "strategyName":
                name_param = p
            elif p.attrib.get("name") == "weight":
                weight_param = p
        if name_param is not None and name_param.attrib.get("value") == strategy_name:
            if weight_param is None:
                raise RuntimeError(f"Strategy {strategy_name} has no weight param")
            print(f"  {strategy_name}: {weight_param.attrib['value']} -> {new_weight}")
            weight_param.attrib["value"] = f"{new_weight}"
            return True
    return False


def main():
    if not INPUT.exists():
        raise SystemExit(f"Input config not found: {INPUT.resolve()}")

    tree = ET.parse(INPUT)
    print(f"Reading  {INPUT.resolve()}")

    # Set DMC to 100% replanning, KeepLastSelected to 0 (disabled).
    # Every agent picks a fresh mode every evaluation — no warm-start noise.
    for name, weight in [
        ("DiscreteModeChoice", 1.0),
        ("KeepLastSelected", 0.0),
    ]:
        if not set_weight(tree, name, weight):
            print(f"  WARNING: strategy {name} not found — no change applied.")

    # Preserve the MATSim DOCTYPE that MATSim's config reader expects.
    tree.write(OUTPUT, encoding="UTF-8", xml_declaration=True)

    # ElementTree doesn't write the DOCTYPE; manually prepend it to match
    # what MATSim's ConfigReader expects.
    raw = OUTPUT.read_text(encoding="utf-8")
    if "<!DOCTYPE" not in raw:
        lines = raw.splitlines(keepends=True)
        # Insert DOCTYPE after <?xml ...?> declaration
        doctype = '<!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">\n'
        if lines and lines[0].startswith("<?xml"):
            lines.insert(1, doctype)
        else:
            lines.insert(0, doctype)
        OUTPUT.write_text("".join(lines), encoding="utf-8")

    print(f"Wrote    {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
