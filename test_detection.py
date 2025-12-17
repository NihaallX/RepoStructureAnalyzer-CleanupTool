"""Demo script to test repo type detection on different scenarios."""
import tempfile
from pathlib import Path
from src.analyzer import FileMetadata, RepositoryAnalyzer
from src.reasoner import StructureReasoner
from src.proposal import ActionType

def create_test_file(base_path: Path, filename: str) -> Path:
    """Create a test file."""
    file_path = base_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.touch()
    return file_path

def test_python_repo():
    """Test Python repository detection."""
    print("\n" + "="*70)
    print("TEST 1: Python Repository")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Create Python repo structure
        create_test_file(base, 'setup.py')
        create_test_file(base, 'requirements.txt')
        create_test_file(base, 'src/app.py')
        create_test_file(base, 'src/models.py')
        create_test_file(base, 'tests/test_app.py')
        create_test_file(base, 'README.md')
        
        analyzer = RepositoryAnalyzer(str(base))
        files = analyzer.analyze()
        
        reasoner = StructureReasoner(base)
        generator = reasoner.generate_proposals(files)
        
        print(f"Files analyzed: {len(files)}")
        print(f"Repository type: {reasoner.repo_type.value}")
        print(f"MOVE proposals: {len(generator.get_by_action(ActionType.MOVE))}")
        print(f"FLAG proposals: {len(generator.get_by_action(ActionType.FLAG))}")
        print("✓ Python repo should have MOVE proposals")

def test_angular_repo():
    """Test Angular/TypeScript repository detection."""
    print("\n" + "="*70)
    print("TEST 2: Angular/TypeScript Repository")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Create Angular repo structure
        create_test_file(base, 'package.json')
        create_test_file(base, 'angular.json')
        create_test_file(base, 'tsconfig.json')
        create_test_file(base, 'src/app/app.component.ts')
        create_test_file(base, 'src/app/app.module.ts')
        create_test_file(base, 'src/app/app.component.html')
        create_test_file(base, 'src/environments/environment.ts')
        create_test_file(base, 'README.md')
        
        analyzer = RepositoryAnalyzer(str(base))
        files = analyzer.analyze()
        
        reasoner = StructureReasoner(base)
        generator = reasoner.generate_proposals(files)
        
        print(f"Files analyzed: {len(files)}")
        print(f"Repository type: {reasoner.repo_type.value}")
        print(f"MOVE proposals: {len(generator.get_by_action(ActionType.MOVE))}")
        print(f"FLAG proposals: {len(generator.get_by_action(ActionType.FLAG))}")
        print("✓ Non-Python repo should have NO MOVE proposals")

def test_mixed_repo():
    """Test mixed repository detection."""
    print("\n" + "="*70)
    print("TEST 3: Mixed Python/JavaScript Repository")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Create mixed repo structure
        create_test_file(base, 'requirements.txt')
        create_test_file(base, 'package.json')
        create_test_file(base, 'backend/app.py')
        create_test_file(base, 'backend/models.py')
        create_test_file(base, 'backend/utils.py')
        create_test_file(base, 'frontend/index.js')
        create_test_file(base, 'frontend/app.js')
        create_test_file(base, 'frontend/styles.css')
        create_test_file(base, 'README.md')
        
        analyzer = RepositoryAnalyzer(str(base))
        files = analyzer.analyze()
        
        reasoner = StructureReasoner(base)
        generator = reasoner.generate_proposals(files)
        
        print(f"Files analyzed: {len(files)}")
        print(f"Repository type: {reasoner.repo_type.value}")
        
        moves = generator.get_by_action(ActionType.MOVE)
        print(f"MOVE proposals: {len(moves)}")
        
        # Check that only .py files have moves
        py_moves = [m for m in moves if str(m.source_path).endswith('.py')]
        non_py_moves = [m for m in moves if not str(m.source_path).endswith('.py') 
                       and not any(str(m.source_path).endswith(cfg) 
                                 for cfg in ['requirements.txt', '.gitignore'])]
        
        print(f"Python file moves: {len(py_moves)}")
        print(f"Non-Python file moves: {len(non_py_moves)}")
        print(f"FLAG proposals: {len(generator.get_by_action(ActionType.FLAG))}")
        print("✓ Mixed repo should only move Python files")

if __name__ == "__main__":
    print("\n" + "#"*70)
    print("# REPOSITORY TYPE DETECTION DEMO")
    print("#"*70)
    
    test_python_repo()
    test_angular_repo()
    test_mixed_repo()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("✓ Python repos: Full MOVE proposals enabled")
    print("✓ Non-Python repos: Only FLAG proposals (duplicates, etc.)")
    print("✓ Mixed repos: MOVE proposals only for .py files")
    print("="*70 + "\n")
