# Repo Structure Analyzer and Cleanup Tool

A decision-support system for Python repository reorganization.

## What This Tool Is

This is a suggest-first tool that helps you decide whether, when, and how safely to reorganize a repository's file structure. It analyzes your repository, proposes structural changes, shows you the consequences, and provides risk assessments. You review the proposals and decide what to apply.

This is not a refactoring tool. It does not modify code, rewrite imports, or change logic. It moves files.

## What This Tool Explicitly Does NOT Do

- Does not rewrite code or modify imports
- Does not refactor logic or change algorithms
- Does not auto-commit or modify Git state
- Does not run `git mv` or alter version control
- Does not promise correctness or safety
- Does not apply changes without explicit approval
- Does not work on non-Python repositories (advisory mode only)
- Does not auto-fix broken imports
- Does not modify files during analysis

## Why This Tool Exists

Repository reorganizations are risky and anxiety-inducing. Most tools over-automate and hide consequences. They promise to "just fix everything" and leave you with broken imports, lost Git history, or worse.

This tool prioritizes visibility, judgment, and reversibility. It shows you what will happen before anything happens. It provides risk assessments, impact summaries, and confidence scores so you can make informed decisions. It preserves your ability to say no.

The philosophy: trust comes from transparency, not automation.

## Core Capabilities

### Analysis

- **Repository type detection**: Identifies Python-dominant, non-Python, or mixed repositories
- **File classification**: Categorizes files as source, test, config, data, documentation, or experiments
- **Structural analysis**: Detects misplaced files, duplicates, and organizational issues

### Proposals

- **MOVE proposals**: Suggests file relocations with explanations (Python repos only)
- **FLAG proposals**: Identifies duplicates and structural issues (all repos)
- **Risk assessment**: Assigns LOW, MEDIUM, or HIGH risk to each proposal
- **Detailed reasoning**: Explains why each change is suggested

### Visualization & Decision Support

- **Before/after tree view**: Shows directory structure changes
- **Impact summary**: Lists affected files, new directories, and proposal breakdown
- **Import breakage warnings**: Detects Python imports that may break (relative imports, same-directory imports, cross-MOVE dependencies)
- **Git awareness**: Warns about uncommitted changes and Git-tracked files (read-only, no Git modifications)
- **Confidence score**: Provides HIGH/MEDIUM/LOW verdict with explainable factors

### Execution

- **Dry-run mode**: Simulates changes without touching the filesystem (default)
- **Interactive apply**: Prompts for approval on each proposal
- **Rollback support**: Undoes applied changes (last N operations)
- **Execution history**: Logs all operations with timestamps

## Who Should Use This

- Python developers reorganizing AI-generated or chaotic projects
- Teams cleaning up messy repository structures
- Maintainers consolidating scattered files
- Anyone who wants to see consequences before making changes

## Who Should Not Use This

- Users expecting automatic import rewriting (this tool does not modify code)
- Users working on non-Python repositories (tool provides advisory mode only)
- Users wanting fully automated reorganization (this tool requires human judgment)
- Users expecting AI-powered refactoring (this tool uses simple heuristics)

Walk away if you need:
- Automatic import fixing
- Code refactoring
- Non-Python repository support with MOVE proposals
- Zero human oversight

## Safety Guarantees

- **No hidden actions**: Every operation is logged and visible
- **No silent filesystem changes**: Dry-run mode is the default
- **No Git mutations**: Tool never runs `git mv`, `git add`, or `git commit`
- **Everything reversible**: Rollback restores original state
- **User always in control**: No changes applied without explicit approval
- **Read-only by default**: Analysis and proposals touch nothing

The tool will not modify your repository unless you explicitly run `--execute` mode and approve each change.

## Installation

```bash
pip install repo-structure-tool
```

Or clone and install:

```bash
git clone https://github.com/yourusername/repo-structure-tool.git
cd repo-structure-tool
pip install -e .
```

## Quick Start

```bash
# Analyze repository (read-only)
repo-tool analyze

# Generate proposals (read-only)
repo-tool propose

# Preview changes with visualization (read-only)
repo-tool preview

# Apply changes interactively (dry-run by default)
repo-tool apply

# Apply changes for real (requires confirmation)
repo-tool apply --execute

# Rollback last operation
repo-tool rollback --undo-last 1 --execute
```

## Commands

### `analyze`
Scans repository and collects file metadata. Shows summary of file types, counts, and structure.

### `propose`
Generates MOVE and FLAG proposals based on repository analysis. Shows risk levels and reasoning.

### `preview`
Displays before/after tree visualization, impact summary, import warnings, Git warnings, and confidence score. Does not modify filesystem.

### `apply`
Applies MOVE proposals interactively. Default is dry-run (simulation). Use `--execute` for real filesystem changes.

Options:
- `--dry-run` (default): Simulate without changes
- `--execute`: Apply changes for real
- `--yes`: Auto-approve all (dangerous)

### `rollback`
Undoes previously applied operations. Reads from `.repo-tool-history.json`.

Options:
- `--undo-last N`: Undo last N operations
- `--execute`: Perform rollback (dry-run by default)

## Risk Levels

- **LOW**: Safe moves (tests to test directories, clear patterns)
- **MEDIUM**: Moderate risk (source files, some ambiguity)
- **HIGH**: Dangerous (duplicates, critical files like .env)

## Confidence Score

Each reorganization run receives a confidence score (HIGH/MEDIUM/LOW) based on:

- Repository type (Python vs non-Python)
- Number and risk level of proposals
- Import breakage warnings
- Test presence
- Execution mode (dry-run vs execute)

The score aggregates all signals into a single verdict with explainable factors.

## Version

Current version: **2.4.0**

### Recent Updates

- **V2.4**: Confidence scoring and Git awareness (read-only)
- **V2.3**: Import breakage warnings for Python
- **V2.2**: Visualization and decision support
- **V2.1**: Interactive apply with rollback

## Limitations

- **Python-focused**: MOVE proposals only generated for Python-dominant repositories
- **No import rewriting**: Tool does not modify code or fix imports
- **Simple heuristics**: Uses pattern matching, not AI or deep analysis
- **Manual verification required**: Always review proposals before applying
- **Git workflows**: Does not integrate with `git mv` or preserve Git history annotations

## License

MIT

## Contributing

Contributions welcome. Follow existing code style. Add tests for new features. Update documentation.

## Support

For issues, questions, or feature requests, open an issue on GitHub.

---

**Remember**: This tool helps you make decisions. It does not make decisions for you. Review all proposals carefully before applying changes.
