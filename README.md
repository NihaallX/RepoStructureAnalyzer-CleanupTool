# Repo Structure Analyzer & Cleanup Tool

![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![Tests](https://img.shields.io/badge/tests-60%20passing-brightgreen.svg)
![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## The Problem

Vibe-coded repositories—projects created through rapid iteration, AI assistance, or learning-by-doing—often accumulate structural chaos:

- Test files scattered in root directories
- Source code mixed with configuration files  
- Duplicate files with unclear purposes
- Build artifacts committed to version control
- Frontend noise drowning out real issues

**This tool restores signal in messy repositories** by analyzing structure and producing safe, actionable proposals without touching your files.

## What This Tool Does

✅ **Analyzes** repository structure with file metadata collection  
✅ **Detects** misplaced files based on Python conventions  
✅ **Flags** duplicate filenames with risk stratification (HIGH/MEDIUM/LOW)  
✅ **Identifies** repository type (Python / Non-Python / Mixed)  
✅ **Groups** duplicates into human-scale output (1 flag per duplicate set, not 1 per file)  
✅ **Excludes** build artifacts (.next, out, dist, coverage) at scan time  
✅ **Suppresses** expected framework patterns (e.g., index.html in Next.js sites)  
✅ **Produces** safe proposals only—never modifies files

## What This Tool Does NOT Do

❌ No automatic file moves or deletions  
❌ No repository mutation or file system writes  
❌ No configuration files or complex CLI setup  
❌ No full normalization of frontend repositories  
❌ No network calls or external dependencies beyond pip packages

## Supported Ecosystems

| Ecosystem | MOVE Proposals | Duplicate Detection | Artifact Exclusion | Framework Awareness |
|-----------|---------------|---------------------|-------------------|---------------------|
| **Python-dominant** | ✅ Full support | ✅ Yes | ✅ Yes | N/A |
| **Next.js / React** | ❌ Disabled (safety) | ✅ Yes (with suppression) | ✅ Yes (.next, out) | ✅ Suppresses index.html, page.tsx, etc. |
| **Mixed (Python + JS)** | ⚠️ Python files only | ✅ Yes | ✅ Yes | ✅ Automatic detection |
| **Non-Python** | ❌ Disabled | ✅ Yes | ✅ Yes | Partial |

## Installation

```bash
git clone https://github.com/NihaallX/RepoStructureAnalyzer-CleanupTool.git
cd RepoStructureAnalyzer-CleanupTool
pip install -e .
```

## Quick Start

### Analyze repository structure
```bash
python -m src.cli analyze path/to/repo
```

Shows file counts, categories, and repository type detection.

### Generate cleanup proposals
```bash
python -m src.cli propose path/to/repo
```

Produces MOVE and FLAG proposals with risk assessment.

## Example Output

### Before V2: Noise Overload
```
# Running on a Next.js repository
Total proposals: 847

FLAGs:
- .next/static/chunks/index.js (duplicate)
- .next/static/chunks/app.js (duplicate)  
- out/index.html (duplicate)
- out/about/index.html (duplicate)
- dist/index.js (duplicate)
... [842 more duplicates from build artifacts]
```

### After V2: Human-Scale Output
```
Repository type: mixed (Next.js + Python)
Ecosystem profile: nextjs

================================================================================
FLAGGED ISSUES (2 total)
================================================================================

[1] FLAG: Duplicate filename: 3 files named 'config.json'
RISK: HIGH
  - api/config.json
  - frontend/config.json
  - backup/config.json

[2] FLAG: Duplicate filename: 2 files named 'utils.py'  
RISK: MEDIUM
  - scripts/utils.py
  - tests/utils.py

================================================================================
SUMMARY
================================================================================
Total proposals: 2
By risk level:
  high: 1
  medium: 1

Note: Build artifacts (.next, out, dist) excluded at scan time.
Note: Framework patterns (index.html, page.tsx) suppressed.
```

See [DEMO.md](DEMO.md) for more examples.

## How It Works

1. **Repository Type Detection** - Identifies Python-dominant, mixed, or non-Python repos
2. **Ecosystem Profile Selection** - Applies appropriate rules (Python / Next.js / Frontend)
3. **Artifact Exclusion** - Skips .next, out, dist, build directories entirely during scan
4. **File Classification** - Categories: tests, source, config, docs, data, scripts
5. **Proposal Generation** - MOVE proposals for Python repos only (safety-gated)
6. **Duplicate Grouping** - Emits 1 FLAG per duplicate set (not 1 per file)
7. **Framework Suppression** - Filters expected patterns (index.html in Next.js)
8. **Risk Stratification** - HIGH/MEDIUM/LOW based on file criticality

## Interpretation of Output

### MOVE Proposals (Python repos only)
- **Action**: Suggests relocating a file to conventional directory
- **Example**: `test_app.py` at root → `tests/test_app.py`
- **Gating**: Automatically disabled for non-Python repos (safety)
- **Risk levels**:
  - **LOW**: Documentation, markdown files
  - **MEDIUM**: Config files, scripts  
  - **HIGH**: Files with many dependencies

### FLAG Proposals (All repos)
- **Action**: Highlights potential issues requiring human judgment
- **V2 Behavior**: Grouped by duplicate set (not per-file)
- **Examples**:
  - **Duplicate filenames**: `3 files named 'config.json'` with example paths
  - **Orphaned files**: Files in unexpected locations
- **Suppression**: Expected framework patterns filtered out (index.html, page.tsx)

### Risk Stratification

| Risk | File Types | Why It Matters | Action |
|------|-----------|----------------|--------|
| **HIGH** | `.env`, `requirements.txt`, `Dockerfile`, `package.json` | Version conflicts, security issues, build breakage | Review immediately |
| **MEDIUM** | Regular code files, config files | Standard organizational issues | Review when convenient |
| **LOW** | `README.md`, `*.log`, documentation | Minimal functional impact | Safe to defer |

**Important**: Duplicate detection ≠ error detection. Many duplicates are valid patterns (e.g., `__init__.py`, `index.html` in multi-page sites). This tool flags for review, not for automatic deletion.

## Known Limitations & Non-Goals

### What This Tool Is NOT

- ❌ **Not an auto-fixer** - Proposals require human review and manual application
- ❌ **Not a linter** - Does not check code quality or style
- ❌ **Not framework-agnostic** - Hardcoded rules for Python and Next.js only
- ❌ **Not configurable** - No config files, no CLI flags, no customization

### Current Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **Python-first design** | Limited usefulness for pure JS/Java repos | Use for Python or mixed repos only |
| **Frontend partial support** | Next.js awareness exists but incomplete | Duplicate detection + artifact exclusion still valuable |
| **No auto-application** | Must manually `mv` files | By design (safety) |
| **Hardcoded ecosystems** | Only Python/Next.js/Frontend-static | Fork and extend `ecosystem.py` if needed |

### Intentional Constraints

- **No configuration files**: Prevents complexity creep
- **No plugin system**: Tool does one thing well
- **No MOVE proposals for non-Python**: Risk > reward for unfamiliar ecosystems
- **Structural files exempted**: `__init__.py`, `conftest.py` never flagged as duplicates

## Safety Guarantees

✅ **Read-only analysis** - Never modifies your files  
✅ **Deterministic output** - Same input → same proposals  
✅ **No side effects** - No writes, no network calls  
✅ **Type-gated proposals** - MOVE disabled for non-Python repos  
✅ **Explicit risk levels** - Every proposal tagged HIGH/MEDIUM/LOW  
✅ **Human-in-the-loop** - No automatic application

## Contributing

This is a V2 release focused on artifact awareness and frontend noise reduction.

**Contributions welcome for:**
- Bug fixes  
- Test coverage improvements  
- Documentation clarity  
- Performance optimizations  
- New ecosystem profiles (with clear use case)

**Please do NOT submit PRs for:**
- Auto-fix features  
- Configuration systems  
- Generic "support all frameworks" refactors  
- Removing safety constraints

## Versioning

- **v0.1**: Initial Python-first analyzer
- **v2.0**: Artifact awareness, ecosystem profiles, grouped duplicates

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Philosophy**: This tool restores trust in repository analysis by producing human-scale output. It does not try to solve every problem—it solves the vibe-coded chaos problem for Python-dominant and mixed repositories.