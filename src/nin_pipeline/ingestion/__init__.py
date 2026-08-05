"""Common SAP-export file discovery and low-level reading utilities.

This package implements Phase 1C of docs/NIN_Python_Plan.md: the shared file
discovery and parsing primitives used by every source transformation
(PRDPL3, MB5T, MRP_ELEMENTS_REC, MRP_ELEMENTS_DOH). See
docs/NIN_Python_Plan.md section 7.6 and docs/nin_data_contracts.md for the
confirmed Power Query behavior this module reproduces.
"""

from .file_reader import (
    detect_sap_header_row,
    find_latest_file,
    find_latest_run_folder,
    find_plant_file,
    read_delimited_text,
)

__all__ = [
    "detect_sap_header_row",
    "find_latest_file",
    "find_latest_run_folder",
    "find_plant_file",
    "read_delimited_text",
]
