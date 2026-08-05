Phase-1 Milestones

1. Current-State Mapping Complete
   - Document all Power Query transformations; confirm final schema and grain.

2. Source Readers Complete
   - Python reads primary SAP exports and writes standardized Parquet outputs.

3. Core Transformations Complete
   - REC and DOH logic reproduced; PRDPL3 and MB5T aggregated correctly.

4. Base Table Complete
   - Python generates the stable NIN base table; Excel can read it.

5. Reconciliation Complete
   - Python and Power Query outputs reconcile; differences documented.

6. Middle-Layer Cutover Complete
   - Final Excel workbook consumes Python output; old queries retired.
