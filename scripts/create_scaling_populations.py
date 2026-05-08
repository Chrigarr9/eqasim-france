#!/usr/bin/env python3
"""Create 5% and 15% Lyon DRT-area scenario directories by hashcode subsampling.

Reads the 100% Lyon DRT-area population (output_100pct/lyon_drt_area/) and
writes subsampled variants using the same Java hashcode algorithm as
filter_population_by_radius.py and RunCreatePermanentPopulations.java:

    keep if abs(java_hashcode(str(person_id))) % 100 < pct

Nested subsets (5% ⊂ 10% ⊂ 15% ⊂ 25% ⊂ 100%) hold when all populations are
sourced from the same 100% base via this deterministic hash.

Shared files (network, facilities, transit, config) are copied from the 25%
scenario (--donor-rate). Households + vehicles are copied from the donor too —
they are supersets of the target but demand extraction does not simulate so
cross-reference consistency is not required.

Usage:
    .venv/Scripts/python scripts/create_scaling_populations.py
    .venv/Scripts/python scripts/create_scaling_populations.py --rates 5,15
    .venv/Scripts/python scripts/create_scaling_populations.py --rates 15 --donor-rate 25pct
"""
import argparse
import gzip
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import xml.etree.ElementTree as ET


EQASIM_ROOT = Path(__file__).resolve().parent.parent

# Config is the only file taken from the donor (25pct) — it provides the
# simulation parameters (scoring, mode choice, DRT config) which are
# population-size independent.
DONOR_FILES = [
    "lyon_drt_area_config.xml",
]

# All other files must come from the SAME synthesis run as the population
# (source_scenario = output_100pct for hashcode-subsampled populations).
# The eqasim cutter produces subtly different outputs per synthesis run:
# - network: link IDs in activity/facility attributes must match netsim links
# - facilities: only facilities referenced by that run's population are included
# - vehicles/households: household-based vehicle IDs embedded in car legs
# - transit: schedule/vehicles may reference different stop link IDs
# Using a different synthesis run for any of these causes runtime crashes.
SOURCE_FILES = [
    "lyon_drt_area_network.xml.gz",
    "lyon_drt_area_facilities.xml.gz",
    "lyon_drt_area_transit_schedule.xml.gz",
    "lyon_drt_area_transit_vehicles.xml.gz",
    "lyon_drt_area_households.xml.gz",
    "lyon_drt_area_vehicles.xml.gz",
]


def java_hashcode(s: str) -> int:
    """Replicate Java String.hashCode() with numpy.int32 32-bit overflow."""
    with np.errstate(over="ignore"):
        h = np.int32(0)
        for c in s:
            h = np.int32(31) * h + np.int32(ord(c))
    return int(abs(h))


def keep_person(person_id: str, pct: int) -> bool:
    return pct >= 100 or java_hashcode(str(person_id)) % 100 < pct


class _DoctypeStrippingStream:
    """Readable binary stream that removes the first <!DOCTYPE ...> declaration.

    Required because Python's xml.etree.ElementTree.iterparse does not handle
    SYSTEM DOCTYPE references that MATSim population XML files include.
    """

    def __init__(self, f):
        first = f.read(16384)
        first = re.sub(rb"<!DOCTYPE[^>]*>", b"", first)
        self._leftover = first
        self._f = f

    def read(self, n=-1):
        if n == -1:
            data = self._leftover + self._f.read()
            self._leftover = b""
            return data
        out = self._leftover[:n]
        self._leftover = self._leftover[n:]
        rem = n - len(out)
        if rem > 0:
            out += self._f.read(rem)
        return out

    def readable(self):
        return True


def _strip_routes(person_elem) -> None:
    """Remove <route> sub-elements from all legs in a person's plans.

    Routes from the 100% full-region synthesis may reference links that are
    invalid in the cut DRT-area network, causing PersonPrepareForSim to crash.
    Demand extraction re-routes everything, so pre-existing routes are unused.
    """
    for plan in person_elem.findall("plan"):
        for leg in plan.findall("leg"):
            route = leg.find("route")
            if route is not None:
                leg.remove(route)


def subsample_population(source: Path, dest: Path, pct: int) -> tuple[int, int]:
    """Stream-filter a MATSim population.xml.gz; return (kept, total)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    kept = total = 0

    with gzip.open(source, "rb") as raw_in, \
            gzip.open(dest, "wt", encoding="utf-8") as fout:

        fout.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        fout.write('<!DOCTYPE population SYSTEM "http://www.matsim.org/files/dtd/population_v6.dtd">\n')
        fout.write("<population>\n\n")

        context = ET.iterparse(_DoctypeStrippingStream(raw_in), events=("start", "end"))
        root = None
        for event, elem in context:
            if event == "start" and elem.tag == "population":
                root = elem
            elif event == "end" and elem.tag == "person":
                total += 1
                pid = elem.get("id", "")
                if keep_person(pid, pct):
                    kept += 1
                    _strip_routes(elem)
                    fout.write("\t")
                    fout.write(ET.tostring(elem, encoding="unicode"))
                    fout.write("\n")
                if root is not None:
                    root.clear()
                if total % 100_000 == 0:
                    ratio = kept / total * 100
                    print(f"    ... {total:,} processed, {kept:,} kept ({ratio:.1f}%)")

        fout.write("\n</population>\n")

    return kept, total


def setup_scenario_dir(eqasim_root: Path, rate: str, donor: Path, source: Path) -> Path:
    """Create output_lyon_drt_{rate}/lyon_drt_area/ and copy shared files.

    donor  — 25pct DRT-area cut: network, config, transit, facilities
    source — 100pct DRT-area cut: households + vehicles (must match population synthesis)
    """
    scenario_dir = eqasim_root / f"output_lyon_drt_{rate}" / "lyon_drt_area"
    scenario_dir.mkdir(parents=True, exist_ok=True)

    for fname, src_dir in [(f, donor) for f in DONOR_FILES] + [(f, source) for f in SOURCE_FILES]:
        src = src_dir / fname
        dst = scenario_dir / fname
        if not src.exists():
            print(f"  WARNING: source file missing, skipping: {src}")
            continue
        if dst.exists():
            print(f"  exists  {fname}")
        else:
            shutil.copy2(src, dst)
            size_mb = dst.stat().st_size / 1e6
            print(f"  copied  {fname}  ({size_mb:.1f} MB)")

    return scenario_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rates", default="5,15",
                        help="Comma-separated sample percentages to generate (default: 5,15)")
    parser.add_argument("--source-rate", default="100pct",
                        help="Source population rate; '100pct' uses output_100pct/lyon_drt_area/ (default: 100pct)")
    parser.add_argument("--donor-rate", default="25pct",
                        help="Scenario to copy shared files from (default: 25pct)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing population files")
    args = parser.parse_args()

    pcts = [int(r.strip()) for r in args.rates.split(",")]

    if args.source_rate == "100pct":
        source_scenario = EQASIM_ROOT / "output_100pct" / "lyon_drt_area"
    else:
        source_scenario = EQASIM_ROOT / f"output_lyon_drt_{args.source_rate}" / "lyon_drt_area"

    source_pop = source_scenario / "lyon_drt_area_population.xml.gz"
    if not source_pop.exists():
        print(f"ERROR: source population not found: {source_pop}", file=sys.stderr)
        sys.exit(1)

    donor = EQASIM_ROOT / f"output_lyon_drt_{args.donor_rate}" / "lyon_drt_area"
    if not donor.exists():
        print(f"ERROR: donor scenario not found: {donor}", file=sys.stderr)
        sys.exit(1)

    print("=== Lyon DRT scaling population generator ===")
    print(f"  Source pop:  {source_pop}  ({source_pop.stat().st_size / 1e6:.0f} MB)")
    print(f"  Donor:       {donor}  (network/config/transit)")
    print(f"  Source hh/v: {source_scenario}  (households + vehicles)")
    print(f"  Target rates: {pcts}%")
    print()

    for pct in pcts:
        rate = f"{pct}pct"
        print(f"--- {pct}% scenario ---")

        scenario_dir = setup_scenario_dir(EQASIM_ROOT, rate, donor, source_scenario)

        dest_pop = scenario_dir / "lyon_drt_area_population.xml.gz"
        if dest_pop.exists() and not args.force:
            print(f"  Population exists — skipping (use --force to overwrite): {dest_pop}")
            print()
            continue

        print(f"  Subsampling {pct}% of {source_pop.name} ...")
        kept, total = subsample_population(source_pop, dest_pop, pct)
        ratio = kept / total * 100 if total > 0 else 0
        print(f"  Kept {kept:,} / {total:,} agents ({ratio:.1f}%)")
        print(f"  Output: {dest_pop}  ({dest_pop.stat().st_size / 1e6:.1f} MB)")
        print()

    print("=== Done. Run demand extraction with: ===")
    for pct in pcts:
        print(f"  bash scripts/run_lyon_demand_extraction.sh {pct}pct")


if __name__ == "__main__":
    main()
