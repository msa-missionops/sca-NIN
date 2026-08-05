"""Tests for nin_pipeline.validation.reconciliation (Phase 1G)."""

from __future__ import annotations

import pandas as pd

from nin_pipeline.validation.reconciliation import (
    compare_base_tables,
    write_reconciliation_workbook,
)


def _python_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "plant_material_key": ["USD1-1", "USD1-2", "USD1-3", "USD1-5"],
            "Plant": ["USD1", "USD1", "USD1", "USD1"],
            "Material Description": ["Widget A", "Widget B", "Widget C", "Widget E"],
            "Available Stock": [10.0, 20.0, 30.0, 5.0],
            "DOH": [1.0, 2.0, 3.0, 4.0],
        }
    )


def _current_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "plant_material_key": ["USD1-1", "USD1-2", "USD1-3", "USD1-4"],
            "Plant": ["USD1", "USD1", "USD1", "USD1"],
            # USD1-2's description differs from the Python output.
            "Material Description": [
                "Widget A",
                "Widget B (old)",
                "Widget C",
                "Widget D",
            ],
            # USD1-3's Available Stock differs beyond tolerance.
            "Available Stock": [10.0, 20.0, 999.0, 40.0],
            "DOH": [1.0, 2.0, 3.0, 4.0],
        }
    )


def test_missing_keys_detected_both_directions():
    result = compare_base_tables(_python_df(), _current_df())
    assert result.missing_in_python["plant_material_key"].tolist() == ["USD1-4"]
    assert result.missing_in_current["plant_material_key"].tolist() == ["USD1-5"]


def test_duplicate_keys_detected():
    python_df = pd.concat([_python_df(), _python_df().iloc[[0]]], ignore_index=True)
    result = compare_base_tables(python_df, _current_df())
    assert "USD1-1" in result.duplicate_keys_python["plant_material_key"].to_list()


def test_changed_descriptive_field_detected():
    result = compare_base_tables(_python_df(), _current_df())
    changed = result.changed_descriptive_fields
    assert (changed["plant_material_key"] == "USD1-2").any()
    row = changed[changed["plant_material_key"] == "USD1-2"].iloc[0]
    assert row["python_value"] == "Widget B"
    assert row["current_value"] == "Widget B (old)"


def test_value_difference_beyond_tolerance_detected():
    result = compare_base_tables(_python_df(), _current_df())
    diffs = result.value_differences
    row = diffs[
        (diffs["plant_material_key"] == "USD1-3")
        & (diffs["field"] == "Available Stock")
    ].iloc[0]
    assert row["python_value"] == 30.0
    assert row["current_value"] == 999.0
    assert row["difference"] == 30.0 - 999.0
    # DOH matches exactly for all common keys, so it must not appear.
    assert not (diffs["field"] == "DOH").any()


def test_result_is_clean_when_frames_match():
    df = _python_df()
    result = compare_base_tables(df, df.copy())
    assert result.is_clean


def test_write_reconciliation_workbook(tmp_path):
    result = compare_base_tables(_python_df(), _current_df())
    output_path = tmp_path / "nin_reconciliation.xlsx"
    written = write_reconciliation_workbook(result, output_path)
    assert written == output_path
    assert output_path.exists()

    sheets = pd.read_excel(output_path, sheet_name=None)
    assert "Summary" in sheets
    assert "Missing in Python" in sheets
    assert "Missing in Current" in sheets
    assert "Value Differences" in sheets
    assert "Duplicate Keys" in sheets
    assert "Validation Results" in sheets
