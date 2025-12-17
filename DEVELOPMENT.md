# Development Guide

## Project Structure

```
repo-structure-tool/
├── src/                    # Source code
│   ├── __init__.py
│   ├── analyzer.py         # Repository scanning and metadata collection
│   ├── classifier.py       # Rule-based file classification
│   ├── reasoner.py         # Structural reasoning and proposal generation
│   ├── proposal.py         # Proposal data structures and formatting
│   ├── executor.py         # Change execution (stub for v1)
│   └── cli.py             # Command-line interface
├── tests/                  # Unit tests
│   ├── __init__.py
│   ├── test_analyzer.py
│   ├── test_classifier.py
│   └── test_reasoner.py
├── requirements.txt        # Dependencies
├── setup.py               # Package setup
├── README.md              # User documentation
└── .gitignore             # Git ignore rules
```

## Setup for Development

1. **Clone or navigate to the repository:**
   ```bash
   cd "c:\Users\Nihal\Documents\Repo Structure Analyzer and Cleanup Tool"
   ```

2. **Create and activate virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install in development mode:**
   ```bash
   pip install -e .
   ```

## Running the Tool

### Analyze a repository
```bash
repo-tool analyze /path/to/repo
repo-tool analyze .  # Current directory
```

### Generate proposals
```bash
repo-tool propose /path/to/repo
repo-tool propose . --format json  # JSON output
repo-tool propose . -o proposals.txt  # Save to file
```

### Run using Python module (if entry point not working)
```bash
python -m src.cli analyze .
python -m src.cli propose .
```

## Testing

### Run all tests
```bash
pytest tests/
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_classifier.py -v
```

### Run with coverage
```bash
pip install pytest-cov
pytest tests/ --cov=src --cov-report=html
```

## Architecture

### 1. Analyzer (`analyzer.py`)

**Purpose:** Scan repository and collect file metadata

**Key Classes:**
- `FileMetadata`: Stores file information (path, imports, flags)
- `RepositoryAnalyzer`: Recursively scans directories

**Features:**
- Ignores .git, venv, __pycache__, etc.
- Parses Python files for imports and structure
- Detects test functions, main blocks, executables

### 2. Classifier (`classifier.py`)

**Purpose:** Classify files into categories using rules

**Categories:**
- `src/` - Application source code
- `tests/` - Test files
- `configs/` - Configuration files
- `scripts/` - Executable scripts
- `docs/` - Documentation
- `markdown/` - Markdown files
- `data/` - Data files
- `experiments/` - Experimental/temporary files
- `trash/` - Needs review

**Classification Rules (in priority order):**
1. **Experimental files** - temp_, playground, scratch
2. **Test files** - test_ prefix, in tests/, imports pytest
3. **Config files** - setup.py, requirements.txt, .yaml
4. **Scripts** - has __main__, run_ prefix
5. **Source code** - in src/, has imports, package structure

### 3. Reasoner (`reasoner.py`)

**Purpose:** Generate structural improvement proposals

**Proposal Types:**
- **MOVE**: Relocate file to better location
- **FLAG**: Mark for manual review
- **DELETE**: Suggest removal (coming soon)

**Risk Levels:**
- **LOW**: Safe moves (tests, docs, data)
- **MEDIUM**: Moderate risk (configs, executables)
- **HIGH**: Many dependencies or critical files

### 4. Proposal (`proposal.py`)

**Purpose:** Format and output proposals

**Output Formats:**
- Terminal-friendly text
- JSON for integrations

### 5. CLI (`cli.py`)

**Purpose:** Command-line interface

**Commands:**
- `analyze` - Scan and show summary
- `propose` - Generate change proposals
- `apply` - Execute changes (stub)
- `rollback` - Undo changes (stub)

## Extending the Tool

### Add a new file category

1. Add enum to `FileCategory` in `classifier.py`:
   ```python
   class FileCategory(Enum):
       # ...
       MY_CATEGORY = "my_category"
   ```

2. Add classification rule in `FileClassifier`:
   ```python
   def _is_my_category(self, metadata, name_lower, path_lower):
       # Your logic here
       return True/False
   ```

3. Add to `_classify_python()` or `_classify_non_python()`:
   ```python
   if self._is_my_category(metadata, name_lower, path_lower):
       return FileCategory.MY_CATEGORY
   ```

### Add a new detection rule

Update the appropriate `_is_*` method in `classifier.py`:
- Check file name patterns
- Check path patterns  
- Check imports
- Check content (via metadata)

### Add a new CLI command

1. Add command to `cli.py`:
   ```python
   @cli.command()
   @click.argument('repo_path')
   def mycommand(repo_path):
       """My command description."""
       # Implementation
   ```

## Code Style

- Follow PEP 8
- Use type hints where helpful
- Add docstrings to all classes and public methods
- Keep functions focused and testable
- Log important operations

## Testing Guidelines

- Write tests for all classification rules
- Test edge cases (empty files, duplicates, etc.)
- Use temporary directories in tests
- Mock file system when appropriate

## Future Enhancements (v2+)

- [ ] Safe apply system with rollback
- [ ] Interactive approval mode
- [ ] Git integration
- [ ] More sophisticated duplicate detection
- [ ] Support for non-Python projects
- [ ] VS Code extension
- [ ] Configuration file for custom rules
- [ ] Dry-run mode improvements
- [ ] Batch operations
- [ ] Undo history

## Troubleshooting

### Import errors
Make sure you installed in development mode:
```bash
pip install -e .
```

### Tests failing
Ensure you have pytest installed:
```bash
pip install pytest
```

### CLI not found
Use the module syntax:
```bash
python -m src.cli analyze .
```

## Contributing

This is a solo/small team tool, but contributions are welcome:

1. Write tests for new features
2. Update documentation
3. Follow existing code patterns
4. Keep it simple and focused
