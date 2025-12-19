"""Tests for the proposal executor module (V2.1)."""
import tempfile
import shutil
from pathlib import Path
import json
import pytest

from src.executor import ProposalExecutor, ExecutionResult
from src.proposal import Proposal, ActionType, RiskLevel


class TestExecutionResult:
    """Test ExecutionResult dataclass."""
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('tests/test.py'),
            reason="Test file",
            risk_level=RiskLevel.MEDIUM
        )
        
        result = ExecutionResult(
            proposal=proposal,
            success=True,
            message="Moved successfully"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['action'] == 'move'
        assert result_dict['source'] == 'test.py'
        assert 'test.py' in result_dict['target']  # Platform-independent path check
        assert result_dict['success'] is True
        assert result_dict['skipped'] is False
        assert result_dict['risk'] == 'medium'
        assert 'timestamp' in result_dict


class TestProposalExecutor:
    """Test ProposalExecutor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / 'test.py'
        self.test_file.write_text('print("test")')
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_executor_initialization(self):
        """Test executor initializes correctly."""
        executor = ProposalExecutor(self.temp_dir, dry_run=True)
        
        assert executor.repo_path == self.temp_dir
        assert executor.dry_run is True
        assert len(executor.results) == 0
        assert executor.log_file == self.temp_dir / '.repo-tool-history.json'
    
    def test_dry_run_mode_no_filesystem_changes(self):
        """Test dry-run mode doesn't modify filesystem."""
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('src/test.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=True)
        result = executor.execute_proposal(proposal)
        
        assert result.success is True
        assert "[DRY-RUN]" in result.message
        assert self.test_file.exists()  # Original file still exists
        assert not (self.temp_dir / 'src' / 'test.py').exists()  # Target not created
    
    def test_execute_mode_moves_file(self):
        """Test execute mode actually moves files."""
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('src/test.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        result = executor.execute_proposal(proposal)
        
        assert result.success is True
        assert "Moved" in result.message
        assert not self.test_file.exists()  # Original file moved
        assert (self.temp_dir / 'src' / 'test.py').exists()  # Target created
    
    def test_validation_source_not_exists(self):
        """Test validation fails if source doesn't exist."""
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('nonexistent.py'),
            target_path=Path('src/nonexistent.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        result = executor.execute_proposal(proposal)
        
        assert result.success is False
        assert "does not exist" in result.message.lower()
    
    def test_validation_target_already_exists(self):
        """Test validation fails if target already exists (conflict)."""
        # Create target file
        target_dir = self.temp_dir / 'src'
        target_dir.mkdir()
        target_file = target_dir / 'test.py'
        target_file.write_text('existing')
        
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('src/test.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        result = executor.execute_proposal(proposal)
        
        assert result.success is False
        assert "already exists" in result.message.lower()
    
    def test_creates_target_directory(self):
        """Test executor creates target directory if needed."""
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('deeply/nested/dir/test.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        result = executor.execute_proposal(proposal)
        
        assert result.success is True
        assert (self.temp_dir / 'deeply' / 'nested' / 'dir' / 'test.py').exists()
    
    def test_unsupported_action_type(self):
        """Test that non-MOVE actions are rejected."""
        proposal = Proposal(
            action=ActionType.FLAG,
            source_path=Path('test.py'),
            target_path=None,
            reason="Test flag",
            risk_level=RiskLevel.HIGH
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        result = executor.execute_proposal(proposal)
        
        assert result.success is False
        assert result.skipped is True
        assert "Unsupported action" in result.message
    
    def test_save_history(self):
        """Test execution history is saved correctly."""
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('src/test.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        executor.execute_proposal(proposal)
        executor.save_history()
        
        log_file = self.temp_dir / '.repo-tool-history.json'
        assert log_file.exists()
        
        with open(log_file) as f:
            history = json.load(f)
        
        assert len(history) == 1
        assert history[0]['action'] == 'move'
        assert history[0]['source'] == 'test.py'
        assert history[0]['success'] is True
    
    def test_get_summary(self):
        """Test execution summary calculation."""
        proposals = [
            Proposal(ActionType.MOVE, Path('file1.py'), Path('src/file1.py'), "Move", RiskLevel.LOW),
            Proposal(ActionType.MOVE, Path('file2.py'), Path('src/file2.py'), "Move", RiskLevel.LOW),
            Proposal(ActionType.FLAG, Path('file3.py'), None, "Flag", RiskLevel.HIGH),  # Will be skipped
        ]
        
        # Create test files
        (self.temp_dir / 'file1.py').write_text('test')
        (self.temp_dir / 'file2.py').write_text('test')
        
        executor = ProposalExecutor(self.temp_dir, dry_run=True)
        
        for proposal in proposals:
            executor.execute_proposal(proposal)
        
        summary = executor.get_summary()
        
        assert summary['total'] == 3
        assert summary['successful'] == 2  # 2 MOVEs succeeded
        assert summary['skipped'] == 1  # FLAG was skipped
        assert summary['failed'] == 0
        assert summary['dry_run'] is True
    
    def test_multiple_executions_append_history(self):
        """Test that multiple executions append to history."""
        proposal1 = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('src/test.py'),
            reason="First move",
            risk_level=RiskLevel.LOW
        )
        
        # First execution
        executor1 = ProposalExecutor(self.temp_dir, dry_run=False)
        executor1.execute_proposal(proposal1)
        executor1.save_history()
        
        # Create another test file
        test_file2 = self.temp_dir / 'test2.py'
        test_file2.write_text('test2')
        
        proposal2 = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test2.py'),
            target_path=Path('src/test2.py'),
            reason="Second move",
            risk_level=RiskLevel.LOW
        )
        
        # Second execution
        executor2 = ProposalExecutor(self.temp_dir, dry_run=False)
        executor2.execute_proposal(proposal2)
        executor2.save_history()
        
        # Check history
        log_file = self.temp_dir / '.repo-tool-history.json'
        with open(log_file) as f:
            history = json.load(f)
        
        assert len(history) == 2
        assert history[0]['source'] == 'test.py'
        assert history[1]['source'] == 'test2.py'


class TestExecutorEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_source_path_none(self):
        """Test validation fails gracefully with None source path."""
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=None,
            target_path=Path('target.py'),
            reason="Test",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        result = executor.execute_proposal(proposal)
        
        assert result.success is False
        assert "Source path is None" in result.message
    
    def test_target_path_none(self):
        """Test validation fails gracefully with None target path."""
        test_file = self.temp_dir / 'test.py'
        test_file.write_text('test')
        
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=None,
            reason="Test",
            risk_level=RiskLevel.LOW
        )
        
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        result = executor.execute_proposal(proposal)
        
        assert result.success is False
        assert "Target path is None" in result.message
