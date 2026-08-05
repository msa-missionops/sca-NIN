"""Tests for the MRP_ELEMENTS_DOH source transformation (Phase 1D)."""

import pandas as pd

from nin_pipeline.sources.mrp_elements_doh import (
    EXPECTED_PIVOT_COLUMNS,
    clean_mrp_elements_doh,
    locate_latest_doh_file,
    pivot_mrp_elements_doh,
)

HEADER = [
    "Plnt",
    "Material",
    "El",
    "Customer Request Date",
    "Rec./reqd.qty",
    "BUn",
]


def write_doh_export(path, data_rows, banner_rows=2, blank_rows=1):
    lines = [f"Banner text {i}" for i in range(banner_rows)]
    lines.extend("" for _ in range(blank_rows))
    lines.append("\t".join(HEADER))
    for row in data_rows:
        lines.append("\t".join(row.get(col, "") for col in HEADER))
    path.write_text("\n".join(lines), encoding="cp1252")


def test_locate_latest_doh_file_picks_latest_run_and_plant_file(tmp_path):
    old_run = tmp_path / "20260101_run"
    new_run = tmp_path / "20260201_run"
    old_run.mkdir()
    new_run.mkdir()

    write_doh_export(old_run / "MM_MRP_ELEMENTS_DOH_20260101_US01_x.txt", [])
    write_doh_export(new_run / "MM_MRP_ELEMENTS_DOH_20260201_US01_x.txt", [])
    write_doh_export(new_run / "MM_MRP_ELEMENTS_DOH_20260201_US02_x.txt", [])

    import os
    import time

    os.utime(old_run, (time.time() - 1000, time.time() - 1000))

    file_path, run_folder_name = locate_latest_doh_file(tmp_path, plant="US01")

    assert file_path.parent == new_run
    assert run_folder_name == "20260201_run"
    assert "US01" in file_path.name


def test_clean_mrp_elements_doh_applies_bb_halving_rule_unsigned(tmp_path):
    path = tmp_path / "MM_MRP_ELEMENTS_DOH_20260201_US01.txt"
    write_doh_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "BB",
                "Customer Request Date": "2026-03-06",
                "Rec./reqd.qty": "10",
                "BUn": "EA",
            },
            {
                "Plnt": "US01",
                "Material": "000456",
                "El": "VJ",
                "Customer Request Date": "2026-03-06",
                "Rec./reqd.qty": "10",
                "BUn": "EA",
            },
        ],
    )
    as_of = pd.Timestamp("2026-02-01")
    result = clean_mrp_elements_doh(
        path, run_folder_name="20260201_run", active_plant="US01", as_of_date=as_of
    )

    bb_row = result.loc[result["Material No."] == "123"].iloc[0]
    vj_row = result.loc[result["Material No."] == "456"].iloc[0]
    assert bb_row["Adj Req Qty"] == 5  # halved, and never negative
    assert vj_row["Adj Req Qty"] == 10  # unchanged


def test_clean_mrp_elements_doh_fills_null_date_and_filters_past(tmp_path):
    path = tmp_path / "MM_MRP_ELEMENTS_DOH_20260201_US01.txt"
    write_doh_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "VJ",
                "Customer Request Date": "",
                "Rec./reqd.qty": "10",
                "BUn": "EA",
            },
            {
                "Plnt": "US01",
                "Material": "000789",
                "El": "VJ",
                "Customer Request Date": "2026-01-01",
                "Rec./reqd.qty": "3",
                "BUn": "EA",
            },
        ],
    )
    as_of = pd.Timestamp("2026-02-01")
    result = clean_mrp_elements_doh(
        path, run_folder_name="20260201_run", active_plant="US01", as_of_date=as_of
    )

    assert len(result) == 1
    assert result.iloc[0]["Requirements Date"] == as_of


def test_pivot_mrp_elements_doh_forces_all_seven_expected_columns(tmp_path):
    path = tmp_path / "MM_MRP_ELEMENTS_DOH_20260201_US01.txt"
    write_doh_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "VJ",
                "Customer Request Date": "2026-03-06",
                "Rec./reqd.qty": "10",
                "BUn": "EA",
            },
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "PP",
                "Customer Request Date": "2026-03-13",
                "Rec./reqd.qty": "5",
                "BUn": "EA",
            },
        ],
    )
    as_of = pd.Timestamp("2026-02-01")
    clean_df = clean_mrp_elements_doh(
        path, run_folder_name="20260201_run", active_plant="US01", as_of_date=as_of
    )
    result = pivot_mrp_elements_doh(clean_df)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["plant_material_key"] == "US01-123"
    for col in EXPECTED_PIVOT_COLUMNS:
        assert col in result.columns
    assert row["VJ"] == 10
    assert row["PP"] == 5
    # VG never appeared in the source data but must still default to 0.
    assert row["VG"] == 0
    assert row["WB"] == 0


def test_pivot_mrp_elements_doh_drops_zero_and_null_adj_req_qty(tmp_path):
    path = tmp_path / "MM_MRP_ELEMENTS_DOH_20260201_US01.txt"
    write_doh_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "VJ",
                "Customer Request Date": "2026-03-06",
                "Rec./reqd.qty": "0",
                "BUn": "EA",
            },
        ],
    )
    as_of = pd.Timestamp("2026-02-01")
    clean_df = clean_mrp_elements_doh(
        path, run_folder_name="20260201_run", active_plant="US01", as_of_date=as_of
    )
    result = pivot_mrp_elements_doh(clean_df)

    assert len(result) == 0
