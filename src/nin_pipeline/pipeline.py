"""End-to-end pipeline orchestration (Phase 1F).

Wires together file discovery (`nin_pipeline.ingestion`), the per-source
transformations (`nin_pipeline.sources`), and the final base-table
assembly (`nin_pipeline.business.build_overview`) into a single run,
following the run/manifest structure in docs/NIN_Python_Plan.md sections
9-10.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nin_pipeline.business.build_overview import (
    assemble_nin_base_table,
    assemble_overview_p1,
)
from nin_pipeline.config import PipelineConfig
from nin_pipeline.ingestion import find_latest_file
from nin_pipeline.reference_data import active_plant, load_reference_data
from nin_pipeline.sources.bobl import clean_bobl, enrich_bobl
from nin_pipeline.sources.mb5t import clean_mb5t, enrich_mb5t
from nin_pipeline.sources.mrp_elements_doh import (
    clean_mrp_elements_doh,
    locate_latest_doh_file,
    pivot_mrp_elements_doh,
)
from nin_pipeline.sources.prdpl3 import clean_prdpl3, enrich_prdpl3

# Convention for this Python port: BOBL's PowerBI matrix export is saved as
# a CSV under `reference_data_folder`, since (unlike the other sources) it
# is not a folder of dated SAP extracts to discover. See
# `nin_pipeline.sources.bobl` and `docs/nin_data_contracts.md` section 5.
BOBL_FILENAME = "bobl.csv"


@dataclass
class PipelineResult:
    run_id: str
    base_table: pd.DataFrame
    manifest_path: Path


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def run_pipeline(config: PipelineConfig, run_id: str | None = None) -> PipelineResult:
    """Run the full pipeline once and return the assembled base table.

    Steps (see docs/NIN_Python_Plan.md sections 9-11):

    1. Load reference/tag data and determine the single active plant.
    2. Discover and parse the latest PRDPL3, MB5T, and MRP_ELEMENTS_DOH
       exports for that plant (MRP_ELEMENTS_REC is intentionally not
       processed here -- it is out of scope for the final base table, per
       docs/nin_data_contracts.md Open Decision #1).
    3. Load and shape the BOBL export.
    4. Assemble `build_overview_p1` from enriched PRDPL3, then the final
       `nin_base_table` by joining DOH/MB5T/BOBL.
    5. Write a run manifest recording the selected source files and row
       counts, per docs/NIN_Python_Plan.md section 10.
    """
    run_id = run_id or _new_run_id()
    paths = config.paths

    reference_data = load_reference_data(paths.reference_data_folder)
    plant = active_plant(reference_data)

    prdpl3_file = find_latest_file(paths.prdpl3_folder)
    prdpl3_clean = clean_prdpl3(prdpl3_file, active_plant=plant)
    prdpl3_enriched = enrich_prdpl3(
        prdpl3_clean,
        reference_data.region,
        reference_data.top60,
        reference_data.sourceplant,
    )

    mb5t_file = find_latest_file(paths.mb5t_folder)
    mb5t_clean = clean_mb5t(mb5t_file, active_plant=plant)
    mb5t_enriched = enrich_mb5t(mb5t_clean)

    doh_file, doh_run_folder = locate_latest_doh_file(paths.mrp_doh_folder, plant=plant)
    doh_clean = clean_mrp_elements_doh(
        doh_file, run_folder_name=doh_run_folder, active_plant=plant
    )
    doh_pivot = pivot_mrp_elements_doh(doh_clean)

    bobl_raw = pd.read_csv(paths.reference_data_folder / BOBL_FILENAME, dtype="string")
    bobl_clean = clean_bobl(bobl_raw)
    bobl_enriched = enrich_bobl(bobl_clean)

    overview_p1 = assemble_overview_p1(prdpl3_enriched)
    base_table = assemble_nin_base_table(
        overview_p1, doh_pivot, mb5t_enriched, bobl_enriched
    )

    manifest_path = _write_manifest(
        config=config,
        run_id=run_id,
        sources={
            "prdpl3": str(prdpl3_file),
            "mrp_rec": None,
            "mrp_doh": str(doh_file),
            "mb5t": str(mb5t_file),
        },
        row_counts={
            "prdpl3_raw": len(prdpl3_clean),
            "mrp_rec_raw": 0,
            "mrp_doh_raw": len(doh_clean),
            "mb5t_raw": len(mb5t_clean),
            "nin_base_table": len(base_table),
        },
    )

    _write_output(config, base_table)

    return PipelineResult(
        run_id=run_id, base_table=base_table, manifest_path=manifest_path
    )


def _write_manifest(
    config: PipelineConfig,
    run_id: str,
    sources: dict,
    row_counts: dict,
) -> Path:
    run_dir = config.paths.run_folder / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "as_of_date": None,
        "sources": sources,
        "row_counts": row_counts,
        "validation_status": "not_run",
        "output_file": str(config.paths.output_folder / "nin_base_table"),
    }
    manifest_path = run_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return manifest_path


def _write_output(config: PipelineConfig, base_table: pd.DataFrame) -> None:
    output_folder = config.paths.output_folder
    output_folder.mkdir(parents=True, exist_ok=True)
    base_path = output_folder / "nin_base_table"

    if config.output.write_csv:
        base_table.to_csv(base_path.with_suffix(".csv"), index=False)
    if config.output.write_parquet:
        base_table.to_parquet(base_path.with_suffix(".parquet"), index=False)
    if config.output.write_excel:
        base_table.to_excel(base_path.with_suffix(".xlsx"), index=False)
