CONTRIBUTING — Solo maintainer guidelines

Purpose
- Short guide for a single-maintainer workflow and minimal guardrails so development stays predictable and reproducible.

Policy
- This repository is maintained by a single maintainer. Direct pushes to main are allowed to minimize overhead.
- CI (GitHub Actions) runs on push and PRs. Ensure tests and linters pass locally before pushing.

Local development
- Create and activate venv (if not already): python -m venv .venv && source .venv/bin/activate
- Install deps: .venv/bin/pip install -r requirements.txt
- Run tests: .venv/bin/pytest -q
- Lint: .venv/bin/ruff check .
- Format check (optional): .venv/bin/black --check .

Snapshots (raw SAP data)
- Add raw exports manually under test_data/raw or provide a directory to scripts/save_snapshot.py
- Capture a snapshot: .venv/bin/python scripts/save_snapshot.py --copy-all-dir /path/to/raw_folder
- To record an existing run: .venv/bin/python scripts/record_snapshot.py --run-id 20260804_143223

Issues & tasks
- Use the provided issue templates for bugs/features. Convert docs/plan_todos.md items into issues for tracking.
- When working on a todo, reference the issue number in commits and PRs (e.g., "Fix X (#3)").

Commits & PRs
- Keep commit messages short and descriptive. PRs are optional for direct pushes but useful for historical context.

Notes
- If you want stricter policies later (required PRs, branch protection, code owners with review), add them via .github settings.

Thank you — reach out via GitHub issues for questions or changes to these guidelines.
