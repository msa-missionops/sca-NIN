"""PRDPL3 source transformation (Phase 1D).

Reproduces stg_prdpl3_clean.pq and stg_prdpl3_enriched.pq / out_prdpl3_review.pq
(docs/powerquery_m/prdpl3/), per the confirmed flow in
docs/NIN_Python_Plan.md section 7.6 and the schema in
docs/nin_data_contracts.md section 1.

PRDPL3 is the anchor grain for the final base table: one row per
`plant_material_key`, filtered to the single active evaluation plant and to
`Product hierarchy` values starting with `"00020"`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nin_pipeline.sources.sap_text import (
    normalize_material,
    normalize_plant,
    parse_pipe_delimited_sap_export,
    reorder_columns_pq_style,
    to_number,
)

TOTAL_COLUMNS = 51
SKIP_BEFORE_HEADER = 6
SKIP_AFTER_HEADER = 1
PRODUCT_HIERARCHY_PREFIX = "00020"

NUMERIC_COLUMNS = (
    "Safety Stock",
    "Threshold Qty",
    "Reorder Point",
    "Tot Valuated Stk",
    "Total Value",
    "Standard price",
    "Price Un",
)

# Column order for the cleaned (pre-enrichment) output, per
# stg_prdpl3_clean.pq's `#"Reordered Columns"` step.
CLEAN_COLUMN_ORDER = (
    "plant_material_key",
    "Plant",
    "Material",
    "Material Description",
    "BUn",
    "Product hierarchy",
    "Basic material",
    "Basic material 2",
    "MRP Typ",
    "MRP Controller",
    "PuRGrp",
    "DelFlag",
    "MtlSt_XPlt",
    "MtlSt_Plt",
    "X-Chn Mtl St",
    "SG",
    "ProcType",
    "Spec Proc",
    "ABC",
    "MTyp",
    "IPT",
    "PDT",
    "GRT",
    "TRLT",
    "Planning time fence",
    "LotSize",
    "Min. Lot Sze",
    "Rounding val.",
    "Max. Lot Size",
    "Fix. lot size",
    "BUn_1",
    "Safety Stock",
    "Reorder Point",
    "Threshold Qty",
    "AvaiChk",
    "Consumption mode",
    "Bwd cons. per.",
    "Fwd cons.period",
    "BkFlush",
    "PSloc",
    "Language",
    "Tot Valuated Stk",
    "Total Value",
    "Standard price",
    "Price Un",
    "SLife",
    "Propos.SA",
    "ESLoc",
    "R. Profile",
    "ProdS",
)

# Column order for the enriched/review output, per
# docs/nin_data_contracts.md section 1. Applied via
# `reorder_columns_pq_style`, matching `Table.ReorderColumns(...,
# MissingField.Ignore)`: entries absent from a given extract are skipped
# (no error), and any extra column the extract *does* have that isn't
# listed here is appended at the end rather than dropped.
ENRICHED_COLUMN_ORDER = (
    "plant_material_key",
    "Plant",
    "Material",
    "Material Description",
    "Region",
    "top_60_flag",
    "source_plant",
    "BUn",
    "Product hierarchy",
    "Basic material",
    "Basic material 2",
    "MRP Typ",
    "MRP Controller",
    "PuRGrp",
    "DelFlag",
    "MtlSt_XPlt",
    "MtlSt_Plt",
    "X-Chn Mtl St",
    "SG",
    "ProcType",
    "Spec Proc",
    "ABC",
    "MTyp",
    "IPT",
    "PDT",
    "GRT",
    "TRLT",
    "Planning time fence",
    "LotSize",
    "Min. Lot Sze",
    "Rounding val.",
    "Max. Lot Size",
    "Fix. lot size",
    "BUn_1",
    "Safety Stock",
    "Reorder Point",
    "Threshold Qty",
    "AvaiChk",
    "Consumption mode",
    "Bwd cons. per.",
    "Fwd cons.period",
    "BkFlush",
    "PSloc",
    "Language",
    "Tot Valuated Stk",
    "Total Value",
    "Standard price",
    "Price Un",
    "SLife",
    "Propos.SA",
    "ESLoc",
    "R. Profile",
    "ProdS",
)


def clean_prdpl3(path: Path, active_plant: str) -> pd.DataFrame:
    """Parse and standardize a PRDPL3 export for the active plant.

    Mirrors stg_prdpl3_clean.pq: parses the fixed-width pipe export, types
    the numeric business fields, normalizes Plant/Material, filters to the
    active plant and to `Product hierarchy` starting with `"00020"`, and
    builds `plant_material_key`.
    """
    df = parse_pipe_delimited_sap_export(
        path,
        total_columns=TOTAL_COLUMNS,
        skip_before_header=SKIP_BEFORE_HEADER,
        skip_after_header=SKIP_AFTER_HEADER,
    )
    df = df.rename(columns={"Plnt": "Plant"})

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = to_number(df[column])

    df["Plant"] = normalize_plant(df["Plant"])
    df["Material"] = normalize_material(df["Material"])

    df = df[df["Plant"] == active_plant.strip().upper()]
    if "Product hierarchy" in df.columns:
        df = df[
            df["Product hierarchy"]
            .astype("string")
            .str.startswith(PRODUCT_HIERARCHY_PREFIX)
        ]

    df = df.copy()
    df["plant_material_key"] = df["Plant"] + "-" + df["Material"]

    df = reorder_columns_pq_style(df, list(CLEAN_COLUMN_ORDER))
    return df.reset_index(drop=True)


def enrich_prdpl3(
    clean_df: pd.DataFrame,
    region_tag: pd.DataFrame,
    top60_tag: pd.DataFrame,
    sourceplant_tag: pd.DataFrame,
) -> pd.DataFrame:
    """Join reference tags onto the cleaned PRDPL3 table.

    Mirrors stg_prdpl3_enriched.pq / out_prdpl3_review.pq:

    - Left-join `tbl_tag_region` on `Plant` -> `Region` (null if unmatched).
    - Left-join `tbl_tag_top60` on `plant_material_key` -> `top_60_flag`,
      default `"standard"` if unmatched.
    - Left-join `tbl_tag_sourceplant` on normalized `Spec Proc` ->
      `source_plant`, default `"None defined"` if unmatched.
    """
    df = clean_df.copy()

    region = region_tag[["Plant", "Region"]].copy()
    region["Plant"] = normalize_plant(region["Plant"])
    df = df.merge(region, on="Plant", how="left")

    top60 = top60_tag[["plant_material_key", "top_60_flag"]].copy()
    top60["plant_material_key"] = normalize_plant(top60["plant_material_key"])
    df = df.merge(top60, on="plant_material_key", how="left")
    df["top_60_flag"] = df["top_60_flag"].fillna("standard")

    sourceplant = sourceplant_tag[["source_key", "source_plant"]].copy()
    sourceplant["source_key"] = normalize_plant(sourceplant["source_key"])
    df["Spec Proc"] = normalize_plant(df["Spec Proc"])
    df = df.merge(sourceplant, left_on="Spec Proc", right_on="source_key", how="left")
    df["source_plant"] = df["source_plant"].fillna("None defined")
    df = df.drop(columns=["source_key"])

    return reorder_columns_pq_style(df, list(ENRICHED_COLUMN_ORDER))
