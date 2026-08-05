# NIN Data Contracts

Purpose: formal schemas for every standardized output the Python pipeline must
produce, derived from the confirmed Power Query flow documented in
`docs/NIN_Python_Plan.md` (sections 7.6 and 14). This is the Phase 1B
deliverable referenced in section 20 of the plan.

Each contract below corresponds to one `out_<group>_review` Power Query output
(or the final `build_overview_p2_review`). Column names are the **current
production names** (post-rename), so reconciliation (Phase 1G) can compare
field-for-field against the existing Excel workbook.

Conventions used throughout:

- `key` — participates in the join/grouping key.
- `plant_material_key` is always `Upper(Trim(Plant)) & "-" & Upper(Trim(Material, leading zeros stripped))`
  unless a source-specific exception is noted.
- "Nullable" reflects what the current Power Query produces, not what is
  necessarily desirable.

---

## Open Decisions Assumed Below

These four items were flagged as unresolved in `NIN_Python_Plan.md` §7.6/§14.
The contracts below adopt the stated **default** so Phase 1C+ can proceed;
revisit with the SME and update this doc (and the contracts) if the default is
wrong.

| # | Question | Default adopted here | Rationale |
|---|---|---|---|
| 1 | Is REC weekly output in scope for Phase 1? | **RESOLVED — yes, in scope.** REC's per-week `Adj Req Qty` is transposed into `Total Forecast (Qty)` + `week 1`..`week 27` columns (`pivot_mrp_elements_rec_weekly` in `mrp_elements_rec.py`) and left-joined into `nin_base_table` in `assemble_nin_base_table`/`run_pipeline`, matching the real final Excel workbook. | SME confirmed (see Open Decision #7): this join has no `.pq` equivalent — the real workbook builds it with a native Excel SUMIFS formula matrix, not Power Query. "week 1" = earliest distinct `Week Ending` date across the *entire* REC output (not calendar/fiscal-relative); `Total Forecast (Qty)` = sum of week 1-27 only (demand beyond week 27 is excluded, not folded in). |
| 2 | Should REC's requirement-type sign be preserved? | **Expose both**: `Adj Req Qty` (absolute, matches current production output exactly) and `Signed Adj Req Qty` (the pre-`Abs()` signed value, for future use / SME review). | Reconciliation (1G) must match production exactly today (always-positive), while not silently discarding the sign logic that appears to have been intended. |
| 3 | Is `VG` guaranteed in the DOH pivot? | **Force all 7 columns** (`WB, PP, U2, VC, VJ, VG, U1`) to default 0 if missing, not just the 6 the current PQ safety net covers. | Fixes a real gap: `build_overview_p2_enriched` expands `VG` unconditionally and would error if it were ever absent. Safer to over-guarantee in the Python port. |
| 4 | Should BOBL's key be upper-cased? | **Yes** — normalize to the same `Upper(Trim(...))` convention as every other group. | Removes a join-miss risk from a casing inconsistency that appears to be an oversight, not a deliberate design choice. |
| 5 | ~~What is MB5T's true header text for the duplicate `Quantity`/`Crcy` columns?~~ **RESOLVED.** | Confirmed: SAP's raw header genuinely repeats `Quantity` and `Crcy` verbatim (no suffix) — `parse_pipe_delimited_sap_export` now renames duplicates to match Power Query's `Table.PromoteHeaders` behavior: the first occurrence of a name is kept as-is, and every subsequent duplicate *anywhere in the row* (not per-name) is suffixed with a single table-wide running counter (`_1`, `_2`, ...). | Confirmed against `docs/design_reference/tbl_tag_sourceplant.csv` reference data and by decoding two real captured exports byte-for-byte: PRDPL3's raw header repeats `BUn` once (→ `BUn`, `BUn_1`, matching `stg_prdpl3_clean.pq`'s expected columns), and MB5T's raw header repeats `Quantity` and `Crcy` (→ `Quantity`, `Quantity_1`, `Crcy`, `Crcy_2` — a *global*, not per-name, counter is required to get `Crcy_2` instead of `Crcy_1`, matching `stg_mb5t_clean.pq` exactly). Regression test: `tests/test_sap_text.py::test_parse_pipe_delimited_sap_export_renumbers_duplicate_headers`. **Correction (this session):** the real raw header's `Amount LC` column does not literally match `stg_mb5t_clean.pq`'s `"Amount in LC"` name, so it is never renamed/type-converted — but it is **not** dropped in real production, since `Table.ReorderColumns(..., MissingField.Ignore)` only reorders the *listed* columns and appends any unlisted column (verified against Microsoft's docs), it does not remove it. An earlier version of this port used a plain column-list filter that *did* silently drop it, which was a real behavioral divergence from production, not a faithful reproduction of a pre-existing bug. Fixed via `reorder_columns_pq_style()` (`sap_text.py`), applied in `clean_mb5t`/`clean_prdpl3`/`enrich_prdpl3`; regression test: `tests/test_mb5t.py::test_clean_mb5t_retains_unmatched_amount_lc_column_appended_at_end`. |
| 6 | Is a duplicate `plant_material_key` possible in PRDPL3? | **Not filtered/deduplicated** — surfaced via `nin_pipeline.validation.reconciliation`'s duplicate-key check instead of silently dropped. | A real captured PRDPL3 export (`runs/20260804_143223/raw/PRDPL3_20260804_084531.csv`) has two rows for `USD1-A2237-04` after cleaning/filtering, both with `DelFlag` blank (neither is soft-deleted). The two rows differ in several fields not obviously derivable from one another (`Basic material` populated on only one; different `PDT`, `GRT`, `Fwd cons.period`, `Standard price`, `Price Un`) — this looks like a genuine SAP extract artifact (e.g. two MRP areas or valuation records for the same plant/material), not a parsing bug. Not yet root-caused; Phase 1E's downstream joins should be reconciled against a real production output before deciding whether/how to dedupe (e.g. keep first, sum, or flag as an error). |
| 7 | Is the true final Excel-facing output identical to `Out_Overview_p2_review.csv` (`nin_base_table`'s current schema)? | **RESOLVED — no, the real final output has more columns, now implemented.** `docs/design_reference/output headers.csv` (confirmed against the `output Excel part 1/2/3.png` screenshots) shows the true final table appends `Total Forecast (Qty)` and `week 1` through `week 27` after `Backlog Qnty`. | User/SME confirmed these columns come from `MRP_ELEMENTS_REC`, transposed by plant-material key and week number via a native Excel SUMIFS formula (not present in any `.pq` file — explains why it wasn't found in `docs/powerquery_m/`). Implemented in `pivot_mrp_elements_rec_weekly` (`mrp_elements_rec.py`) and wired into `assemble_nin_base_table`/`run_pipeline`. See Open Decision #1 (updated). |
| 8 | ~~Does `to_number` correctly parse SAP's negative-number convention?~~ **RESOLVED — fixed a real bug.** SAP exports negative quantities/amounts with a **trailing** minus sign (e.g. `"17-"` meaning `-17`), not a leading one. `to_number()` (`sap_text.py`) now detects and re-signs trailing-minus values before calling `pd.to_numeric`. | Found via a genuine Phase 1G reconciliation: plant DED2's raw MB5T export, cleaned/enriched Python output, and final `nin_base_table` were diffed cell-by-cell against real production output files (`tests/ouput/out_overview_p2_review.csv` = real `out_prdpl3_review` for DED2, 1290 rows; `tests/ouput/overview.csv` = real final base table for DED2, 1143 rows, minus REC weekly columns). Every field matched exactly except `Quantity in Transit` (14/1143 rows) — production showed small negative values (e.g. `-3`, `-5`) for materials with return/reversal MB5T transactions (`S` flag = `E`, `Name 1` = "POC DE Inventory"), while the unfixed port showed `0`/positive because `pd.to_numeric("17-")` silently returned `NaN`, which then summed to 0. After the fix, all 46 shared, non-stub-reference columns between our output and the real DED2 output match exactly (byte-for-byte after normalizing float display precision and Region/top_60/Source Plant, which used empty stub reference data, not real data). Regression test: `tests/test_sap_text.py::test_to_number_handles_sap_trailing_minus_sign`. This also fixes the same latent risk in every other source (`prdpl3`, `mrp_elements_doh`, `mrp_elements_rec`, `bobl`) that shares `to_number`/`to_integer`, even though no other source's real data sample happened to exercise a trailing-minus value. |
| 9 | How should business-user-maintained "tag" tables (`Region`, `Top60`, `Source Plant`, `rec_req_type`, `plant_evaluation`, `BOBL`) be supplied to the Python pipeline? | **Both CSV-folder and single-workbook loading are supported.** These six tables are genuine Excel `Table` (ListObject) objects the SME edits directly inside the workbook (confirmed via `Excel.CurrentWorkbook(){[Name="tbl_Tag_Region"]}` etc. in `docs/powerquery_m/`), not files exported/copy-pasted between runs. `load_reference_data_from_workbook(path)` (`reference_data.py`) opens one `.xlsx` via `openpyxl` and reads each named table by name (case-insensitive match), regardless of which worksheet it lives on, so the SME's existing edit-in-Excel workflow needs zero change. `PipelinePaths` now accepts either `reference_data_folder` (existing CSV convention) or `reference_data_workbook` (new) — `load_config` requires exactly one to be set. `run_pipeline` dispatches to whichever loader matches. | Confirmed real table names (mixed casing preserved intentionally): `tbl_Tag_Region`, `tbl_Tag_Top60`, `tbl_tag_sourceplant`, `rec_req_type`, `plant_evaluation`, `Table_BOBL`. Regression tests: `tests/test_reference_data.py::test_load_reference_data_from_workbook_reads_named_tables_across_sheets` (+ missing-table error case), `tests/test_config.py` (3 tests for the new config option), and an end-to-end pipeline test using the workbook path: `tests/test_pipeline.py::test_run_pipeline_accepts_reference_data_workbook_instead_of_csv_folder`. |

---

## 1. `prdpl3` (standardized + enriched)

Source: `docs/powerquery_m/prdpl3/` — anchor grain for the final base table.

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| plant_material_key | text | no | key | `Plant-Material`, upper/trim, leading zeros stripped from Material |
| Plant | text | no | key | Active evaluation plant (single value per run) |
| Material | text | no | key | SAP material number, leading zeros stripped |
| Material Description | text | yes | | |
| Region | text | yes | | Left-joined from `tbl_tag_region`; null if plant not tagged |
| top_60_flag | text | no | | Left-joined from `tbl_tag_top60`; default `"standard"` if unmatched |
| source_plant | text | no | | Left-joined from `tbl_tag_sourceplant` keyed on normalized `Spec Proc`; default `"None defined"` if unmatched |
| Product hierarchy | text | yes | | Filtered upstream to values starting with `"00020"` |
| Basic material, Basic material 2, MRP Typ, MRP Controller, PuRGrp, DelFlag, MtlSt_XPlt, MtlSt_Plt, X-Chn Mtl St, SG, ProcType, Spec Proc, ABC, MTyp, IPT, PDT, GRT, TRLT, Planning time fence, LotSize, Min. Lot Sze, Rounding val., Max. Lot Size, Fix. lot size, BUn, BUn_1, Consumption mode, Bwd cons. per., Fwd cons.period, BkFlush, PSloc, Language, SLife, Propos.SA, ESLoc, R. Profile, ProdS | text/number (mixed) | yes | | Passed through from SAP export; see `stg_prdpl3_clean.pq` for exact SAP column source |
| Safety Stock, Reorder Point, Threshold Qty | number | yes | | |
| Tot Valuated Stk | number | yes | | Consumed downstream as `Total Stock Quantity` |
| Total Value | number | yes | | Consumed downstream as `Total Value Stock on Hand` |
| Standard price, Price Un | number | yes | | |
| AvaiChk | text | yes | | |

Filters applied before this grain is finalized: active plant only;
`Product hierarchy` starts with `"00020"`.

---

## 2. `mb5t` (standardized + enriched)

Source: `docs/powerquery_m/mb5t/`.

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| plant_material_key | text | no | key | Same convention as PRDPL3 |
| Quantity in Transit | number | no | | `sum(Quantity)` grouped by `plant_material_key`; nulls replaced with 0 |

Note: the raw `stg_mb5t_clean` grain carries many more SAP columns (Pur. Doc.,
Item, SPlt, S, BUn, Amount in LC, Crcy, Quantity_1, OUn, Net Value, Crcy_2,
and a vestigial always-null `Group` column) but they are dropped by the
`enriched`/`review` aggregation and are **not** part of this contract's output
grain. Retain them only if a future detail-level report needs them.

---

## 3. `mm_mrp_elements_doh` (standardized + pivoted)

Source: `docs/powerquery_m/mm_mrp_elements_doh/`.

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| plant_material_key | text | no | key | |
| Material No. | text | no | key | |
| Plant | text | no | key | |
| WB | number | no | | Pivoted requirement-type sum; default 0 |
| PP | number | no | | Pivoted requirement-type sum; default 0 |
| U2 | number | no | | Pivoted requirement-type sum; default 0 |
| VC | number | no | | Pivoted requirement-type sum; default 0 |
| VJ | number | no | | Pivoted requirement-type sum; default 0 |
| VG | number | no | | Pivoted requirement-type sum; default 0 (see Open Decision #3 — force-guaranteed in this contract even though current PQ's safety net omits it) |
| U1 | number | no | | Pivoted requirement-type sum; default 0 |

Row-level rule applied before pivot/grouping: `Adj Req Qty = Req. Qty. / 2`
when `Requirements Type = "BB"`, else unchanged. Rows with
`Requirements Date < as-of date` are dropped upstream (forward-looking only).

---

## 4. `mm_mrp_elements_rec` (standardized + enriched) — weekly grain

Source: `docs/powerquery_m/mm_mrp_elements_rec/`.
**Joined into the final base table** via a downstream transpose step with no
`.pq` equivalent (see Open Decision #1/#7): `pivot_mrp_elements_rec_weekly`
turns this weekly-grain table into one row per `plant_material_key` with
`Total Forecast (Qty)` + `week 1`..`week 27` columns, which
`assemble_nin_base_table` left-joins onto the base table.

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| plant_material_key | text | no | key | |
| Week Ending | date | no | key | Next Friday on/after `Requirements Date` |
| Adj Req Qty | number | no | | Absolute value — matches current production `out_mm_mrp_elements_rec_review` exactly; this is the SUMIFS source column for `week N` |
| Signed Adj Req Qty | number | no | | Pre-`Abs()` signed value using `rec_req_type.negative`; **not** present in current production output — added here per Open Decision #2 for future use/SME review |

Row-level rule: null `Requirements Date` replaced with the file's as-of date;
rows with `Requirements Date < as-of date` dropped.

---

## 5. `bobl` (standardized + enriched)

Source: `docs/powerquery_m/BOBL/`. Source data is a pasted PowerBI matrix
export (`Table_BOBL`), not a SAP flat-file extract.

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| plant_material_key | text | no | key | **Upper-cased** in this contract per Open Decision #4 (current PQ only trims, does not upper-case) |
| Backorder Actual | number | no | | Summed across duplicate key rows |
| Backorder Qnty | number | no | | Summed across duplicate key rows |
| Backlog Actual | number | no | | Summed across duplicate key rows |
| Backlog Qnty | number | no | | Summed across duplicate key rows |

---

## 6. Reference / Tag Tables

| Table | Columns | Join key | Consumed by |
|---|---|---|---|
| `tbl_tag_region` | Plant, Region | Plant | PRDPL3 enrichment |
| `tbl_tag_top60` | plant_material_key, plant, material, top_60_flag | plant_material_key | PRDPL3 enrichment |
| `tbl_tag_sourceplant` | source_key, desc, source_plant | source_key = normalized Spec Proc | PRDPL3 enrichment |
| `rec_req_type` | type, negative | Requirements Type | REC enrichment (sign lookup) |
| `plant_evaluation` | Plant, Evaluate | n/a (single active row) | Every source query — determines the one plant processed per run |
| `stg_sap_t460a` | Plant, Special procurement, Procurement type, ... | unconfirmed | Not observed joined into any current flow; usage unconfirmed — do not port a join until confirmed with SME |

---

## 7. Final Base Table (`nin_base_table` / `build_overview_p2_review`)

Grain: one row per `plant_material_key` (PRDPL3-anchored, active plant,
`Product hierarchy` starting with `"00020"`, `DelFlag = ""`).

| Column | Type | Nullable | Source | Description |
|---|---|---|---|---|
| plant_material_key | text | no | PRDPL3 | key |
| Region | text | yes | PRDPL3 tag join | |
| Plant | text | no | PRDPL3 | |
| Major PG | text | yes | derived | `Text.Middle(Product hierarchy, 3, 2)` |
| Product hierarchy | text | yes | PRDPL3 | |
| Material | text | no | PRDPL3 | |
| Material Description | text | yes | PRDPL3 | |
| Source Plant | text | no | PRDPL3 tag join (renamed from `source_plant`) | |
| Safety Stock | number | yes | PRDPL3 | |
| BUn | text | yes | PRDPL3 | |
| top_60_flag | text | no | PRDPL3 tag join | |
| ABC | text | yes | PRDPL3 | |
| Spec Proc | text | yes | PRDPL3 | |
| ProcType | text | yes | PRDPL3 | |
| TRLT | text/number | yes | PRDPL3 | |
| Total Stock Quantity | number | yes | PRDPL3 (`Tot Valuated Stk`, renamed) | |
| Stocked Status | text | no | derived | `"Yes"` if `Total Stock Quantity > 0` else `"No"` |
| Total Value Stock on Hand | number | yes | PRDPL3 (`Total Value`, renamed) | |
| Basic material | text | yes | PRDPL3 | |
| MRP Typ | text | yes | PRDPL3 | |
| MRP Controller | text | yes | PRDPL3 | |
| DelFlag | text | no | PRDPL3 | filtered to `""` upstream |
| SG | text | yes | PRDPL3 | |
| MTyp | text | yes | PRDPL3 | |
| IPT | text/number | yes | PRDPL3 | |
| PDT | text/number | yes | PRDPL3 | |
| GRT | text/number | yes | PRDPL3 | |
| Planning time fence | number | yes | PRDPL3 | |
| LotSize | text | yes | PRDPL3 | |
| Reorder Point | number | yes | PRDPL3 | |
| Threshold Qty | number | yes | PRDPL3 | |
| AvaiChk | text | yes | PRDPL3 | |
| Standard price | number | yes | PRDPL3 | |
| Price Un | number | yes | PRDPL3 | |
| WB | number | no | DOH join | absolute value |
| VJ | number | no | DOH join | absolute value |
| VC | number | no | DOH join | absolute value |
| VG | number | no | DOH join | absolute value; see Open Decision #3 |
| PP | number | no | DOH join | absolute value |
| U1 | number | no | DOH join | absolute value |
| U2 | number | no | DOH join | absolute value |
| Quantity in Transit | number | no | MB5T join | **not** used in Available Stock/DOH calc (presentation-only today) |
| Available Stock | number | no | derived | `max(0, Total Stock Quantity - (VJ+VC+VG+U1))` |
| Average Monthly Forecast Demand | number | no | derived | `(VJ+PP+U1)/3` |
| DOH | number | no | derived | `0` if forecast `=0` else `(Available Stock / forecast) * 30`; not rounded |
| Backorder Actual | number | yes | BOBL join | |
| Backorder Qnty | number | yes | BOBL join | |
| Backlog Actual | number | yes | BOBL join | |
| Backlog Qnty | number | yes | BOBL join | |

---

## Next Step

Phase 1C (`docs/NIN_Python_Plan.md` §20): build the common SAP-export file
reader (latest-file selection, latest-run-folder selection, dynamic
SAP-header-row detection, pipe/tab delimiter handling) that all five source
transformations in this contract will use.
