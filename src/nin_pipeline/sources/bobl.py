"""BOBL (backorder/backlog) source transformation (Phase 1D).

Reproduces stg_bobl_clean.pq and stg_bobl_enriched.pq / out_bobl_review.pq
(docs/powerquery_m/BOBL/), per docs/NIN_Python_Plan.md section 7.6 and
docs/nin_data_contracts.md section 5.

Unlike the other sources, BOBL's input is a pasted PowerBI matrix export
(`Table_BOBL`), not a SAP flat-file extract, so there is no file-discovery
step here -- the caller is expected to already have this as a DataFrame
with the raw PowerBI column names (e.g. loaded from wherever that export
is refreshed to). `stg_bobl_clean.pq`'s only *active* step is a type
conversion; a large block of key-building/grouping/duplicate-flagging
logic is present in the source file but commented out (`/* ... */`) and
therefore not part of current production behavior, so it is not ported.

Note the confirmed key-casing inconsistency (docs/NIN_Python_Plan.md
section 7.6, Open Decision #4): production's `stg_bobl_enriched.pq` builds
`plant_material_key` with `Text.Trim()` only, no `Text.Upper()`, unlike
every other source. Per `docs/nin_data_contracts.md`'s adopted default,
`enrich_bobl()` here upper-cases the key for consistency with the rest of
the pipeline; revisit if the SME wants production's Trim-only behavior
reproduced exactly instead.
"""

from __future__ import annotations

import pandas as pd

from nin_pipeline.sources.sap_text import to_number

PLANT_COL = "PowerBI Consolidated Backlog by PG Last N Weeks[Plant]"
MATERIAL_COL = (
    "PowerBI Consolidated Backlog by PG Last N Weeks" "[Material.Material Level 01.Key]"
)

NUMERIC_COLUMNS = (
    "[SumBackorder_Actual]",
    "[SumBackorder_Quantity]",
    "[SumBacklog_Quantity]",
    "[SumBacklog_Actual]",
)

RENAMES = {
    "[SumBackorder_Actual]": "Backorder Actual",
    "[SumBackorder_Quantity]": "Backorder Qnty",
    "[SumBacklog_Quantity]": "Backlog Qnty",
    "[SumBacklog_Actual]": "Backlog Actual",
}

ENRICHED_COLUMN_ORDER = (
    "plant_material_key",
    "Backorder Actual",
    "Backorder Qnty",
    "Backlog Actual",
    "Backlog Qnty",
)


def clean_bobl(raw: pd.DataFrame) -> pd.DataFrame:
    """Type-coerce the raw `Table_BOBL` PowerBI matrix export.

    Mirrors stg_bobl_clean.pq's only active step (`#"Changed Type"`):
    coerces the plant/material key columns to text and the four
    backorder/backlog measure columns to numeric, tolerating blanks.
    Any other columns present in `raw` (the full PowerBI export has ~30)
    are passed through unchanged, since downstream `enrich_bobl()` selects
    only the columns it needs.
    """
    df = raw.copy()
    if PLANT_COL in df.columns:
        df[PLANT_COL] = df[PLANT_COL].astype("string")
    if MATERIAL_COL in df.columns:
        df[MATERIAL_COL] = df[MATERIAL_COL].astype("string")
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = to_number(df[col])
    return df


def enrich_bobl(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Build `plant_material_key` and sum the backorder/backlog measures
    across any duplicate key rows.

    Mirrors stg_bobl_enriched.pq: selects the plant/material/measure
    columns, builds the key, sums each measure per key (treating
    non-numeric/blank values as 0, matching the source's `ToNumberOrZero`
    helper), renames the measure columns, and orders them per
    `ENRICHED_COLUMN_ORDER`.
    """
    df = clean_df[[PLANT_COL, MATERIAL_COL, *NUMERIC_COLUMNS]].copy()

    plant = df[PLANT_COL].astype("string").str.strip().str.upper()
    material = df[MATERIAL_COL].astype("string").str.strip().str.upper()
    df["plant_material_key"] = plant + "-" + material

    for col in NUMERIC_COLUMNS:
        df[col] = to_number(df[col]).fillna(0)

    grouped = df.groupby("plant_material_key", as_index=False)[
        list(NUMERIC_COLUMNS)
    ].sum()
    grouped = grouped.rename(columns=RENAMES)

    return (
        grouped[list(ENRICHED_COLUMN_ORDER)]
        .sort_values("plant_material_key", kind="stable")
        .reset_index(drop=True)
    )
