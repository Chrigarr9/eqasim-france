"""Generate 1%, 10%, 25%, and 100% samples from a radius-filtered Lyon population.

Runs filter_population_by_radius.py four times from the same 100% synthesis output.
All samples share the same geographic filter; smaller samples are nested subsets
(each is drawn from the full radius-filtered pool, not from the previous sample).

Usage:
    python scripts/generate_samples.py \
        --input output_100pct \
        --prefix lyon_100pct_ \
        --radius 30 \
        --commune "Ambérieu-en-Bugey"

    # Custom sample rates:
    python scripts/generate_samples.py \
        --input output_100pct \
        --prefix lyon_100pct_ \
        --radius 30 \
        --commune "Ambérieu-en-Bugey" \
        --samples 0.01 0.10 0.25 1.0
"""
import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_SAMPLES = [0.01, 0.10, 0.25, 1.0]
def main():
    parser = argparse.ArgumentParser(description="Generate multiple sample sizes from Lyon 100% output")
    parser.add_argument("--input", required=True, help="Input directory with eqasim 100%% output")
    parser.add_argument("--prefix", required=True, help="File prefix (e.g. lyon_100pct_)")
    parser.add_argument("--radius", type=float, default=30.0, help="Radius in km (default: 30)")
    parser.add_argument("--center", default=None, help="Center x,y in EPSG:2154 (alternative to --commune)")
    parser.add_argument("--commune", default=None, help="Commune name (looks up centroid from IGN IRIS)")
    parser.add_argument("--iris", default=None, help="Override path to IGN IRIS GeoPackage")
    parser.add_argument("--samples", type=float, nargs="+", default=DEFAULT_SAMPLES,
                        help="Sample fractions to generate (default: 0.01 0.10 0.25 1.0)")
    args = parser.parse_args()

    if args.commune is None and args.center is None:
        parser.error("Provide either --commune or --center")

    script = Path(__file__).parent / "filter_population_by_radius.py"

    print(f"Generating {len(args.samples)} samples from {args.input}")
    print(f"Rates: {[f'{r:.0%}' for r in sorted(args.samples)]}\n")

    results = []
    for rate in sorted(args.samples):
        label = f"{int(rate * 100)}%"
        print(f"{'='*50}")
        print(f"  Sample: {label}")
        print(f"{'='*50}")

        cmd = [
            sys.executable, str(script),
            "--input", args.input,
            "--prefix", args.prefix,
            "--radius", str(args.radius),
            "--sample", str(rate),
            "--seed", str(SEED),
        ]
        if args.commune:
            cmd += ["--commune", args.commune]
        if args.center:
            cmd += ["--center", args.center]
        if args.iris:
            cmd += ["--iris", args.iris]

        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\nERROR: {label} sample failed — stopping.")
            sys.exit(1)

        results.append((label, result.returncode == 0))
        print()

    print("=" * 50)
    print("All samples complete:")
    for label, ok in results:
        print(f"  {label}: {'OK' if ok else 'FAILED'}")


if __name__ == "__main__":
    main()
