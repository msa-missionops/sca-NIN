"""Tests for the MB5T source transformation (Phase 1D)."""

from nin_pipeline.sources.mb5t import CLEAN_COLUMN_ORDER, clean_mb5t, enrich_mb5t

HEADER = [
    "Material",
    "Material Description",
    "Quantity",
    "Plnt",
    "Name 1",
    "Pur. Doc.",
    "Item",
    "SPlt",
    "S",
    "BUn",
    "Amount in LC",
    "Crcy",
    "Quantity_1",
    "OUn",
    "Net Value",
    "Crcy_2",
]

assert len(HEADER) == 16  # 18 total columns minus the two wrapper columns


def _row(overrides):
    values = {name: "" for name in HEADER}
    values.update(overrides)
    return "|" + "|".join(values[name] for name in HEADER) + "|"


def write_mb5t_export(path, data_rows):
    lines = [f"BANNER LINE {i}" for i in range(3)]  # 3 skipped banner rows
    lines.append(_row(dict(zip(HEADER, HEADER))))  # header row (row 4)
    lines.append(_row({}))  # 1 skipped post-header row
    lines.extend(_row(row) for row in data_rows)
    path.write_text("\n".join(lines), encoding="cp1252")


def test_clean_mb5t_filters_plant_and_blank_material(tmp_path):
    path = tmp_path / "MB5T_export.txt"
    write_mb5t_export(
        path,
        [
            {"Plnt": "us01", "Material": "000123", "Quantity": "10"},
            {"Plnt": "US01", "Material": "", "Quantity": "5"},  # blank -> dropped
            {"Plnt": "US02", "Material": "000456", "Quantity": "7"},  # wrong plant
        ],
    )

    result = clean_mb5t(path, active_plant="US01")

    assert len(result) == 1
    row = result.iloc[0]
    assert row["Plnt"] == "US01"  # note: NOT renamed to "Plant"
    assert row["Material"] == "123"
    assert row["plant_material_key"] == "US01-123"
    assert row["Quantity"] == 10
    assert row["Group"] is None or str(row["Group"]) == "<NA>"
    assert list(result.columns) == [
        c for c in CLEAN_COLUMN_ORDER if c in result.columns
    ]


def test_enrich_mb5t_aggregates_quantity_by_key(tmp_path):
    path = tmp_path / "MB5T_export.txt"
    write_mb5t_export(
        path,
        [
            {"Plnt": "US01", "Material": "000123", "Quantity": "10"},
            {"Plnt": "US01", "Material": "000123", "Quantity": "5"},
            {"Plnt": "US01", "Material": "000456", "Quantity": "2"},
        ],
    )
    clean_df = clean_mb5t(path, active_plant="US01")

    result = enrich_mb5t(clean_df)
    result = result.set_index("plant_material_key")

    assert result.loc["US01-123", "Quantity in Transit"] == 15
    assert result.loc["US01-456", "Quantity in Transit"] == 2


def test_enrich_mb5t_nulls_become_zero(tmp_path):
    path = tmp_path / "MB5T_export.txt"
    write_mb5t_export(
        path,
        [
            {"Plnt": "US01", "Material": "000123", "Quantity": "not_a_number"},
        ],
    )
    clean_df = clean_mb5t(path, active_plant="US01")

    result = enrich_mb5t(clean_df)

    assert result.iloc[0]["Quantity in Transit"] == 0
