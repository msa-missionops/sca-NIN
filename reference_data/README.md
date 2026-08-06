# Reference / Tag Data

This folder is the **central, version-controlled source of truth** for the
five small business-maintained lookup ("tag") tables the pipeline joins
against. It is loaded via `paths.reference_data_folder` in
`config/settings.example.yaml` (see `docs/NIN_Python_Plan.md` section 8.1
and `docs/nin_data_contracts.md` Open Decision #9 for the full design
rationale).

These values change infrequently, so a plain CSV folder — not a live Excel
workbook — is the recommended way to maintain them. Edit the CSV directly
(or paste in from the master Excel workbook when a value changes), commit
the change, and re-run the pipeline.

If you ever *do* need live-editing-in-Excel instead, the pipeline also
supports pointing `paths.reference_data_workbook` at a single `.xlsx` file
containing the same five tables as named Excel Tables — see
`nin_pipeline.reference_data.load_reference_data_from_workbook`. Use
exactly one of the two options, not both.

## Files

| File | Columns | Purpose |
|---|---|---|
| `region.csv` | `Plant, Region` | Maps each plant code to its region (APAC/EMEA/LAR/NNA). Seeded here from `docs/design_reference/tbl_tag_region.png`. |
| `top60.csv` | `plant_material_key, plant, material, top_60_flag` | Flags specific plant-material combinations as "top 60" priority items. **Only a sample of 4 DED2 rows are seeded here** (from `docs/design_reference/tbl_tag_top60.png`) — replace with the full list from the master workbook. |
| `sourceplant.csv` | `source_key, desc, source_plant` | Decodes MRP "source" codes (e.g. `EB` = "Costing - from DED2") to a plant. Full list copied from `docs/design_reference/tbl_tag_sourceplant.csv`. |
| `rec_req_type.csv` | `type, negative` | Marks which REC "Requirements Type" codes represent negative (supply-reducing) quantities. `negative` accepts `true`/`false`, `1`/`0`, or `yes`/`no` (case-insensitive); blank/unknown types default to not-negative. **Empty template** — populate from the master workbook. |
| `plant_evaluation.csv` | `Plant` | The single active evaluation plant for a given pipeline run. **Empty template** — add exactly one row before running. |

## Updating a value

1. Edit the relevant CSV directly in this folder (or copy the current
   value from the master Excel workbook).
2. Commit the change with a note on what changed and why.
3. Re-run the pipeline — no code changes needed.
