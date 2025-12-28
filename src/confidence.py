"""Confidence scoring for reorganization proposals.

V2.4: Provides a single HIGH/MEDIUM/LOW verdict with explainable reasons.
Read-only advisory - no execution blocking.
"""
from enum import Enum
from typing import List, Tuple
from pathlib import Path

from .proposal import Proposal, ActionType, RiskLevel
from .repo_type import RepoType


class ConfidenceLevel(Enum):
    """Overall confidence level for reorganization."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ConfidenceScore:
    """Calculates and explains reorganization confidence."""
    
    def __init__(self, proposals: List[Proposal], repo_type: RepoType = None, 
                 has_tests: bool = False, import_warnings_count: int = 0,
                 is_dry_run: bool = True):
        """Initialize confidence scorer.
        
        Args:
            proposals: List of all proposals (MOVE and FLAG)
            repo_type: Repository type (python_dominant, non_python, etc)
            has_tests: Whether tests were detected in repository
            import_warnings_count: Number of import breakage warnings
            is_dry_run: Whether running in dry-run mode (safer than execute)
        """
        self.proposals = proposals
        self.repo_type = repo_type
        self.has_tests = has_tests
        self.import_warnings_count = import_warnings_count
        self.is_dry_run = is_dry_run
        
        # Extract move proposals and risk breakdown
        self.move_proposals = [p for p in proposals if p.action == ActionType.MOVE]
        self.high_risk_moves = [p for p in self.move_proposals if p.risk_level == RiskLevel.HIGH]
        self.medium_risk_moves = [p for p in self.move_proposals if p.risk_level == RiskLevel.MEDIUM]
        self.low_risk_moves = [p for p in self.move_proposals if p.risk_level == RiskLevel.LOW]
        
        # Calculate confidence
        self.confidence_level = self._calculate_confidence()
        self.positive_factors, self.risk_factors = self._collect_factors()
    
    def _calculate_confidence(self) -> ConfidenceLevel:
        """Calculate confidence level using simple thresholds.
        
        Returns:
            ConfidenceLevel (HIGH, MEDIUM, or LOW)
        """
        # Start with base score
        score = 100
        
        # Penalty for non-Python repos (higher risk)
        if self.repo_type and self.repo_type == RepoType.NON_PYTHON:
            score -= 30
        
        # Penalty for high-risk moves
        if len(self.high_risk_moves) > 0:
            score -= 20 * min(len(self.high_risk_moves), 3)  # Cap at 60 penalty
        
        # Penalty for medium-risk moves
        if len(self.medium_risk_moves) > 5:
            score -= 15
        elif len(self.medium_risk_moves) > 10:
            score -= 25
        
        # Penalty for import breakage warnings
        if self.import_warnings_count > 0:
            score -= 10 * min(self.import_warnings_count, 3)  # Cap at 30 penalty
        
        # Penalty for no tests (harder to validate changes)
        if not self.has_tests and len(self.move_proposals) > 0:
            score -= 10
        
        # Bonus for dry-run mode (safer)
        if self.is_dry_run:
            score += 5
        
        # Penalty for too many changes at once
        if len(self.move_proposals) > 20:
            score -= 15
        
        # Convert score to confidence level
        if score >= 70:
            return ConfidenceLevel.HIGH
        elif score >= 40:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _collect_factors(self) -> Tuple[List[str], List[str]]:
        """Collect positive and risk factors for explainability.
        
        Returns:
            Tuple of (positive_factors, risk_factors) as string lists
        """
        positives = []
        risks = []
        
        # Repo type factor
        if self.repo_type:
            if self.repo_type == RepoType.PYTHON_DOMINANT:
                positives.append("Python-dominant repository")
            elif self.repo_type == RepoType.NON_PYTHON:
                risks.append("Non-Python repository (higher risk)")
            else:
                positives.append(f"{self.repo_type.value} repository")
        
        # Test presence
        if self.has_tests:
            positives.append("Tests detected (easier to validate changes)")
        elif len(self.move_proposals) > 0:
            risks.append("No tests detected (harder to validate)")
        
        # Move proposal count
        move_count = len(self.move_proposals)
        if move_count == 0:
            positives.append("No structural changes proposed")
        elif move_count <= 5:
            positives.append(f"Small number of changes ({move_count} moves)")
        elif move_count <= 15:
            risks.append(f"Moderate number of changes ({move_count} moves)")
        else:
            risks.append(f"Large number of changes ({move_count} moves)")
        
        # Risk level breakdown
        if len(self.high_risk_moves) > 0:
            risks.append(f"{len(self.high_risk_moves)} high-risk moves")
        
        if len(self.medium_risk_moves) > 0:
            risks.append(f"{len(self.medium_risk_moves)} medium-risk moves")
        
        if len(self.low_risk_moves) > 0 and len(self.high_risk_moves) == 0 and len(self.medium_risk_moves) == 0:
            positives.append(f"All moves are low-risk ({len(self.low_risk_moves)} moves)")
        
        # Import warnings
        if self.import_warnings_count > 0:
            risks.append(f"{self.import_warnings_count} potential import breakage(s)")
        elif move_count > 0:
            positives.append("No import breakage warnings")
        
        # Dry-run mode
        if self.is_dry_run:
            positives.append("Dry-run mode (simulation only)")
        
        return positives, risks
    
    def to_text(self) -> str:
        """Render confidence score as formatted text.
        
        Returns:
            Formatted confidence score with verdict and reasons
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"📊 REORGANIZATION CONFIDENCE: {self.confidence_level.value}")
        lines.append("=" * 60)
        lines.append("")
        
        if self.positive_factors:
            lines.append("Positive factors:")
            for factor in self.positive_factors:
                lines.append(f"  ✔ {factor}")
        
        if self.risk_factors:
            if self.positive_factors:
                lines.append("")
            lines.append("Risk factors:")
            for factor in self.risk_factors:
                lines.append(f"  ⚠ {factor}")
        
        lines.append("")
        
        # Add interpretation
        if self.confidence_level == ConfidenceLevel.HIGH:
            lines.append("Interpretation: Changes appear safe to apply.")
        elif self.confidence_level == ConfidenceLevel.MEDIUM:
            lines.append("Interpretation: Review changes carefully before applying.")
        else:
            lines.append("Interpretation: High risk - consider smaller batches or manual review.")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def get_summary(self) -> dict:
        """Get confidence summary as dictionary.
        
        Returns:
            Dictionary with confidence data
        """
        return {
            "confidence_level": self.confidence_level.value,
            "positive_factors": self.positive_factors,
            "risk_factors": self.risk_factors,
            "move_count": len(self.move_proposals),
            "high_risk_count": len(self.high_risk_moves),
            "medium_risk_count": len(self.medium_risk_moves),
            "low_risk_count": len(self.low_risk_moves),
            "import_warnings_count": self.import_warnings_count,
            "has_tests": self.has_tests,
            "is_dry_run": self.is_dry_run
        }
