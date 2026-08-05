"""Tests for the MRP_ELEMENTS_REC source transformation (Phase 1D)."""

import pandas as pd

from nin_pipeline.sources.mrp_elements_rec import (
    WEEKLY_FORECAST_WEEK_COUNT,
    clean_mrp_elements_rec,
    enrich_mrp_elements_rec,
    locate_latest_rec_file,
    pivot_mrp_elements_rec_weekly,
)

HEADER = [
    "Plnt",
    "Material",
    "El",
    "Customer Request Date",
    "Rec./reqd.qty",
    "BUn",
]


def write_rec_export(path, data_rows, banner_rows=2, blank_rows=1):
    lines = [f"Banner text {i}" for i in range(banner_rows)]
    lines.extend("" for _ in range(blank_rows))
    lines.append("\t".join(HEADER))
    for row in data_rows:
        lines.append("\t".join(row.get(col, "") for col in HEADER))
    path.write_text("\n".join(lines), encoding="cp1252")


def test_locate_latest_rec_file_picks_latest_run_and_plant_file(tmp_path):
    old_run = tmp_path / "20260101_run"
    new_run = tmp_path / "20260201_run"
    old_run.mkdir()
    new_run.mkdir()

    write_rec_export(old_run / "MM_MRP_ELEMENTS_REC_20260101_US01_x.txt", [])
    write_rec_export(new_run / "MM_MRP_ELEMENTS_REC_20260201_US01_x.txt", [])
    write_rec_export(new_run / "MM_MRP_ELEMENTS_REC_20260201_US02_x.txt", [])

    # Writing files updates a directory's own mtime, so set the "old" run
    # folder's mtime back *after* all writes to make it reliably older.
    import os
    import time

    os.utime(old_run, (time.time() - 1000, time.time() - 1000))

    file_path, run_folder_name = locate_latest_rec_file(tmp_path, plant="US01")

    assert file_path.parent == new_run
    assert run_folder_name == "20260201_run"
    assert "US01" in file_path.name


def test_clean_mrp_elements_rec_filters_past_dates_and_fills_null_dates(tmp_path):
    path = tmp_path / "MM_MRP_ELEMENTS_REC_20260201_US01.txt"
    write_rec_export(
        path,
        [
            {
                "Plnt": "us01",
                "Material": "000123",
                "El": "bb",
                "Customer Request Date": "2026-03-01",
                "Rec./reqd.qty": "10",
                "BUn": "ea",
            },
            {
                "Plnt": "US01",
                "Material": "000456",
                "El": "vj",
                "Customer Request Date": "",  # null -> filled with as-of date
                "Rec./reqd.qty": "5",
                "BUn": "EA",
            },
            {
                "Plnt": "US01",
                "Material": "000789",
                "El": "vj",
                "Customer Request Date": "2026-01-01",  # before as-of -> dropped
                "Rec./reqd.qty": "3",
                "BUn": "EA",
            },
        ],
    )
    as_of = pd.Timestamp("2026-02-01")

    result = clean_mrp_elements_rec(
        path, run_folder_name="20260201_run", active_plant="US01", as_of_date=as_of
    )

    assert len(result) == 2
    assert set(result["Material No."]) == {"123", "456"}
    filled_row = result.loc[result["Material No."] == "456"].iloc[0]
    assert filled_row["Requirements Date"] == as_of


def test_enrich_mrp_elements_rec_applies_sign_then_absolute_value(tmp_path):
    path = tmp_path / "MM_MRP_ELEMENTS_REC_20260201_US01.txt"
    write_rec_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "VJ",
                "Customer Request Date": "2026-03-06",  # Friday
                "Rec./reqd.qty": "10",
                "BUn": "EA",
            },
            {
                "Plnt": "US01",
                "Material": "000456",
                "El": "PP",
                "Customer Request Date": "2026-03-06",
                "Rec./reqd.qty": "0",  # zero -> dropped in enrich
                "BUn": "EA",
            },
        ],
    )
    as_of = pd.Timestamp("2026-02-01")
    clean_df = clean_mrp_elements_rec(
        path, run_folder_name="20260201_run", active_plant="US01", as_of_date=as_of
    )

    rec_req_type = pd.DataFrame({"type": ["VJ", "PP"], "negative": [True, False]})
    result = enrich_mrp_elements_rec(clean_df, rec_req_type)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["plant_material_key"] == "US01-123"
    # Signed value reflects the (negative) sign lookup...
    assert row["Signed Adj Req Qty"] == -10
    # ...but the exposed "Adj Req Qty" matches production: always absolute.
    assert row["Adj Req Qty"] == 10


def test_enrich_mrp_elements_rec_defaults_to_not_negative_when_unmatched(tmp_path):
    path = tmp_path / "MM_MRP_ELEMENTS_REC_20260201_US01.txt"
    write_rec_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "El": "ZZ",  # not present in rec_req_type
                "Customer Request Date": "2026-03-06",
                "Rec./reqd.qty": "10",
                "BUn": "EA",
            },
        ],
    )
    as_of = pd.Timestamp("2026-02-01")
    clean_df = clean_mrp_elements_rec(
        path, run_folder_name="20260201_run", active_plant="US01", as_of_date=as_of
    )

    rec_req_type = pd.DataFrame({"type": ["VJ"], "negative": [True]})
    result = enrich_mrp_elements_rec(clean_df, rec_req_type)

    row = result.iloc[0]
    assert row["Signed Adj Req Qty"] == 10  # default not-negative -> positive
    assert row["Adj Req Qty"] == 10


def test_pivot_mrp_elements_rec_weekly_transposes_by_earliest_distinct_dates():
    """Mirrors the real Excel workbook's SUMIFS matrix (no .pq equivalent,
    confirmed by SME): "week 1" is the earliest distinct Week Ending date
    across the whole REC output, "week 2" the next, and so on; each cell
    sums Adj Req Qty for that key/week, and Total Forecast (Qty) sums only
    the forced week columns."""
    enriched = pd.DataFrame(
        {
            "plant_material_key": ["US01-123", "US01-123", "US01-456"],
            "Week Ending": [
                pd.Timestamp("2026-03-06"),  # earliest -> week 1
                pd.Timestamp("2026-03-13"),  # next -> week 2
                pd.Timestamp("2026-03-06"),  # same date as week 1
            ],
            "Adj Req Qty": [10.0, 5.0, 3.0],
        }
    )

    result = pivot_mrp_elements_rec_weekly(enriched, week_count=3)

    assert list(result.columns) == [
        "plant_material_key",
        "Total Forecast (Qty)",
        "week 1",
        "week 2",
        "week 3",
    ]
    row_123 = result.loc[result["plant_material_key"] == "US01-123"].iloc[0]
    assert row_123["week 1"] == 10.0
    assert row_123["week 2"] == 5.0
    assert row_123["week 3"] == 0
    assert row_123["Total Forecast (Qty)"] == 15.0

    row_456 = result.loc[result["plant_material_key"] == "US01-456"].iloc[0]
    assert row_456["week 1"] == 3.0
    assert row_456["week 2"] == 0
    assert row_456["Total Forecast (Qty)"] == 3.0


def test_pivot_mrp_elements_rec_weekly_ignores_dates_beyond_week_count():
    """Any REC demand in weeks past `week_count` is excluded entirely from
    Total Forecast (Qty), matching the real workbook's fixed-width matrix."""
    enriched = pd.DataFrame(
        {
            "plant_material_key": ["US01-123", "US01-123"],
            "Week Ending": [pd.Timestamp("2026-03-06"), pd.Timestamp("2026-03-13")],
            "Adj Req Qty": [10.0, 999.0],
        }
    )

    result = pivot_mrp_elements_rec_weekly(enriched, week_count=1)

    assert list(result.columns) == [
        "plant_material_key",
        "Total Forecast (Qty)",
        "week 1",
    ]
    row = result.iloc[0]
    assert row["week 1"] == 10.0
    assert row["Total Forecast (Qty)"] == 10.0  # 999.0 in week 2 excluded


def test_pivot_mrp_elements_rec_weekly_forces_all_columns_when_empty():
    empty = pd.DataFrame(columns=["plant_material_key", "Week Ending", "Adj Req Qty"])
    result = pivot_mrp_elements_rec_weekly(empty)

    assert len(result) == 0
    expected_columns = ["plant_material_key", "Total Forecast (Qty)"] + [
        f"week {i}" for i in range(1, WEEKLY_FORECAST_WEEK_COUNT + 1)
    ]
    assert list(result.columns) == expected_columns
