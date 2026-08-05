"""Tests for the BOBL source transformation (Phase 1D)."""

import pandas as pd

from nin_pipeline.sources.bobl import (
    MATERIAL_COL,
    PLANT_COL,
    clean_bobl,
    enrich_bobl,
)


def make_raw(rows):
    return pd.DataFrame(rows)


def test_clean_bobl_coerces_numeric_columns_tolerating_blanks():
    raw = make_raw(
        [
            {
                PLANT_COL: "US01",
                MATERIAL_COL: "123",
                "[SumBackorder_Actual]": "1,000",
                "[SumBackorder_Quantity]": "",
                "[SumBacklog_Quantity]": "5",
                "[SumBacklog_Actual]": "2.5",
            }
        ]
    )
    result = clean_bobl(raw)

    assert result["[SumBackorder_Actual]"].iloc[0] == 1000
    assert pd.isna(result["[SumBackorder_Quantity]"].iloc[0])
    assert result["[SumBacklog_Actual]"].iloc[0] == 2.5


def test_enrich_bobl_builds_upper_cased_key_and_sums_duplicates():
    raw = make_raw(
        [
            {
                PLANT_COL: " us01 ",
                MATERIAL_COL: " 123 ",
                "[SumBackorder_Actual]": 10,
                "[SumBackorder_Quantity]": 1,
                "[SumBacklog_Quantity]": 2,
                "[SumBacklog_Actual]": 20,
            },
            {
                PLANT_COL: "US01",
                MATERIAL_COL: "123",
                "[SumBackorder_Actual]": 5,
                "[SumBackorder_Quantity]": None,  # non-numeric -> treated as 0
                "[SumBacklog_Quantity]": 3,
                "[SumBacklog_Actual]": 0,
            },
            {
                PLANT_COL: "US02",
                MATERIAL_COL: "999",
                "[SumBackorder_Actual]": 1,
                "[SumBackorder_Quantity]": 1,
                "[SumBacklog_Quantity]": 1,
                "[SumBacklog_Actual]": 1,
            },
        ]
    )
    clean_df = clean_bobl(raw)
    result = enrich_bobl(clean_df)

    assert list(result.columns) == [
        "plant_material_key",
        "Backorder Actual",
        "Backorder Qnty",
        "Backlog Actual",
        "Backlog Qnty",
    ]
    assert len(result) == 2

    row = result.loc[result["plant_material_key"] == "US01-123"].iloc[0]
    assert row["Backorder Actual"] == 15
    assert row["Backorder Qnty"] == 1  # 1 + 0 (None coerced to 0)
    assert row["Backlog Qnty"] == 5
    assert row["Backlog Actual"] == 20
