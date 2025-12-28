"""Visualization and decision support for proposals.

V2.2 Phase 2: Provides tree diff preview, impact summaries, and better decision clarity.
V2.3: Added import breakage warnings (preflight checks).
V2.4: Added confidence scoring and Git awareness.
No execution risk - read-only simulation only.
"""
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from .proposal import Proposal, ActionType, RiskLevel
from .import_analyzer import ImportAnalyzer, ImportWarning
from .confidence import ConfidenceScore
from .git_detector import GitDetector
from .repo_type import RepoType


class TreeNode:
    """Represents a node in the directory tree."""
    
    def __init__(self, name: str, is_file: bool = False):
        self.name = name
        self.is_file = is_file
        self.children: Dict[str, TreeNode] = {}
    
    def add_path(self, path: Path):
        """Add a path to the tree."""
        parts = path.parts
        if not parts:
            return
        
        first = parts[0]
        if first not in self.children:
            is_file = len(parts) == 1
            self.children[first] = TreeNode(first, is_file=is_file)
        
        if len(parts) > 1:
            self.children[first].add_path(Path(*parts[1:]))
    
    def render(self, prefix: str = "", is_last: bool = True) -> List[str]:
        """Render the tree as a list of formatted strings."""
        lines = []
        
        if self.name != ".":
            connector = "└── " if is_last else "├── "
            suffix = "/" if not self.is_file else ""
            lines.append(f"{prefix}{connector}{self.name}{suffix}")
            
            if not self.is_file:
                extension = "    " if is_last else "│   "
                new_prefix = prefix + extension
            else:
                new_prefix = prefix
        else:
            new_prefix = prefix
        
        # Render children
        if not self.is_file:
            children = sorted(self.children.items(), key=lambda x: (x[1].is_file, x[0]))
            for i, (name, child) in enumerate(children):
                is_last_child = (i == len(children) - 1)
                lines.extend(child.render(new_prefix, is_last_child))
        
        return lines


class TreeDiffVisualizer:
    """Generates before/after tree visualization and impact summaries.
    
    Pure simulation - no filesystem writes. Works for all repository types.
    V2.3: Added import breakage detection for Python repos.
    V2.4: Added confidence scoring and Git awareness.
    """
    
    def __init__(self, proposals: List[Proposal], current_files: List[Path], 
                 repo_path: Optional[Path] = None, enable_import_check: bool = True,
                 repo_type: Optional[RepoType] = None, has_tests: bool = False,
                 is_dry_run: bool = True):
        """Initialize visualizer.
        
        Args:
            proposals: List of proposals (MOVE and FLAG)
            current_files: List of current file paths in repository
            repo_path: Root path of repository (required for import analysis)
            enable_import_check: Whether to check for import breakage (Python only)
            repo_type: Repository type (for confidence scoring)
            has_tests: Whether tests detected (for confidence scoring)
            is_dry_run: Whether in dry-run mode (for confidence scoring)
        """
        self.proposals = proposals
        self.current_files = current_files
        self.move_proposals = [p for p in proposals if p.action == ActionType.MOVE]
        self.flag_proposals = [p for p in proposals if p.action == ActionType.FLAG]
        self.repo_path = repo_path
        self.enable_import_check = enable_import_check
        self.repo_type = repo_type
        self.has_tests = has_tests
        self.is_dry_run = is_dry_run
        self._import_warnings = None  # Cached warnings
        self._confidence_score = None  # Cached confidence
        self._git_warnings = None  # Cached git warnings
    
    def generate_tree_diff(self, max_depth: int = 3, max_files: int = 50) -> Dict[str, str]:
        """Generate before/after tree visualization.
        
        Args:
            max_depth: Maximum tree depth to display
            max_files: Maximum files to show (for large repos)
        
        Returns:
            Dict with 'before' and 'after' tree strings
        """
        # Build BEFORE tree (current state)
        before_root = TreeNode(".")
        affected_files = self._get_affected_files()
        
        for file_path in affected_files[:max_files]:
            before_root.add_path(file_path)
        
        # Build AFTER tree (simulated state after moves)
        after_root = TreeNode(".")
        after_files = self._simulate_after_state()
        
        for file_path in after_files[:max_files]:
            after_root.add_path(file_path)
        
        # Render trees
        before_lines = before_root.render()
        after_lines = after_root.render()
        
        # Truncation notice
        truncated = len(affected_files) > max_files
        truncation_note = f"\n... showing {max_files} of {len(affected_files)} affected files" if truncated else ""
        
        return {
            'before': ".\n" + "\n".join(before_lines) + truncation_note,
            'after': ".\n" + "\n".join(after_lines) + truncation_note
        }
    
    def _get_affected_files(self) -> List[Path]:
        """Get list of files affected by proposals."""
        affected = set()
        
        # Add all files that will be moved
        for proposal in self.move_proposals:
            affected.add(proposal.source_path)
        
        # Add flagged files
        for proposal in self.flag_proposals:
            affected.add(proposal.source_path)
        
        return sorted(affected)
    
    def _simulate_after_state(self) -> List[Path]:
        """Simulate file paths after all MOVE proposals are applied."""
        # Start with affected files
        files_map = {}
        
        # Map source -> target for all moves
        for proposal in self.move_proposals:
            files_map[proposal.source_path] = proposal.target_path
        
        # Apply transformations
        after_files = []
        for source in self._get_affected_files():
            if source in files_map:
                after_files.append(files_map[source])
            else:
                # Flagged but not moved
                after_files.append(source)
        
        return sorted(after_files)
    
    def generate_impact_summary(self) -> Dict:
        """Generate impact summary with key metrics.
        
        Returns:
            Dict with:
            - total_moves: Number of MOVE proposals
            - total_flags: Number of FLAG proposals
            - new_directories: Set of new directories that will be created
            - risk_breakdown: Dict of risk level counts
            - duplicate_groups: Number of duplicate groups detected
        """
        # Count moves and flags
        total_moves = len(self.move_proposals)
        total_flags = len(self.flag_proposals)
        
        # Identify new directories
        new_dirs = set()
        for proposal in self.move_proposals:
            target_path = proposal.target_path
            # Get all parent directories
            for parent in target_path.parents:
                if parent != Path('.'):
                    new_dirs.add(str(parent))
        
        # Count by risk level
        risk_breakdown = {
            'high': sum(1 for p in self.move_proposals if p.risk_level == RiskLevel.HIGH),
            'medium': sum(1 for p in self.move_proposals if p.risk_level == RiskLevel.MEDIUM),
            'low': sum(1 for p in self.move_proposals if p.risk_level == RiskLevel.LOW),
        }
        
        # Count duplicate groups (FLAGs with "Duplicate filename:")
        duplicate_groups = sum(
            1 for p in self.flag_proposals 
            if 'Duplicate filename:' in p.reason
        )
        
        return {
            'total_moves': total_moves,
            'total_flags': total_flags,
            'new_directories': sorted(new_dirs),
            'risk_breakdown': risk_breakdown,
            'duplicate_groups': duplicate_groups,
        }
    
    def render_impact_summary(self) -> str:
        """Render impact summary as formatted text."""
        summary = self.generate_impact_summary()
        
        lines = []
        lines.append("=" * 60)
        lines.append("IMPACT SUMMARY")
        lines.append("=" * 60)
        
        # Files to be moved
        if summary['total_moves'] > 0:
            lines.append(f"Files to be moved:     {summary['total_moves']}")
        
        # New directories
        if summary['new_directories']:
            dirs_preview = ', '.join(summary['new_directories'][:5])
            if len(summary['new_directories']) > 5:
                dirs_preview += f" (+{len(summary['new_directories']) - 5} more)"
            lines.append(f"New directories:       {len(summary['new_directories'])} ({dirs_preview})")
        
        # Risk breakdown
        risk = summary['risk_breakdown']
        if risk['high'] > 0:
            lines.append(f"High-risk moves:       {risk['high']}")
        if risk['medium'] > 0:
            lines.append(f"Medium-risk moves:     {risk['medium']}")
        if risk['low'] > 0:
            lines.append(f"Low-risk moves:        {risk['low']}")
        
        # Flags
        if summary['total_flags'] > 0:
            lines.append(f"Files flagged:         {summary['total_flags']}")
        
        # Duplicate groups
        if summary['duplicate_groups'] > 0:
            lines.append(f"Duplicate groups:      {summary['duplicate_groups']}")
        
        # Advisory message for non-Python repos
        if summary['total_moves'] == 0 and summary['total_flags'] > 0:
            lines.append("")
            lines.append("[!] ADVISORY MODE: No moves proposed (non-Python repository)")
            lines.append("    Review flagged items for manual cleanup")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def render_tree_diff(self) -> str:
        """Render before/after tree diff as formatted text."""
        diff = self.generate_tree_diff()
        
        lines = []
        lines.append("=" * 60)
        lines.append("DIRECTORY STRUCTURE PREVIEW")
        lines.append("=" * 60)
        lines.append("")
        lines.append("BEFORE (current):")
        lines.append(diff['before'])
        lines.append("")
        lines.append("AFTER (if proposals applied):")
        lines.append(diff['after'])
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)    
    def generate_import_warnings(self) -> List[ImportWarning]:
        """Detect potential import breakage from MOVE proposals.
        
        Only analyzes Python repositories. Returns empty list for non-Python repos.
        Results are cached after first call.
        
        Returns:
            List of import warnings (empty if import checking disabled or non-Python repo)
        """
        if self._import_warnings is not None:
            return self._import_warnings
        
        if not self.enable_import_check or not self.repo_path:
            self._import_warnings = []
            return []
        
        analyzer = ImportAnalyzer(self.repo_path)
        self._import_warnings = analyzer.analyze_proposals(self.move_proposals)
        return self._import_warnings
    
    def render_import_warnings(self, warnings: Optional[List[ImportWarning]] = None) -> str:
        """Render import warnings as formatted text.
        
        Args:
            warnings: List of warnings to render (if None, generates them)
        
        Returns:
            Formatted warning text (empty string if no warnings)
        """
        if warnings is None:
            warnings = self.generate_import_warnings()
        
        if not warnings:
            return ""
        
        lines = []
        lines.append("=" * 60)
        lines.append("⚠️  IMPORT BREAKAGE WARNINGS (Python)")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Found {len(warnings)} potential import issue(s):")
        lines.append("")
        
        for warning in warnings:
            lines.append(warning.to_text())
            lines.append("")
        
        lines.append("These are advisory warnings. Review imports carefully.")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def generate_confidence_score(self) -> ConfidenceScore:
        """Generate confidence score for reorganization.
        
        Results are cached after first call.
        
        Returns:
            ConfidenceScore object
        """
        if self._confidence_score is not None:
            return self._confidence_score
        
        # Count import warnings
        import_warnings = self.generate_import_warnings()
        import_warnings_count = len(import_warnings)
        
        # Create confidence scorer
        self._confidence_score = ConfidenceScore(
            proposals=self.proposals,
            repo_type=self.repo_type,
            has_tests=self.has_tests,
            import_warnings_count=import_warnings_count,
            is_dry_run=self.is_dry_run
        )
        
        return self._confidence_score
    
    def render_confidence_score(self, confidence: Optional[ConfidenceScore] = None) -> str:
        """Render confidence score as formatted text.
        
        Args:
            confidence: ConfidenceScore to render (if None, generates it)
        
        Returns:
            Formatted confidence score text
        """
        if confidence is None:
            confidence = self.generate_confidence_score()
        
        return confidence.to_text()
    
    def generate_git_warnings(self) -> List:
        """Generate Git-related warnings.
        
        Results are cached after first call.
        
        Returns:
            List of GitWarning objects (empty if not Git repo)
        """
        if self._git_warnings is not None:
            return self._git_warnings
        
        if not self.repo_path:
            self._git_warnings = []
            return []
        
        detector = GitDetector(self.repo_path)
        self._git_warnings = detector.analyze_proposals(self.proposals)
        return self._git_warnings
    
    def render_git_warnings(self, warnings: Optional[List] = None) -> str:
        """Render Git warnings as formatted text.
        
        Args:
            warnings: List of warnings to render (if None, generates them)
        
        Returns:
            Formatted warning text (empty string if no warnings or not Git repo)
        """
        if not self.repo_path:
            return ""
        
        detector = GitDetector(self.repo_path)
        
        if warnings is None:
            warnings = self.generate_git_warnings()
        
        return detector.render_warnings(warnings, self.proposals)
