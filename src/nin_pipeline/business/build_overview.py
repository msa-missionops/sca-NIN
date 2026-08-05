"""Final base-table assembly (Phase 1E).

Reproduces `build_overview_p1_enriched.pq` / `build_overview_p1_review.pq`
and `build_overview_p2_enriched.pq` / `build_overview_p2_review.pq`
(``docs/powerquery_m/build overview/``), per the confirmed dependency
graph in ``docs/NIN_Python_Plan.md`` section 7.6 and the final schema in
``docs/nin_data_contracts.md`` section 7.

PRDPL3 (already shaped by ``nin_pipeline.sources.prdpl3.enrich_prdpl3``) is
the anchor grain, one row per ``plant_material_key``. MRP_ELEMENTS_DOH's
pivoted output, MB5T's aggregated in-transit quantity, and BOBL's
aggregated backorder/backlog measures are then left-joined onto it.
MRP_ELEMENTS_REC is intentionally **not** joined here -- per
``docs/nin_data_contracts.md`` Open Decision #1, it is out of scope for
the final base table in the current production query and in this port.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Column order for `build_overview_p1_review`, per the
# `#"Removed Other Columns"` step of build_overview_p1_enriched.pq.
OVERVIEW_P1_COLUMN_ORDER = (
    "plant_material_key",
    "Region",
    "Plant",
    "Major PG",
    "Product hierarchy",
    "Material",
    "Material Description",
    "Source Plant",
    "Safety Stock",
    "BUn",
    "top_60_flag",
    "ABC",
    "Spec Proc",
    "ProcType",
    "TRLT",
    "Tot Valuated Stk",
    "Total Value",
    "Basic material",
    "MRP Typ",
    "MRP Controller",
    "DelFlag",
    "SG",
    "MTyp",
    "IPT",
    "PDT",
    "GRT",
    "Planning time fence",
    "LotSize",
    "Reorder Point",
    "Threshold Qty",
    "AvaiChk",
    "Standard price",
    "Price Un",
)

DOH_DEMAND_COLUMNS = ("WB", "PP", "U2", "VC", "VJ", "VG", "U1")

# Final column order for `nin_base_table` / `build_overview_p2_review`,
# per docs/nin_data_contracts.md section 7.
BASE_TABLE_COLUMN_ORDER = (
    "plant_material_key",
    "Region",
    "Plant",
    "Major PG",
    "Product hierarchy",
    "Material",
    "Material Description",
    "Source Plant",
    "Safety Stock",
    "BUn",
    "top_60_flag",
    "ABC",
    "Spec Proc",
    "ProcType",
    "TRLT",
    "Total Stock Quantity",
    "Stocked Status",
    "Total Value Stock on Hand",
    "Basic material",
    "MRP Typ",
    "MRP Controller",
    "DelFlag",
    "SG",
    "MTyp",
    "IPT",
    "PDT",
    "GRT",
    "Planning time fence",
    "LotSize",
    "Reorder Point",
    "Threshold Qty",
    "AvaiChk",
    "Standard price",
    "Price Un",
    "WB",
    "VJ",
    "VC",
    "VG",
    "PP",
    "U1",
    "U2",
    "Quantity in Transit",
    "Available Stock",
    "Average Monthly Forecast Demand",
    "DOH",
    "Backorder Actual",
    "Backorder Qnty",
    "Backlog Actual",
    "Backlog Qnty",
)


def assemble_overview_p1(prdpl3_enriched: pd.DataFrame) -> pd.DataFrame:
    """Shape enriched PRDPL3 into `build_overview_p1_review`.

    Mirrors build_overview_p1_enriched.pq: derives `Major PG` as
    characters 3-4 of `Product hierarchy` (`Text.Middle(_, 3, 2)`), renames
    `source_plant` to `Source Plant`, and selects/orders the P1 column set.
    """
    df = prdpl3_enriched.copy()
    df["Major PG"] = df["Product hierarchy"].astype("string").str.slice(3, 5)
    df = df.rename(columns={"source_plant": "Source Plant"})

    ordered = [c for c in OVERVIEW_P1_COLUMN_ORDER if c in df.columns]
    return df[ordered].reset_index(drop=True)


def assemble_nin_base_table(
    overview_p1: pd.DataFrame,
    doh_pivot: pd.DataFrame,
    mb5t_enriched: pd.DataFrame,
    bobl_enriched: pd.DataFrame,
) -> pd.DataFrame:
    """Assemble `nin_base_table` (`build_overview_p2_review`).

    Mirrors build_overview_p2_enriched.pq:

    1. Drop deleted materials (`DelFlag != ""`).
    2. Left-join the DOH pivot on `plant_material_key`; missing/blank
       demand columns default to 0 (`ToNumberOrZero`) and every value is
       made absolute (`Number.Abs`).
    3. Left-join MB5T's aggregated `Quantity in Transit` (stays null if
       unmatched -- no default-to-zero in the source for this column).
    4. Compute `Available Stock = max(0, Total Stock Quantity - (VJ+VC+VG+U1))`.
       Note `WB`, `PP`, `U2`, and `Quantity in Transit` are **not**
       subtracted, matching confirmed current production behavior.
    5. `Stocked Status = "Yes" if Total Stock Quantity > 0 else "No"`.
    6. `Average Monthly Forecast Demand = (VJ + PP + U1) / 3`.
    7. `DOH = 0 if forecast == 0 else (Available Stock / forecast) * 30`
       (not rounded).
    8. Left-join BOBL's backorder/backlog measures (stay null if
       unmatched -- no default-to-zero in the source for these columns).
    """
    df = overview_p1.copy()
    df = df[df["DelFlag"].astype("string").fillna("") == ""].copy()

    df = df.merge(doh_pivot, on="plant_material_key", how="left", suffixes=("", "_doh"))
    for col in DOH_DEMAND_COLUMNS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).abs()

    df = df.merge(
        mb5t_enriched[["plant_material_key", "Quantity in Transit"]],
        on="plant_material_key",
        how="left",
    )

    total_stock = pd.to_numeric(df["Tot Valuated Stk"], errors="coerce").fillna(0)
    vj = df["VJ"]
    vc = df["VC"]
    vg = df["VG"]
    u1 = df["U1"]
    available_stock = total_stock - (vj + vc + vg + u1)
    df["Available Stock"] = available_stock.clip(lower=0)

    df = df.rename(
        columns={
            "Tot Valuated Stk": "Total Stock Quantity",
            "Total Value": "Total Value Stock on Hand",
        }
    )

    total_stock_qty = pd.to_numeric(df["Total Stock Quantity"], errors="coerce").fillna(
        0
    )
    df["Stocked Status"] = (total_stock_qty > 0).map({True: "Yes", False: "No"})

    pp = df["PP"]
    forecast_demand = (vj + pp + u1) / 3
    df["Average Monthly Forecast Demand"] = forecast_demand

    safe_forecast = forecast_demand.replace(0, np.nan)
    df["DOH"] = ((df["Available Stock"] / safe_forecast) * 30).fillna(0)

    df = df.merge(
        bobl_enriched,
        on="plant_material_key",
        how="left",
    )

    ordered = [c for c in BASE_TABLE_COLUMN_ORDER if c in df.columns]
    return df[ordered].reset_index(drop=True)
