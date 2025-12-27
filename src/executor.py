"""Proposal executor - safely applies approved structural changes.

V2.1: Human-in-the-loop execution layer with interactive approval.
"""
import shutil
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import json

from .proposal import Proposal, ActionType, RiskLevel

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of executing a single proposal."""
    
    def __init__(self, proposal: Proposal, success: bool, message: str, skipped: bool = False):
        self.proposal = proposal
        self.success = success
        self.message = message
        self.skipped = skipped
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging."""
        return {
            'timestamp': self.timestamp,
            'action': self.proposal.action.value,
            'source': str(self.proposal.source_path),
            'target': str(self.proposal.target_path) if self.proposal.target_path else None,
            'success': self.success,
            'skipped': self.skipped,
            'message': self.message,
            'risk': self.proposal.risk_level.value,
        }


class ProposalExecutor:
    """Safely executes approved proposals with validation and logging.
    
    V2.1 Features:
    - Dry-run mode by default
    - Interactive approval required
    - Path validation and conflict detection
    - Operation logging for audit trail
    - MOVE operations only (no code modification)
    """
    
    def __init__(self, repo_path: Path, dry_run: bool = True):
        """Initialize executor.
        
        Args:
            repo_path: Root path of the repository
            dry_run: If True, simulate operations without filesystem changes
        """
        self.repo_path = Path(repo_path).resolve()
        self.dry_run = dry_run
        self.results: List[ExecutionResult] = []
        self.log_file = self.repo_path / '.repo-tool-history.json'
        
        logger.info(f"Executor initialized (dry_run={dry_run})")
    
    def execute_proposal(self, proposal: Proposal) -> ExecutionResult:
        """Execute a single proposal with validation.
        
        Args:
            proposal: The proposal to execute
        
        Returns:
            ExecutionResult with success status and message
        """
        # Only support MOVE operations for now
        if proposal.action != ActionType.MOVE:
            result = ExecutionResult(
                proposal=proposal,
                success=False,
                message=f"Unsupported action: {proposal.action.value} (only MOVE supported in V2.1)",
                skipped=True
            )
            self.results.append(result)
            return result
        
        # Validate the move operation
        validation_error = self._validate_move(proposal)
        if validation_error:
            result = ExecutionResult(
                proposal=proposal,
                success=False,
                message=f"Validation failed: {validation_error}"
            )
            self.results.append(result)
            return result
        
        # Execute the move
        try:
            if self.dry_run:
                message = f"[DRY-RUN] Would move {proposal.source_path} -> {proposal.target_path}"
                logger.info(message)
                result = ExecutionResult(proposal=proposal, success=True, message=message)
            else:
                message = self._execute_move(proposal)
                logger.info(message)
                result = ExecutionResult(proposal=proposal, success=True, message=message)
            
            self.results.append(result)
            return result
            
        except Exception as e:
            error_msg = f"Failed to execute: {str(e)}"
            logger.error(error_msg)
            result = ExecutionResult(proposal=proposal, success=False, message=error_msg)
            self.results.append(result)
            return result
    
    def _validate_move(self, proposal: Proposal) -> Optional[str]:
        """Validate a MOVE proposal before execution.
        
        Returns:
            Error message if validation fails, None if valid
        """
        if not proposal.source_path:
            return "Source path is None"
        
        if not proposal.target_path:
            return "Target path is None"
        
        source_full = self.repo_path / proposal.source_path
        target_full = self.repo_path / proposal.target_path
        
        # Check source exists
        if not source_full.exists():
            return f"Source file does not exist: {source_full}"
        
        # Check source is a file (not directory)
        if not source_full.is_file():
            return f"Source is not a file: {source_full}"
        
        # Check target doesn't already exist (conflict)
        if target_full.exists():
            return f"Target already exists (conflict): {target_full}"
        
        # Check target directory is valid
        target_dir = target_full.parent
        if target_dir.exists() and not target_dir.is_dir():
            return f"Target parent exists but is not a directory: {target_dir}"
        
        return None
    
    def _execute_move(self, proposal: Proposal) -> str:
        """Execute a MOVE operation (real filesystem change).
        
        Returns:
            Success message
        
        Raises:
            Exception if move fails
        """
        source_full = self.repo_path / proposal.source_path
        target_full = self.repo_path / proposal.target_path
        
        # Create target directory if needed
        target_dir = target_full.parent
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {target_dir}")
        
        # Move the file
        shutil.move(str(source_full), str(target_full))
        
        return f"Moved {proposal.source_path} -> {proposal.target_path}"
    
    def save_history(self):
        """Save execution history to log file for audit trail."""
        if not self.results:
            return
        
        # Load existing history
        history = []
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing history: {e}")
        
        # Append current results
        history.extend([r.to_dict() for r in self.results])
        
        # Save
        try:
            with open(self.log_file, 'w') as f:
                json.dump(history, f, indent=2)
            logger.info(f"Saved execution history to {self.log_file}")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def get_summary(self) -> Dict:
        """Get summary of execution results."""
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success and not r.skipped)
        skipped = sum(1 for r in self.results if r.skipped)
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'skipped': skipped,
            'dry_run': self.dry_run,
        }
    
    def rollback_moves(self, count: int) -> List[ExecutionResult]:
        """Rollback (undo) the last N successful MOVE operations.
        
        This reverses previously executed MOVE operations by reading the history
        file and moving files from target back to source in reverse order (LIFO).
        
        Args:
            count: Number of operations to rollback
        
        Returns:
            List of ExecutionResult for each rollback attempt
        
        Safety guarantees:
        - Only undoes MOVE actions with status=SUCCESS
        - Validates target exists and source doesn't exist before undo
        - Fails fast on first validation error
        - Logs all rollback operations to history
        """
        # Read history file
        if not self.log_file.exists():
            logger.warning(f"No history file found: {self.log_file}")
            return []
        
        try:
            with open(self.log_file, 'r') as f:
                history = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            return []
        
        # Filter for successful MOVE operations
        moves = [
            entry for entry in history
            if entry.get('action', '').upper() == 'MOVE' 
            and entry.get('success') is True
            and entry.get('skipped') is not True
        ]
        
        if not moves:
            logger.info("No successful MOVE operations found in history")
            return []
        
        # Take last N moves (reverse chronological)
        moves_to_undo = moves[-count:] if count < len(moves) else moves
        moves_to_undo.reverse()  # LIFO: undo most recent first
        
        logger.info(f"Rolling back {len(moves_to_undo)} operations (dry_run={self.dry_run})")
        
        rollback_results = []
        
        for i, move_entry in enumerate(moves_to_undo, 1):
            # Extract paths (swap source/target for rollback)
            original_source = Path(move_entry['source'])
            original_target = Path(move_entry['target'])
            
            # For rollback: move target → source
            rollback_source = original_target
            rollback_target = original_source
            
            # Validate rollback operation
            source_full = self.repo_path / rollback_source
            target_full = self.repo_path / rollback_target
            
            # Safety check: target (original location) must exist
            if not source_full.exists():
                error_msg = f"Rollback validation failed: Target file does not exist: {source_full}"
                logger.error(error_msg)
                result = ExecutionResult(
                    proposal=Proposal(
                        action=ActionType.MOVE,
                        source_path=rollback_source,
                        target_path=rollback_target,
                        reason=f"Rollback of {original_source} -> {original_target}",
                        risk_level=RiskLevel.HIGH
                    ),
                    success=False,
                    message=error_msg
                )
                rollback_results.append(result)
                logger.error(f"Aborting rollback after {i-1}/{len(moves_to_undo)} operations")
                break
            
            # Safety check: source (original location) must NOT exist
            if target_full.exists():
                error_msg = f"Rollback validation failed: Source location already exists (conflict): {target_full}"
                logger.error(error_msg)
                result = ExecutionResult(
                    proposal=Proposal(
                        action=ActionType.MOVE,
                        source_path=rollback_source,
                        target_path=rollback_target,
                        reason=f"Rollback of {original_source} -> {original_target}",
                        risk_level=RiskLevel.HIGH
                    ),
                    success=False,
                    message=error_msg
                )
                rollback_results.append(result)
                logger.error(f"Aborting rollback after {i-1}/{len(moves_to_undo)} operations")
                break
            
            # Execute rollback
            try:
                if self.dry_run:
                    message = f"[DRY-RUN] Would rollback {rollback_source} -> {rollback_target}"
                    logger.info(message)
                    result = ExecutionResult(
                        proposal=Proposal(
                            action=ActionType.MOVE,
                            source_path=rollback_source,
                            target_path=rollback_target,
                            reason=f"Rollback of {original_source} -> {original_target}",
                            risk_level=RiskLevel.HIGH
                        ),
                        success=True,
                        message=message
                    )
                else:
                    # Create target directory if needed
                    target_dir = target_full.parent
                    if not target_dir.exists():
                        target_dir.mkdir(parents=True, exist_ok=True)
                        logger.info(f"Created directory: {target_dir}")
                    
                    # Move the file back
                    shutil.move(str(source_full), str(target_full))
                    message = f"Rolled back {rollback_source} -> {rollback_target}"
                    logger.info(message)
                    
                    result = ExecutionResult(
                        proposal=Proposal(
                            action=ActionType.MOVE,
                            source_path=rollback_source,
                            target_path=rollback_target,
                            reason=f"Rollback of {original_source} -> {original_target}",
                            risk_level=RiskLevel.HIGH
                        ),
                        success=True,
                        message=message
                    )
                
                rollback_results.append(result)
                
            except Exception as e:
                error_msg = f"Rollback failed: {str(e)}"
                logger.error(error_msg)
                result = ExecutionResult(
                    proposal=Proposal(
                        action=ActionType.MOVE,
                        source_path=rollback_source,
                        target_path=rollback_target,
                        reason=f"Rollback of {original_source} -> {original_target}",
                        risk_level=RiskLevel.HIGH
                    ),
                    success=False,
                    message=error_msg
                )
                rollback_results.append(result)
                logger.error(f"Aborting rollback after {i-1}/{len(moves_to_undo)} operations")
                break
        
        # Save rollback operations to history
        if not self.dry_run and rollback_results:
            self._save_rollback_history(rollback_results)
        
        return rollback_results
    
    def _save_rollback_history(self, rollback_results: List[ExecutionResult]):
        """Save rollback operations to history file."""
        if not rollback_results:
            return
        
        # Load existing history
        history = []
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    history = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing history: {e}")
        
        # Append rollback results with ROLLBACK action marker
        for result in rollback_results:
            entry = result.to_dict()
            entry['action'] = 'ROLLBACK'  # Mark as rollback operation
            history.append(entry)
        
        # Save
        try:
            with open(self.log_file, 'w') as f:
                json.dump(history, f, indent=2)
            logger.info(f"Saved rollback history to {self.log_file}")
        except Exception as e:
            logger.error(f"Failed to save rollback history: {e}")
