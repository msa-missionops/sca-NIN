# Docs Index

Files:

- NIN_Python_Plan.md — full plan (single-file canonical source)
- nin_data_contracts.md — Phase 1B data contracts: confirmed schemas for every source/output, derived from NIN_Python_Plan.md sections 7.6/14
- current_state_transformation_inventory.md — index into docs/powerquery_m/ query files and their role
- plan_todos.md — tracked todos exported from the session tracker
- summary.md — concise project purpose, scope, and primary deliverable
- milestones.md — Phase-1 milestones and success criteria
- thoughts.doc — raw notes (binary/doc)

Use summary.md for a quick onboarding; use NIN_Python_Plan.md for detailed design and implementation steps; use nin_data_contracts.md as the schema reference when implementing Phase 1C+.

## design_reference/

Drop screenshots, diagrams (`.jpeg`/`.gif`/`.png`), sample production
outputs (Excel/CSV snippets), or any other reference material that helps
confirm the design here. These are small, human-authored reference files
and are meant to be committed to git (unlike `runs/`, `test_data/raw/`,
which hold large raw SAP exports and are gitignored). If a file is large
(multi-MB raw export, video, etc.), put it under `test_data/raw/` or
`runs/` instead and only commit a note here describing what it shows and
where it lives locally.
