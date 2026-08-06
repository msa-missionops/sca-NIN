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
from nin_pipeline.config import FileSelectionConfig, PipelineConfig, PipelinePaths
from nin_pipeline.ingestion import find_latest_file
from nin_pipeline.reference_data import (
    ReferenceData,
    active_plant,
    load_active_plants,
    load_reference_data,
    load_reference_data_from_workbook,
)
from nin_pipeline.sources.mb5t import clean_mb5t, enrich_mb5t
from nin_pipeline.sources.mrp_elements_doh import (
    clean_mrp_elements_doh,
    locate_latest_doh_file,
    pivot_mrp_elements_doh,
)
from nin_pipeline.sources.mrp_elements_rec import (
    clean_mrp_elements_rec,
    enrich_mrp_elements_rec,
    locate_latest_rec_file,
    pivot_mrp_elements_rec_weekly,
)
from nin_pipeline.sources.prdpl3 import clean_prdpl3, enrich_prdpl3


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

    1. Load reference/tag data and determine which plant(s) to run for --
       either the single plant in `plant_evaluation.csv`, or, if
       `paths.active_plants_folder` is configured, every plant listed in
       the latest file there (see
       `nin_pipeline.reference_data.load_active_plants` and
       docs/nin_data_contracts.md Open Decision #11).
    2. For each plant: discover and parse the latest PRDPL3, MB5T,
       MRP_ELEMENTS_DOH, and MRP_ELEMENTS_REC exports. REC's per-week
       requirement rows are transposed into `Total Forecast (Qty)`/
       `week 1`..`week 27` columns (see
       `nin_pipeline.sources.mrp_elements_rec.pivot_mrp_elements_rec_weekly`)
       -- per docs/nin_data_contracts.md Open Decision #1 (updated), this
       join has no `.pq` equivalent; the real final Excel workbook builds
       it with a native SUMIFS formula matrix, confirmed by SME.
    3. Assemble `build_overview_p1` from enriched PRDPL3, then the final
       `nin_base_table` by joining DOH/MB5T/REC-weekly. BOBL processing is
       deferred for now (see docs/nin_data_contracts.md Open Decision #10)
       -- its four output columns are emitted as null placeholders. When
       multiple plants are run, each plant's base table is assembled
       independently, then concatenated into one combined result.
    4. Write a run manifest recording the selected source files and row
       counts per plant, per docs/NIN_Python_Plan.md section 10.
    """
    run_id = run_id or _new_run_id()
    paths = config.paths

    reference_data = (
        load_reference_data_from_workbook(paths.reference_data_workbook)
        if paths.reference_data_workbook is not None
        else load_reference_data(paths.reference_data_folder)
    )

    if paths.active_plants_folder is not None:
        active_plants_file = find_latest_file(paths.active_plants_folder)
        plants = load_active_plants(active_plants_file)
        if not plants:
            raise ValueError(
                f"No plant codes found in {active_plants_file} "
                f"(paths.active_plants_folder)."
            )
    else:
        active_plants_file = None
        plants = [active_plant(reference_data)]

    per_plant_results = [
        _run_for_plant(paths, reference_data, plant, config.file_selection)
        for plant in plants
    ]

    base_table = pd.concat(
        [result.base_table for result in per_plant_results], ignore_index=True
    )

    sources: dict = {
        "plants": {p: r.sources for p, r in zip(plants, per_plant_results)}
    }
    if active_plants_file is not None:
        sources["active_plants_file"] = str(active_plants_file)

    row_counts: dict = {
        "plants": {p: r.row_counts for p, r in zip(plants, per_plant_results)},
        "nin_base_table": len(base_table),
    }

    manifest_path = _write_manifest(
        config=config,
        run_id=run_id,
        sources=sources,
        row_counts=row_counts,
    )

    _write_output(config, base_table)

    return PipelineResult(
        run_id=run_id, base_table=base_table, manifest_path=manifest_path
    )


@dataclass
class _PlantResult:
    base_table: pd.DataFrame
    sources: dict
    row_counts: dict


def _run_for_plant(
    paths: PipelinePaths,
    reference_data: ReferenceData,
    plant: str,
    file_selection: FileSelectionConfig,
) -> _PlantResult:
    """Run every per-source step for a single plant and assemble its base
    table. Shared by both the single-plant and multi-plant (all-plants)
    code paths in `run_pipeline`."""
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

    doh_file, doh_run_folder = locate_latest_doh_file(
        paths.mrp_doh_folder,
        plant=plant,
        extension=file_selection.mrp_doh_file_extension,
    )
    doh_clean = clean_mrp_elements_doh(
        doh_file, run_folder_name=doh_run_folder, active_plant=plant
    )
    doh_pivot = pivot_mrp_elements_doh(doh_clean)

    rec_file, rec_run_folder = locate_latest_rec_file(
        paths.mrp_rec_folder,
        plant=plant,
        extension=file_selection.mrp_rec_file_extension,
    )
    rec_clean = clean_mrp_elements_rec(
        rec_file, run_folder_name=rec_run_folder, active_plant=plant
    )
    rec_enriched = enrich_mrp_elements_rec(rec_clean, reference_data.rec_req_type)
    rec_weekly = pivot_mrp_elements_rec_weekly(rec_enriched)

    overview_p1 = assemble_overview_p1(prdpl3_enriched)
    base_table = assemble_nin_base_table(
        overview_p1,
        doh_pivot,
        mb5t_enriched,
        rec_weekly=rec_weekly,
    )

    return _PlantResult(
        base_table=base_table,
        sources={
            "prdpl3": str(prdpl3_file),
            "mrp_rec": str(rec_file),
            "mrp_doh": str(doh_file),
            "mb5t": str(mb5t_file),
        },
        row_counts={
            "prdpl3_raw": len(prdpl3_clean),
            "mrp_rec_raw": len(rec_clean),
            "mrp_doh_raw": len(doh_clean),
            "mb5t_raw": len(mb5t_clean),
            "nin_base_table": len(base_table),
        },
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
