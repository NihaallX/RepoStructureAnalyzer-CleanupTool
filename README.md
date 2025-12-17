# Repo Structure Analyzer & Cleanup Tool

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![Tests](https://img.shields.io/badge/tests-60%20passing-brightgreen.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Overview

A **read-only, Python-first repository analyzer** that detects structural issues and produces safe, actionable proposals (MOVE / FLAG) without modifying files. Designed for AI-generated projects and sprawling codebases that need organizational cleanup.

## What This Tool Does

- Analyzes repository structure with file metadata collection
- Detects misplaced files based on Python conventions
- Flags duplicate filenames with risk stratification
- Detects repository type (Python / Non-Python / Mixed)
- Produces **safe proposals only** (no automatic changes)
- Groups results by category and risk level (LOW / MEDIUM / HIGH)
- Provides human-readable, actionable output

## What This Tool Does NOT Do

- ❌ No automatic file moves or deletions
- ❌ No repository mutation or file system writes
- ❌ No configuration files or complex CLI flags
- ❌ No framework-specific detection (Python conventions only)
- ❌ No network calls or external dependencies beyond listed packages

## Safety Guarantees

- **Read-only analysis**: Never modifies your files
- **Deterministic output**: Same input always produces same proposals
- **No side effects**: No file system writes, no network calls
- **Type safety**: Repository type detection prevents incorrect MOVE proposals on non-Python repos
- **Explicit risk levels**: All proposals tagged with LOW/MEDIUM/HIGH risk

## Installation

```bash
git clone https://github.com/NihaallX/RepoStructureAnalyzer-CleanupTool.git
cd RepoStructureAnalyzer-CleanupTool
pip install -e .
```

## Quick Start

### Analyze a repository
```bash
python -m src.cli analyze path/to/repo
```

Shows file counts, categories, and repository type detection.

### Generate proposals
```bash
python -m src.cli propose path/to/repo
```

Produces MOVE and FLAG proposals with risk assessment.

## Example Output

Given a simple Python project:
```
my-project/
├── app.py
├── test_app.py
├── utils.py
├── config.json
└── README.md
```

Running `python -m src.cli propose my-project` produces:

```
Repository type: python_dominant

================================================================================
STRUCTURAL CHANGE PROPOSALS (3 total)
================================================================================

--------------------------------------------------------------------------------
TESTS (1 proposals)
--------------------------------------------------------------------------------

[1] MOVE: test_app.py
    → tests/test_app.py
REASON: Contains test functions/classes
RISK: MEDIUM
  category: tests
  current_location: root

--------------------------------------------------------------------------------
SOURCE CODE (2 proposals)
--------------------------------------------------------------------------------

[2] MOVE: app.py
    → src/app.py
REASON: Has 3 imports; Appears to be application code
RISK: LOW
  category: src
  current_location: root

[3] MOVE: utils.py
    → src/utils.py
REASON: Has 2 imports; Appears to be application code
RISK: LOW
  category: src
  current_location: root

================================================================================
SUMMARY
================================================================================
Total proposals: 3

By action:
  move: 3

By risk level:
  low: 2
  medium: 1

By category:
  Tests: 1
  Source Code: 2
```

See [DEMO.md](DEMO.md) for more examples.

## Interpretation of Output

### MOVE Proposals
- **Action**: Suggests relocating a file to a more appropriate directory
- **Example**: `test_app.py` at root → `tests/test_app.py`
- **Risk levels**:
  - **LOW**: Documentation, markdown files
  - **MEDIUM**: Configuration files, scripts
  - **HIGH**: Files with many dependencies

### FLAG Proposals
- **Action**: Highlights potential issues without suggesting a specific move
- **Types**:
  - **Duplicate filenames**: Multiple files with the same name in different locations
  - **Orphaned files**: Files that seem misplaced but no clear target location

### Risk Stratification
Proposals are categorized by risk level to help prioritize:

- **HIGH**: Critical files (requirements.txt, .env, Dockerfile, package.json)
  - Review immediately - duplicates could cause version conflicts or security issues

- **MEDIUM**: Regular code files and configs
  - Review when convenient - standard organizational improvements

- **LOW**: Documentation and logs (README.md, *.log files)
  - Safe to review later - minimal impact on functionality

## Known Limitations

- **Python-first design**: Tool is optimized for Python repository conventions
- **Frontend noise**: Frontend build directories (out/, .next/, dist/) generate duplicate flags in v0.1
- **Non-Python repos**: Limited to duplicate detection only; no MOVE proposals for safety
- **No auto-fix**: Proposals must be manually reviewed and applied
- **Structural files**: __init__.py and conftest.py are exempted from duplicate detection

## Contributing

This is a v0.1 release focused on core functionality. Contributions welcome for:
- Bug fixes
- Test coverage improvements
- Documentation clarity
- Performance optimizations

Please do not submit PRs for:
- Auto-fix features
- Configuration systems
- Framework-specific detection

## License

MIT License - see [LICENSE](LICENSE) file for details.