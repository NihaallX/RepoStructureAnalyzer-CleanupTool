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


class TestRollback:
    """Test rollback (undo) functionality (V2.2)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_rollback_dry_run_no_changes(self):
        """Test rollback dry-run makes no filesystem changes."""
        # Create initial file and execute move
        test_file = self.temp_dir / 'test.py'
        test_file.write_text('test')
        
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('src/test.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        # Execute move
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        executor.execute_proposal(proposal)
        executor.save_history()
        
        # Verify move happened
        assert not test_file.exists()
        assert (self.temp_dir / 'src' / 'test.py').exists()
        
        # Rollback in dry-run mode
        rollback_executor = ProposalExecutor(self.temp_dir, dry_run=True)
        results = rollback_executor.rollback_moves(count=1)
        
        # Verify dry-run didn't change filesystem
        assert len(results) == 1
        assert results[0].success is True
        assert "DRY-RUN" in results[0].message
        assert not test_file.exists()  # Still doesn't exist
        assert (self.temp_dir / 'src' / 'test.py').exists()  # Still exists
    
    def test_rollback_execute_restores_files(self):
        """Test rollback execution actually restores files to original location."""
        # Create initial file and execute move
        test_file = self.temp_dir / 'test.py'
        test_file.write_text('test content')
        
        proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path('test.py'),
            target_path=Path('src/test.py'),
            reason="Test move",
            risk_level=RiskLevel.LOW
        )
        
        # Execute move
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        executor.execute_proposal(proposal)
        executor.save_history()
        
        # Verify move happened
        assert not test_file.exists()
        target = self.temp_dir / 'src' / 'test.py'
        assert target.exists()
        assert target.read_text() == 'test content'
        
        # Rollback in execute mode
        rollback_executor = ProposalExecutor(self.temp_dir, dry_run=False)
        results = rollback_executor.rollback_moves(count=1)
        
        # Verify rollback succeeded
        assert len(results) == 1
        assert results[0].success is True
        assert "Rolled back" in results[0].message
        
        # Verify file restored to original location
        assert test_file.exists()
        assert test_file.read_text() == 'test content'
        assert not target.exists()
    
    def test_rollback_multiple_operations_lifo(self):
        """Test rollback handles multiple operations in LIFO order."""
        # Create and move multiple files
        files = []
        for i in range(3):
            test_file = self.temp_dir / f'test{i}.py'
            test_file.write_text(f'test {i}')
            files.append(test_file)
        
        # Execute moves
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        for i, test_file in enumerate(files):
            proposal = Proposal(
                action=ActionType.MOVE,
                source_path=Path(f'test{i}.py'),
                target_path=Path(f'src/test{i}.py'),
                reason="Test move",
                risk_level=RiskLevel.LOW
            )
            executor.execute_proposal(proposal)
        executor.save_history()
        
        # Verify all moved
        for test_file in files:
            assert not test_file.exists()
        
        # Rollback last 2 operations
        rollback_executor = ProposalExecutor(self.temp_dir, dry_run=False)
        results = rollback_executor.rollback_moves(count=2)
        
        # Verify 2 rollbacks succeeded
        assert len(results) == 2
        assert all(r.success for r in results)
        
        # Verify test2.py and test1.py restored (LIFO order)
        assert (self.temp_dir / 'test2.py').exists()
        assert (self.temp_dir / 'test1.py').exists()
        assert not (self.temp_dir / 'test0.py').exists()  # Not rolled back
    
    def test_rollback_validation_target_not_exists(self):
        """Test rollback fails if target file doesn't exist."""
        # Create history manually with fake entry
        history = [{
            'timestamp': '2025-12-19T12:00:00',
            'action': 'MOVE',
            'source': 'test.py',
            'target': 'src/test.py',
            'success': True,
            'skipped': False,
            'risk': 'low',
            'message': 'Moved'
        }]
        
        history_file = self.temp_dir / '.repo-tool-history.json'
        with open(history_file, 'w') as f:
            json.dump(history, f)
        
        # Target doesn't exist (file was never actually moved)
        # Rollback should fail validation
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        results = executor.rollback_moves(count=1)
        
        assert len(results) == 1
        assert results[0].success is False
        assert "Target file does not exist" in results[0].message
    
    def test_rollback_validation_source_already_exists(self):
        """Test rollback fails if source location already has a file (conflict)."""
        # Create initial file and move it
        test_file = self.temp_dir / 'test.py'
        test_file.write_text('original')
        
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
        
        # Create a conflicting file at original location
        test_file.write_text('conflict')
        
        # Rollback should fail due to conflict
        rollback_executor = ProposalExecutor(self.temp_dir, dry_run=False)
        results = rollback_executor.rollback_moves(count=1)
        
        assert len(results) == 1
        assert results[0].success is False
        assert "already exists (conflict)" in results[0].message
    
    def test_rollback_logs_to_history(self):
        """Test rollback operations are logged to history."""
        # Create and move file
        test_file = self.temp_dir / 'test.py'
        test_file.write_text('test')
        
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
        
        # Rollback
        rollback_executor = ProposalExecutor(self.temp_dir, dry_run=False)
        rollback_executor.rollback_moves(count=1)
        
        # Check history
        history_file = self.temp_dir / '.repo-tool-history.json'
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        # Should have 2 entries: original MOVE and ROLLBACK
        assert len(history) == 2
        assert history[0]['action'].upper() == 'MOVE'
        assert history[1]['action'].upper() == 'ROLLBACK'
        assert history[1]['success'] is True
    
    def test_rollback_no_history_file(self):
        """Test rollback handles missing history file gracefully."""
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        results = executor.rollback_moves(count=1)
        
        assert len(results) == 0
    
    def test_rollback_only_undoes_successful_moves(self):
        """Test rollback only processes successful MOVE operations."""
        # Create history with mixed entries
        history = [
            {
                'timestamp': '2025-12-19T12:00:00',
                'action': 'MOVE',
                'source': 'test1.py',
                'target': 'src/test1.py',
                'success': True,
                'skipped': False,
                'risk': 'low',
                'message': 'Moved'
            },
            {
                'timestamp': '2025-12-19T12:01:00',
                'action': 'MOVE',
                'source': 'test2.py',
                'target': 'src/test2.py',
                'success': False,  # Failed move
                'skipped': False,
                'risk': 'low',
                'message': 'Failed'
            },
            {
                'timestamp': '2025-12-19T12:02:00',
                'action': 'FLAG',  # Non-MOVE action
                'source': 'test3.py',
                'target': None,
                'success': True,
                'skipped': False,
                'risk': 'low',
                'message': 'Flagged'
            }
        ]
        
        # Create only the successfully moved file
        moved_file = self.temp_dir / 'src' / 'test1.py'
        moved_file.parent.mkdir(parents=True)
        moved_file.write_text('test1')
        
        history_file = self.temp_dir / '.repo-tool-history.json'
        with open(history_file, 'w') as f:
            json.dump(history, f)
        
        # Rollback should only process the successful MOVE
        executor = ProposalExecutor(self.temp_dir, dry_run=False)
        results = executor.rollback_moves(count=10)  # Request more than available
        
        # Should only rollback the one successful MOVE
        assert len(results) == 1
        assert (self.temp_dir / 'test1.py').exists()

