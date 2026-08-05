"""MB5T source transformation (Phase 1D).

Reproduces stg_mb5t_clean.pq, stg_mb5t_enriched.pq, and out_mb5t_review.pq
(docs/powerquery_m/mb5t/), per the confirmed flow in
docs/NIN_Python_Plan.md section 7.6 and the schema in
docs/nin_data_contracts.md section 2.

MB5T provides in-transit stock quantity, aggregated to one row per
`plant_material_key`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nin_pipeline.sources.sap_text import (
    normalize_material,
    normalize_plant,
    parse_pipe_delimited_sap_export,
    reorder_columns_pq_style,
    to_integer,
    to_number,
)

TOTAL_COLUMNS = 18
SKIP_BEFORE_HEADER = 3
SKIP_AFTER_HEADER = 1

FLOAT_COLUMNS = ("Net Value", "Amount in LC")
INTEGER_COLUMNS = ("Quantity", "Quantity_1")

# Note: unlike PRDPL3, the current production stg_mb5t_clean.pq does NOT
# rename "Plnt" to "Plant" -- the raw SAP column name is retained in both
# the clean and enriched/review outputs.
CLEAN_COLUMN_ORDER = (
    "plant_material_key",
    "Group",
    "Material",
    "Material Description",
    "Quantity",
    "Plnt",
    "Name 1",
    "Pur. Doc.",
    "Item",
    "SPlt",
    "S",
    "BUn",
    "Amount in LC",
    "Crcy",
    "Quantity_1",
    "OUn",
    "Net Value",
    "Crcy_2",
)


def clean_mb5t(path: Path, active_plant: str) -> pd.DataFrame:
    """Parse and standardize an MB5T export for the active plant.

    Mirrors stg_mb5t_clean.pq: parses the fixed-width pipe export, types the
    numeric fields, normalizes `Plnt`/`Material` (without renaming `Plnt`),
    filters to the active plant, builds `plant_material_key`, adds the
    vestigial always-null `Group` column (see docs/NIN_Python_Plan.md
    section 7.6 -- kept only for shape compatibility with an earlier
    defined-set grouping that no longer applies), sorts by `Plnt`/`Material`,
    and drops rows with a blank `Material`.

    Column ordering mirrors `Table.ReorderColumns(..., MissingField.Ignore)`:
    columns in `CLEAN_COLUMN_ORDER` are moved to the front in that order,
    and any other column present in the export (e.g. the real raw header's
    `Amount LC`, which doesn't match the `.pq`'s expected `"Amount in LC"`
    name -- see docs/nin_data_contracts.md Open Decision #5) is *not*
    dropped, only appended at the end, matching real `Table.ReorderColumns`
    semantics.
    """
    df = parse_pipe_delimited_sap_export(
        path,
        total_columns=TOTAL_COLUMNS,
        skip_before_header=SKIP_BEFORE_HEADER,
        skip_after_header=SKIP_AFTER_HEADER,
    )

    for column in FLOAT_COLUMNS:
        if column in df.columns:
            df[column] = to_number(df[column])
    for column in INTEGER_COLUMNS:
        if column in df.columns:
            df[column] = to_integer(df[column])

    df["Plnt"] = normalize_plant(df["Plnt"])
    df["Material"] = normalize_material(df["Material"])

    df = df[df["Plnt"] == active_plant.strip().upper()].copy()

    df["plant_material_key"] = df["Plnt"] + "-" + df["Material"]
    df["Group"] = pd.NA

    df = df.sort_values(["Plnt", "Material"], kind="stable")
    df = df[df["Material"] != ""]

    df = reorder_columns_pq_style(df, list(CLEAN_COLUMN_ORDER))
    return df.reset_index(drop=True)


def enrich_mb5t(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate MB5T quantity to one row per `plant_material_key`.

    Mirrors stg_mb5t_enriched.pq / out_mb5t_review.pq: sums `Quantity`
    grouped by `plant_material_key` (nulls treated as 0, matching pandas'
    default `sum(skipna=True)` behavior for all-null groups), and renames
    the result to `"Quantity in Transit"`.
    """
    grouped = (
        clean_df[["plant_material_key", "Quantity"]]
        .assign(Quantity=lambda d: d["Quantity"].astype("Float64"))
        .groupby("plant_material_key", as_index=False)["Quantity"]
        .sum()
    )
    return grouped.rename(columns={"Quantity": "Quantity in Transit"})
