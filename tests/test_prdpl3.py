"""Tests for the PRDPL3 source transformation (Phase 1D)."""

import pandas as pd

from nin_pipeline.sources.prdpl3 import (
    ENRICHED_COLUMN_ORDER,
    clean_prdpl3,
    enrich_prdpl3,
)

HEADER = [
    "Plnt",
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
]

assert len(HEADER) == 49  # 51 total columns minus the two wrapper columns


def _row(overrides):
    values = {name: "" for name in HEADER}
    values.update(overrides)
    return "|" + "|".join(values[name] for name in HEADER) + "|"


def write_prdpl3_export(path, data_rows):
    lines = [f"BANNER LINE {i}" for i in range(6)]  # 6 skipped banner rows
    lines.append(_row(dict(zip(HEADER, HEADER))))  # header row (row 7)
    lines.append(_row({}))  # 1 skipped post-header row (units/blank row)
    lines.extend(_row(row) for row in data_rows)
    path.write_text("\n".join(lines), encoding="cp1252")


def test_clean_prdpl3_filters_plant_and_product_hierarchy(tmp_path):
    path = tmp_path / "PRDPL3_export.txt"
    write_prdpl3_export(
        path,
        [
            {
                "Plnt": "us01",
                "Material": "000123",
                "Product hierarchy": "00020ABC",
                "Safety Stock": "1,200",
                "DelFlag": "",
            },
            {
                "Plnt": "US01",
                "Material": "000456",
                "Product hierarchy": "00099XYZ",  # wrong hierarchy -> filtered out
            },
            {
                "Plnt": "US02",
                "Material": "000789",
                "Product hierarchy": "00020ABC",  # wrong plant -> filtered out
            },
        ],
    )

    result = clean_prdpl3(path, active_plant="US01")

    assert len(result) == 1
    row = result.iloc[0]
    assert row["Plant"] == "US01"
    assert row["Material"] == "123"
    assert row["plant_material_key"] == "US01-123"
    assert row["Safety Stock"] == 1200.0


def test_enrich_prdpl3_applies_tag_defaults_when_unmatched(tmp_path):
    path = tmp_path / "PRDPL3_export.txt"
    write_prdpl3_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "Product hierarchy": "00020ABC",
                "Spec Proc": "UNKNOWN",
            }
        ],
    )
    clean_df = clean_prdpl3(path, active_plant="US01")

    region_tag = pd.DataFrame({"Plant": ["US01"], "Region": ["Northeast"]})
    top60_tag = pd.DataFrame(
        {"plant_material_key": ["US99-999"], "top_60_flag": ["top60"]}
    )
    sourceplant_tag = pd.DataFrame({"source_key": ["ZZ"], "source_plant": ["US02"]})

    enriched = enrich_prdpl3(clean_df, region_tag, top60_tag, sourceplant_tag)

    assert list(enriched.columns) == [
        c for c in ENRICHED_COLUMN_ORDER if c in enriched.columns
    ]
    row = enriched.iloc[0]
    assert row["Region"] == "Northeast"
    assert row["top_60_flag"] == "standard"  # unmatched -> default
    assert row["source_plant"] == "None defined"  # unmatched -> default


def test_enrich_prdpl3_matches_tags_when_present(tmp_path):
    path = tmp_path / "PRDPL3_export.txt"
    write_prdpl3_export(
        path,
        [
            {
                "Plnt": "US01",
                "Material": "000123",
                "Product hierarchy": "00020ABC",
                "Spec Proc": "40",
            }
        ],
    )
    clean_df = clean_prdpl3(path, active_plant="US01")

    region_tag = pd.DataFrame({"Plant": ["US01"], "Region": ["Northeast"]})
    top60_tag = pd.DataFrame(
        {"plant_material_key": ["US01-123"], "top_60_flag": ["top60"]}
    )
    sourceplant_tag = pd.DataFrame({"source_key": ["40"], "source_plant": ["US03"]})

    enriched = enrich_prdpl3(clean_df, region_tag, top60_tag, sourceplant_tag)
    row = enriched.iloc[0]

    assert row["Region"] == "Northeast"
    assert row["top_60_flag"] == "top60"
    assert row["source_plant"] == "US03"
