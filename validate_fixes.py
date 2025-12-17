"""Validation demo for the two targeted fixes."""
import tempfile
from pathlib import Path
from src.analyzer import RepositoryAnalyzer
from src.reasoner import StructureReasoner
from src.proposal import ActionType

def create_file(base: Path, filename: str) -> Path:
    """Create a test file."""
    file_path = base / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch()
    return file_path

print("\n" + "="*70)
print("VALIDATION: FIX 1 - Structural File Exemption")
print("="*70)

with tempfile.TemporaryDirectory() as tmpdir:
    base = Path(tmpdir)
    
    # Create Python monorepo with many __init__.py files
    create_file(base, 'setup.py')
    create_file(base, 'requirements.txt')
    create_file(base, 'pkg1/__init__.py')
    create_file(base, 'pkg2/__init__.py')
    create_file(base, 'pkg3/__init__.py')
    create_file(base, 'pkg1/sub1/__init__.py')
    create_file(base, 'pkg1/sub2/__init__.py')
    create_file(base, 'pkg2/sub1/__init__.py')
    create_file(base, 'tests/__init__.py')
    create_file(base, 'tests/unit/__init__.py')
    create_file(base, 'tests/integration/__init__.py')
    create_file(base, 'tests/conftest.py')
    create_file(base, 'tests/unit/conftest.py')
    
    analyzer = RepositoryAnalyzer(str(base))
    files = analyzer.analyze()
    
    reasoner = StructureReasoner(base)
    generator = reasoner.generate_proposals(files)
    
    flags = generator.get_by_action(ActionType.FLAG)
    duplicate_flags = [f for f in flags if 'duplicate' in f.reason.lower()]
    
    # Check for __init__.py duplicates
    init_duplicates = [f for f in duplicate_flags if '__init__.py' in str(f.source_path).lower()]
    conftest_duplicates = [f for f in duplicate_flags if 'conftest.py' in str(f.source_path).lower()]
    
    print(f"Total files analyzed: {len(files)}")
    print(f"Total FLAG proposals: {len(flags)}")
    print(f"Duplicate FLAG proposals: {len(duplicate_flags)}")
    print(f"__init__.py duplicate flags: {len(init_duplicates)}")
    print(f"conftest.py duplicate flags: {len(conftest_duplicates)}")
    
    if len(init_duplicates) == 0 and len(conftest_duplicates) == 0:
        print("✅ FIX 1 VALIDATED: No false-positive duplicates for structural files")
    else:
        print("❌ FIX 1 FAILED: Still flagging structural files")

print("\n" + "="*70)
print("VALIDATION: FIX 2 - MOVE Gating Enforcement")
print("="*70)

with tempfile.TemporaryDirectory() as tmpdir:
    base = Path(tmpdir)
    
    # Create non-Python repo (Angular)
    create_file(base, 'package.json')
    create_file(base, 'angular.json')
    create_file(base, 'tsconfig.json')
    for i in range(30):
        create_file(base, f'src/component{i}.ts')
    
    analyzer = RepositoryAnalyzer(str(base))
    files = analyzer.analyze()
    
    reasoner = StructureReasoner(base)
    generator = reasoner.generate_proposals(files)
    
    print(f"Total files analyzed: {len(files)}")
    print(f"Repository type: {reasoner.repo_type.value}")
    
    moves = generator.get_by_action(ActionType.MOVE)
    flags = generator.get_by_action(ActionType.FLAG)
    
    print(f"MOVE proposals: {len(moves)}")
    print(f"FLAG proposals: {len(flags)}")
    
    if reasoner.repo_type.value == "non_python" and len(moves) == 0:
        print("✅ FIX 2 VALIDATED: Zero MOVE proposals in non-Python repo")
    else:
        print(f"❌ FIX 2 FAILED: Found {len(moves)} MOVE proposals in non-Python repo")

print("\n" + "="*70)
print("VALIDATION: Mixed Repo Safety")
print("="*70)

with tempfile.TemporaryDirectory() as tmpdir:
    base = Path(tmpdir)
    
    # Create mixed repo
    create_file(base, 'requirements.txt')
    create_file(base, 'package.json')
    create_file(base, 'backend.py')
    create_file(base, 'models.py')
    create_file(base, 'utils.py')
    create_file(base, 'frontend.ts')
    create_file(base, 'app.js')
    create_file(base, 'index.html')
    
    analyzer = RepositoryAnalyzer(str(base))
    files = analyzer.analyze()
    
    reasoner = StructureReasoner(base)
    generator = reasoner.generate_proposals(files)
    
    print(f"Repository type: {reasoner.repo_type.value}")
    
    moves = generator.get_by_action(ActionType.MOVE)
    print(f"Total MOVE proposals: {len(moves)}")
    
    # Check all moves are for .py files only
    py_moves = [m for m in moves if str(m.source_path).endswith('.py')]
    non_py_moves = [m for m in moves if not str(m.source_path).endswith('.py') 
                   and not any(str(m.source_path).endswith(cfg) 
                             for cfg in ['requirements.txt', 'package.json'])]
    
    print(f"Python file MOVE proposals: {len(py_moves)}")
    print(f"Non-Python file MOVE proposals: {len(non_py_moves)}")
    
    if len(non_py_moves) == 0:
        print("✅ MIXED REPO SAFETY: Only Python files have MOVE proposals")
    else:
        print(f"❌ MIXED REPO FAILED: Non-Python files in MOVE proposals")

print("\n" + "="*70)
print("ALL VALIDATIONS COMPLETE")
print("="*70 + "\n")
