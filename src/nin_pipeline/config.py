"""Pipeline configuration (Phase 1F).

Loads the technical settings described in docs/NIN_Python_Plan.md section 8
from a YAML file: source folders, file-selection strategy, and output
options. Business-managed mappings (region/top60/sourceplant/rec_req_type/
plant_evaluation) are *not* part of this config -- they live as reference
data files under `paths.reference_data_folder` (see
`nin_pipeline.reference_data`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PipelinePaths:
    prdpl3_folder: Path
    mrp_rec_folder: Path
    mrp_doh_folder: Path
    mb5t_folder: Path
    reference_data_folder: Path
    output_folder: Path
    run_folder: Path
    log_folder: Path


@dataclass
class FileSelectionConfig:
    strategy: str = "latest_modified"
    ignore_hidden: bool = True


@dataclass
class OutputConfig:
    write_parquet: bool = True
    write_csv: bool = True
    write_excel: bool = True


@dataclass
class PipelineConfig:
    paths: PipelinePaths
    file_selection: FileSelectionConfig = field(default_factory=FileSelectionConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def _require(d: dict, key: str, section: str) -> str:
    if key not in d or d[key] in (None, ""):
        raise ValueError(f"Missing required config key: {section}.{key}")
    return d[key]


def load_config(path: str | Path) -> PipelineConfig:
    """Load a `PipelineConfig` from a YAML file matching the schema in
    docs/NIN_Python_Plan.md section 8."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    paths_raw = raw.get("paths", {})
    paths = PipelinePaths(
        prdpl3_folder=Path(_require(paths_raw, "prdpl3_folder", "paths")),
        mrp_rec_folder=Path(_require(paths_raw, "mrp_rec_folder", "paths")),
        mrp_doh_folder=Path(_require(paths_raw, "mrp_doh_folder", "paths")),
        mb5t_folder=Path(_require(paths_raw, "mb5t_folder", "paths")),
        reference_data_folder=Path(
            _require(paths_raw, "reference_data_folder", "paths")
        ),
        output_folder=Path(_require(paths_raw, "output_folder", "paths")),
        run_folder=Path(_require(paths_raw, "run_folder", "paths")),
        log_folder=Path(_require(paths_raw, "log_folder", "paths")),
    )

    fs_raw = raw.get("file_selection", {})
    file_selection = FileSelectionConfig(
        strategy=fs_raw.get("strategy", "latest_modified"),
        ignore_hidden=fs_raw.get("ignore_hidden", True),
    )

    out_raw = raw.get("output", {})
    output = OutputConfig(
        write_parquet=out_raw.get("write_parquet", True),
        write_csv=out_raw.get("write_csv", True),
        write_excel=out_raw.get("write_excel", True),
    )

    return PipelineConfig(paths=paths, file_selection=file_selection, output=output)
