# Demo: Repository Structure Analyzer in Action

This document demonstrates the tool's capabilities on realistic repository structures.

---

## Example 1: Typical AI-Generated Python Project

### Repository Structure
```
ai-chatbot/
├── main.py
├── bot.py
├── test_bot.py
├── config.json
├── utils.py
├── helpers.py
├── requirements.txt
├── README.md
└── data.csv
```

### Command
```bash
python -m src.cli propose ai-chatbot
```

### Output
```
Analyzing repository: ai-chatbot
Found 9 files
Generating proposals...
Repository type: python_dominant

================================================================================
STRUCTURAL CHANGE PROPOSALS (6 total)
================================================================================

--------------------------------------------------------------------------------
CONFIGURATION (1 proposals)
--------------------------------------------------------------------------------

[1] MOVE: config.json
    → configs/config.json
REASON: Configuration file
RISK: MEDIUM
  category: configs
  current_location: root

--------------------------------------------------------------------------------
TESTS (1 proposals)
--------------------------------------------------------------------------------

[2] MOVE: test_bot.py
    → tests/test_bot.py
REASON: Contains test functions/classes
RISK: MEDIUM
  category: tests
  current_location: root

--------------------------------------------------------------------------------
SOURCE CODE (3 proposals)
--------------------------------------------------------------------------------

[3] MOVE: bot.py
    → src/bot.py
REASON: Has 4 imports; Appears to be application code
RISK: LOW
  category: src
  current_location: root

[4] MOVE: utils.py
    → src/utils.py
REASON: Has 2 imports; Appears to be application code
RISK: LOW
  category: src
  current_location: root

[5] MOVE: helpers.py
    → src/helpers.py
REASON: Has 3 imports; Appears to be application code
RISK: LOW
  category: src
  current_location: root

--------------------------------------------------------------------------------
OTHER (1 proposals)
--------------------------------------------------------------------------------

[6] MOVE: main.py
    → scripts/main.py
REASON: Has __main__ block; Executable script pattern
RISK: MEDIUM
  category: scripts
  current_location: root

================================================================================
SUMMARY
================================================================================
Total proposals: 6

By action:
  move: 6

By risk level:
  low: 3
  medium: 3

By category:
  Configuration: 1
  Tests: 1
  Source Code: 3
  Other: 1
```

**Interpretation**: All files at root should be organized into proper directories (src/, tests/, configs/, scripts/).

---

## Example 2: Project with Duplicates

### Repository Structure
```
web-app/
├── requirements.txt
├── app.py
├── utils.py
├── backup/
│   ├── requirements.txt  ← duplicate!
│   └── utils.py          ← duplicate!
├── README.md
└── old/
    └── README.md         ← duplicate!
```

### Command
```bash
python -m src.cli propose web-app
```

### Output (Partial)
```
Repository type: python_dominant

================================================================================
STRUCTURAL CHANGE PROPOSALS (9 total)
================================================================================

--------------------------------------------------------------------------------
DEPENDENCIES (2 proposals)
--------------------------------------------------------------------------------

[1] FLAG: requirements.txt
REASON: Duplicate filename: 2 files named 'requirements.txt'
RISK: HIGH
  duplicates: ['requirements.txt', 'backup/requirements.txt']

[2] FLAG: backup/requirements.txt
REASON: Duplicate filename: 2 files named 'requirements.txt'
RISK: HIGH
  duplicates: ['requirements.txt', 'backup/requirements.txt']

--------------------------------------------------------------------------------
DOCUMENTATION (2 proposals)
--------------------------------------------------------------------------------

[3] FLAG: README.md
REASON: Duplicate filename: 2 files named 'readme.md'
RISK: LOW
  duplicates: ['README.md', 'old/README.md']

[4] FLAG: old/README.md
REASON: Duplicate filename: 2 files named 'readme.md'
RISK: LOW
  duplicates: ['README.md', 'old/README.md']

...

================================================================================
SUMMARY
================================================================================
Total proposals: 9

By action:
  flag: 6
  move: 3

By risk level:
  high: 2    ← Critical duplicates
  low: 4
  medium: 3
```

**Interpretation**: 
- **HIGH risk** duplicates (requirements.txt) need immediate attention
- **LOW risk** duplicates (README.md) are safe to review later
- MOVE proposals suggest organizing root files

---

## Example 3: Non-Python Repository

### Repository Structure
```
react-app/
├── package.json
├── package-lock.json
├── src/
│   ├── App.tsx
│   ├── index.tsx
│   └── utils.ts
├── public/
│   └── index.html
└── README.md
```

### Command
```bash
python -m src.cli propose react-app
```

### Output
```
Analyzing repository: react-app
Found 6 files
Generating proposals...
Repository type: non_python

⚠️ Non-Python repository: Only duplicate detection active

================================================================================
STRUCTURAL CHANGE PROPOSALS (0 total)
================================================================================

No proposals generated.

================================================================================
SUMMARY
================================================================================
Total proposals: 0
```

**Interpretation**: Tool correctly detects non-Python repository and skips MOVE proposals for safety. Only duplicate detection would run if duplicates existed.

---

## Example 4: Analyzing This Repository

### Command
```bash
python -m src.cli analyze .
```

### Output
```
Analyzing repository: .
Found 20 files

REPOSITORY SUMMARY
==================
Total files: 20
Python files: 17

By category:
  src: 7
  tests: 4
  configs: 3
  markdown: 2
  scripts: 2
  experiments: 1
  trash: 0

Repository type: python_dominant (85.0% Python files)
Python score: 7
Non-Python score: 0
```

**Interpretation**: 
- Repository is well-organized (most files already in proper directories)
- High Python percentage confirms this is a Python project
- Tool detects its own structure correctly

---

## Key Takeaways

1. **MOVE proposals** suggest structural improvements based on Python conventions
2. **FLAG proposals** highlight issues requiring manual review (especially duplicates)
3. **Risk levels** help prioritize which proposals to address first
4. **Repository type detection** prevents inappropriate proposals on non-Python repos
5. **Output is read-only** - you decide which changes to make
