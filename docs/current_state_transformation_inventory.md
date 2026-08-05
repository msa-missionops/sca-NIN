# Current State Transformation Inventory

Purpose: document every Power Query step that composes the current middle-layer transformations so the Python implementation can reproduce it exactly.

How to use this document:
- Open each Power Query in the Excel workbook that feeds the final NIN report.
- For each query, record: name, role (source/transform/reference/final), input table(s), output schema, column renames, filters, joins, custom calculations (M code), and sample rows.
- Save small sample output files under test_data/expected for regression testing.

Template per query

- Query name:
- Role: (source|transformation|reference|support|final)
- Workbook/Location:
- Inputs (file/query names and paths):
- Output columns (name, type, description):
- Column renames / mappings (original -> standardized):
- Filters applied (full predicate text):
- Joins (other queries/tables, join keys, join type):
- Custom M code or expressions (paste exact M code or screenshots):
- Business calculations (human-readable formula):
- Assumptions or notes:
- Owner / SME:
- Sample output file: test_data/expected/<query_name>_sample.csv

Suggested initial list (based on plan) — confirm and expand:
- PRDPL3 (inventory source)
- MRP_ELEMENTS_REC (requirements/receipts)
- MRP_ELEMENTS_DOH (DOH horizon requirements)
- MB5T (in-transit stock)
- Requirement type mapping
- Plant evaluation mapping
- Region mapping
- Source plant mapping

Next steps
1. Open the final Excel workbook and identify the top-level query that produces the base table.
2. For each upstream query, fill the template above.
3. Save a small sample (50-200 rows) of the final query output into test_data/expected for golden tests.
4. Capture any M-code snippets that perform complex transforms.

If helpful, permit me to open and parse any Power Query M code files you can provide; otherwise, collect the details manually and I will convert them into a formal specification in docs/nin_data_contracts.md.

---

## Confirmed Inventory (parsed from docs/powerquery_m/)

The `.pq` files are now present under `docs/powerquery_m/`, grouped by SAP
extract / topic. Every group follows the same clean -> enriched(/pivot) ->
review chain. Full flow narrative, dependency graph, and business-rule
definitions have been moved into `docs/NIN_Python_Plan.md` sections **7.6**
and **14** (single source of truth, to avoid drift between two documents).
This section indexes where each query lives and its role/output for quick
lookup; see the Plan doc for the authoritative details, formulas, and known
risks (VG pivot-column gap, REC sign bug, BOBL casing inconsistency, etc.).

| Query group | Files (`docs/powerquery_m/<dir>/`) | Role | Grain / Output |
|---|---|---|---|
| PRDPL3 | `prdpl3/stg_prdpl3_clean.pq`, `stg_prdpl3_enriched.pq`, `out_prdpl3_review.pq` | Anchor source: inventory, safety stock, planning fields; tags Region/Top60/SourcePlant | One row per `plant_material_key` |
| MB5T | `mb5t/stg_mb5t_clean.pq`, `stg_mb5t_enriched.pq`, `out_mb5t_review.pq` | In-transit quantity | One row per `plant_material_key`; column `Quantity in Transit` |
| MRP_ELEMENTS_DOH | `mm_mrp_elements_doh/stg_mm_mrp_elements_doh_clean.pq`, `stg_mm_mrp_elements_doh_pivot.pq`, `out_mm_mrp_elements_doh_review.pq` | Forward demand within DOH horizon, pivoted by requirement type | One row per `plant_material_key`; columns `WB, PP, U2, VC, VJ, U1` (+`VG` expected downstream) |
| MRP_ELEMENTS_REC | `mm_mrp_elements_rec/stg_mm_mrp_elements_rec_clean.pq`, `stg_mm_mrp_elements_rec_enriched.pq`, `out_mm_mrp_elements_rec_review.pq` | Weekly signed requirement forecast | One row per `plant_material_key` + `Week Ending`; **not currently joined into the final base table** |
| BOBL | `BOBL/stg_bobl_clean.pq`, `stg_bobl_enriched.pq`, `out_bobl_review.pq` | Backlog/backorder from a pasted PowerBI matrix export | One row per `plant_material_key`; columns `Backorder Actual/Qnty`, `Backlog Actual/Qnty` |
| Tags/reference | `tags/tbl_tag_region.pq`, `tbl_tag_top60.pq`, `tbl_tag_sourceplant.pq`, `stg_sap_t460a.pq` | Lookup tables joined into PRDPL3 enrichment (`t460a` usage unconfirmed) | Reference tables |
| Final assembly | `build overview/build_overview_p1_clean.pq` ... `build_overview_p2_review.pq` | Anchors on PRDPL3, left-joins DOH/MB5T/BOBL, computes Available Stock / DOH / Forecast | `build_overview_p2_review` = final table handed to Excel |

Next step for Phase 1B (data contracts): use section 7.6/14 of
`docs/NIN_Python_Plan.md` as the input to formally define
`docs/nin_data_contracts.md` schemas for each of the six confirmed outputs
above, and to resolve the flagged risks with the SME before porting.
