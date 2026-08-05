"""Tests for shared SAP text parsing helpers (sap_text.py)."""

import pandas as pd

from nin_pipeline.sources.sap_text import (
    normalize_material,
    normalize_plant,
    parse_pipe_delimited_sap_export,
    reorder_columns_pq_style,
    to_number,
)


def test_parse_pipe_delimited_sap_export_skips_banner_and_promotes_header(
    tmp_path,
):
    path = tmp_path / "export.txt"
    lines = [
        "banner 1",
        "banner 2",
        "|Plnt|Material|Amount|",
        "|blank units row||",
        "|US01|123|10.5|",
        "|US02|456|20|",
    ]
    path.write_text("\n".join(lines), encoding="cp1252")

    df = parse_pipe_delimited_sap_export(
        path, total_columns=5, skip_before_header=2, skip_after_header=1
    )

    assert list(df.columns) == ["Plnt", "Material", "Amount"]
    assert df.iloc[0]["Plnt"] == "US01"
    assert df.iloc[1]["Material"] == "456"


def test_parse_pipe_delimited_sap_export_renumbers_duplicate_headers(tmp_path):
    """Mirrors Power Query's Table.PromoteHeaders behavior confirmed against
    real captured exports: the first occurrence of a duplicated name is
    left unchanged, and every subsequent duplicate anywhere in the row
    (regardless of which name it duplicates) is suffixed with a single
    table-wide running counter -- e.g. stg_mb5t_clean.pq's raw header has
    "Quantity" and "Crcy" each appear twice, and expects them typed as
    "Quantity"/"Quantity_1" and "Crcy"/"Crcy_2" (not "Crcy_1")."""
    path = tmp_path / "export.txt"
    lines = [
        "banner 1",
        "|BUn|Quantity|Crcy|Quantity|Net Value|Crcy|",
        "|EA|10|USD|20|5.00|MXN|",
    ]
    path.write_text("\n".join(lines), encoding="cp1252")

    df = parse_pipe_delimited_sap_export(path, total_columns=8, skip_before_header=1)

    assert list(df.columns) == [
        "BUn",
        "Quantity",
        "Crcy",
        "Quantity_1",
        "Net Value",
        "Crcy_2",
    ]
    assert df.iloc[0]["Quantity_1"] == "20"
    assert df.iloc[0]["Crcy_2"] == "MXN"


def test_to_number_strips_thousands_separator():
    series = pd.Series(["1,200", "300", "", None])
    result = to_number(series)
    assert result.tolist()[:2] == [1200.0, 300.0]
    assert pd.isna(result.iloc[2])
    assert pd.isna(result.iloc[3])


def test_to_number_handles_sap_trailing_minus_sign():
    """SAP exports negative quantities/amounts with a trailing (not
    leading) minus sign, e.g. reversal/return transactions in MB5T
    (`"17-"` meaning `-17`). Confirmed against a real MB5T export where
    naive `pd.to_numeric` silently dropped these to NaN, understating
    `Quantity in Transit` sums (real production output showed negative
    values that our unfixed port rendered as 0)."""
    series = pd.Series(["17-", "1.37-", "1,866.49-", "100", "-5", None])
    result = to_number(series)
    assert result.tolist()[:5] == [-17.0, -1.37, -1866.49, 100.0, -5.0]
    assert pd.isna(result.iloc[5])


def test_normalize_plant_trims_and_uppercases():
    series = pd.Series([" us01 ", "US02"])
    assert normalize_plant(series).tolist() == ["US01", "US02"]


def test_normalize_material_strips_leading_zeros():
    series = pd.Series(["000123", " 456 ", "0000"])
    assert normalize_material(series).tolist() == ["123", "456", ""]


def test_reorder_columns_pq_style_moves_listed_columns_front_and_keeps_extras():
    """Matches real Table.ReorderColumns(..., MissingField.Ignore) semantics:
    listed columns move to the front in the given order; unlisted columns
    are NOT dropped, they're appended at the end in original order; listed
    columns absent from the table are simply skipped."""
    df = pd.DataFrame(
        {
            "A": [1],
            "B": [2],
            "C": [3],
            "Extra": [4],
        }
    )
    result = reorder_columns_pq_style(df, ["C", "A", "NotPresent"])
    assert list(result.columns) == ["C", "A", "B", "Extra"]
