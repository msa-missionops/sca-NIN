"""Tests for the final base-table assembly (Phase 1E)."""

import pandas as pd

from nin_pipeline.business.build_overview import (
    assemble_nin_base_table,
    assemble_overview_p1,
)


def make_prdpl3_enriched():
    return pd.DataFrame(
        [
            {
                "plant_material_key": "US01-123",
                "Plant": "US01",
                "Material": "123",
                "Material Description": "Widget",
                "Region": "NA",
                "top_60_flag": "top_60",
                "source_plant": "US01",
                "BUn": "EA",
                "Product hierarchy": "00020010200",
                "Basic material": "STEEL",
                "MRP Typ": "PD",
                "MRP Controller": "001",
                "DelFlag": "",
                "SG": "1",
                "ProcType": "E",
                "Spec Proc": "",
                "ABC": "A",
                "MTyp": "FERT",
                "IPT": "1",
                "PDT": "2",
                "GRT": "3",
                "TRLT": "5",
                "Planning time fence": 10,
                "LotSize": "EX",
                "Safety Stock": 100,
                "Reorder Point": 50,
                "Threshold Qty": 10,
                "AvaiChk": "02",
                "Tot Valuated Stk": 200,
                "Total Value": 5000,
                "Standard price": 25,
                "Price Un": 1,
            },
            {
                "plant_material_key": "US01-999",
                "Plant": "US01",
                "Material": "999",
                "Material Description": "Deleted Widget",
                "Region": "NA",
                "top_60_flag": "standard",
                "source_plant": "US01",
                "BUn": "EA",
                "Product hierarchy": "00020030400",
                "Basic material": "STEEL",
                "MRP Typ": "PD",
                "MRP Controller": "001",
                "DelFlag": "X",  # deleted -> dropped
                "SG": "1",
                "ProcType": "E",
                "Spec Proc": "",
                "ABC": "B",
                "MTyp": "FERT",
                "IPT": "1",
                "PDT": "2",
                "GRT": "3",
                "TRLT": "5",
                "Planning time fence": 10,
                "LotSize": "EX",
                "Safety Stock": 10,
                "Reorder Point": 5,
                "Threshold Qty": 1,
                "AvaiChk": "02",
                "Tot Valuated Stk": 0,
                "Total Value": 0,
                "Standard price": 1,
                "Price Un": 1,
            },
        ]
    )


def test_assemble_overview_p1_derives_major_pg_and_renames_source_plant():
    result = assemble_overview_p1(make_prdpl3_enriched())

    assert "Source Plant" in result.columns
    assert "source_plant" not in result.columns
    row = result.loc[result["plant_material_key"] == "US01-123"].iloc[0]
    # Product hierarchy "00020010200" -> Text.Middle(_, 3, 2) -> chars at
    # 0-based index 3,4 -> "20".
    assert row["Major PG"] == "20"


def test_assemble_nin_base_table_drops_deleted_materials_and_computes_calcs():
    overview_p1 = assemble_overview_p1(make_prdpl3_enriched())

    doh_pivot = pd.DataFrame(
        [
            {
                "plant_material_key": "US01-123",
                "Material No.": "123",
                "Plant": "US01",
                "WB": 0,
                "VJ": -30,  # negative -> must be made absolute
                "VC": 10,
                "VG": 0,
                "PP": 15,
                "U1": 5,
                "U2": 0,
            }
        ]
    )
    mb5t_enriched = pd.DataFrame(
        [{"plant_material_key": "US01-123", "Quantity in Transit": 7}]
    )
    bobl_enriched = pd.DataFrame(
        [
            {
                "plant_material_key": "US01-123",
                "Backorder Actual": 1,
                "Backorder Qnty": 2,
                "Backlog Actual": 3,
                "Backlog Qnty": 4,
            }
        ]
    )

    result = assemble_nin_base_table(
        overview_p1, doh_pivot, mb5t_enriched, bobl_enriched
    )

    # Deleted material dropped.
    assert len(result) == 1
    row = result.iloc[0]

    assert row["VJ"] == 30  # abs() applied
    assert row["Quantity in Transit"] == 7

    # Available Stock = max(0, 200 - (30 + 10 + 0 + 5)) = 155
    assert row["Available Stock"] == 155
    assert row["Stocked Status"] == "Yes"

    # Average Monthly Forecast Demand = (30 + 15 + 5) / 3 = 16.666...
    assert row["Average Monthly Forecast Demand"] == (30 + 15 + 5) / 3

    # DOH = (155 / 16.666...) * 30
    expected_doh = (155 / ((30 + 15 + 5) / 3)) * 30
    assert abs(row["DOH"] - expected_doh) < 1e-9

    assert row["Backorder Actual"] == 1
    assert row["Backlog Qnty"] == 4
    assert row["Total Stock Quantity"] == 200
    assert row["Total Value Stock on Hand"] == 5000


def test_assemble_nin_base_table_zero_forecast_demand_gives_zero_doh():
    overview_p1 = assemble_overview_p1(make_prdpl3_enriched())
    doh_pivot = pd.DataFrame(
        [
            {
                "plant_material_key": "US01-123",
                "Material No.": "123",
                "Plant": "US01",
                "WB": 0,
                "VJ": 0,
                "VC": 0,
                "VG": 0,
                "PP": 0,
                "U1": 0,
                "U2": 0,
            }
        ]
    )
    mb5t_enriched = pd.DataFrame(
        [{"plant_material_key": "US01-123", "Quantity in Transit": 0}]
    )
    bobl_enriched = pd.DataFrame(
        columns=[
            "plant_material_key",
            "Backorder Actual",
            "Backorder Qnty",
            "Backlog Actual",
            "Backlog Qnty",
        ]
    )

    result = assemble_nin_base_table(
        overview_p1, doh_pivot, mb5t_enriched, bobl_enriched
    )
    row = result.iloc[0]
    assert row["Average Monthly Forecast Demand"] == 0
    assert row["DOH"] == 0


def test_assemble_nin_base_table_missing_doh_row_defaults_demand_to_zero():
    overview_p1 = assemble_overview_p1(make_prdpl3_enriched())
    # No DOH row at all for this plant_material_key.
    doh_pivot = pd.DataFrame(
        columns=[
            "plant_material_key",
            "Material No.",
            "Plant",
            "WB",
            "VJ",
            "VC",
            "VG",
            "PP",
            "U1",
            "U2",
        ]
    )
    mb5t_enriched = pd.DataFrame(columns=["plant_material_key", "Quantity in Transit"])
    bobl_enriched = pd.DataFrame(
        columns=[
            "plant_material_key",
            "Backorder Actual",
            "Backorder Qnty",
            "Backlog Actual",
            "Backlog Qnty",
        ]
    )

    result = assemble_nin_base_table(
        overview_p1, doh_pivot, mb5t_enriched, bobl_enriched
    )
    row = result.iloc[0]
    for col in ("WB", "VJ", "VC", "VG", "PP", "U1", "U2"):
        assert row[col] == 0
    # Available Stock = max(0, 200 - 0) = 200
    assert row["Available Stock"] == 200
    assert row["DOH"] == 0


def test_assemble_nin_base_table_joins_rec_weekly_forecast_and_defaults_missing_to_zero():
    """rec_weekly (Total Forecast (Qty)/week 1..week N, from
    pivot_mrp_elements_rec_weekly) is optional and, when given, is
    left-joined with unmatched keys defaulting to 0 -- matching the real
    Excel workbook's SUMIFS matrix."""
    overview_p1 = assemble_overview_p1(make_prdpl3_enriched())
    doh_pivot = pd.DataFrame(
        columns=[
            "plant_material_key",
            "Material No.",
            "Plant",
            "WB",
            "VJ",
            "VC",
            "VG",
            "PP",
            "U1",
            "U2",
        ]
    )
    mb5t_enriched = pd.DataFrame(columns=["plant_material_key", "Quantity in Transit"])
    bobl_enriched = pd.DataFrame(
        columns=[
            "plant_material_key",
            "Backorder Actual",
            "Backorder Qnty",
            "Backlog Actual",
            "Backlog Qnty",
        ]
    )
    # Only "US01-123" (the surviving, non-deleted row) has REC forecast data.
    rec_weekly = pd.DataFrame(
        [
            {
                "plant_material_key": "US01-123",
                "Total Forecast (Qty)": 15.0,
                "week 1": 10.0,
                "week 2": 5.0,
            }
        ]
    )

    result = assemble_nin_base_table(
        overview_p1, doh_pivot, mb5t_enriched, bobl_enriched, rec_weekly=rec_weekly
    )
    row = result.iloc[0]
    assert row["Total Forecast (Qty)"] == 15.0
    assert row["week 1"] == 10.0
    assert row["week 2"] == 5.0


def test_assemble_nin_base_table_without_rec_weekly_omits_weekly_columns():
    """rec_weekly defaults to None, keeping full backward compatibility for
    callers that don't yet supply REC data."""
    overview_p1 = assemble_overview_p1(make_prdpl3_enriched())
    doh_pivot = pd.DataFrame(
        columns=[
            "plant_material_key",
            "Material No.",
            "Plant",
            "WB",
            "VJ",
            "VC",
            "VG",
            "PP",
            "U1",
            "U2",
        ]
    )
    mb5t_enriched = pd.DataFrame(columns=["plant_material_key", "Quantity in Transit"])
    bobl_enriched = pd.DataFrame(
        columns=[
            "plant_material_key",
            "Backorder Actual",
            "Backorder Qnty",
            "Backlog Actual",
            "Backlog Qnty",
        ]
    )

    result = assemble_nin_base_table(
        overview_p1, doh_pivot, mb5t_enriched, bobl_enriched
    )
    assert "Total Forecast (Qty)" not in result.columns
    assert "week 1" not in result.columns
