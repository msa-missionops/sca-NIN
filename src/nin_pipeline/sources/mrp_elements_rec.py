"""MRP_ELEMENTS_REC source transformation (Phase 1D).

Reproduces stg_mm_mrp_elements_rec_clean.pq and
stg_mm_mrp_elements_rec_enriched.pq / out_mm_mrp_elements_rec_review.pq
(docs/powerquery_m/mm_mrp_elements_rec/), per the confirmed flow in
docs/NIN_Python_Plan.md section 7.6 and the schema in
docs/nin_data_contracts.md section 4.

MRP_ELEMENTS_REC produces a weekly-grain signed requirement forecast. Per
docs/nin_data_contracts.md Open Decision #1 (updated), this output *is*
joined into the final base table via `pivot_mrp_elements_rec_weekly` below
-- but not through any `.pq` step. The real final Excel workbook builds the
`Total Forecast (Qty)`/`week 1`..`week 27` columns with a native Excel
SUMIFS formula matrix that has no Power Query equivalent (confirmed by
SME; see docs/design_reference/"output headers.csv" and the "output Excel
part *.png" screenshots).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nin_pipeline.ingestion import find_latest_run_folder, find_plant_file
from nin_pipeline.sources.sap_text import (
    normalize_material,
    normalize_plant,
    parse_dynamic_header_sap_export,
    to_number,
    week_ending_friday,
)

HEADER_TOKENS = {"Plnt", "Material", "El"}
FILE_PREFIX = "MM_MRP_ELEMENTS_REC_"

RENAMES = {
    "Plnt": "Plant",
    "Material": "Material No.",
    "El": "Requirements Type",
    "Customer Request Date": "Requirements Date",
    "Rec./reqd.qty": "Req. Qty.",
}


def locate_latest_rec_file(root: Path, plant: str, extension: str = "txt"):
    """Find the latest run folder under `root` and the latest REC export
    within it matching `plant`.

    Mirrors the `FolderSource`/`SortedFolders`/`FileFiltered`/
    `SortedPlantFiles` steps in stg_mm_mrp_elements_rec_clean.pq.

    Returns `(file_path, run_folder_name)`.
    """
    run_folder = find_latest_run_folder(root)
    file_path = find_plant_file(
        run_folder, plant=plant, prefix=FILE_PREFIX, extension=extension
    )
    return file_path, run_folder.name


def clean_mrp_elements_rec(
    path: Path,
    run_folder_name: str,
    active_plant: str,
    as_of_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Parse and standardize an MRP_ELEMENTS_REC export for the active plant.

    Mirrors stg_mm_mrp_elements_rec_clean.pq: locates the SAP header row
    dynamically, renames columns, tags the row with source metadata, treats
    a null `Requirements Date` as the as-of date, drops rows earlier than
    the as-of date, computes `Week Ending`, normalizes keys, and sorts.

    `as_of_date` defaults to the file's modification date (see
    docs/NIN_Python_Plan.md section 7.6 for the documented deviation from
    Power Query's use of Windows file-creation time).
    """
    df = parse_dynamic_header_sap_export(path, HEADER_TOKENS)
    df = df.rename(columns=RENAMES)

    df["Source File"] = path.name
    df["Run Folder"] = run_folder_name
    df["Evaluation Plant"] = active_plant.strip().upper()

    if as_of_date is None:
        as_of_date = pd.Timestamp(path.stat().st_mtime, unit="s").normalize()
    else:
        as_of_date = pd.Timestamp(as_of_date).normalize()

    if "Req. Qty." in df.columns:
        df["Req. Qty."] = to_number(df["Req. Qty."])
    if "Requirements Date" in df.columns:
        df["Requirements Date"] = pd.to_datetime(
            df["Requirements Date"], errors="coerce"
        )
    if "Changed on" in df.columns:
        df["Changed on"] = pd.to_datetime(df["Changed on"], errors="coerce")

    df["Requirements Date"] = df["Requirements Date"].fillna(as_of_date)
    df = df[df["Requirements Date"] >= as_of_date].copy()

    df["Week Ending"] = week_ending_friday(df["Requirements Date"])

    df["Plant"] = normalize_plant(df["Plant"])
    df["Material No."] = normalize_material(df["Material No."])
    df["Requirements Type"] = normalize_plant(df["Requirements Type"])
    if "BUn" in df.columns:
        df["BUn"] = normalize_plant(df["BUn"])

    df = df.sort_values(
        ["Plant", "Material No.", "Week Ending", "Requirements Date"],
        kind="stable",
    ).reset_index(drop=True)
    return df


def enrich_mrp_elements_rec(
    clean_df: pd.DataFrame, rec_req_type: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate MRP_ELEMENTS_REC to weekly signed/absolute requirement
    quantity per `plant_material_key`.

    Mirrors stg_mm_mrp_elements_rec_enriched.pq: drops zero/null requirement
    rows, joins the `rec_req_type` sign table (default `False`/not-negative
    if unmatched), and computes the signed quantity.

    Per docs/nin_data_contracts.md section 4 (Open Decision #2), this
    exposes **both**:

    - `Adj Req Qty` -- absolute value, matching current production
      `out_mm_mrp_elements_rec_review` exactly (the source query's final
      `AbsAdjReqQty` step discards the sign it just computed).
    - `Signed Adj Req Qty` -- the pre-`Abs()` signed value, not present in
      current production output, added here for future use / SME review.
    """
    df = clean_df[
        ["Material No.", "Plant", "Week Ending", "Requirements Type", "Req. Qty."]
    ].copy()
    df = df[df["Req. Qty."].notna() & (df["Req. Qty."] != 0)]

    df["Plant"] = normalize_plant(df["Plant"])
    df["Material No."] = normalize_material(df["Material No."])
    df["Requirements Type"] = normalize_plant(df["Requirements Type"])
    df["Req. Qty."] = to_number(df["Req. Qty."])

    sign_table = rec_req_type.rename(columns={"type": "Requirements Type"}).copy()
    sign_table["Requirements Type"] = normalize_plant(sign_table["Requirements Type"])
    df = df.merge(
        sign_table[["Requirements Type", "negative"]],
        on="Requirements Type",
        how="left",
    )
    df["negative"] = df["negative"].fillna(False).astype(bool)

    sign = df["negative"].map({True: -1, False: 1})
    signed_qty = df["Req. Qty."].abs() * sign

    df["Signed Adj Req Qty"] = signed_qty
    df["Adj Req Qty"] = signed_qty.abs()

    df["plant_material_key"] = df["Plant"] + "-" + df["Material No."]

    result = df[
        ["plant_material_key", "Week Ending", "Adj Req Qty", "Signed Adj Req Qty"]
    ].sort_values(["plant_material_key", "Week Ending"], kind="stable")
    return result.reset_index(drop=True)


WEEKLY_FORECAST_WEEK_COUNT = 27


def pivot_mrp_elements_rec_weekly(
    enriched_df: pd.DataFrame, week_count: int = WEEKLY_FORECAST_WEEK_COUNT
) -> pd.DataFrame:
    """Transpose enriched MRP_ELEMENTS_REC into one row per
    `plant_material_key` with `week 1`..`week <week_count>` columns plus a
    `Total Forecast (Qty)` column, matching the final Excel workbook's
    SUMIFS-based matrix (see module docstring -- this has no `.pq`
    equivalent; confirmed by SME).

    Rules (confirmed by SME against the real workbook):

    - "week 1" is the *earliest* distinct `Week Ending` date present
      anywhere in the REC output (across all `plant_material_key`s), not a
      calendar/fiscal week number and not relative to today's date;
      "week 2" is the next earliest distinct date, and so on, through the
      `week_count`-th distinct date. Every `plant_material_key` shares the
      same week-to-column date mapping.
    - Each `week N` cell is the SUMIFS-equivalent sum of `Adj Req Qty` for
      that `plant_material_key` and that week's date (0 if no matching
      rows).
    - `Total Forecast (Qty)` is the row-wise sum of `week 1`..
      `week <week_count>` **only** -- any REC demand in weeks beyond
      `week_count` is not represented anywhere in the final output,
      matching the real workbook's fixed-width column matrix.
    """
    week_columns = [f"week {i}" for i in range(1, week_count + 1)]

    if enriched_df.empty:
        pivot = pd.DataFrame(columns=["plant_material_key"])
    else:
        distinct_weeks = sorted(enriched_df["Week Ending"].dropna().unique())[
            :week_count
        ]
        pivot = enriched_df.pivot_table(
            index="plant_material_key",
            columns="Week Ending",
            values="Adj Req Qty",
            aggfunc="sum",
            fill_value=0,
        )
        pivot = pivot.reindex(columns=distinct_weeks, fill_value=0)
        pivot.columns = [f"week {i + 1}" for i in range(len(distinct_weeks))]
        pivot = pivot.reset_index()

    for column in week_columns:
        if column not in pivot.columns:
            pivot[column] = 0

    pivot["Total Forecast (Qty)"] = pivot[week_columns].sum(axis=1)

    return pivot[
        ["plant_material_key", "Total Forecast (Qty)", *week_columns]
    ].reset_index(drop=True)
