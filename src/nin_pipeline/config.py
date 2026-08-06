"""Pipeline configuration (Phase 1F).

Loads the technical settings described in docs/NIN_Python_Plan.md section 8
from a YAML file: source folders, file-selection strategy, and output
options. Business-managed mappings (region/top60/sourceplant/rec_req_type/
plant_evaluation) are *not* part of this config -- they are loaded by
`nin_pipeline.reference_data` from either a single Excel workbook
(`paths.reference_data_workbook`, recommended -- lets business users keep
editing the same named Excel Tables they already maintain, no export step)
or a folder of CSVs (`paths.reference_data_folder`, for automated/CSV-only
setups). Exactly one of the two must be set.

Optionally, `paths.active_plants_folder` points at a folder containing a
headerless, single-column CSV of plant codes (one per row) -- the latest
file in that folder is used, matching the same "latest file" convention as
every other source folder (see `nin_pipeline.reference_data.load_active_plants`
and docs/nin_data_contracts.md Open Decision #11). When set, the pipeline
runs once per listed plant and concatenates the results into one combined
`nin_base_table`, instead of running for the single plant named in
`plant_evaluation.csv`.

`file_selection.mrp_doh_file_extension`/`mrp_rec_file_extension` control the
file extension `find_plant_file` filters on when locating each plant's
MRP_ELEMENTS_DOH/MRP_ELEMENTS_REC export (mirrors the `FileExt` parameter in
the original Power Query source). Defaults to "txt"; set to "csv" if the
live SAP exports are written as .csv files.
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
    output_folder: Path
    run_folder: Path
    log_folder: Path
    reference_data_folder: Path | None = None
    reference_data_workbook: Path | None = None
    active_plants_folder: Path | None = None


@dataclass
class FileSelectionConfig:
    strategy: str = "latest_modified"
    ignore_hidden: bool = True
    mrp_doh_file_extension: str = "txt"
    mrp_rec_file_extension: str = "txt"


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

    reference_data_folder = paths_raw.get("reference_data_folder") or None
    reference_data_workbook = paths_raw.get("reference_data_workbook") or None
    active_plants_folder = paths_raw.get("active_plants_folder") or None

    paths = PipelinePaths(
        prdpl3_folder=Path(_require(paths_raw, "prdpl3_folder", "paths")),
        mrp_rec_folder=Path(_require(paths_raw, "mrp_rec_folder", "paths")),
        mrp_doh_folder=Path(_require(paths_raw, "mrp_doh_folder", "paths")),
        mb5t_folder=Path(_require(paths_raw, "mb5t_folder", "paths")),
        output_folder=Path(_require(paths_raw, "output_folder", "paths")),
        run_folder=Path(_require(paths_raw, "run_folder", "paths")),
        log_folder=Path(_require(paths_raw, "log_folder", "paths")),
        reference_data_folder=(
            Path(reference_data_folder) if reference_data_folder else None
        ),
        reference_data_workbook=(
            Path(reference_data_workbook) if reference_data_workbook else None
        ),
        active_plants_folder=(
            Path(active_plants_folder) if active_plants_folder else None
        ),
    )

    if bool(paths.reference_data_folder) == bool(paths.reference_data_workbook):
        raise ValueError(
            "Exactly one of paths.reference_data_folder or "
            "paths.reference_data_workbook must be set."
        )

    fs_raw = raw.get("file_selection", {})
    file_selection = FileSelectionConfig(
        strategy=fs_raw.get("strategy", "latest_modified"),
        ignore_hidden=fs_raw.get("ignore_hidden", True),
        mrp_doh_file_extension=fs_raw.get("mrp_doh_file_extension", "txt"),
        mrp_rec_file_extension=fs_raw.get("mrp_rec_file_extension", "txt"),
    )

    out_raw = raw.get("output", {})
    output = OutputConfig(
        write_parquet=out_raw.get("write_parquet", True),
        write_csv=out_raw.get("write_csv", True),
        write_excel=out_raw.get("write_excel", True),
    )

    return PipelineConfig(paths=paths, file_selection=file_selection, output=output)
