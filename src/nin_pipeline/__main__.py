"""nin_pipeline CLI entrypoint.

Usage:
    python -m nin_pipeline run --config config/settings.yaml
"""

from __future__ import annotations

import argparse
import sys

from nin_pipeline.config import load_config
from nin_pipeline.pipeline import run_pipeline


def _run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    result = run_pipeline(config)
    print(f"Run {result.run_id} completed: {len(result.base_table)} base table rows.")
    print(f"Manifest: {result.manifest_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nin_pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="Run the full pipeline once and write nin_base_table"
    )
    run_parser.add_argument(
        "--config",
        required=True,
        help=(
            "Path to a YAML pipeline configuration file "
            "(see docs/NIN_Python_Plan.md section 8)"
        ),
    )
    run_parser.set_defaults(func=_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
