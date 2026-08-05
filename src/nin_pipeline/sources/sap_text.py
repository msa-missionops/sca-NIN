"""Shared parsing helpers for fixed-width-column SAP pipe/tab exports.

These reproduce the "wrap in N columns, skip banner rows, promote header"
pattern used identically by stg_prdpl3_clean.pq and stg_mb5t_clean.pq (see
docs/NIN_Python_Plan.md section 7.6): the SAP export is imported with a fixed
column count, the leading/trailing wrapper columns created by the leading and
trailing delimiter on each line are dropped, a fixed number of banner/
metadata rows are skipped, the next row is promoted to the header, and (for
PRDPL3) one further row is dropped.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from nin_pipeline.ingestion import read_delimited_text


def _pad_or_truncate(row: list[str], width: int) -> list[str]:
    """Force a row to exactly `width` cells, mirroring the fixed `Columns=N`
    behavior of Power Query's `Csv.Document`."""
    if len(row) < width:
        return row + [""] * (width - len(row))
    return row[:width]


def parse_pipe_delimited_sap_export(
    path: Path,
    total_columns: int,
    skip_before_header: int,
    skip_after_header: int = 0,
    delimiter: str = "|",
    encoding: str = "cp1252",
) -> pd.DataFrame:
    """Parse a pipe-delimited SAP export into a string-typed DataFrame.

    Steps (matching the Power Query source):

    1. Read the file and force every row to `total_columns` cells.
    2. Drop the first and last column (wrapper columns created by the
       leading/trailing delimiter on each line).
    3. Skip `skip_before_header` banner/metadata rows.
    4. Trim all remaining cells.
    5. Promote the next row to the column header.
    6. Skip `skip_after_header` further rows (e.g. a units/blank row).

    No type conversion, renaming, filtering, or key-building is performed
    here; that is source-specific and handled by the caller (e.g.
    `nin_pipeline.sources.prdpl3`).
    """
    rows = read_delimited_text(path, delimiter=delimiter, encoding=encoding)
    rows = [_pad_or_truncate(row, total_columns) for row in rows]
    rows = [row[1:-1] for row in rows]

    body = rows[skip_before_header:]
    if not body:
        raise ValueError(
            f"No rows remain after skipping {skip_before_header} banner rows: {path}"
        )

    header = [cell.strip() for cell in body[0]]
    data_rows = [
        [cell.strip() for cell in row] for row in body[1 + skip_after_header :]
    ]

    return pd.DataFrame(data_rows, columns=header, dtype="string")


def to_number(series: pd.Series) -> pd.Series:
    """Convert a text column to a numeric column, tolerating thousands
    separators and blanks, matching `Table.TransformColumnTypes(..., type
    number)` with a `Text.Replace(_, ",", "")`-style cleanup."""
    cleaned = series.astype("string").str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_plant(series: pd.Series) -> pd.Series:
    """`Text.Upper(Text.Trim(_))`, applied to a Plant column."""
    return series.astype("string").str.strip().str.upper()


def normalize_material(series: pd.Series) -> pd.Series:
    """`Text.TrimStart(Text.Upper(Text.Trim(_)), {"0"})`, applied to a
    Material column: trims whitespace, upper-cases, then strips leading
    zeros."""
    return series.astype("string").str.strip().str.upper().str.lstrip("0")
