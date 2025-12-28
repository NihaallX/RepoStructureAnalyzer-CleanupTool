"""Git awareness for repository reorganization.

V2.4: Read-only Git detection and advisory warnings.
No Git state modification - warnings only.
"""
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from .proposal import Proposal, ActionType

logger = logging.getLogger(__name__)


class GitWarning:
    """Represents a Git-related warning."""
    
    def __init__(self, warning_type: str, message: str, details: List[str] = None):
        """Initialize Git warning.
        
        Args:
            warning_type: Type of warning (uncommitted, tracked, etc)
            message: Human-readable warning message
            details: Optional list of detail strings
        """
        self.warning_type = warning_type
        self.message = message
        self.details = details or []


class GitDetector:
    """Detects Git repository status and provides advisory warnings."""
    
    def __init__(self, repo_path: Path):
        """Initialize Git detector.
        
        Args:
            repo_path: Root path of repository to check
        """
        self.repo_path = Path(repo_path)
        self._is_git_repo = None
        self._uncommitted_files = None
        self._tracked_files_cache = {}
    
    def is_git_repository(self) -> bool:
        """Check if repository is Git-managed.
        
        Returns:
            True if .git directory exists
        """
        if self._is_git_repo is None:
            git_dir = self.repo_path / ".git"
            self._is_git_repo = git_dir.exists() and git_dir.is_dir()
        return self._is_git_repo
    
    def get_uncommitted_files(self) -> List[Path]:
        """Get list of files with uncommitted changes.
        
        Uses `git status --porcelain` for detection.
        
        Returns:
            List of file paths with uncommitted changes (empty if not Git repo)
        """
        if self._uncommitted_files is not None:
            return self._uncommitted_files
        
        if not self.is_git_repository():
            self._uncommitted_files = []
            return []
        
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.warning(f"Git status failed: {result.stderr}")
                self._uncommitted_files = []
                return []
            
            # Parse git status output
            uncommitted = []
            for line in result.stdout.splitlines():
                if len(line) < 4:
                    continue
                
                # Format: "XY filename" where X is staged, Y is unstaged
                status = line[:2]
                filepath = line[3:].strip()
                
                # Skip if completely clean
                if status.strip() == "":
                    continue
                
                # Add to uncommitted list
                uncommitted.append(Path(filepath))
            
            self._uncommitted_files = uncommitted
            return uncommitted
            
        except subprocess.TimeoutExpired:
            logger.warning("Git status timed out")
            self._uncommitted_files = []
            return []
        except FileNotFoundError:
            logger.warning("Git executable not found")
            self._uncommitted_files = []
            return []
        except Exception as e:
            logger.warning(f"Error checking Git status: {e}")
            self._uncommitted_files = []
            return []
    
    def is_file_tracked(self, file_path: Path) -> bool:
        """Check if a file is tracked by Git.
        
        Args:
            file_path: Relative file path to check
        
        Returns:
            True if file is Git-tracked, False otherwise
        """
        if not self.is_git_repository():
            return False
        
        # Check cache
        file_str = str(file_path)
        if file_str in self._tracked_files_cache:
            return self._tracked_files_cache[file_str]
        
        try:
            result = subprocess.run(
                ["git", "ls-files", "--", str(file_path)],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                self._tracked_files_cache[file_str] = False
                return False
            
            # If output is non-empty, file is tracked
            is_tracked = len(result.stdout.strip()) > 0
            self._tracked_files_cache[file_str] = is_tracked
            return is_tracked
            
        except Exception as e:
            logger.warning(f"Error checking if file is tracked: {e}")
            self._tracked_files_cache[file_str] = False
            return False
    
    def analyze_proposals(self, proposals: List[Proposal]) -> List[GitWarning]:
        """Analyze proposals for Git-related risks.
        
        Args:
            proposals: List of proposals to analyze
        
        Returns:
            List of Git warnings (empty if not Git repo)
        """
        if not self.is_git_repository():
            return []
        
        warnings = []
        
        # Check for uncommitted changes
        uncommitted = self.get_uncommitted_files()
        if uncommitted:
            warning = GitWarning(
                warning_type="uncommitted",
                message="Uncommitted changes detected",
                details=[str(f) for f in uncommitted[:5]]  # Show first 5
            )
            warnings.append(warning)
        
        # Check if MOVE proposal files are Git-tracked
        move_proposals = [p for p in proposals if p.action == ActionType.MOVE]
        tracked_moves = []
        
        for proposal in move_proposals:
            if self.is_file_tracked(proposal.source_path):
                tracked_moves.append(proposal.source_path)
        
        if tracked_moves:
            warning = GitWarning(
                warning_type="tracked_files",
                message=f"{len(tracked_moves)} files to move are Git-tracked",
                details=[str(f) for f in tracked_moves[:5]]  # Show first 5
            )
            warnings.append(warning)
        
        return warnings
    
    def render_warnings(self, warnings: Optional[List[GitWarning]] = None, 
                       proposals: Optional[List[Proposal]] = None) -> str:
        """Render Git warnings as formatted text.
        
        Args:
            warnings: List of warnings to render (if None, analyzes proposals)
            proposals: List of proposals for analysis (if warnings not provided)
        
        Returns:
            Formatted warning text (empty string if no warnings)
        """
        if not self.is_git_repository():
            return ""
        
        if warnings is None:
            if proposals is None:
                return ""
            warnings = self.analyze_proposals(proposals)
        
        if not warnings:
            return ""
        
        lines = []
        lines.append("=" * 60)
        lines.append("🔀 GIT AWARENESS (Read-Only)")
        lines.append("=" * 60)
        lines.append("")
        
        for warning in warnings:
            lines.append(f"⚠ {warning.message}")
            
            if warning.details:
                for detail in warning.details:
                    lines.append(f"    - {detail}")
                
                # Show "and X more" if truncated
                if warning.warning_type == "uncommitted":
                    uncommitted = self.get_uncommitted_files()
                    if len(uncommitted) > 5:
                        lines.append(f"    ... and {len(uncommitted) - 5} more")
                elif warning.warning_type == "tracked_files":
                    # Count tracked moves from details length vs actual
                    if len(warning.details) >= 5:
                        lines.append(f"    ... and possibly more")
            
            lines.append("")
        
        lines.append("ℹ Recommendation: Run `git status` and commit changes before")
        lines.append("  applying reorganization. This tool does NOT run `git mv`.")
        lines.append("=" * 60)
        
        return "\n".join(lines)
