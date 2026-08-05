"""Reference / tag data loading (Phase 1F).

Loads the small business-managed lookup tables that were Excel-workbook
tables in the current production process (`tbl_tag_region`,
`tbl_tag_top60`, `tbl_tag_sourceplant`, `rec_req_type`, `plant_evaluation`)
-- see docs/nin_data_contracts.md section 6 -- from CSV files under a
`reference_data_folder`, so `nin_pipeline.sources.prdpl3.enrich_prdpl3` and
`nin_pipeline.sources.mrp_elements_rec.enrich_mrp_elements_rec` can be
called with plain DataFrames as they already expect.

Expected file names under `reference_data_folder` (one CSV per table,
column names matching the corresponding `.pq` source exactly):

- `region.csv` -- columns: Plant, Region
- `top60.csv` -- columns: plant_material_key, plant, material, top_60_flag
- `sourceplant.csv` -- columns: source_key, desc, source_plant
- `rec_req_type.csv` -- columns: type, negative (accepts "true"/"false",
  "1"/"0", or "yes"/"no", case-insensitive; any other/blank value is
  treated as not-negative, matching the default in
  `enrich_mrp_elements_rec`)
- `plant_evaluation.csv` -- columns: Plant (single active-plant row)

These file names/format are a Python-port convention (there is no
pre-existing file-based convention in production, where these lived as
Excel table objects in the same workbook as the Power Query); revisit if
the SME has an established naming convention to match instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TRUE_VALUES = {"true", "1", "yes"}


@dataclass
class ReferenceData:
    region: pd.DataFrame
    top60: pd.DataFrame
    sourceplant: pd.DataFrame
    rec_req_type: pd.DataFrame
    plant_evaluation: pd.DataFrame


def _read_csv(folder: Path, filename: str) -> pd.DataFrame:
    path = folder / filename
    if not path.exists():
        raise FileNotFoundError(f"Reference data file not found: {path}")
    return pd.read_csv(path, dtype="string")


def load_reference_data(folder: str | Path) -> ReferenceData:
    """Load all reference/tag tables from `folder` (see module docstring
    for expected file names and columns)."""
    folder = Path(folder)

    rec_req_type = _read_csv(folder, "rec_req_type.csv")
    rec_req_type["negative"] = (
        rec_req_type["negative"]
        .astype("string")
        .str.strip()
        .str.lower()
        .isin(TRUE_VALUES)
    )

    return ReferenceData(
        region=_read_csv(folder, "region.csv"),
        top60=_read_csv(folder, "top60.csv"),
        sourceplant=_read_csv(folder, "sourceplant.csv"),
        rec_req_type=rec_req_type,
        plant_evaluation=_read_csv(folder, "plant_evaluation.csv"),
    )


def active_plant(reference_data: ReferenceData) -> str:
    """Return the single active evaluation plant, matching the
    `ParamPlant` step used identically by every `stg_<source>_clean.pq`."""
    df = reference_data.plant_evaluation
    if len(df) == 0:
        raise ValueError("plant_evaluation table must contain one plant row.")
    return str(df.iloc[0]["Plant"]).strip().upper()
