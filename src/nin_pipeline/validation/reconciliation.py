"""Reconciliation of the Python `nin_base_table` against the existing
Power Query / Excel output (Phase 1G).

Implements the comparisons described in docs/NIN_Python_Plan.md section 16:

- 16.1 Row-level comparison (missing/extra/duplicate keys, changed
  descriptive fields).
- 16.2 Numeric comparison (value differences beyond a tolerance).
- 16.3 Aggregate comparison (totals grouped by a dimension column).
- 16.4 Difference output (a multi-tab `nin_reconciliation.xlsx` workbook).

This module only performs the comparison; it does not know how to obtain
the "current" (Power Query) output -- that must be supplied by the caller,
typically an export of the existing Excel workbook's final table for the
same raw input files. As of this writing no such export has been captured
in this repository (see `runs/*/manifest.json`'s `powerquery_output` field,
which is still `null`), so real reconciliation is still pending; this
module is exercised with synthetic data until a real comparison file is
available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# Per docs/nin_data_contracts.md section 7 / build_overview.BASE_TABLE_COLUMN_ORDER.
DEFAULT_KEY_COLUMN = "plant_material_key"

DEFAULT_DESCRIPTIVE_COLUMNS = (
    "Plant",
    "Source Plant",
    "Material Description",
    "Major PG",
)

DEFAULT_NUMERIC_COLUMNS = (
    "Safety Stock",
    "Total Stock Quantity",
    "Total Value Stock on Hand",
    "Quantity in Transit",
    "Available Stock",
    "Average Monthly Forecast Demand",
    "DOH",
    "Backorder Actual",
    "Backorder Qnty",
    "Backlog Actual",
    "Backlog Qnty",
)

DEFAULT_AGGREGATE_DIMENSIONS = (
    "Plant",
    "Major PG",
    "Source Plant",
    "Region",
)

DEFAULT_TOLERANCE = 0.01


@dataclass
class ReconciliationResult:
    """Holds every comparison table produced by `compare_base_tables`."""

    key_column: str
    missing_in_python: pd.DataFrame
    missing_in_current: pd.DataFrame
    duplicate_keys_python: pd.DataFrame
    duplicate_keys_current: pd.DataFrame
    changed_descriptive_fields: pd.DataFrame
    value_differences: pd.DataFrame
    aggregate_comparisons: dict[str, pd.DataFrame] = field(default_factory=dict)
    summary: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def is_clean(self) -> bool:
        """True if there are no missing keys, no duplicate keys, no changed
        descriptive fields, and no value differences beyond tolerance."""
        return (
            self.missing_in_python.empty
            and self.missing_in_current.empty
            and self.duplicate_keys_python.empty
            and self.duplicate_keys_current.empty
            and self.changed_descriptive_fields.empty
            and self.value_differences.empty
        )


def _duplicate_keys(df: pd.DataFrame, key_column: str) -> pd.DataFrame:
    if key_column not in df.columns:
        return pd.DataFrame(columns=[key_column, "count"])
    counts = df[key_column].value_counts()
    duplicated = counts[counts > 1]
    return duplicated.rename("count").rename_axis(key_column).reset_index()


def compare_base_tables(
    python_df: pd.DataFrame,
    current_df: pd.DataFrame,
    key_column: str = DEFAULT_KEY_COLUMN,
    descriptive_columns: tuple[str, ...] = DEFAULT_DESCRIPTIVE_COLUMNS,
    numeric_columns: tuple[str, ...] = DEFAULT_NUMERIC_COLUMNS,
    aggregate_dimensions: tuple[str, ...] = DEFAULT_AGGREGATE_DIMENSIONS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> ReconciliationResult:
    """Compare a Python-generated base table against the current (Power
    Query / Excel) output for the same raw inputs.

    `descriptive_columns`, `numeric_columns`, and `aggregate_dimensions`
    are restricted to columns actually present in both frames, so this
    works against partial/synthetic extracts as well as the full
    `nin_base_table` schema.
    """
    descriptive_columns = tuple(
        c
        for c in descriptive_columns
        if c in python_df.columns and c in current_df.columns
    )
    numeric_columns = tuple(
        c for c in numeric_columns if c in python_df.columns and c in current_df.columns
    )
    aggregate_dimensions = tuple(
        c
        for c in aggregate_dimensions
        if c in python_df.columns and c in current_df.columns
    )

    python_keys = set(python_df[key_column])
    current_keys = set(current_df[key_column])

    missing_in_python = current_df[
        current_df[key_column].isin(current_keys - python_keys)
    ].copy()
    missing_in_current = python_df[
        python_df[key_column].isin(python_keys - current_keys)
    ].copy()

    duplicate_keys_python = _duplicate_keys(python_df, key_column)
    duplicate_keys_current = _duplicate_keys(current_df, key_column)

    common_keys = python_keys & current_keys
    python_common = (
        python_df[python_df[key_column].isin(common_keys)]
        .drop_duplicates(subset=key_column, keep="first")
        .set_index(key_column)
    )
    current_common = (
        current_df[current_df[key_column].isin(common_keys)]
        .drop_duplicates(subset=key_column, keep="first")
        .set_index(key_column)
    )
    # Align both frames to the same key order for row-wise comparison.
    current_common = current_common.reindex(python_common.index)

    changed_rows = []
    for column in descriptive_columns:
        python_values = python_common[column].astype("string")
        current_values = current_common[column].astype("string")
        differs = python_values.fillna("") != current_values.fillna("")
        if differs.any():
            changed = pd.DataFrame(
                {
                    key_column: python_common.index[differs],
                    "field": column,
                    "python_value": python_values[differs].to_numpy(),
                    "current_value": current_values[differs].to_numpy(),
                }
            )
            changed_rows.append(changed)
    changed_descriptive_fields = (
        pd.concat(changed_rows, ignore_index=True)
        if changed_rows
        else pd.DataFrame(
            columns=[key_column, "field", "python_value", "current_value"]
        )
    )

    diff_rows = []
    for column in numeric_columns:
        python_values = pd.to_numeric(python_common[column], errors="coerce")
        current_values = pd.to_numeric(current_common[column], errors="coerce")
        difference = python_values - current_values
        differs = difference.abs() > tolerance
        # A value that is null on one side and populated on the other is
        # also a real difference, even though the numeric subtraction
        # above would evaluate to NaN (not > tolerance).
        differs = differs | (python_values.isna() ^ current_values.isna())
        if differs.any():
            diff = pd.DataFrame(
                {
                    key_column: python_common.index[differs],
                    "field": column,
                    "python_value": python_values[differs].to_numpy(),
                    "current_value": current_values[differs].to_numpy(),
                    "difference": difference[differs].to_numpy(),
                }
            )
            diff_rows.append(diff)
    value_differences = (
        pd.concat(diff_rows, ignore_index=True)
        if diff_rows
        else pd.DataFrame(
            columns=[key_column, "field", "python_value", "current_value", "difference"]
        )
    )

    aggregate_comparisons: dict[str, pd.DataFrame] = {}
    for dimension in aggregate_dimensions:
        aggregate_columns = [c for c in numeric_columns if c != dimension]
        if not aggregate_columns:
            continue
        python_totals = python_df.groupby(dimension)[list(aggregate_columns)].sum(
            numeric_only=True
        )
        current_totals = current_df.groupby(dimension)[list(aggregate_columns)].sum(
            numeric_only=True
        )
        comparison = python_totals.join(
            current_totals,
            how="outer",
            lsuffix="_python",
            rsuffix="_current",
        ).fillna(0)
        for column in aggregate_columns:
            comparison[f"{column}_difference"] = (
                comparison[f"{column}_python"] - comparison[f"{column}_current"]
            )
        aggregate_comparisons[dimension] = comparison.reset_index()

    summary = pd.DataFrame(
        [
            {"check": "Keys missing in Python", "count": len(missing_in_python)},
            {
                "check": "Extra keys in Python (missing in current)",
                "count": len(missing_in_current),
            },
            {"check": "Duplicate keys in Python", "count": len(duplicate_keys_python)},
            {
                "check": "Duplicate keys in current",
                "count": len(duplicate_keys_current),
            },
            {
                "check": "Rows with changed descriptive fields",
                "count": len(changed_descriptive_fields),
            },
            {
                "check": "Value differences beyond tolerance",
                "count": len(value_differences),
            },
        ]
    )

    return ReconciliationResult(
        key_column=key_column,
        missing_in_python=missing_in_python.reset_index(drop=True),
        missing_in_current=missing_in_current.reset_index(drop=True),
        duplicate_keys_python=duplicate_keys_python,
        duplicate_keys_current=duplicate_keys_current,
        changed_descriptive_fields=changed_descriptive_fields,
        value_differences=value_differences,
        aggregate_comparisons=aggregate_comparisons,
        summary=summary,
    )


def write_reconciliation_workbook(result: ReconciliationResult, path: Path) -> Path:
    """Write `result` to a multi-tab XLSX workbook per
    docs/NIN_Python_Plan.md section 16.4.

    Tabs: Summary, Missing in Python, Missing in Current, Value
    Differences, Duplicate Keys, Validation Results (one tab per
    aggregate dimension).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    duplicate_keys = pd.concat(
        [
            result.duplicate_keys_python.assign(source="python"),
            result.duplicate_keys_current.assign(source="current"),
        ],
        ignore_index=True,
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        result.summary.to_excel(writer, sheet_name="Summary", index=False)
        result.missing_in_python.to_excel(
            writer, sheet_name="Missing in Python", index=False
        )
        result.missing_in_current.to_excel(
            writer, sheet_name="Missing in Current", index=False
        )
        result.value_differences.to_excel(
            writer, sheet_name="Value Differences", index=False
        )
        duplicate_keys.to_excel(writer, sheet_name="Duplicate Keys", index=False)
        result.changed_descriptive_fields.to_excel(
            writer, sheet_name="Validation Results", index=False
        )
        for dimension, comparison in result.aggregate_comparisons.items():
            sheet_name = f"Agg - {dimension}"[:31]  # Excel sheet-name limit.
            comparison.to_excel(writer, sheet_name=sheet_name, index=False)

    return path
