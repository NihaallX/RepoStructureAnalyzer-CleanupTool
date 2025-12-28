"""Tests for confidence scoring module (V2.4)."""
import pytest
from pathlib import Path

from src.confidence import ConfidenceScore, ConfidenceLevel
from src.proposal import Proposal, ActionType, RiskLevel
from src.repo_type import RepoType


@pytest.fixture
def sample_proposals():
    """Create sample proposals for testing."""
    return [
        Proposal(
            action=ActionType.MOVE,
            source_path=Path("test_file.py"),
            target_path=Path("tests/test_file.py"),
            reason="Misplaced test file",
            risk_level=RiskLevel.LOW,
            details={}
        ),
        Proposal(
            action=ActionType.MOVE,
            source_path=Path("utils.py"),
            target_path=Path("src/utils.py"),
            reason="Misplaced source file",
            risk_level=RiskLevel.MEDIUM,
            details={}
        ),
        Proposal(
            action=ActionType.FLAG,
            source_path=Path("duplicate.py"),
            target_path=None,
            reason="Duplicate file",
            risk_level=RiskLevel.HIGH,
            details={}
        )
    ]


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""
    
    def test_confidence_levels_exist(self):
        """Test that all confidence levels are defined."""
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.LOW.value == "LOW"


class TestConfidenceScore:
    """Tests for ConfidenceScore class."""
    
    def test_high_confidence_python_repo_low_risk(self, sample_proposals):
        """Test high confidence for Python repo with low-risk moves."""
        low_risk_proposals = [p for p in sample_proposals if p.risk_level == RiskLevel.LOW]
        
        confidence = ConfidenceScore(
            proposals=low_risk_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        assert confidence.confidence_level == ConfidenceLevel.HIGH
        assert len(confidence.positive_factors) > 0
    
    def test_medium_confidence_medium_risk_moves(self, sample_proposals):
        """Test medium confidence with medium-risk moves."""
        confidence = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=2,
            is_dry_run=True
        )
        
        # Should be medium due to import warnings and mixed risk levels
        assert confidence.confidence_level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
    
    def test_low_confidence_high_risk_moves(self):
        """Test low confidence with high-risk moves."""
        high_risk_proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path(f"file{i}.py"),
                target_path=Path(f"new/file{i}.py"),
                reason="Test",
                risk_level=RiskLevel.HIGH,
                details={}
            )
            for i in range(5)
        ]
        
        confidence = ConfidenceScore(
            proposals=high_risk_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=False,
            import_warnings_count=5,
            is_dry_run=False
        )
        
        assert confidence.confidence_level == ConfidenceLevel.LOW
    
    def test_non_python_repo_lowers_confidence(self, sample_proposals):
        """Test that non-Python repos have lower confidence."""
        confidence = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.NON_PYTHON,
            has_tests=False,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        # Non-Python should have lower confidence
        assert confidence.confidence_level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]
        assert any("Non-Python" in factor for factor in confidence.risk_factors)
    
    def test_no_tests_is_risk_factor(self, sample_proposals):
        """Test that missing tests is a risk factor."""
        confidence = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=False,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        # Should mention lack of tests
        assert any("test" in factor.lower() for factor in confidence.risk_factors)
    
    def test_import_warnings_affect_confidence(self, sample_proposals):
        """Test that import warnings lower confidence."""
        confidence_no_warnings = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        confidence_with_warnings = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=5,
            is_dry_run=True
        )
        
        # More warnings should lower or maintain confidence level
        confidence_order = [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
        no_warn_idx = confidence_order.index(confidence_no_warnings.confidence_level)
        with_warn_idx = confidence_order.index(confidence_with_warnings.confidence_level)
        
        assert with_warn_idx <= no_warn_idx
    
    def test_many_moves_lowers_confidence(self):
        """Test that many moves lower confidence."""
        many_proposals = [
            Proposal(
                action=ActionType.MOVE,
                source_path=Path(f"file{i}.py"),
                target_path=Path(f"new/file{i}.py"),
                reason="Test",
                risk_level=RiskLevel.LOW,
                details={}
            )
            for i in range(25)
        ]
        
        confidence = ConfidenceScore(
            proposals=many_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        # Many moves should be flagged
        assert any("Large number" in factor or "changes" in factor 
                  for factor in confidence.risk_factors)
    
    def test_no_proposals_high_confidence(self):
        """Test that no changes give high confidence."""
        confidence = ConfidenceScore(
            proposals=[],
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        assert confidence.confidence_level == ConfidenceLevel.HIGH
        assert any("No structural changes" in factor for factor in confidence.positive_factors)
    
    def test_to_text_includes_verdict(self, sample_proposals):
        """Test that text output includes verdict and reasons."""
        confidence = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        text = confidence.to_text()
        
        assert "REORGANIZATION CONFIDENCE" in text
        assert confidence.confidence_level.value in text
        assert "Positive factors:" in text or "Risk factors:" in text
        assert "Interpretation:" in text
    
    def test_get_summary_returns_dict(self, sample_proposals):
        """Test that get_summary returns comprehensive data."""
        confidence = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=2,
            is_dry_run=True
        )
        
        summary = confidence.get_summary()
        
        assert "confidence_level" in summary
        assert "positive_factors" in summary
        assert "risk_factors" in summary
        assert "move_count" in summary
        assert "high_risk_count" in summary
        assert "medium_risk_count" in summary
        assert "low_risk_count" in summary
        assert "import_warnings_count" in summary
        assert "has_tests" in summary
        assert "is_dry_run" in summary
        
        # Verify counts
        assert summary["move_count"] == 2  # 2 MOVE proposals
        assert summary["import_warnings_count"] == 2
        assert summary["has_tests"] is True
        assert summary["is_dry_run"] is True


class TestConfidenceEdgeCases:
    """Tests for edge cases in confidence scoring."""
    
    def test_none_repo_type(self, sample_proposals):
        """Test handling of None repo type."""
        confidence = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=None,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        # Should still generate confidence
        assert confidence.confidence_level in [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW
        ]
    
    def test_execute_mode_affects_confidence(self, sample_proposals):
        """Test that execute mode affects confidence differently."""
        confidence_dry_run = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=True
        )
        
        confidence_execute = ConfidenceScore(
            proposals=sample_proposals,
            repo_type=RepoType.PYTHON_DOMINANT,
            has_tests=True,
            import_warnings_count=0,
            is_dry_run=False
        )
        
        # Dry-run should mention it in positive factors
        assert any("Dry-run" in factor for factor in confidence_dry_run.positive_factors)
        assert not any("Dry-run" in factor for factor in confidence_execute.positive_factors)
