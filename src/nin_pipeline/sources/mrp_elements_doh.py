"""MRP_ELEMENTS_DOH source transformation (Phase 1D).

Reproduces stg_mm_mrp_elements_doh_clean.pq and
stg_mm_mrp_elements_doh_pivot.pq (docs/powerquery_m/mm_mrp_elements_doh/),
per the confirmed flow in docs/NIN_Python_Plan.md section 7.6 and the
schema in docs/nin_data_contracts.md section 3.

Unlike MRP_ELEMENTS_REC, this output *is* joined into the final base table
(`build_overview_p2_enriched`): the pivoted requirement-type columns
(WB/VJ/VC/VG/PP/U1/U2) feed the Available Stock and DOH calculations
(docs/NIN_Python_Plan.md section 14).
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
FILE_PREFIX = "MM_MRP_ELEMENTS_DOH_"

RENAMES = {
    "Plnt": "Plant",
    "Material": "Material No.",
    "El": "Requirements Type",
    "Customer Request Date": "Requirements Date",
    "Rec./reqd.qty": "Req. Qty.",
}

# Per docs/nin_data_contracts.md section 3, Open Decision #3: force all 7
# pivot columns (the current production query's safety net only forces 6,
# omitting "VG", which build_overview_p2_enriched unconditionally expands).
EXPECTED_PIVOT_COLUMNS = ["WB", "VJ", "VC", "VG", "PP", "U1", "U2"]


def locate_latest_doh_file(root: Path, plant: str, extension: str = "txt"):
    """Find the latest run folder under `root` and the latest DOH export
    within it matching `plant`.

    Mirrors the `FolderSource`/`SortedFolders`/`FileFiltered`/
    `SortedPlantFiles` steps in stg_mm_mrp_elements_doh_clean.pq.

    Returns `(file_path, run_folder_name)`.
    """
    run_folder = find_latest_run_folder(root)
    file_path = find_plant_file(
        run_folder, plant=plant, prefix=FILE_PREFIX, extension=extension
    )
    return file_path, run_folder.name


def clean_mrp_elements_doh(
    path: Path,
    run_folder_name: str,
    active_plant: str,
    as_of_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Parse and standardize an MRP_ELEMENTS_DOH export for the active plant.

    Mirrors stg_mm_mrp_elements_doh_clean.pq: locates the SAP header row
    dynamically, renames columns, tags the row with source metadata, treats
    a null `Requirements Date` as the as-of date, drops rows earlier than
    the as-of date, computes `Week Ending`, applies the DOH-specific
    (unsigned) `Adj Req Qty` rule (`Req. Qty. / 2` when `Requirements Type`
    is "BB", else `Req. Qty.` unchanged -- no sign lookup, unlike REC),
    normalizes keys, and sorts.

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

    is_bb = df["Requirements Type"].astype("string").str.strip().str.lower() == "bb"
    df["Adj Req Qty"] = df["Req. Qty."].where(~is_bb, df["Req. Qty."] / 2)

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


def pivot_mrp_elements_doh(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot MRP_ELEMENTS_DOH to one row per `plant_material_key` with a
    column per requirement type, summed across weeks.

    Mirrors stg_mm_mrp_elements_doh_pivot.pq: drops zero/null adjusted
    requirement rows, fills a blank `Requirements Type` with "UNSPEC",
    groups and pivots, then forces all of `EXPECTED_PIVOT_COLUMNS` to exist
    (defaulting to 0) -- per docs/nin_data_contracts.md Open Decision #3,
    this Python port forces all 7 expected columns (including `VG`), not
    just the 6 the current production safety net covers.
    """
    df = clean_df[["Material No.", "Plant", "Requirements Type", "Adj Req Qty"]].copy()
    df = df[df["Adj Req Qty"].notna() & (df["Adj Req Qty"] != 0)]

    df["Plant"] = normalize_plant(df["Plant"])
    df["Material No."] = normalize_material(df["Material No."])
    df["Requirements Type"] = normalize_plant(df["Requirements Type"])
    req_type = df["Requirements Type"].astype("string")
    df["Requirements Type"] = req_type.where(
        req_type.str.strip().fillna("") != "", "UNSPEC"
    )

    grouped = (
        df.groupby(["Material No.", "Plant", "Requirements Type"], as_index=False)[
            "Adj Req Qty"
        ]
        .sum()
        .rename(columns={"Adj Req Qty": "Req_Qty"})
    )

    pivoted = grouped.pivot_table(
        index=["Material No.", "Plant"],
        columns="Requirements Type",
        values="Req_Qty",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    pivoted.columns.name = None

    for col in EXPECTED_PIVOT_COLUMNS:
        if col not in pivoted.columns:
            pivoted[col] = 0

    pivoted["plant_material_key"] = pivoted["Plant"] + "-" + pivoted["Material No."]

    non_key = [
        c
        for c in pivoted.columns
        if c not in ("plant_material_key", "Material No.", "Plant")
    ]
    pivoted[non_key] = pivoted[non_key].fillna(0)

    ordered = ["plant_material_key", "Material No.", "Plant"] + EXPECTED_PIVOT_COLUMNS
    extra_cols = [c for c in non_key if c not in EXPECTED_PIVOT_COLUMNS]
    result = pivoted[ordered + extra_cols].sort_values(
        "plant_material_key", kind="stable"
    )
    return result.reset_index(drop=True)
