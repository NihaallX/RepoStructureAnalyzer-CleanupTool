# Repo Structure Analyzer & Cleanup Tool

A **read-only, Python-first repository analyzer** that detects structural issues
and produces safe, actionable proposals (MOVE / FLAG) without modifying files.

## What this tool does
- Analyzes repository structure
- Detects misplaced files
- Flags duplicate filenames
- Produces **safe proposals only** (no auto-fix)
- Groups results with risk levels (LOW / MEDIUM / HIGH)

## What this tool deliberately does NOT do
- ❌ No automatic file moves
- ❌ No deletions
- ❌ No repo mutation
- ❌ No config files or CLI flags
- ❌ No framework-specific magic

## Supported repositories
- ✅ Python repositories (primary target)
- ⚠️ Frontend repositories are analyzed as-is and may produce high duplicate noise

> Frontend build artifacts (e.g. `out/`, `.next/`, `dist/`) are **not collapsed** in v0.1.
> This is intentional and will be addressed in a future version.

## Safety guarantees
- Read-only analysis
- Deterministic output
- No file system writes
- No network calls

## Installation
```bash
pip install -e .

## Usage
python -m src.cli analyze .
python -m src.cli propose .

Output

MOVE proposals (when safe)

FLAG proposals with risk stratification

Clean summary grouped by action and risk

Known limitations

Frontend build directories generate noisy duplicate flags

Tool is optimized for Python repo conventions
