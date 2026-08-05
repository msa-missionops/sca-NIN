NIN Python — Summary

Purpose: Replace the Power Query transformation layer with a deterministic Python pipeline that reads SAP raw exports and produces a stable, validated base table consumed by the existing Excel workbook.

Scope (Phase 1): Ingest PRDPL3, MRP_ELEMENTS_REC, MRP_ELEMENTS_DOH, MB5T; standardize, apply business logic, validate, and publish nin_base_table (CSV/XLSX/Parquet).

Primary deliverable: nin_base_table (parquet + Excel/CSV handoff) and reconciliation artifacts.
