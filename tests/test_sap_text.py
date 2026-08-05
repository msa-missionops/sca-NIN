"""Tests for shared SAP text parsing helpers (sap_text.py)."""

import pandas as pd

from nin_pipeline.sources.sap_text import (
    normalize_material,
    normalize_plant,
    parse_pipe_delimited_sap_export,
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


def test_to_number_strips_thousands_separator():
    series = pd.Series(["1,200", "300", "", None])
    result = to_number(series)
    assert result.tolist()[:2] == [1200.0, 300.0]
    assert pd.isna(result.iloc[2])
    assert pd.isna(result.iloc[3])


def test_normalize_plant_trims_and_uppercases():
    series = pd.Series([" us01 ", "US02"])
    assert normalize_plant(series).tolist() == ["US01", "US02"]


def test_normalize_material_strips_leading_zeros():
    series = pd.Series(["000123", " 456 ", "0000"])
    assert normalize_material(series).tolist() == ["123", "456", ""]
