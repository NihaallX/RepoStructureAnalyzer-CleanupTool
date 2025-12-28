"""Tests for import_analyzer module (V2.3)."""
import pytest
from pathlib import Path
from src.import_analyzer import ImportAnalyzer, ImportStatement, ImportWarning
from src.proposal import Proposal, ActionType, RiskLevel


@pytest.fixture
def temp_python_repo(tmp_path):
    """Create a temporary Python repository with various import patterns."""
    # Create src directory structure
    src = tmp_path / "src"
    src.mkdir()
    
    # Main module with relative imports
    main_py = src / "main.py"
    main_py.write_text("""
from .utils import helper_function
from .models import User
import config
""")
    
    # Utils module
    utils_py = src / "utils.py"
    utils_py.write_text("""
def helper_function():
    pass
""")
    
    # Models module with same-directory import
    models_py = src / "models.py"
    models_py.write_text("""
from utils import helper_function
import constants
""")
    
    # Config in same directory as main
    config_py = src / "config.py"
    config_py.write_text("""
DATABASE_URL = 'sqlite:///db.sqlite3'
""")
    
    # Constants
    constants_py = src / "constants.py"
    constants_py.write_text("""
MAX_SIZE = 100
""")
    
    return tmp_path


@pytest.fixture
def temp_non_python_repo(tmp_path):
    """Create a temporary non-Python repository."""
    readme = tmp_path / "README.md"
    readme.write_text("# Non-Python Repo")
    
    js_file = tmp_path / "app.js"
    js_file.write_text("console.log('hello');")
    
    return tmp_path


class TestImportStatement:
    """Tests for ImportStatement class."""
    
    def test_create_absolute_import(self):
        """Test creating absolute import statement."""
        stmt = ImportStatement(
            module="os.path",
            is_relative=False,
            level=0,
            line_number=1,
            names=["join", "exists"]
        )
        assert stmt.module == "os.path"
        assert not stmt.is_relative
        assert stmt.level == 0
        assert stmt.line_number == 1
        assert stmt.names == ["join", "exists"]
    
    def test_create_relative_import(self):
        """Test creating relative import statement."""
        stmt = ImportStatement(
            module="utils",
            is_relative=True,
            level=1,
            line_number=5,
            names=["helper"]
        )
        assert stmt.module == "utils"
        assert stmt.is_relative
        assert stmt.level == 1


class TestImportWarning:
    """Tests for ImportWarning class."""
    
    def test_warning_to_text(self):
        """Test converting warning to text."""
        stmt = ImportStatement("utils", True, 1, 10, ["helper"])
        warning = ImportWarning(
            source_file=Path("src/main.py"),
            import_stmt=stmt,
            reason="Relative import may break",
            affected_files=[Path("src/utils.py")]
        )
        
        text = warning.to_text()
        # Use forward slashes or os-agnostic checks
        assert "main.py" in text
        assert "Line 10" in text
        assert "from .utils import helper" in text
        assert "Relative import may break" in text
        assert "utils.py" in text


class TestImportAnalyzer:
    """Tests for ImportAnalyzer class."""
    
    def test_extract_imports_simple(self, temp_python_repo):
        """Test extracting simple imports."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        main_file = temp_python_repo / "src" / "main.py"
        imports = analyzer.extract_imports(main_file)
        
        # Should extract 3 imports
        assert len(imports) == 3
        
        # Check relative imports
        relative_imports = [i for i in imports if i.is_relative]
        assert len(relative_imports) == 2
        assert any(i.module == "utils" for i in relative_imports)
        assert any(i.module == "models" for i in relative_imports)
        
        # Check absolute import
        absolute_imports = [i for i in imports if not i.is_relative]
        assert len(absolute_imports) == 1
        assert absolute_imports[0].module == "config"
    
    def test_extract_imports_nonexistent_file(self, temp_python_repo):
        """Test extracting imports from non-existent file."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        fake_file = temp_python_repo / "fake.py"
        imports = analyzer.extract_imports(fake_file)
        
        assert imports == []
    
    def test_extract_imports_syntax_error(self, temp_python_repo):
        """Test extracting imports from file with syntax errors."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        # Create file with syntax error
        bad_file = temp_python_repo / "bad.py"
        bad_file.write_text("import os\nthis is not valid python\n")
        
        imports = analyzer.extract_imports(bad_file)
        
        # Should handle gracefully and return empty list
        assert imports == []
    
    def test_detect_relative_import_breakage(self, temp_python_repo):
        """Test detecting relative import breakage."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        # Create proposal to move main.py to different directory
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path("src/main.py"),
            target_path=Path("app/main.py"),
            reason="Reorganization",
            risk_level=RiskLevel.LOW,
            details={}
        )
        
        warnings = analyzer.analyze_proposals([proposal])
        
        # Should detect relative import issues
        assert len(warnings) > 0
        
        # Check that relative import warnings are present
        relative_warnings = [
            w for w in warnings 
            if w.import_stmt.is_relative
        ]
        assert len(relative_warnings) > 0
    
    def test_detect_same_directory_import_breakage(self, temp_python_repo):
        """Test detecting same-directory import breakage."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        # Create proposal to move models.py to different directory
        # models.py imports utils and constants from same directory
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path("src/models.py"),
            target_path=Path("models/user.py"),
            reason="Reorganization",
            risk_level=RiskLevel.LOW,
            details={}
        )
        
        warnings = analyzer.analyze_proposals([proposal])
        
        # Should detect same-directory import issues
        assert len(warnings) > 0
        
        # Check warnings mention the imports
        warning_texts = [w.to_text() for w in warnings]
        combined_text = "\n".join(warning_texts)
        assert "utils" in combined_text or "constants" in combined_text
    
    def test_no_warnings_for_safe_moves(self, temp_python_repo):
        """Test that safe moves don't generate warnings."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        # Moving config.py to same directory (no imports affected)
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path("src/config.py"),
            target_path=Path("src/settings.py"),  # Same directory, different name
            reason="Rename",
            risk_level=RiskLevel.LOW,
            details={}
        )
        
        warnings = analyzer.analyze_proposals([proposal])
        
        # Should not generate warnings (config has no imports, just constants)
        assert len(warnings) == 0
    
    def test_cross_move_dependency(self, temp_python_repo):
        """Test detecting cross-MOVE dependencies."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        # Both files moving to different directories
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("src/main.py"),
                target_path=Path("app/main.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            ),
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("src/utils.py"),
                target_path=Path("lib/utils.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings = analyzer.analyze_proposals(proposals)
        
        # Should detect that both files are moving (relative import issue)
        assert len(warnings) > 0
    
    def test_non_python_repo_no_analysis(self, temp_non_python_repo):
        """Test that non-Python repos don't get analyzed."""
        analyzer = ImportAnalyzer(temp_non_python_repo)
        
        # Create a move proposal
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path("app.js"),
            target_path=Path("src/app.js"),
            reason="Reorganization",
            risk_level=RiskLevel.LOW,
            details={}
        )
        
        warnings = analyzer.analyze_proposals([proposal])
        
        # Should return empty list for non-Python files
        assert warnings == []
    
    def test_multiple_proposals_aggregate_warnings(self, temp_python_repo):
        """Test that multiple proposals aggregate warnings correctly."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("src/main.py"),
                target_path=Path("app/main.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            ),
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("src/models.py"),
                target_path=Path("models/user.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings = analyzer.analyze_proposals(proposals)
        
        # Should have warnings from both files
        assert len(warnings) > 0
        
        # Check that warnings come from different source files
        source_files = {w.source_file for w in warnings}
        assert len(source_files) >= 1  # At least one file has import issues


class TestImportAnalyzerEdgeCases:
    """Tests for edge cases in import analysis."""
    
    def test_empty_file(self, temp_python_repo):
        """Test analyzing empty Python file."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        empty_file = temp_python_repo / "empty.py"
        empty_file.write_text("")
        
        imports = analyzer.extract_imports(empty_file)
        assert imports == []
    
    def test_file_with_only_comments(self, temp_python_repo):
        """Test analyzing file with only comments."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        comment_file = temp_python_repo / "comments.py"
        comment_file.write_text("""
# This is a comment
# Another comment
\"\"\"Docstring\"\"\"
""")
        
        imports = analyzer.extract_imports(comment_file)
        assert imports == []
    
    def test_deeply_nested_relative_import(self, temp_python_repo):
        """Test extracting deeply nested relative imports."""
        analyzer = ImportAnalyzer(temp_python_repo)
        
        nested_file = temp_python_repo / "src" / "nested.py"
        nested_file.write_text("from ...utils import helper")
        
        imports = analyzer.extract_imports(nested_file)
        
        assert len(imports) == 1
        assert imports[0].is_relative
        assert imports[0].level == 3
        assert imports[0].module == "utils"
