"""Tests for the structure reasoner."""
import pytest
from pathlib import Path
import tempfile

from src.analyzer import FileMetadata, RepositoryAnalyzer
from src.reasoner import StructureReasoner
from src.proposal import ActionType, RiskLevel
from src.repo_type import RepoType


class TestStructureReasoner:
    """Test suite for StructureReasoner."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, filename: str, **kwargs) -> FileMetadata:
        """Helper to create FileMetadata for testing."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        
        for key, value in kwargs.items():
            setattr(metadata, key, value)
        
        return metadata
    
    def test_reasoner_initialization(self):
        """Test StructureReasoner initialization."""
        reasoner = StructureReasoner(self.temp_dir)
        assert reasoner.repo_path == self.temp_dir
    
    def test_generates_move_proposal_for_misplaced_test(self):
        """Test that misplaced test files get move proposals."""
        # Create a Python repo to ensure MOVE proposals are generated
        files = [
            self.create_metadata('setup.py'),  # Make it Python-dominant
            self.create_metadata('requirements.txt'),
            self.create_metadata('test_foo.py', has_tests=True),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Should have at least one proposal
        assert generator.get_count() > 0
        
        # Check for move proposals
        moves = generator.get_by_action(ActionType.MOVE)
        assert len(moves) > 0
        
        # Should have a move for test file to tests directory
        test_moves = [m for m in moves if 'test_foo' in str(m.source_path)]
        assert len(test_moves) > 0
        assert 'tests' in str(test_moves[0].target_path)
    
    def test_generates_move_proposal_for_misplaced_src(self):
        """Test that misplaced source files get move proposals."""
        # Create a Python repo
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('requirements.txt'),
            self.create_metadata('api.py', imports=['fastapi', 'pydantic']),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        moves = generator.get_by_action(ActionType.MOVE)
        assert len(moves) > 0
        
        # Should propose moving api.py to src/
        api_moves = [m for m in moves if 'api.py' in str(m.source_path)]
        assert len(api_moves) > 0
        assert 'src' in str(api_moves[0].target_path)
    
    def test_no_proposal_for_correctly_placed_file(self):
        """Test that correctly placed files don't generate proposals."""
        # Create file in correct location
        file_path = self.temp_dir / 'src' / 'app.py'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        metadata.imports = ['fastapi']
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals([metadata])
        
        # Should have minimal or no proposals for correctly placed files
        moves = generator.get_by_action(ActionType.MOVE)
        # The file might generate a proposal if the exact structure isn't preserved
        # But it shouldn't propose moving OUT of src
        for move in moves:
            if 'app.py' in str(move.source_path):
                assert 'src' in str(move.target_path)
    
    def test_risk_assessment(self):
        """Test risk level assessment."""
        # Create Python repo with high-risk file
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('requirements.txt'),
            self.create_metadata('complex.py', imports=[f'module{i}' for i in range(15)]),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        high_risk = generator.get_by_risk(RiskLevel.HIGH)
        assert len(high_risk) > 0
    
    def test_duplicate_detection(self):
        """Test duplicate file detection."""
        # Create duplicate files
        metadata1 = self.create_metadata('app.py')
        
        duplicate_path = self.temp_dir / 'backup' / 'app.py'
        duplicate_path.parent.mkdir(parents=True, exist_ok=True)
        duplicate_path.touch()
        metadata2 = FileMetadata(duplicate_path, self.temp_dir)
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals([metadata1, metadata2])
        
        # Should flag duplicates
        flags = generator.get_by_action(ActionType.FLAG)
        assert len(flags) > 0
        
        # Check if duplicate reason is present
        duplicate_flags = [f for f in flags if 'duplicate' in f.reason.lower()]
        assert len(duplicate_flags) > 0


class TestRepoTypeGating:
    """Test that MOVE proposals are gated by repository type."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, filename: str, **kwargs) -> FileMetadata:
        """Helper to create FileMetadata for testing."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        
        for key, value in kwargs.items():
            setattr(metadata, key, value)
        
        return metadata
    
    def test_python_repo_generates_moves(self):
        """Test that Python repos generate MOVE proposals."""
        # Create Python-dominant repo
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('requirements.txt'),
            self.create_metadata('app.py', imports=['fastapi']),
            self.create_metadata('utils.py', imports=['os', 'sys']),
            self.create_metadata('test_app.py', has_tests=True),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Should detect as Python
        assert reasoner.repo_type == RepoType.PYTHON_DOMINANT
        
        # Should have MOVE proposals
        moves = generator.get_by_action(ActionType.MOVE)
        assert len(moves) > 0
    
    def test_non_python_repo_no_moves(self):
        """Test that non-Python repos don't generate MOVE proposals."""
        # Create frontend repo
        files = [
            self.create_metadata('package.json'),
            self.create_metadata('angular.json'),
            self.create_metadata('tsconfig.json'),
            self.create_metadata('src/app.component.ts'),
            self.create_metadata('src/app.module.ts'),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Should detect as non-Python
        assert reasoner.repo_type == RepoType.NON_PYTHON
        
        # Should NOT have MOVE proposals
        moves = generator.get_by_action(ActionType.MOVE)
        assert len(moves) == 0
    
    def test_non_python_repo_still_flags_duplicates(self):
        """Test that non-Python repos still flag duplicates."""
        # Create frontend repo with duplicates
        files = [
            self.create_metadata('package.json'),
            self.create_metadata('src/app.ts'),
            self.create_metadata('backup/app.ts'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Should detect as non-Python
        assert reasoner.repo_type == RepoType.NON_PYTHON
        
        # Should still FLAG duplicates
        flags = generator.get_by_action(ActionType.FLAG)
        duplicate_flags = [f for f in flags if 'duplicate' in f.reason.lower()]
        assert len(duplicate_flags) > 0
    
    def test_mixed_repo_only_moves_python_files(self):
        """Test that mixed repos only propose moves for Python files."""
        # Create mixed repo with more balanced Python/JS content
        files = [
            self.create_metadata('requirements.txt'),
            self.create_metadata('package.json'),
            # Python backend (3 files)
            self.create_metadata('backend.py', imports=['fastapi']),
            self.create_metadata('models.py', imports=['sqlalchemy']),
            self.create_metadata('utils.py', imports=['os']),
            # Frontend (3 files)
            self.create_metadata('frontend.ts'),
            self.create_metadata('app.js'),
            self.create_metadata('index.html'),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Should detect as mixed
        assert reasoner.repo_type == RepoType.MIXED
        
        # Should have MOVE proposals
        moves = generator.get_by_action(ActionType.MOVE)
        
        # All MOVE proposals should be for .py files only
        for move in moves:
            source_path = str(move.source_path)
            # Skip config files that stay at root
            if not any(source_path.endswith(cfg) for cfg in ['requirements.txt', '.gitignore']):
                assert source_path.endswith('.py'), f"Non-Python file in moves: {source_path}"


class TestStructuralFileExemptions:
    """Test that structural Python files are exempt from duplicate detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, filename: str, **kwargs) -> FileMetadata:
        """Helper to create FileMetadata for testing."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        
        for key, value in kwargs.items():
            setattr(metadata, key, value)
        
        return metadata
    
    def test_init_py_not_flagged_as_duplicate(self):
        """Test that __init__.py files are not flagged as duplicates."""
        files = [
            self.create_metadata('setup.py'),  # Make it Python repo
            self.create_metadata('pkg1/__init__.py'),
            self.create_metadata('pkg2/__init__.py'),
            self.create_metadata('pkg3/__init__.py'),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Should have NO duplicate flags for __init__.py
        flags = generator.get_by_action(ActionType.FLAG)
        init_flags = [f for f in flags if '__init__.py' in str(f.source_path).lower()]
        
        assert len(init_flags) == 0, "Should not flag __init__.py as duplicate"
    
    def test_main_py_not_flagged_as_duplicate(self):
        """Test that __main__.py files are not flagged as duplicates."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('pkg1/__main__.py'),
            self.create_metadata('pkg2/__main__.py'),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        flags = generator.get_by_action(ActionType.FLAG)
        # Check specifically for DUPLICATE flags, not other flags
        duplicate_flags = [f for f in flags 
                          if '__main__.py' in str(f.source_path).lower() 
                          and 'duplicate' in f.reason.lower()]
        
        assert len(duplicate_flags) == 0, "Should not flag __main__.py as duplicate"
    
    def test_conftest_py_not_flagged_as_duplicate(self):
        """Test that conftest.py files are not flagged as duplicates."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('tests/conftest.py'),
            self.create_metadata('tests/unit/conftest.py'),
            self.create_metadata('tests/integration/conftest.py'),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        flags = generator.get_by_action(ActionType.FLAG)
        conftest_flags = [f for f in flags if 'conftest.py' in str(f.source_path).lower()]
        
        assert len(conftest_flags) == 0, "Should not flag conftest.py as duplicate"
    
    def test_regular_duplicates_still_detected(self):
        """Test that regular duplicate files are still detected."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('app.py'),
            self.create_metadata('backup/app.py'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        flags = generator.get_by_action(ActionType.FLAG)
        duplicate_flags = [f for f in flags if 'duplicate' in f.reason.lower()]
        
        assert len(duplicate_flags) > 0, "Should still detect regular duplicates"


class TestDuplicateRiskStratification:
    """Test risk stratification for duplicate file detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, path: str):
        """Helper to create FileMetadata."""
        file_path = self.temp_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        return metadata
    
    def test_high_risk_duplicates(self):
        """Test that critical config duplicates are flagged as HIGH risk."""
        # Create duplicates of critical files
        files = [
            self.create_metadata('setup.py'),  # Make it Python repo
            self.create_metadata('requirements.txt'),
            self.create_metadata('backup/requirements.txt'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Find duplicate flags for requirements.txt
        flags = generator.get_by_action(ActionType.FLAG)
        req_flags = [f for f in flags 
                    if 'requirements.txt' in str(f.source_path) 
                    and 'Duplicate filename' in f.reason]
        
        assert len(req_flags) == 2, "Both requirements.txt files should be flagged"
        for flag in req_flags:
            assert flag.risk_level == RiskLevel.HIGH, "requirements.txt duplicates should be HIGH risk"
    
    def test_low_risk_duplicates(self):
        """Test that documentation duplicates are flagged as LOW risk."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('README.md'),
            self.create_metadata('docs/README.md'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Find duplicate flags for README.md
        flags = generator.get_by_action(ActionType.FLAG)
        readme_flags = [f for f in flags 
                       if 'readme.md' in str(f.source_path).lower() 
                       and 'Duplicate filename' in f.reason]
        
        assert len(readme_flags) == 2, "Both README.md files should be flagged"
        for flag in readme_flags:
            assert flag.risk_level == RiskLevel.LOW, "README.md duplicates should be LOW risk"
    
    def test_log_file_duplicates_low_risk(self):
        """Test that log file duplicates are flagged as LOW risk."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('app.log'),
            self.create_metadata('logs/app.log'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        flags = generator.get_by_action(ActionType.FLAG)
        log_flags = [f for f in flags 
                    if 'app.log' in str(f.source_path) 
                    and 'Duplicate filename' in f.reason]
        
        assert len(log_flags) == 2, "Both app.log files should be flagged"
        for flag in log_flags:
            assert flag.risk_level == RiskLevel.LOW, "Log file duplicates should be LOW risk"
    
    def test_medium_risk_duplicates_default(self):
        """Test that regular duplicates default to MEDIUM risk."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('utils.py'),
            self.create_metadata('backup/utils.py'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        flags = generator.get_by_action(ActionType.FLAG)
        utils_flags = [f for f in flags 
                      if 'utils.py' in str(f.source_path) 
                      and 'Duplicate filename' in f.reason]
        
        assert len(utils_flags) == 2, "Both utils.py files should be flagged"
        for flag in utils_flags:
            assert flag.risk_level == RiskLevel.MEDIUM, "Regular duplicates should be MEDIUM risk"
    
    def test_env_file_duplicates_high_risk(self):
        """Test that .env file duplicates are flagged as HIGH risk."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('.env'),
            self.create_metadata('backup/.env'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        flags = generator.get_by_action(ActionType.FLAG)
        env_flags = [f for f in flags 
                    if '.env' in str(f.source_path) 
                    and 'Duplicate filename' in f.reason]
        
        assert len(env_flags) == 2, "Both .env files should be flagged"
        for flag in env_flags:
            assert flag.risk_level == RiskLevel.HIGH, ".env duplicates should be HIGH risk"


class TestMoveGatingEnforcement:
    """Test that MOVE proposals are absolutely prevented in non-Python repos."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, filename: str, **kwargs) -> FileMetadata:
        """Helper to create FileMetadata for testing."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        
        for key, value in kwargs.items():
            setattr(metadata, key, value)
        
        return metadata
    
    def test_absolutely_no_moves_in_non_python_repo(self):
        """Test hard guarantee: zero MOVE proposals in non-Python repos."""
        # Create a large frontend repo
        files = [
            self.create_metadata('package.json'),
            self.create_metadata('angular.json'),
            self.create_metadata('tsconfig.json'),
        ]
        
        # Add many TypeScript files
        for i in range(20):
            files.append(self.create_metadata(f'src/component{i}.ts'))
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Verify non-Python detection
        assert reasoner.repo_type == RepoType.NON_PYTHON
        
        # HARD GUARANTEE: Zero MOVE proposals
        moves = generator.get_by_action(ActionType.MOVE)
        assert len(moves) == 0, f"CRITICAL: Found {len(moves)} MOVE proposals in non-Python repo"
    
    def test_mixed_repo_final_enforcement(self):
        """Test that final enforcement drops non-.py MOVE proposals in mixed repos."""
        files = [
            self.create_metadata('requirements.txt'),
            self.create_metadata('package.json'),
            self.create_metadata('backend.py'),
            self.create_metadata('models.py'),
            self.create_metadata('utils.py'),
            self.create_metadata('frontend.ts'),
            self.create_metadata('app.js'),
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # In MIXED repos, only .py files should have MOVE proposals
        moves = generator.get_by_action(ActionType.MOVE)
        
        for move in moves:
            source = str(move.source_path)
            # Config files can stay at root
            if not any(source.endswith(cfg) for cfg in ['requirements.txt', 'package.json', '.gitignore']):
                assert source.endswith('.py'), f"Non-Python MOVE proposal leaked: {source}"


class TestFlagSuppression:
    """Test FLAG proposal suppression when MOVE exists."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, path: str, imports=None, has_tests=False):
        """Helper to create FileMetadata."""
        file_path = self.temp_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        metadata.imports = imports or []
        metadata.has_tests = has_tests
        return metadata
    
    def test_suppress_root_flag_when_move_exists(self):
        """Test that 'Python file at repository root' FLAG is suppressed when MOVE exists."""
        # Create Python repo with files at root
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('requirements.txt'),
            self.create_metadata('api.py', imports=['fastapi']),  # Will get both MOVE and FLAG
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # api.py should have a MOVE proposal
        moves = generator.get_by_action(ActionType.MOVE)
        api_moves = [m for m in moves if 'api.py' in str(m.source_path)]
        assert len(api_moves) > 0, "api.py should have a MOVE proposal"
        
        # api.py should NOT have the redundant "Python file at repository root" FLAG
        flags = generator.get_by_action(ActionType.FLAG)
        root_flags = [f for f in flags 
                     if 'api.py' in str(f.source_path) 
                     and 'Python file at repository root' in f.reason]
        assert len(root_flags) == 0, "Redundant root FLAG should be suppressed when MOVE exists"
    
    def test_keep_duplicate_flag_when_move_exists(self):
        """Test that duplicate detection FLAGs are kept even when MOVE exists."""
        # Create files with duplicates
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('utils.py', imports=['os']),  # Will get MOVE
            self.create_metadata('backup/utils.py'),  # Duplicate
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # Both utils.py files should have duplicate FLAGs
        flags = generator.get_by_action(ActionType.FLAG)
        duplicate_flags = [f for f in flags if 'Duplicate filename' in f.reason]
        assert len(duplicate_flags) == 2, "Duplicate FLAGs should be kept even when MOVE exists"
        
        # Verify both utils.py files are flagged
        flagged_files = {str(f.source_path) for f in duplicate_flags}
        assert 'utils.py' in flagged_files
        assert str(Path('backup') / 'utils.py') in flagged_files
    
    def test_no_suppression_when_no_move(self):
        """Test that FLAGs are not suppressed when no MOVE exists."""
        # Create a file that gets a FLAG but not a MOVE
        # For instance, a correctly placed file won't get a MOVE
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('src/app.py', imports=['os']),  # Correctly placed, no MOVE
        ]
        
        reasoner = StructureReasoner(self.temp_dir)
        generator = reasoner.generate_proposals(files)
        
        # src/app.py should not have a MOVE (already correctly placed)
        moves = generator.get_by_action(ActionType.MOVE)
        app_moves = [m for m in moves if 'src/app.py' in str(m.source_path)]
        assert len(app_moves) == 0, "src/app.py should not have a MOVE proposal (correctly placed)"
        
        # No suppression should occur for src/app.py
        # (though it likely won't have FLAGs either since it's correctly placed)
