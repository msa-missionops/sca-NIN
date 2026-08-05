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
