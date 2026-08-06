# Maintain Git Repository

## 1. Purpose

This guide defines how to set up, use, maintain, and deploy the Git repository for the NIN Python project.

The working environment is:

```text
Development
- WSL Debian
- VS Code
- Python virtual environment
- Copilot CLI available
- Git in WSL
- Work GitHub accessed through HTTPS and corporate SSO

Production
- Windows 11 workstation
- Git for Windows
- Python runtime
- No Copilot CLI dependency
- Approved code pulled from the same GitHub repository
```

Copilot CLI is a development aid only. It is not part of the application runtime and is not required in production.

---

## 2. Repository Responsibilities

The Git repository is the controlled source of truth for:

- Python source code
- tests
- project documentation
- non-sensitive configuration templates
- dependency definitions
- release history
- deployment versions

The repository must not be used to store:

- production SAP extracts
- customer-sensitive data
- generated Excel reports
- passwords, tokens, or credentials
- local virtual environments
- production logs
- run folders
- production-only configuration containing sensitive values

---

## 3. Recommended Repository and Folder Names

Recommended repository name:

```text
nin-python
```

Recommended WSL development path:

```text
~/dev_work/projects/nin-python
```

Recommended Windows production path:

```text
C:\NIN\nin-python
```

Recommended production support folders:

```text
C:\NIN\config
C:\NIN\data
C:\NIN\logs
C:\NIN\output
C:\NIN\runs
```

Suggested production layout:

```text
C:\NIN\
├── nin-python\       Version-controlled source
├── config\           Production configuration
├── data\             Inputs and reference data
├── logs\             Runtime logs
├── output\           Python-generated NIN base table
└── runs\             Run manifests and intermediates
```

Keep production data and configuration separate from the Git working tree.

---

## 4. Authentication Model

The expected authentication method is:

```text
HTTPS
+
Corporate browser-based SSO
+
Git Credential Manager
```

SSH keys are not required for this setup.

The flow is:

```text
WSL Git
    |
    v
Git Credential Manager for Windows
    |
    v
Corporate browser SSO
    |
    v
Work GitHub repository
```

Use the exact HTTPS clone URL shown by the work GitHub repository.

It may resemble:

```text
https://github.com/<organization>/nin-python.git
```

or:

```text
https://github.<company-domain>/<organization>/nin-python.git
```

---

## 5. Initial Git Setup in WSL Debian

### 5.1 Install Git

```bash
sudo apt update
sudo apt install -y git ca-certificates
```

Verify:

```bash
git --version
```

### 5.2 Configure Git Identity

Use the name and work email associated with the corporate GitHub account:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.work.email@company.com"
```

Recommended settings:

```bash
git config --global init.defaultBranch main
git config --global core.autocrlf input
git config --global pull.ff only
git config --global fetch.prune true
```

Review:

```bash
git config --global --list
```

---

## 6. Configure Git Credential Manager for WSL

First test whether Git Credential Manager is already available:

```bash
git credential-manager --version
```

If it works, continue to cloning the repository.

If it is not found, configure WSL Git to call the credential manager installed with Git for Windows:

```bash
git config --global credential.helper   "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe"
```

Confirm:

```bash
git config --global --get credential.helper
```

The Windows executable path can vary. To locate it from Windows Command Prompt:

```bat
where git-credential-manager
```

or:

```bat
where git-credential-manager-core
```

A common alternative path is:

```text
C:\Program Files\Git\mingw64\bin\git-credential-manager-core.exe
```

Convert the Windows path to the corresponding WSL path when configuring the helper.

Example:

```bash
git config --global credential.helper   "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager-core.exe"
```

---

## 7. Clone the Repository in WSL

From the GitHub repository page:

```text
Code
→ HTTPS
→ Copy
```

Then run:

```bash
mkdir -p ~/dev_work/projects
cd ~/dev_work/projects

git clone https://<github-host>/<organization>/nin-python.git
cd nin-python
```

The first authenticated operation may open a Windows browser. Complete the corporate SSO flow.

Verify:

```bash
git status
git remote -v
```

Expected remote:

```text
origin  https://<github-host>/<organization>/nin-python.git (fetch)
origin  https://<github-host>/<organization>/nin-python.git (push)
```

---

## 8. Creating the Project Before the Remote Repository Exists

Create the local project:

```bash
mkdir -p ~/dev_work/projects/nin-python
cd ~/dev_work/projects/nin-python

git init
git branch -M main
```

After the GitHub repository is created:

```bash
git remote add origin   https://<github-host>/<organization>/nin-python.git
```

Verify:

```bash
git remote -v
```

After the first commit:

```bash
git push -u origin main
```

If direct pushes to `main` are blocked, push a feature branch instead.

---

## 9. Recommended Repository Structure

```text
nin-python/
├── README.md
├── NIN_Python_Plan.md
├── maintain git repo.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .gitignore
├── .gitattributes
│
├── config/
│   ├── settings.example.yaml
│   └── validation_rules.yaml
│
├── docs/
│   ├── current_state_transformation_inventory.md
│   ├── nin_data_contracts.md
│   └── deployment_guide.md
│
├── src/
│   └── nin_pipeline/
│
├── tests/
│
├── test_data/
│   ├── raw/
│   └── expected/
│
└── scripts/
    ├── run_nin_dev.sh
    └── run_nin_production.bat
```

Production configuration should remain outside the repository:

```text
C:\NIN\config\production.yaml
```

The repository should contain only a safe template:

```text
config/settings.example.yaml
```

---

## 10. Recommended `.gitignore`

Create `.gitignore` in the repository root:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyd
*.so

# Virtual environments
.venv/
venv/
env/

# Tests and analysis
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml
htmlcov/

# Build output
build/
dist/
*.egg-info/

# Editors
.vscode/
.idea/

# Local environment files
.env
.env.*
!.env.example

# Local and production configuration
config/development.local.yaml
config/production.yaml
config/*.local.yaml

# Runtime output
runs/
logs/
output/
data/raw/
data/processed/

# Production data formats
*.xls
*.xlsm
*.csv
*.parquet

# Explicitly permit approved templates and fixtures
!templates/*.xlsx
!test_data/**/*.csv
!test_data/**/*.parquet

# Excel temporary files
~$*.xlsx
~$*.xlsm
~$*.xls

# Temporary and OS files
*.tmp
*.temp
*.bak
.DS_Store
Thumbs.db
desktop.ini
```

Review the broad CSV, Excel, and Parquet exclusions. Use explicit exceptions only for sanitized test fixtures and approved templates.

Before committing:

```bash
git status
git diff --cached --name-only
```

---

## 11. Files That Must Not Be Committed

Never commit:

- GitHub tokens
- SSO tokens
- passwords
- SAP credentials
- `.env` files containing secrets
- production SAP extracts
- customer-sensitive data
- actual production reports
- local `.venv` folders
- production logs
- generated output
- run folders
- production-only configuration
- temporary Excel lock files

For test fixtures:

- use synthetic data where possible
- reduce row counts
- remove customer information
- mask sensitive values
- confirm that repository storage is permitted

---

## 12. Line Ending Control

Development occurs in Linux through WSL, while production runs on Windows.

Recommended WSL setting:

```bash
git config --global core.autocrlf input
```

Create `.gitattributes`:

```gitattributes
* text=auto

*.py text eol=lf
*.md text eol=lf
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
*.sh text eol=lf

*.bat text eol=crlf
*.cmd text eol=crlf
*.ps1 text eol=crlf

*.xlsx binary
*.xlsm binary
*.parquet binary
```

This prevents inconsistent line endings between WSL and Windows.

---

## 13. Python Virtual Environment

Create the development environment locally:

```bash
cd ~/dev_work/projects/nin-python
python3 -m venv .venv
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install dependencies:

```bash
pip install -r requirements-dev.txt
```

The `.venv` folder must remain excluded from Git.

---

## 14. Dependency Files

### `requirements.txt`

Runtime packages only:

```text
pandas
openpyxl
pyarrow
PyYAML
```

### `requirements-dev.txt`

Development tools:

```text
-r requirements.txt
pytest
ruff
mypy
```

Before production deployment, pin the tested versions.

Example:

```text
pandas==<tested-version>
openpyxl==<tested-version>
pyarrow==<tested-version>
PyYAML==<tested-version>
```

Use:

```bash
pip freeze
```

to inspect installed versions. Do not automatically replace `requirements.txt` with every package returned by `pip freeze` unless that is the selected dependency strategy.

---

## 15. Branch Strategy

Use a simple branch model.

### Main branch

```text
main
```

Purpose:

- stable code
- reviewed changes
- release-ready source
- basis for production releases

Do not use `main` for experimental work.

### Feature branches

Examples:

```text
feature/nin-python-foundation
feature/prdpl3-ingestion
feature/mb5t-transform
feature/mrp-rec-transform
feature/nin-base-table
```

Create one:

```bash
git switch main
git pull --ff-only
git switch -c feature/prdpl3-ingestion
```

### Fix branches

Examples:

```text
fix/mb5t-duplicate-key
fix/sap-date-parsing
fix/output-column-order
```

---

## 16. Daily Development Workflow

Start the session:

```bash
cd ~/dev_work/projects/nin-python
source .venv/bin/activate

git status
git fetch origin
git pull --ff-only
git branch --show-current
```

Review changes:

```bash
git status
git diff
```

Run tests:

```bash
pytest
```

Stage selected files:

```bash
git add <file-or-folder>
```

Review staged changes:

```bash
git diff --cached
```

Commit:

```bash
git commit -m "Add PRDPL3 source ingestion"
```

Push:

```bash
git push
```

First push of a new branch:

```bash
git push -u origin feature/prdpl3-ingestion
```

---

## 17. Commit Standards

Use clear action-oriented messages.

Good examples:

```text
Initialize NIN Python project structure
Add latest-file discovery for SAP exports
Add PRDPL3 schema validation
Implement MB5T in-transit aggregation
Add NIN reconciliation output
Fix duplicate plant-material records
Document production deployment
```

Avoid:

```text
update
changes
fix stuff
work
test
```

A good commit should:

- represent one coherent change
- avoid unrelated files
- pass applicable tests
- contain no generated data
- contain no secrets
- be understandable from the message and diff

---

## 18. Pull Request Workflow

Recommended flow:

```text
Feature branch
    |
    v
Push to GitHub
    |
    v
Open pull request
    |
    v
Review and checks
    |
    v
Merge to main
```

Before opening a pull request:

```bash
git status
git fetch origin
git rebase origin/main
pytest
git push
```

If a previously pushed branch was rebased:

```bash
git push --force-with-lease
```

Use `--force-with-lease`, not plain `--force`.

The pull request should state:

- what changed
- why it changed
- affected source or calculation
- how it was tested
- expected output differences
- configuration changes
- deployment implications

---

## 19. Updating a Feature Branch

Rebase onto current `main`:

```bash
git switch feature/prdpl3-ingestion
git fetch origin
git rebase origin/main
```

Resolve conflicts, then:

```bash
git add <resolved-file>
git rebase --continue
```

Abort if necessary:

```bash
git rebase --abort
```

If the work team requires merge commits instead:

```bash
git merge origin/main
```

Follow the repository's established policy.

---

## 20. Release Tags

Production should use an identified release rather than an arbitrary development commit.

Recommended format:

```text
v0.1.0
v0.2.0
v0.2.1
v1.0.0
```

Interpretation:

```text
v0.1.0  Initial development release
v0.2.0  New functionality
v0.2.1  Bug fix
v1.0.0  First approved production release
```

Create an annotated tag:

```bash
git switch main
git pull --ff-only

git tag -a v0.1.0 -m "NIN Python initial transformation release"
git push origin v0.1.0
```

Inspect tags:

```bash
git tag --list
git show v0.1.0
```

---

## 21. Initial Production Setup on Windows 11

From Command Prompt or Git Bash:

```bat
mkdir C:\NIN
cd C:\NIN

git clone https://<github-host>/<organization>/nin-python.git
cd nin-python
```

Complete browser SSO when prompted.

Verify:

```bat
git remote -v
git status
```

Production should not be used for normal code development.

Do not edit tracked Python files directly on the production workstation.

---

## 22. Deploying a Release to Production

Recommended deployment:

```bat
cd C:\NIN\nin-python

git status
git fetch --all --tags
git checkout v0.1.0
```

A tag checkout creates a detached `HEAD`, which is acceptable for a read-only deployment.

Confirm:

```bat
git describe --tags --exact-match
git rev-parse HEAD
git status
```

The NIN run manifest should eventually record:

- release tag
- commit hash
- Python version
- configuration path
- source files
- run timestamp

---

## 23. Invoking WSL-Resident Scripts from Windows 11

Development happens inside WSL Debian, but production execution happens on the Windows 11 workstation. These are two different filesystems, and Windows does not natively resolve Linux paths such as `/home/<user>/nin-python`.

The recommended deployment model in this document is to `git clone` a dedicated copy of the repository directly on Windows (see Section 21/22), so production runs entirely against a native Windows path such as `C:\NIN\nin-python`. Use this model whenever possible.

If a script, scheduled task, or batch file on Windows must instead call a Python script or entry point that still physically resides inside the WSL filesystem (rather than a separate Windows-native clone), reference it through the WSL UNC network path, not a drive letter or POSIX path:

```text
\\wsl$\Debian\home\<user>\nin-python\run_nin_production.bat
```

or, on newer WSL versions where `\\wsl$` has been superseded:

```text
\\wsl.localhost\Debian\home\<user>\nin-python\run_nin_production.bat
```

Notes:

- Replace `Debian` with the exact WSL distribution name reported by `wsl -l -v` from Windows.
- These UNC paths only resolve while the WSL virtual machine is running (invoking them from Windows Explorer or a script will auto-start it, but scheduled tasks may need an explicit `wsl.exe` warm-up step).
- Do not hardcode `\\wsl$\...` paths into committed configuration files or the application itself; keep them in local, uncommitted Windows launch scripts or Task Scheduler actions only.
- Prefer invoking the interpreter explicitly rather than relying on a shebang, for example:

```bat
\\wsl$\Debian\home\<user>\nin-python\.venv\bin\python ^
  -m nin_pipeline run ^
  --config C:\NIN\config\production.yaml
```

- Mixed-path execution (Windows-triggered, WSL-resident code) is acceptable for ad hoc or support use, but it is not the primary production path. The dedicated Windows clone described in Sections 21–22 remains the recommended production layout because it avoids depending on WSL being installed and running on the production workstation.

---

## 24. Production Python Environment

Create the production virtual environment:

```bat
cd C:\NIN\nin-python
py -m venv .venv
.venv\Scripts\activate
```

Install runtime dependencies:

```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copilot CLI and development-only packages are not required.

Run the application using the external production configuration:

```bat
C:\NIN\nin-python\.venv\Scripts\python.exe ^
  -m nin_pipeline run ^
  --config C:\NIN\config\production.yaml
```

---

## 25. Production Configuration

Keep production configuration outside Git:

```text
C:\NIN\config\production.yaml
```

Commit only a safe example:

```text
config/settings.example.yaml
```

This prevents deployment operations from overwriting production paths and local settings.

Do not use `git update-index --assume-unchanged` as the main method of protecting production configuration. It creates hidden local state that is easy to forget.

---

## 26. Rollback Procedure

To roll back:

```bat
cd C:\NIN\nin-python
git fetch --all --tags
git checkout v0.0.9
```

Confirm:

```bat
git describe --tags --exact-match
git rev-parse HEAD
```

If dependencies changed:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
```

Then execute the standard production smoke test.

---

## 27. Production Working Tree Check

Before deployment or execution:

```bat
git status
```

Expected:

```text
nothing to commit, working tree clean
```

If tracked files changed:

```bat
git diff
```

Do not discard or overwrite changes until their source is understood.

Production should not normally have local modifications.

---

## 28. Removing Merged Branches

After a feature is merged:

```bash
git switch main
git pull --ff-only
git branch -d feature/prdpl3-ingestion
```

Delete the remote branch if required:

```bash
git push origin --delete feature/prdpl3-ingestion
```

Remove stale references:

```bash
git fetch --prune
```

Use forced deletion only when intentional:

```bash
git branch -D <branch-name>
```

---

## 29. Correcting Recent Work

Amend the latest unpushed commit:

```bash
git add <corrected-files>
git commit --amend
```

Change only the message:

```bash
git commit --amend -m "Corrected commit message"
```

Avoid rewriting history that other users may already be using.

---

## 30. Temporarily Saving Work

Use stash:

```bash
git stash push -m "Temporary NIN work"
```

List:

```bash
git stash list
```

Restore and remove from stash:

```bash
git stash pop
```

Restore without removing:

```bash
git stash apply
```

Include untracked files:

```bash
git stash push -u -m "Temporary work including new files"
```

---

## 31. Discarding Local Changes

Review first:

```bash
git diff
```

Discard one file:

```bash
git restore <file>
```

Unstage a file while keeping its changes:

```bash
git restore --staged <file>
```

Discard all unstaged tracked changes:

```bash
git restore .
```

These actions can permanently remove local work.

---

## 32. Repository Health Commands

Useful commands:

```bash
git status
git status -sb
git remote -v
git branch -vv
git branch -r
git tag --list
git fetch --prune
git log --oneline --decorate --graph -20
```

---

## 33. Troubleshooting HTTPS and SSO

### Repeated authentication prompts

Check:

```bash
git config --global --get credential.helper
git credential-manager --version
```

### Browser does not open

Trigger an authenticated operation:

```bash
git fetch origin
```

Confirm that the Windows Git Credential Manager and browser SSO process work outside WSL if necessary.

### Access denied

Confirm:

- correct GitHub account
- correct organization
- active SSO session
- repository permission
- correct HTTPS remote

### Wrong remote

```bash
git remote -v
```

Correct it:

```bash
git remote set-url origin   https://<github-host>/<organization>/nin-python.git
```

### Branch is behind

```bash
git fetch origin
git rebase origin/<branch-name>
git push
```

### Push to `main` rejected

Create a feature branch:

```bash
git switch -c feature/<change-name>
git push -u origin feature/<change-name>
```

Then open a pull request.

### Corporate certificate error

Do not disable SSL validation globally.

Do not use:

```bash
git config --global http.sslVerify false
```

Use the approved corporate certificate chain or follow corporate IT guidance.

---

## 34. Backup and Availability

Local work is not protected until it is committed and pushed.

Recommended practice:

- commit logical work regularly
- push at the end of each development session
- do not leave critical work only in WSL
- use pull requests for traceability
- use tags for production releases

---

## 35. Suggested Initial Commit Sequence

Create the initial branch:

```bash
git switch -c feature/nin-python-foundation
```

Suggested commits:

```text
Initialize NIN Python repository structure
Add NIN Python project plan
Add Git repository maintenance guide
Add Python dependency definitions
Add Git ignore and line-ending rules
Add initial package and test structure
```

Push:

```bash
git push -u origin feature/nin-python-foundation
```

Then open a pull request into `main`.

---

## 36. Production Release Checklist

Before tagging:

- working tree is clean
- all changes are committed
- feature work is merged
- tests pass
- reconciliation passes
- no production data is present
- no secrets are present
- dependencies are tested
- configuration template is current
- documentation is current
- output schema changes are documented
- Excel handoff has been tested

Release:

```bash
git switch main
git pull --ff-only
git tag -a v0.1.0 -m "NIN Python initial release"
git push origin v0.1.0
```

Production:

```bat
cd C:\NIN\nin-python
git fetch --all --tags
git checkout v0.1.0
```

---

## 37. Operating Model

```text
WSL Development
    |
    | Feature branch
    | Develop and test
    | Commit and push
    v
GitHub
    |
    | Pull request
    | Review
    | Merge to main
    | Tag release
    v
Windows 11 Production
    |
    | Fetch tags
    | Checkout approved release
    | Install runtime dependencies
    | Run smoke test
    v
NIN Production Execution
```

---

## 38. Information to Confirm

The guide is usable now. The following details would allow the placeholders and governance sections to be finalized:

1. Exact work GitHub hostname.
2. Exact GitHub organization name.
3. Final repository name.
4. Whether direct pushes to `main` are blocked.
5. Whether pull-request approval is required.
6. Whether release tags are permitted.
7. Whether Git Credential Manager is already callable from WSL.
8. Whether production should deploy tags or a controlled production branch.
9. Whether sanitized SAP test fixtures may be stored in the repository.
10. Whether production can install packages from the public Python package index or must use an internal package source.

These details do not block the initial repository setup.

---

## 39. Working Standard

The NIN Python project will be developed in WSL Debian and stored in the work GitHub repository through HTTPS and corporate SSO.

Development changes will be made on feature branches, tested, committed, and pushed to GitHub. Stable changes will be merged into `main` and identified using release tags.

The Windows 11 production workstation will retrieve only approved releases. Copilot CLI will remain a development-only tool and will not be required to run the production application.
