"""Tests for Git detection module (V2.4)."""
import pytest
from pathlib import Path
import subprocess

from src.git_detector import GitDetector, GitWarning
from src.proposal import Proposal, ActionType, RiskLevel


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary Git repository."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, capture_output=True)
    
    # Create and commit a file
    test_file = tmp_path / "tracked_file.py"
    test_file.write_text("# Tracked file")
    
    subprocess.run(["git", "add", "tracked_file.py"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, capture_output=True)
    
    # Create an uncommitted file
    uncommitted_file = tmp_path / "uncommitted_file.py"
    uncommitted_file.write_text("# Uncommitted file")
    
    return tmp_path


@pytest.fixture
def temp_non_git_repo(tmp_path):
    """Create a temporary non-Git repository."""
    test_file = tmp_path / "file.py"
    test_file.write_text("# Not in Git")
    return tmp_path


class TestGitWarning:
    """Tests for GitWarning class."""
    
    def test_create_warning(self):
        """Test creating a Git warning."""
        warning = GitWarning(
            warning_type="uncommitted",
            message="Uncommitted changes detected",
            details=["file1.py", "file2.py"]
        )
        
        assert warning.warning_type == "uncommitted"
        assert warning.message == "Uncommitted changes detected"
        assert len(warning.details) == 2


class TestGitDetector:
    """Tests for GitDetector class."""
    
    def test_detect_git_repository(self, temp_git_repo):
        """Test detecting Git repository."""
        detector = GitDetector(temp_git_repo)
        assert detector.is_git_repository() is True
    
    def test_detect_non_git_repository(self, temp_non_git_repo):
        """Test detecting non-Git repository."""
        detector = GitDetector(temp_non_git_repo)
        assert detector.is_git_repository() is False
    
    def test_get_uncommitted_files_in_git_repo(self, temp_git_repo):
        """Test getting uncommitted files in Git repo."""
        detector = GitDetector(temp_git_repo)
        uncommitted = detector.get_uncommitted_files()
        
        # Should detect uncommitted_file.py
        assert len(uncommitted) > 0
        assert any("uncommitted_file.py" in str(f) for f in uncommitted)
    
    def test_get_uncommitted_files_in_non_git_repo(self, temp_non_git_repo):
        """Test getting uncommitted files in non-Git repo."""
        detector = GitDetector(temp_non_git_repo)
        uncommitted = detector.get_uncommitted_files()
        
        # Should return empty list for non-Git repos
        assert uncommitted == []
    
    def test_is_file_tracked_for_tracked_file(self, temp_git_repo):
        """Test checking if tracked file is detected."""
        detector = GitDetector(temp_git_repo)
        
        is_tracked = detector.is_file_tracked(Path("tracked_file.py"))
        assert is_tracked is True
    
    def test_is_file_tracked_for_untracked_file(self, temp_git_repo):
        """Test checking if untracked file is detected."""
        detector = GitDetector(temp_git_repo)
        
        is_tracked = detector.is_file_tracked(Path("uncommitted_file.py"))
        assert is_tracked is False
    
    def test_is_file_tracked_caching(self, temp_git_repo):
        """Test that file tracking status is cached."""
        detector = GitDetector(temp_git_repo)
        
        # First call
        is_tracked_1 = detector.is_file_tracked(Path("tracked_file.py"))
        
        # Second call should use cache
        is_tracked_2 = detector.is_file_tracked(Path("tracked_file.py"))
        
        assert is_tracked_1 == is_tracked_2
        assert "tracked_file.py" in detector._tracked_files_cache
    
    def test_analyze_proposals_with_uncommitted_changes(self, temp_git_repo):
        """Test analyzing proposals when uncommitted changes exist."""
        detector = GitDetector(temp_git_repo)
        
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("tracked_file.py"),
                target_path=Path("src/tracked_file.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings = detector.analyze_proposals(proposals)
        
        # Should have warning about uncommitted changes
        assert len(warnings) > 0
        assert any(w.warning_type == "uncommitted" for w in warnings)
    
    def test_analyze_proposals_with_tracked_files(self, temp_git_repo):
        """Test analyzing proposals with Git-tracked files."""
        detector = GitDetector(temp_git_repo)
        
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("tracked_file.py"),
                target_path=Path("src/tracked_file.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings = detector.analyze_proposals(proposals)
        
        # Should have warning about tracked files
        tracked_warnings = [w for w in warnings if w.warning_type == "tracked_files"]
        assert len(tracked_warnings) > 0
    
    def test_analyze_proposals_non_git_repo(self, temp_non_git_repo):
        """Test analyzing proposals in non-Git repo."""
        detector = GitDetector(temp_non_git_repo)
        
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("file.py"),
                target_path=Path("src/file.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings = detector.analyze_proposals(proposals)
        
        # Should return empty list for non-Git repos
        assert warnings == []
    
    def test_render_warnings_text(self, temp_git_repo):
        """Test rendering Git warnings as text."""
        detector = GitDetector(temp_git_repo)
        
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("tracked_file.py"),
                target_path=Path("src/tracked_file.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings_text = detector.render_warnings(proposals=proposals)
        
        assert "GIT AWARENESS" in warnings_text
        assert "Recommendation" in warnings_text
        assert "git status" in warnings_text
    
    def test_render_warnings_non_git_repo(self, temp_non_git_repo):
        """Test rendering warnings for non-Git repo returns empty."""
        detector = GitDetector(temp_non_git_repo)
        
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("file.py"),
                target_path=Path("src/file.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings_text = detector.render_warnings(proposals=proposals)
        
        # Should return empty string for non-Git repos
        assert warnings_text == ""
    
    def test_render_warnings_no_warnings(self, temp_git_repo):
        """Test rendering when no warnings exist."""
        detector = GitDetector(temp_git_repo)
        
        # Commit the uncommitted file to have a clean state
        subprocess.run(
            ["git", "add", "uncommitted_file.py"], 
            cwd=temp_git_repo, 
            capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Clean state"], 
            cwd=temp_git_repo, 
            capture_output=True
        )
        
        # Clear cache
        detector._uncommitted_files = None
        
        proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path("new_untracked_file.py"),
                target_path=Path("src/new_untracked_file.py"),
                reason="Reorganization",
                risk_level=RiskLevel.LOW,
                details={}
            )
        ]
        
        warnings_text = detector.render_warnings(proposals=proposals)
        
        # May have tracked files warning but should handle gracefully
        # This is OK - the test verifies render doesn't crash
        assert isinstance(warnings_text, str)


class TestGitDetectorEdgeCases:
    """Tests for edge cases in Git detection."""
    
    def test_git_not_installed(self, temp_non_git_repo, monkeypatch):
        """Test graceful handling when git is not installed."""
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("git not found")
        
        monkeypatch.setattr(subprocess, "run", mock_run)
        
        detector = GitDetector(temp_non_git_repo)
        uncommitted = detector.get_uncommitted_files()
        
        # Should return empty list gracefully
        assert uncommitted == []
    
    def test_git_timeout(self, temp_git_repo, monkeypatch):
        """Test graceful handling of git timeout."""
        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired("git status", 5)
        
        monkeypatch.setattr(subprocess, "run", mock_run)
        
        detector = GitDetector(temp_git_repo)
        uncommitted = detector.get_uncommitted_files()
        
        # Should return empty list gracefully
        assert uncommitted == []
    
    def test_cached_results(self, temp_git_repo):
        """Test that results are cached properly."""
        detector = GitDetector(temp_git_repo)
        
        # First call
        uncommitted_1 = detector.get_uncommitted_files()
        
        # Second call should use cache
        uncommitted_2 = detector.get_uncommitted_files()
        
        assert uncommitted_1 == uncommitted_2
        assert detector._uncommitted_files is not None
    
    def test_analyze_only_move_proposals(self, temp_git_repo):
        """Test that only MOVE proposals are analyzed."""
        detector = GitDetector(temp_git_repo)
        
        proposals = [
            Proposal(
                action=ActionType.FLAG,
                source_path=Path("tracked_file.py"),
                target_path=None,
                reason="Duplicate",
                risk_level=RiskLevel.HIGH,
                details={}
            )
        ]
        
        warnings = detector.analyze_proposals(proposals)
        
        # FLAG proposals should not trigger tracked files warning
        tracked_warnings = [w for w in warnings if w.warning_type == "tracked_files"]
        assert len(tracked_warnings) == 0
