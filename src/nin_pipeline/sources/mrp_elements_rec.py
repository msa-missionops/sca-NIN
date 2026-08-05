"""MRP_ELEMENTS_REC source transformation (Phase 1D).

Reproduces stg_mm_mrp_elements_rec_clean.pq and
stg_mm_mrp_elements_rec_enriched.pq / out_mm_mrp_elements_rec_review.pq
(docs/powerquery_m/mm_mrp_elements_rec/), per the confirmed flow in
docs/NIN_Python_Plan.md section 7.6 and the schema in
docs/nin_data_contracts.md section 4.

MRP_ELEMENTS_REC produces a weekly-grain signed requirement forecast. Per
docs/NIN_Python_Plan.md section 7.6.1, this output is **not currently joined
into the final base table** -- it is defined here for completeness and for
any future weekly-forecast view, not because Phase 1 requires it in
`nin_base_table`.
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
