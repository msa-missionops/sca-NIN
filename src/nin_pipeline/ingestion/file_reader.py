"""File discovery and low-level text parsing shared by all source readers.

These functions reproduce the file-selection and parsing behavior confirmed
in the Power Query source (docs/powerquery_m/) and documented in
docs/NIN_Python_Plan.md section 7.6:

- PRDPL3 and MB5T select the single latest file in a fixed output folder.
- MRP_ELEMENTS_REC and MRP_ELEMENTS_DOH select the latest *run* subfolder,
  then the latest file within it matching the active plant.
- REC and DOH locate the real SAP header row dynamically by scanning for a
  row containing a known set of column names (the SAP export has a variable
  number of banner/metadata rows above the header).

Note on "latest": the Power Query logic sorts by `Date created`. Windows file
creation time is not reliably available cross-platform in Python, so these
helpers sort by modification time (`st_mtime`) instead. This is documented
here as a known deviation to confirm during reconciliation (Phase 1G) if the
two ever disagree on a real filesystem.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path


def _visible_entries(paths: Iterable[Path]) -> list[Path]:
    """Filter out hidden entries (dotfiles), mirroring the Power Query
    `[Attributes]?[Hidden]? <> true` filter used before every latest-file/
    latest-folder selection."""
    return [p for p in paths if not p.name.startswith(".")]


def find_latest_file(folder: Path, pattern: str = "*") -> Path:
    """Return the most recently modified visible file in `folder`.

    Mirrors the `Folder.Files` + `HiddenFiltered` + `LatestRow` steps used by
    stg_prdpl3_clean.pq and stg_mb5t_clean.pq.

    Raises FileNotFoundError if no matching visible file exists.
    """
    folder = Path(folder)
    candidates = _visible_entries(p for p in folder.glob(pattern) if p.is_file())
    if not candidates:
        raise FileNotFoundError(f"No files found in: {folder}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def find_latest_run_folder(root: Path) -> Path:
    """Return the most recently modified visible subfolder of `root`.

    Mirrors the `Folder.Contents` + `VisibleFolders` + `SortedFolders` steps
    used by stg_mm_mrp_elements_rec_clean.pq and
    stg_mm_mrp_elements_doh_clean.pq to find the latest run folder.

    Raises FileNotFoundError if no visible subfolder exists.
    """
    root = Path(root)
    candidates = _visible_entries(p for p in root.iterdir() if p.is_dir())
    if not candidates:
        raise FileNotFoundError(f"No run folders found under: {root}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def find_plant_file(
    folder: Path,
    plant: str,
    prefix: str,
    extension: str,
) -> Path:
    """Return the latest visible file in `folder` matching a transaction's
    naming convention for the given plant.

    Mirrors the `FileFiltered` + `SortedPlantFiles` steps used by
    stg_mm_mrp_elements_rec_clean.pq / stg_mm_mrp_elements_doh_clean.pq:
    the file extension must match, the name must start with `prefix`
    (case-insensitive), and the name must contain `_<PLANT>_`
    (case-insensitive).

    Raises FileNotFoundError with a message naming the plant and folder,
    matching the descriptive errors raised by the Power Query source.
    """
    folder = Path(folder)
    ext = extension.lower().lstrip(".")
    plant_token = f"_{plant.upper()}_"
    prefix_upper = prefix.upper()

    candidates = []
    for p in _visible_entries(x for x in folder.iterdir() if x.is_file()):
        if p.suffix.lower().lstrip(".") != ext:
            continue
        name_upper = p.name.upper()
        if not name_upper.startswith(prefix_upper):
            continue
        if plant_token not in name_upper:
            continue
        candidates.append(p)

    if not candidates:
        raise FileNotFoundError(
            f"No {prefix} export file found for plant {plant} in folder: {folder}"
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)


def read_delimited_text(
    path: Path,
    delimiter: str = "|",
    encoding: str = "cp1252",
) -> list[list[str]]:
    """Read a delimited text file into a list of trimmed string rows.

    `delimiter` accepts the literal M-code placeholder `"#(tab)"` used in
    the SAP export queries, translated here to an actual tab character.

    This performs no header promotion, column skipping, or type conversion;
    those are source-specific responsibilities (Phase 1D).
    """
    sep = "\t" if delimiter == "#(tab)" else delimiter
    with open(path, "r", encoding=encoding, errors="ignore", newline="") as fh:
        raw_rows = [line.rstrip("\r\n") for line in fh]
    return [[cell.strip() for cell in row.split(sep)] for row in raw_rows]


def detect_sap_header_row(
    rows: Sequence[Sequence[str]],
    required_tokens: Iterable[str],
) -> int:
    """Return the index of the first row containing every value in
    `required_tokens` as an exact cell value.

    Mirrors the `AddIndex` + `HeaderRows` + `HeaderRowIndex` steps used by
    stg_mm_mrp_elements_rec_clean.pq / stg_mm_mrp_elements_doh_clean.pq to
    locate the real SAP header row (e.g. the row containing "Plnt",
    "Material", "El") beneath a variable number of banner/metadata rows.

    Raises ValueError if no row contains all required tokens.
    """
    tokens = set(required_tokens)
    for index, row in enumerate(rows):
        if tokens.issubset(set(row)):
            return index
    raise ValueError(
        f"Could not find SAP header row containing all of: {sorted(tokens)}"
    )
