# NIN Python Rebuild Plan

## 1. Purpose

This document defines the initial rebuild plan for moving the core NIN data-processing workflow from Excel Power Query into Python.

The immediate objective is **not** to replace the entire NIN process at once.

The first implementation phase will retain:

1. The existing Excel and SAP GUI process that generates the raw SAP extracts.
2. The existing Excel workbook used for final user-facing cleanup, formatting, formulas, and presentation.

Python will initially replace the transformation and consolidation layer between those two existing components.

The working architecture for the first phase is:

```text
Existing Excel / SAP GUI Extraction
                |
                v
        Raw SAP Export Files
                |
                v
       Python Processing Pipeline
                |
                v
      Python-Generated Base Table
                |
                v
 Existing Excel Final Cleanup / User Views
```

The Python application will read the raw SAP exports, perform all required cleansing, joining, aggregation, and NIN business calculations, and publish a stable table that Excel can read as the source for the final user-facing workbook.

---

## 2. Current Project Boundary

### 2.1 Retained for the Initial Phase

The following existing components will remain in place during the first phase:

- Excel VBA SAP extraction orchestration.
- SAP GUI scripting currently launched from Excel.
- Existing transaction execution and export logic.
- Current raw SAP file formats and output folders.
- Current final Excel workbook.
- Existing final Excel cleanup steps that are primarily presentation-oriented.
- Existing user-facing worksheet layout, formulas, pivots, and formatting where they are still needed.

### 2.2 Replaced in the Initial Phase

Python will replace the middle processing layer currently handled primarily through Power Query.

This includes:

- Reading the latest raw SAP exports.
- Removing SAP metadata rows.
- Detecting and promoting headers.
- Standardizing column names.
- Enforcing data types.
- Cleaning materials, plants, quantities, dates, and requirement types.
- Building plant-material keys.
- Filtering invalid or irrelevant rows.
- Applying positive and negative quantity logic.
- Aggregating requirements.
- Pivoting requirement types.
- Merging stock, requirements, in-transit, source-plant, regional, and other reference data.
- Calculating available stock.
- Calculating forecast consumption.
- Calculating days on hand.
- Building the final NIN base table.
- Validating the output before publishing it for Excel.

### 2.3 Deferred Until Later

The following work will be postponed until the Python transformation engine is stable:

- Replacing Excel SAP extraction with Python SAP GUI scripting.
- Replacing the final Excel workbook with a Python-generated workbook.
- Removing all remaining Excel formulas.
- Replacing user-facing Excel controls.
- Automating final workbook publication.
- Migrating source extraction from SAP GUI to Snowflake or another direct source.
- Scheduling or unattended execution.

---

## 3. Phase-One Target Architecture

```text
NIN Excel Orchestrator
    |
    | Generates raw SAP extracts
    v
Configured Raw Extract Folders
    |
    | PRDPL3
    | MRP_ELEMENTS_REC
    | MRP_ELEMENTS_DOH
    | MB5T
    | Supporting reference files
    v
Python NIN Pipeline
    |
    | 1. Locate source files
    | 2. Validate inputs
    | 3. Read raw extracts
    | 4. Standardize schemas
    | 5. Transform each source
    | 6. Build common datasets
    | 7. Merge business model
    | 8. Calculate NIN fields
    | 9. Validate result
    | 10. Publish base table
    v
Python Output
    |
    | CSV, XLSX, or Parquet
    v
Existing NIN Excel Workbook
    |
    | Reads the Python-generated base table
    | Performs final user cleanup and presentation
    v
Final User Report
```

The Python pipeline must be executable independently after the raw SAP files have been created.

The user should be able to rerun the Python transformations without rerunning SAP.

---

## 4. Primary Phase-One Deliverable

The primary deliverable will be a Python-generated table that serves as the authoritative base dataset for the existing Excel report.

A provisional output name is:

```text
nin_base_table.xlsx
```

or:

```text
nin_base_table.csv
```

A parallel Parquet file should also be considered for development, testing, and performance:

```text
nin_base_table.parquet
```

The Excel-facing file and the internal Python file do not need to be the same format.

Recommended approach:

- Use Parquet for intermediate and validated internal datasets.
- Use XLSX or CSV for the file consumed by Excel.
- Treat the Python-generated base table as the formal handoff between the Python process and the final Excel process.

---

## 5. Design Principles

### 5.1 Python Owns the Business Logic

All transformation and calculation logic required to build the NIN base table should reside in Python.

Excel should not be required to reconstruct or repeat core business logic.

### 5.2 Raw Extracts Remain Immutable

Python should not modify the raw SAP exports.

Each source file should be read as an input and preserved unchanged for audit and troubleshooting.

### 5.3 Transformations Should Be Modular

Each SAP source should have its own ingestion and transformation module.

The solution should avoid one large script containing all transformations.

### 5.4 Every Stage Should Be Testable

Individual source-cleaning functions and business calculations should be testable using saved SAP export samples.

### 5.5 Intermediate Results Should Be Inspectable

Python should be able to write intermediate datasets during development and troubleshooting.

### 5.6 Output Should Be Deterministic

The same raw files and configuration should produce the same result.

### 5.7 Excel Is a Consumer

Excel should read the completed Python output rather than participate in its construction.

### 5.8 The Design Should Support Future Extraction Replacement

The initial source will be Excel-generated SAP exports, but the downstream Python model should not depend on how the files were created.

A later Python SAP extraction or Snowflake source should be able to feed the same transformation layer.

---

## 6. Proposed Repository Structure

```text
nin_python/
├── README.md
├── NIN_Python_Plan.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
│
├── config/
│   ├── settings.yaml
│   ├── column_mappings.yaml
│   └── validation_rules.yaml
│
├── src/
│   └── nin_pipeline/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── orchestrator.py
│       ├── configuration.py
│       ├── logging_setup.py
│       ├── run_context.py
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── file_discovery.py
│       │   ├── sap_export_reader.py
│       │   ├── excel_reader.py
│       │   └── schemas.py
│       │
│       ├── transforms/
│       │   ├── __init__.py
│       │   ├── common.py
│       │   ├── prdpl3.py
│       │   ├── mrp_rec.py
│       │   ├── mrp_doh.py
│       │   ├── mb5t.py
│       │   ├── plant_evaluation.py
│       │   ├── source_plant.py
│       │   ├── region.py
│       │   └── requirement_types.py
│       │
│       ├── model/
│       │   ├── __init__.py
│       │   ├── requirements.py
│       │   ├── inventory.py
│       │   ├── in_transit.py
│       │   ├── availability.py
│       │   ├── days_on_hand.py
│       │   └── nin_base_table.py
│       │
│       ├── validation/
│       │   ├── __init__.py
│       │   ├── source_validation.py
│       │   ├── schema_validation.py
│       │   ├── business_validation.py
│       │   └── reconciliation.py
│       │
│       └── output/
│           ├── __init__.py
│           ├── parquet_writer.py
│           ├── csv_writer.py
│           ├── excel_writer.py
│           └── run_summary_writer.py
│
├── reference_data/
│   ├── plant_evaluation.xlsx
│   ├── rec_req_type.xlsx
│   ├── region.xlsx
│   └── source_plant.xlsx
│
├── test_data/
│   ├── raw/
│   └── expected/
│
├── tests/
│   ├── test_prdpl3.py
│   ├── test_mrp_rec.py
│   ├── test_mrp_doh.py
│   ├── test_mb5t.py
│   ├── test_availability.py
│   └── test_nin_base_table.py
│
├── runs/
├── logs/
└── output/
```

This structure can be simplified at the beginning, but the logical separation should remain.

---

## 7. Source Files in Scope

The current Python rebuild should begin with the raw files already generated by the existing Excel process.

### 7.1 PRDPL3

Expected role:

- Material and plant inventory source.
- Safety stock.
- Total stock.
- Stock value.
- Other inventory and planning fields used in the final NIN output.

Likely transformation responsibilities:

- Read the latest file.
- Remove SAP metadata rows.
- Promote headers.
- Normalize material and plant.
- Standardize quantity fields.
- Remove duplicate plant-material rows if required.
- Build `plant_material_key`.
- Retain the fields required by the final NIN model.

### 7.2 MRP_ELEMENTS_REC

Expected role:

- Requirements and receipt elements.
- Forecast, purchase, production, customer, and other MRP element quantities.
- Requirement dates.
- Requirement type classifications.

Known transformation responsibilities:

- Detect the actual header row.
- Rename SAP columns to standard names.
- Convert dates and quantities.
- Replace null requirement dates with the run as-of date where required.
- Filter requirements earlier than the as-of date according to current business rules.
- Remove zero or null quantities.
- Normalize requirement-type text.
- Join to the requirement-type mapping.
- Apply positive or negative signs.
- Aggregate by plant, material, and requirement type.
- Pivot requirement types into columns.
- Build `plant_material_key`.

Known requirement columns may include:

```text
WB
PP
U1
U2
VJ
VC
VG
```

The exact list must be confirmed from the current production transformation.

### 7.3 MRP_ELEMENTS_DOH

Expected role:

- Forward-looking requirements used for days-on-hand calculations.
- Requirement quantities within the configured DOH horizon.
- Requirement-type filtering.

Likely transformation responsibilities:

- Apply the same base cleaning framework as REC.
- Use the DOH-specific date horizon.
- Aggregate required demand by plant and material.
- Produce forecast or demand values used in the DOH calculation.
- Preserve enough detail for reconciliation.

### 7.4 MB5T

Expected role:

- Stock in transit.
- Supplying plant and receiving plant relationships.
- Open stock-transfer quantity.

Likely transformation responsibilities:

- Normalize receiving plant, source plant, and material.
- Standardize in-transit quantity.
- Aggregate by receiving plant and material.
- Build `plant_material_key`.
- Retain source-plant detail if the final report requires it.

### 7.5 Supporting Reference Data

Known supporting data includes:

- Defined set.
- Plant evaluation.
- Requirement-type mapping.
- Region mapping.
- Source-plant mapping.
- Reporting group mapping.
- Any material, plant, or source-plant overrides.

Each reference source should have:

- A defined owner.
- A controlled schema.
- A validation rule.
- A documented join key.
- A stated duplicate-handling rule.

---

## 8. Configuration Strategy

Technical configuration should not be embedded throughout Python code.

A configuration file should define source locations and output locations.

Example:

```yaml
paths:
  prdpl3_folder: "\\\\filer3\\power_bi$\\GSP\\NIN\\output\\PRDPL3"
  mrp_rec_folder: "\\\\filer3\\power_bi$\\GSP\\NIN\\output\\MRP_REC"
  mrp_doh_folder: "\\\\filer3\\power_bi$\\GSP\\NIN\\output\\MRP_DOH"
  mb5t_folder: "\\\\filer3\\power_bi$\\GSP\\NIN\\output\\MB5T"
  reference_data_folder: ".\\reference_data"
  output_folder: ".\\output"
  run_folder: ".\\runs"
  log_folder: ".\\logs"

file_selection:
  strategy: latest_created
  ignore_hidden: true

output:
  write_parquet: true
  write_csv: true
  write_excel: true
```

Configuration should include only technical settings.

Business-managed mappings should remain separate reference files.

---

## 9. File Discovery and Run Selection

The current Power Query pattern generally loads the latest file in each configured folder.

The Python version should initially reproduce that behavior explicitly.

For each source:

1. List all files in the configured folder.
2. Exclude hidden and temporary files.
3. Filter to the expected file extension and naming convention.
4. Select the latest valid file.
5. Record the selected file in the run manifest.
6. Validate that the file is not empty.
7. Validate that the file contains the expected columns after parsing.

The file-selection strategy should be configurable because later designs may use:

- latest file by creation date;
- latest file by modified date;
- filename timestamp;
- explicit run folder;
- explicit file path supplied by the user.

The selected source files must be recorded so the run can be reproduced.

---

## 10. Run Context and Manifest

Every execution should create a unique run identifier.

Example:

```text
20260804_104500
```

Suggested run folder:

```text
runs/
└── 20260804_104500/
    ├── manifest.json
    ├── logs/
    ├── standardized/
    ├── business/
    ├── validation/
    └── output/
```

The run manifest should capture:

```json
{
  "run_id": "20260804_104500",
  "started_at": "2026-08-04T10:45:00-04:00",
  "status": "completed",
  "as_of_date": "2026-08-04",
  "sources": {
    "prdpl3": "\\\\server\\folder\\PRDPL3_20260804.csv",
    "mrp_rec": "\\\\server\\folder\\MRP_REC_20260804.csv",
    "mrp_doh": "\\\\server\\folder\\MRP_DOH_20260804.csv",
    "mb5t": "\\\\server\\folder\\MB5T_20260804.csv"
  },
  "row_counts": {
    "prdpl3_raw": 0,
    "mrp_rec_raw": 0,
    "mrp_doh_raw": 0,
    "mb5t_raw": 0,
    "nin_base_table": 0
  },
  "validation_status": "passed",
  "output_file": ".\\output\\nin_base_table.xlsx"
}
```

---

## 11. Data Processing Layers

The Python pipeline should use distinct logical layers.

### 11.1 Raw Layer

The raw layer represents the source files exactly as read.

No business transformations should occur at this stage.

Responsibilities:

- File discovery.
- File parsing.
- Header detection.
- SAP metadata removal.
- Initial column capture.
- Source filename tagging.
- Raw row counts.

### 11.2 Standardized Layer

The standardized layer creates a stable schema for each source.

Responsibilities:

- Rename columns.
- Trim text.
- Normalize nulls.
- Convert material numbers to text.
- Normalize plant codes.
- Convert date fields.
- Convert quantity fields.
- Normalize decimal and thousands separators.
- Remove clearly invalid rows.
- Build common keys.
- Add source metadata.

Example common columns:

```text
plant
material
plant_material_key
source_file
source_transaction
run_id
```

### 11.3 Business Layer

The business layer applies source-specific and cross-source rules.

Responsibilities:

- Requirement sign logic.
- Requirement-type mapping.
- Requirement aggregation.
- Requirement pivoting.
- Inventory aggregation.
- In-transit aggregation.
- Defined-set filtering.
- Plant and regional enrichment.
- Source-plant logic.
- Available-stock calculation.
- Forecast calculation.
- DOH calculation.

### 11.4 Presentation Base Layer

The presentation base layer produces the table consumed by Excel.

Responsibilities:

- Final joins.
- Final column naming.
- Final column ordering.
- User-friendly null handling.
- Output data typing.
- One row per required report grain.
- Removal of implementation-only fields where appropriate.
- Addition of run metadata fields.

---

## 12. Expected Final Grain

The expected base-table grain should be explicitly confirmed before coding.

The likely grain is:

```text
One row per plant-material combination
```

Primary key:

```text
plant_material_key = Plant + " - " + Material
```

Potential exceptions must be identified:

- Multiple source plants for one receiving plant-material.
- Multiple reporting groups.
- Multiple in-transit sources.
- Materials with multiple planning records.
- Duplicate source records from SAP extracts.
- Materials included in the defined set but absent from one or more source extracts.

The final grain must be stable before the main joins are built.

---

## 13. Initial NIN Base Table Fields

The initial Python base table should aim to reproduce the current source table used by the final Excel cleanup.

A provisional field set is:

```text
plant_material_key
Reporting Group
Major PG
Material
Material Description
Plant
Safety Stock
Total Stock (Qnty)
Total Value of Stock on Hand
Source Plant
DOH
Available Stock
In Transit
```

Additional requirement or calculation columns may include:

```text
WB
PP
U1
U2
VJ
VC
VG
Average Monthly Forecast
Forecast Demand
Adjusted Requirement Quantity
As Of Date
Run ID
Source File Dates
Validation Status
```

The exact field list and order should be derived from the current final Power Query output, not inferred solely from the user-facing workbook.

---

## 14. Core Business Calculations

The current business calculations must be extracted from Power Query and Excel and written as formal definitions.

### 14.1 Plant-Material Key

Provisional definition:

```text
plant_material_key = Plant + " - " + Material
```

Material and plant must first be converted to trimmed text.

### 14.2 Signed Requirement Quantity

The requirement-type mapping determines whether the quantity is positive or negative.

Provisional logic:

```text
signed_quantity = raw_quantity * requirement_type_sign
```

The mapping table must define the sign and the final requirement category.

### 14.3 Available Stock

The current definition must be confirmed.

Possible structure:

```text
available_stock =
    total_stock
    + applicable_receipts
    - applicable_requirements
```

The exact included requirement and receipt types must be documented.

### 14.4 Average Monthly Forecast

A known provisional formula is:

```text
average_monthly_forecast = (VJ + PP + U1) / 3
```

This must be reconciled against the production Power Query logic.

### 14.5 Days on Hand

A known provisional formula is:

```text
DOH =
    0                                      when average_monthly_forecast = 0
    (available_stock / average_monthly_forecast) * 30 otherwise
```

The following must be confirmed:

- Whether negative available stock is allowed.
- Whether DOH may be negative.
- Whether the result is rounded.
- Whether forecast is based on REC, DOH, or both.
- Whether stock in transit is included.
- Whether safety stock is deducted.
- Whether the calculation is calendar-day or fixed 30-day logic.

### 14.6 In-Transit Quantity

Provisional definition:

```text
in_transit = sum(MB5T quantity)
```

The aggregation grain and receiving-plant logic must be confirmed.

---

## 15. Validation Requirements

The Python output should not be passed to Excel until validation succeeds.

### 15.1 Source-Level Validation

For each source:

- File exists.
- File is not empty.
- File extension is valid.
- Expected header row is found.
- Required columns are present.
- Row count is greater than zero where required.
- Quantity columns can be parsed.
- Material and plant fields are not entirely blank.

### 15.2 Standardized-Layer Validation

- Plant values are valid text.
- Material values are valid text.
- Keys are not blank.
- Date conversion failure rate is within tolerance.
- Quantity conversion failure rate is within tolerance.
- Duplicate behavior matches the source design.
- Requirement types map successfully.

### 15.3 Business-Layer Validation

- Final key uniqueness matches the expected grain.
- No unintended many-to-many joins occur.
- Reference tables do not contain duplicate join keys.
- Requirement totals reconcile before and after pivoting.
- MB5T totals reconcile before and after aggregation.
- No source is silently dropped during joins.
- Defined-set materials remain represented where required.

### 15.4 Output Validation

- Final table is not empty.
- Final table contains all required columns.
- Final row count is within a reasonable range.
- Key fields contain no unexpected nulls.
- Numeric columns contain valid numeric values.
- Excel-facing file can be opened.
- Output table name is stable.
- Existing Excel can read the output without manual repair.

---

## 16. Reconciliation Against the Existing Process

The Python pipeline should initially run in parallel with the current Power Query process.

Comparison should occur at multiple levels.

### 16.1 Row-Level Comparison

Compare by `plant_material_key`:

- Missing keys in Python.
- Extra keys in Python.
- Duplicate keys.
- Changed source plant.
- Changed reporting group.
- Changed material description.

### 16.2 Numeric Comparison

Compare:

- Safety stock.
- Total stock.
- Stock value.
- In-transit quantity.
- Requirement quantities.
- Available stock.
- Forecast.
- DOH.

### 16.3 Aggregate Comparison

Compare totals by:

- Plant.
- Reporting group.
- Major product group.
- Source plant.
- Region.
- Requirement type.

### 16.4 Difference Output

Python should generate a reconciliation file.

Example:

```text
nin_reconciliation.xlsx
```

Suggested tabs:

```text
Summary
Missing in Python
Missing in Current
Value Differences
Duplicate Keys
Validation Results
```

---

## 17. Logging

The Python pipeline should use structured logging.

Minimum log content:

- Run ID.
- Start and end time.
- Selected source files.
- Source row counts.
- Standardized row counts.
- Aggregated row counts.
- Join row counts.
- Duplicate counts.
- Unmapped requirement types.
- Missing reference mappings.
- Validation warnings.
- Validation failures.
- Output file paths.
- Final execution status.

Logs should be written both to the console and to a run-specific log file.

---

## 18. Error Handling

The pipeline should fail clearly rather than publish a partially valid table.

Examples of hard failures:

- Required source file missing.
- Required source column missing.
- Input file unreadable.
- Reference table contains duplicate keys where uniqueness is required.
- Final output is empty.
- Final primary key is not unique.
- Required requirement types are unmapped.
- Output file cannot be written.

Examples of warnings:

- Optional reference mapping missing.
- Row count differs moderately from the previous run.
- A small number of invalid dates were converted to null.
- Optional source contains no rows.
- Material description is missing for a limited number of records.

Warnings and failures should be summarized in the run manifest.

---

## 19. Execution Interface

The first version can use a command-line entry point.

Example:

```bash
python -m nin_pipeline run
```

Optional parameters:

```bash
python -m nin_pipeline run --as-of-date 2026-08-04
python -m nin_pipeline run --config config/settings.yaml
python -m nin_pipeline transform-only
python -m nin_pipeline validate-only
python -m nin_pipeline reconcile
```

The initial implementation should support transformation-only execution because the raw SAP files are created externally.

A later Excel button may call the Python command, but Python should remain independently executable.

---

## 20. Proposed Development Sequence

### Phase 1A — Inventory the Existing Transformation Logic

Tasks:

1. Identify every current Power Query used in the NIN middle layer.
2. Classify each query as source, transformation, reference, support, or final.
3. Document its input and output.
4. Record all column renames.
5. Record all filters.
6. Record all joins.
7. Record all custom calculations.
8. Record the final query grain.
9. Identify logic still performed in Excel formulas.
10. Separate presentation-only logic from core business logic.

Deliverable:

```text
docs/current_state_transformation_inventory.md
```

### Phase 1B — Define Data Contracts

Tasks:

1. Define raw source schemas.
2. Define standardized schemas.
3. Define reference table schemas.
4. Define the final base-table schema.
5. Confirm the primary key.
6. Confirm the as-of-date rule.
7. Confirm file-selection rules.
8. Confirm calculation formulas.

Deliverable:

```text
docs/nin_data_contracts.md
```

### Phase 1C — Build Common File Reader

Tasks:

1. Implement latest-file selection.
2. Implement SAP metadata-row removal.
3. Implement header detection.
4. Implement tab-delimited and CSV parsing.
5. Implement standard source metadata fields.
6. Implement basic file validation.

Deliverable:

```text
src/nin_pipeline/ingestion/
```

### Phase 1D — Build Source Transformations

Recommended order:

1. PRDPL3.
2. MB5T.
3. MRP_ELEMENTS_REC.
4. MRP_ELEMENTS_DOH.
5. Reference mappings.

Each source transformation should produce a validated Parquet output.

### Phase 1E — Build the Business Model

Tasks:

1. Establish the plant-material base population.
2. Merge inventory.
3. Merge requirements.
4. Merge DOH demand.
5. Merge in-transit stock.
6. Merge source plant.
7. Merge region and reporting mappings.
8. Calculate available stock.
9. Calculate forecast.
10. Calculate DOH.
11. Produce the final ordered table.

### Phase 1F — Build Excel Handoff Output

Tasks:

1. Confirm the format preferred by the existing Excel workbook.
2. Write the base table to XLSX, CSV, or both.
3. Use a stable file path and table name.
4. Ensure the existing Excel query can refresh from the file.
5. Preserve numeric and date data types.
6. Add run metadata.

### Phase 1G — Reconciliation

Tasks:

1. Run the current Power Query process.
2. Run the Python process from the same raw files.
3. Compare outputs.
4. Investigate all material differences.
5. Document accepted differences.
6. Repeat until stable.

### Phase 1H — Cutover of the Middle Layer

Tasks:

1. Point the existing final Excel workbook to the Python base table.
2. Retain the old Power Query logic temporarily as a fallback.
3. Run side-by-side for an agreed validation period.
4. Retire the old middle-layer queries after signoff.

---

## 21. Initial Milestones

### Milestone 1 — Current-State Mapping Complete

Success criteria:

- Every current transformation query is documented.
- The final Power Query output schema is documented.
- The expected final grain is confirmed.
- All business formulas are identified.

### Milestone 2 — Source Readers Complete

Success criteria:

- Python reads all four primary SAP exports.
- Latest-file logic matches the current process.
- Source schemas are validated.
- Clean source datasets can be written to Parquet.

### Milestone 3 — Core Transformations Complete

Success criteria:

- REC and DOH logic is reproduced.
- Requirement types are mapped and pivoted.
- PRDPL3 and MB5T are aggregated correctly.
- Supporting mappings are integrated.

### Milestone 4 — Base Table Complete

Success criteria:

- Python generates one stable NIN base table.
- Final key uniqueness is validated.
- Required output columns are present.
- Excel can read the file.

### Milestone 5 — Reconciliation Complete

Success criteria:

- Python and current Power Query outputs reconcile.
- Remaining differences are understood and documented.
- No unexplained material variances remain.

### Milestone 6 — Middle-Layer Cutover Complete

Success criteria:

- Final Excel workbook consumes the Python base table.
- Existing user-facing workflow continues to function.
- Old transformation queries are no longer required for production.

---

## 22. Testing Strategy

### 22.1 Unit Tests

Create unit tests for:

- Header detection.
- Material normalization.
- Plant normalization.
- SAP date parsing.
- SAP numeric parsing.
- Plant-material key creation.
- Requirement sign assignment.
- Requirement pivoting.
- Available-stock calculation.
- DOH calculation.

### 22.2 Source Fixture Tests

Store small representative source files in `test_data/raw`.

Each fixture should include:

- Valid rows.
- Blank values.
- Duplicate rows.
- Invalid dates.
- Zero quantities.
- Unmapped requirement types.
- Multiple source plants.
- Missing reference mappings.

### 22.3 Golden Output Tests

Store expected transformed outputs in `test_data/expected`.

A test should confirm that a fixed set of source files produces the expected result.

### 22.4 Regression Tests

After each logic change:

- Reprocess a known production snapshot.
- Compare the new result to the prior validated output.
- Review all changed records.

---

## 23. Technology Recommendations

Initial recommended stack:

```text
Python
pandas
openpyxl
pyarrow
PyYAML
pytest
```

Purpose:

- `pandas`: tabular transformations.
- `openpyxl`: Excel input and output.
- `pyarrow`: Parquet support.
- `PyYAML`: configuration files.
- `pytest`: automated tests.

Potential later additions:

- `pydantic` for configuration and schema validation.
- `pandera` for DataFrame schema validation.
- `typer` for a cleaner command-line interface.
- `xlsxwriter` for advanced Excel output.
- `polars` if performance requires it.

The first version should favor clarity and maintainability over adding unnecessary frameworks.

---

## 24. Immediate Next Steps

The next work should focus on documenting and reproducing the existing middle-layer behavior.

Recommended order:

1. Identify the current final Power Query that feeds the user-facing Excel process.
2. Capture its exact output columns and data types.
3. List every upstream query required to build it.
4. Save one complete set of raw SAP extracts as a fixed development snapshot.
5. Save the current Power Query output from the same snapshot.
6. Create the Python repository and virtual environment.
7. Implement the common SAP-export reader.
8. Rebuild PRDPL3 first.
9. Rebuild MB5T second.
10. Rebuild REC and DOH after the basic ingestion pattern is stable.
11. Build the final merge and calculation layer.
12. Reconcile Python output against the saved Power Query output.

---

## 25. Phase-One Definition of Done

The first phase is complete when:

- The existing Excel process continues to generate the SAP raw files.
- Python reads those files without Power Query.
- Python performs the complete middle-layer transformation.
- Python writes a stable NIN base table.
- The existing final Excel workbook reads that table.
- Core business logic no longer depends on Power Query.
- Python output reconciles to the existing process.
- Run logs and validation results are available.
- The Python process can be rerun without rerunning SAP.
- SAP extraction and final Excel presentation remain available for later migration phases.

---

## 26. Future Phases

### Future Phase 2 — Replace SAP Extraction

Python will replace the Excel VBA SAP extraction process.

Potential scope:

- SAP GUI COM session attachment.
- Transaction-specific Python modules.
- Input-list generation.
- SAP export verification.
- Retry and timeout handling.
- Run-level extraction logging.

### Future Phase 3 — Replace Final Excel Cleanup

Python will generate the final formatted Excel workbook directly.

Potential scope:

- Template-driven workbook output.
- User views.
- Summary tables.
- Exception tabs.
- Conditional formatting.
- Charts and pivots.
- Production publishing.

### Future Phase 4 — Replace SAP GUI Sources

Potential direct sources:

- Snowflake object-layer tables.
- SAP BW sources.
- Direct database extracts.
- Controlled APIs or scheduled enterprise data feeds.

The downstream Python data model should remain stable as source methods change.

---

## 27. Working Project Statement

The NIN Python rebuild will initially replace only the transformation and consolidation layer.

The current Excel and SAP GUI process will continue to generate raw SAP extracts. Python will read those extracts, build the complete validated NIN base table, and publish that table for the existing Excel workbook to consume.

SAP extraction and final Excel presentation will be migrated only after the Python middle layer is proven, reconciled, and stable.
