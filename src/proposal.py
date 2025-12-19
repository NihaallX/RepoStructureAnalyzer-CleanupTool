"""Proposal generation and output formatting."""
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict
import json
from pathlib import Path


class RiskLevel(Enum):
    """Risk level for proposed changes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(Enum):
    """Type of action to perform."""
    MOVE = "move"
    DELETE = "delete"
    FLAG = "flag"


@dataclass
class Proposal:
    """A proposed structural change."""
    action: ActionType
    source_path: Path
    target_path: Path = None
    reason: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    details: Dict = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "source": str(self.source_path),
            "target": str(self.target_path) if self.target_path else None,
            "reason": self.reason,
            "risk": self.risk_level.value,
            "details": self.details or {},
        }
    
    def to_text(self) -> str:
        """Convert to human-readable text."""
        lines = []
        lines.append(f"{self.action.value.upper()}: {self.source_path}")
        if self.target_path:
            lines.append(f"    → {self.target_path}")
        lines.append(f"REASON: {self.reason}")
        lines.append(f"RISK: {self.risk_level.value.upper()}")
        if self.details:
            # Special handling for grouped duplicates
            if 'examples' in self.details:
                lines.append(f"  Examples:")
                for example in self.details['examples']:
                    lines.append(f"    - {example}")
                if 'remaining' in self.details:
                    lines.append(f"    ({self.details['remaining']})")
            else:
                # Regular details
                for key, value in self.details.items():
                    # Skip internal keys used for grouping
                    if key not in ('all_duplicates',):
                        lines.append(f"  {key}: {value}")
        return '\n'.join(lines)


class ProposalGenerator:
    """Generates output for proposals."""
    
    # File patterns for grouping (display only)
    CONFIG_PATTERNS = {
        '.env', '.gitignore', '.editorconfig', '.dockerignore',
        'setup.py', 'setup.cfg', 'pyproject.toml',
        'tox.ini', 'pytest.ini', '.flake8', '.pylintrc',
        'tsconfig.json', 'angular.json', 'webpack.config.js',
        '.eslintrc', '.prettierrc',
    }
    
    DEPENDENCY_PATTERNS = {
        'requirements.txt', 'requirements-dev.txt', 'Pipfile', 'poetry.lock',
        'package.json', 'package-lock.json', 'yarn.lock',
        'Gemfile', 'go.mod', 'go.sum', 'pom.xml',
    }
    
    LOG_PATTERNS = {'.log', '.tmp', '.cache'}
    
    DOC_PATTERNS = {'.md', '.rst', '.txt', 'LICENSE', 'CHANGELOG'}
    
    def __init__(self):
        self.proposals: List[Proposal] = []
    
    def add(self, proposal: Proposal):
        """Add a proposal."""
        self.proposals.append(proposal)
    
    def add_move(self, source: Path, target: Path, reason: str, risk: RiskLevel = RiskLevel.LOW, **details):
        """Add a move proposal."""
        self.proposals.append(Proposal(
            action=ActionType.MOVE,
            source_path=source,
            target_path=target,
            reason=reason,
            risk_level=risk,
            details=details,
        ))
    
    def add_flag(self, source: Path, reason: str, risk: RiskLevel = RiskLevel.LOW, **details):
        """Add a flag proposal (for review)."""
        self.proposals.append(Proposal(
            action=ActionType.FLAG,
            source_path=source,
            reason=reason,
            risk_level=risk,
            details=details,
        ))
    
    def add_delete(self, source: Path, reason: str, risk: RiskLevel = RiskLevel.MEDIUM, **details):
        """Add a delete proposal."""
        self.proposals.append(Proposal(
            action=ActionType.DELETE,
            source_path=source,
            reason=reason,
            risk_level=risk,
            details=details,
        ))
    
    def to_text(self) -> str:
        """Generate terminal-friendly text output."""
        if not self.proposals:
            return "No proposals generated."
        
        lines = []
        lines.append("=" * 80)
        lines.append(f"STRUCTURAL CHANGE PROPOSALS ({len(self.proposals)} total)")
        lines.append("=" * 80)
        lines.append("")
        
        # Group proposals by category
        groups = self._group_proposals()
        
        # Sort groups for consistent display
        group_order = [
            "Configuration", "Dependencies", "Documentation", 
            "Source Code", "Tests", "Scripts", 
            "Logs & Artifacts", "Other"
        ]
        
        proposal_num = 1
        for group_name in group_order:
            if group_name not in groups:
                continue
            
            group_proposals = groups[group_name]
            
            # Group header
            lines.append("-" * 80)
            lines.append(f"{group_name.upper()} ({len(group_proposals)} proposals)")
            lines.append("-" * 80)
            lines.append("")
            
            # List proposals in this group
            for proposal in group_proposals:
                lines.append(f"[{proposal_num}] {proposal.to_text()}")
                lines.append("")
                proposal_num += 1
        
        # Summary
        lines.append("=" * 80)
        lines.append("SUMMARY")
        lines.append("=" * 80)
        
        by_action = {}
        by_risk = {}
        for p in self.proposals:
            by_action[p.action.value] = by_action.get(p.action.value, 0) + 1
            by_risk[p.risk_level.value] = by_risk.get(p.risk_level.value, 0) + 1
        
        lines.append(f"Total proposals: {len(self.proposals)}")
        lines.append("\nBy action:")
        for action, count in sorted(by_action.items()):
            lines.append(f"  {action}: {count}")
        
        lines.append("\nBy risk level:")
        for risk, count in sorted(by_risk.items()):
            lines.append(f"  {risk}: {count}")
        
        lines.append("\nBy category:")
        for group_name in group_order:
            if group_name in groups:
                lines.append(f"  {group_name}: {len(groups[group_name])}")
        
        return '\n'.join(lines)
    
    def to_json(self, indent: int = 2) -> str:
        """Generate JSON output."""
        data = {
            "total_proposals": len(self.proposals),
            "proposals": [p.to_dict() for p in self.proposals],
            "summary": {
                "by_action": {},
                "by_risk": {},
            }
        }
        
        for p in self.proposals:
            action = p.action.value
            risk = p.risk_level.value
            data["summary"]["by_action"][action] = data["summary"]["by_action"].get(action, 0) + 1
            data["summary"]["by_risk"][risk] = data["summary"]["by_risk"].get(risk, 0) + 1
        
        return json.dumps(data, indent=indent)
    
    def get_count(self) -> int:
        """Get total number of proposals."""
        return len(self.proposals)
    
    def get_by_risk(self, risk: RiskLevel) -> List[Proposal]:
        """Get proposals by risk level."""
        return [p for p in self.proposals if p.risk_level == risk]
    
    def get_by_action(self, action: ActionType) -> List[Proposal]:
        """Get proposals by action type."""
        return [p for p in self.proposals if p.action == action]
    
    def _categorize_proposal(self, proposal: Proposal) -> str:
        """Categorize a proposal for grouping (display only)."""
        source = str(proposal.source_path).lower()
        filename = Path(source).name.lower()
        
        # Configuration files
        if filename in {p.lower() for p in self.CONFIG_PATTERNS}:
            return "Configuration"
        if any(source.endswith(ext) for ext in ['.ini', '.cfg', '.conf', '.yaml', '.yml', '.toml']):
            if 'config' in filename or 'settings' in filename:
                return "Configuration"
        
        # Dependency files
        if filename in {p.lower() for p in self.DEPENDENCY_PATTERNS}:
            return "Dependencies"
        
        # Logs and artifacts
        if any(source.endswith(ext) for ext in self.LOG_PATTERNS):
            return "Logs & Artifacts"
        
        # Documentation
        if any(source.endswith(ext) for ext in self.DOC_PATTERNS):
            return "Documentation"
        if 'readme' in filename or 'license' in filename or 'changelog' in filename:
            return "Documentation"
        
        # Scripts
        if 'script' in source or '/scripts/' in source or '\\scripts\\' in source:
            return "Scripts"
        
        # Tests
        if 'test' in source or '/tests/' in source or '\\tests\\' in source:
            return "Tests"
        
        # Source code
        if source.endswith('.py') or source.endswith('.ts') or source.endswith('.js'):
            if '/src/' in source or '\\src\\' in source:
                return "Source Code"
        
        return "Other"
    
    def _group_proposals(self) -> Dict[str, List[Proposal]]:
        """Group proposals by category for display."""
        groups = {}
        for proposal in self.proposals:
            category = self._categorize_proposal(proposal)
            if category not in groups:
                groups[category] = []
            groups[category].append(proposal)
        return groups
