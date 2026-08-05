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
| 1 | Is REC weekly output in scope for Phase 1? | **Contract defined, but excluded from the final base table join.** | Matches current production: REC is not joined into `build_overview_p2_review` today. Keeps Phase 1 scope identical to the current Excel-facing output. Revisit if a forecast-trend view needs it later (Future Phase). |
| 2 | Should REC's requirement-type sign be preserved? | **Expose both**: `Adj Req Qty` (absolute, matches current production output exactly) and `Signed Adj Req Qty` (the pre-`Abs()` signed value, for future use / SME review). | Reconciliation (1G) must match production exactly today (always-positive), while not silently discarding the sign logic that appears to have been intended. |
| 3 | Is `VG` guaranteed in the DOH pivot? | **Force all 7 columns** (`WB, PP, U2, VC, VJ, VG, U1`) to default 0 if missing, not just the 6 the current PQ safety net covers. | Fixes a real gap: `build_overview_p2_enriched` expands `VG` unconditionally and would error if it were ever absent. Safer to over-guarantee in the Python port. |
| 4 | Should BOBL's key be upper-cased? | **Yes** — normalize to the same `Upper(Trim(...))` convention as every other group. | Removes a join-miss risk from a casing inconsistency that appears to be an oversight, not a deliberate design choice. |

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
**Not currently joined into the final base table** (see Open Decision #1).
Defined here so the contract exists if/when it is brought into scope.

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| plant_material_key | text | no | key | |
| Week Ending | date | no | key | Next Friday on/after `Requirements Date` |
| Adj Req Qty | number | no | | Absolute value — matches current production `out_mm_mrp_elements_rec_review` exactly |
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
