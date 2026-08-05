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


def parse_dynamic_header_sap_export(
    path: Path,
    header_tokens: set[str],
    delimiter: str = "#(tab)",
    encoding: str = "cp1252",
) -> pd.DataFrame:
    """Parse a SAP export where the real header row's position is not fixed
    (a variable number of banner/metadata rows precede it), matching
    stg_mm_mrp_elements_rec_clean.pq / stg_mm_mrp_elements_doh_clean.pq's
    `TransformSapFile` inner function.

    Steps:

    1. Read the file with the given delimiter (tab by default).
    2. Drop fully-blank rows (every cell empty).
    3. Locate the header row as the first row containing every value in
       `header_tokens` (see `detect_sap_header_row`).
    4. Promote that row to the column header, dropping any column whose
       header name is blank.
    """
    from nin_pipeline.ingestion import detect_sap_header_row

    rows = read_delimited_text(path, delimiter=delimiter, encoding=encoding)
    non_blank = [row for row in rows if any(cell != "" for cell in row)]

    header_index = detect_sap_header_row(non_blank, header_tokens)
    header_row = non_blank[header_index]
    data_rows = non_blank[header_index + 1 :]

    keep_indices = [i for i, name in enumerate(header_row) if name.strip() != ""]
    header = [header_row[i].strip() for i in keep_indices]
    kept_rows = [
        [row[i] if i < len(row) else "" for i in keep_indices] for row in data_rows
    ]

    return pd.DataFrame(kept_rows, columns=header, dtype="string")


def to_number(series: pd.Series) -> pd.Series:
    """Convert a text column to a numeric column, tolerating thousands
    separators and blanks, matching `Table.TransformColumnTypes(..., type
    number)` with a `Text.Replace(_, ",", "")`-style cleanup."""
    cleaned = series.astype("string").str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def to_integer(series: pd.Series) -> pd.Series:
    """Convert a text column to a nullable integer column, matching
    `Table.TransformColumnTypes(..., Int64.Type)`. Values are rounded before
    casting since real SAP quantity fields are expected to be whole numbers;
    a fractional source value indicates a data-quality issue worth
    surfacing during reconciliation rather than silently truncating."""
    return to_number(series).round().astype("Int64")


def normalize_plant(series: pd.Series) -> pd.Series:
    """`Text.Upper(Text.Trim(_))`, applied to a Plant column."""
    return series.astype("string").str.strip().str.upper()


def normalize_material(series: pd.Series) -> pd.Series:
    """`Text.TrimStart(Text.Upper(Text.Trim(_)), {"0"})`, applied to a
    Material column: trims whitespace, upper-cases, then strips leading
    zeros."""
    return series.astype("string").str.strip().str.upper().str.lstrip("0")


def week_ending_friday(dates: pd.Series) -> pd.Series:
    """Compute `Week Ending` the same way as
    stg_mm_mrp_elements_rec_clean.pq / stg_mm_mrp_elements_doh_clean.pq:

    ```text
    Date.AddDays(d, 7 - Date.DayOfWeek(d, Day.Friday))
    ```

    `Date.DayOfWeek(d, Day.Friday)` returns 0 for Friday, 1 for Saturday, ...,
    6 for Thursday. **Note the confirmed quirk**: for a date that already
    falls on a Friday, this formula adds a full 7 days (result = the
    *following* Friday), not 0 days. This is reproduced exactly here since
    it is the behavior confirmed in the current production query; flag with
    the SME if same-day Friday dates were intended to map to themselves.
    """
    dates = pd.to_datetime(dates, errors="coerce")
    day_of_week_from_friday = (dates.dt.dayofweek - 4) % 7
    return dates + pd.to_timedelta(7 - day_of_week_from_friday, unit="D")
