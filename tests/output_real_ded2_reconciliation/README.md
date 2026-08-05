# Real Production Reconciliation Fixture (Plant DED2)

These two CSVs are **real production output**, captured directly from the
current Power Query / Excel middle layer for plant `DED2`, provided by the
user for Phase 1G reconciliation. They are committed deliberately (with the
user's explicit consent) as a permanent ground-truth fixture, since they
already found and helped fix one real bug (see below).

## Files

- `out_overview_p2_review.csv` — real `out_prdpl3_review` output (the
  cleaned + enriched PRDPL3 stage), 1,290 rows, 53 columns. Despite its
  filename, this is **not** the final `build_overview_p2_review` table --
  its column set matches `docs/design_reference/out_prdpl3_review.csv`'s
  schema exactly (PRDPL3-specific fields like `MtlSt_XPlt`, `PuRGrp`,
  `Consumption mode`, `PSloc`, etc. that never reach the final base table).
- `overview.csv` — real final base table (`nin_base_table` /
  `build_overview_p2_review` equivalent), 1,143 rows, 49 columns. Missing
  `Total Forecast (Qty)`/`week 1`..`week 27` (the REC weekly columns) --
  per the user, the real Excel workbook builds those with a native SUMIFS
  formula matrix that isn't captured in this particular export.

## What this fixture proved (2026-08-05 reconciliation)

Running the Python pipeline against the matching real raw SAP exports for
plant DED2 (`runs/20260804_143223/raw/...`, gitignored/local-only, not
committed) and diffing cell-by-cell against these two files found:

- **Enriched PRDPL3 stage**: exact match on row count (1,290), keys, column
  order, and every field except `Material Description` (5 rows) -- which
  is a display-only Unicode-vs-`?` mojibake artifact in *this* real export,
  not a defect in the Python port (ours preserves the correct `–`/`×`
  characters).
- **Final base table**: exact match on row count (1,143), keys, and every
  shared column **except** `Quantity in Transit` (14 rows) -- which
  uncovered a real bug: SAP encodes negative quantities/amounts with a
  **trailing** minus sign (e.g. `"17-"` meaning `-17`, seen on MB5T
  return/reversal transactions), which the shared `to_number()` helper
  (`src/nin_pipeline/sources/sap_text.py`) silently parsed as `NaN` (then
  summed to 0). Fixed by re-signing trailing-minus values before calling
  `pd.to_numeric`; regression test:
  `tests/test_sap_text.py::test_to_number_handles_sap_trailing_minus_sign`.
  After the fix, `Quantity in Transit` (and every other shared, non-stub
  column) matches exactly.
- `Region`, `top_60_flag`, and `Source Plant` were *not* compared for exact
  match -- the reconciliation run used empty-stub reference data (no real
  `region.csv`/`top60.csv` exists yet), so these are expected to differ
  until real reference data is available.

## Reproducing this reconciliation

The real raw SAP exports needed to reproduce this comparison are not
committed (sensitive, gitignored under `runs/`). If you have access to a
fresh capture for plant DED2, point a `settings.yaml` at it (see
`docs/NIN_Python_Plan.md` section 8), run
`python -m nin_pipeline run --config settings.yaml`, and diff the resulting
`nin_base_table.csv` against `overview.csv` in this folder (and the
enriched-PRDPL3 stage against `out_overview_p2_review.csv`), excluding the
`Region`/`top_60_flag`/`Source Plant` columns and normalizing float display
precision.
