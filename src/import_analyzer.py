"""Import breakage detection for Python files.

Preflight warnings for MOVE proposals that may break imports.
Read-only analysis - no code modification or auto-fixing.
"""
import ast
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import logging

from .proposal import Proposal, ActionType

logger = logging.getLogger(__name__)


class ImportStatement:
    """Represents a single import statement in a Python file."""
    
    def __init__(self, module: str, is_relative: bool, level: int, line_number: int, names: List[str]):
        """Initialize import statement.
        
        Args:
            module: Module name (e.g., 'utils', 'os.path')
            is_relative: True if relative import (e.g., from .utils import foo)
            level: Number of dots in relative import (0 = absolute)
            line_number: Line number in source file
            names: List of imported names (e.g., ['foo', 'bar'])
        """
        self.module = module
        self.is_relative = is_relative
        self.level = level
        self.line_number = line_number
        self.names = names
    
    def __repr__(self):
        if self.is_relative:
            dots = '.' * self.level
            if self.module:
                return f"from {dots}{self.module} import {', '.join(self.names)}"
            else:
                return f"from {dots} import {', '.join(self.names)}"
        else:
            if self.names:
                return f"from {self.module} import {', '.join(self.names)}"
            else:
                return f"import {self.module}"


class ImportWarning:
    """Represents a potential import breakage warning."""
    
    def __init__(self, source_file: Path, import_stmt: ImportStatement, 
                 reason: str, affected_files: List[Path]):
        """Initialize import warning.
        
        Args:
            source_file: File containing the import
            import_stmt: The import statement that may break
            reason: Why this import may break
            affected_files: Files involved in the breakage
        """
        self.source_file = source_file
        self.import_stmt = import_stmt
        self.reason = reason
        self.affected_files = affected_files
    
    def to_text(self) -> str:
        """Convert warning to human-readable text."""
        lines = []
        lines.append(f"[!] Import Risk in {self.source_file}:")
        lines.append(f"    Line {self.import_stmt.line_number}: {self.import_stmt}")
        lines.append(f"    Risk: {self.reason}")
        if self.affected_files:
            lines.append(f"    Affected: {', '.join(str(f) for f in self.affected_files[:3])}")
        return "\n".join(lines)


class ImportAnalyzer:
    """Analyzes Python imports to detect potential breakage from MOVE proposals.
    
    Advisory-only warnings. No code modification. Python-only.
    """
    
    def __init__(self, repo_path: Path):
        """Initialize import analyzer.
        
        Args:
            repo_path: Root path of the repository
        """
        self.repo_path = Path(repo_path).resolve()
        self.file_imports: Dict[Path, List[ImportStatement]] = {}
    
    def extract_imports(self, file_path: Path) -> List[ImportStatement]:
        """Extract import statements from a Python file using AST.
        
        Args:
            file_path: Path to Python file (relative to repo root)
        
        Returns:
            List of ImportStatement objects
        """
        full_path = self.repo_path / file_path
        
        if not full_path.exists() or not full_path.is_file():
            return []
        
        if full_path.suffix != '.py':
            return []
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    # import module
                    for alias in node.names:
                        imports.append(ImportStatement(
                            module=alias.name,
                            is_relative=False,
                            level=0,
                            line_number=node.lineno,
                            names=[]
                        ))
                
                elif isinstance(node, ast.ImportFrom):
                    # from module import name
                    module = node.module or ''
                    level = node.level
                    is_relative = level > 0
                    names = [alias.name for alias in node.names]
                    
                    imports.append(ImportStatement(
                        module=module,
                        is_relative=is_relative,
                        level=level,
                        line_number=node.lineno,
                        names=names
                    ))
            
            return imports
        
        except SyntaxError:
            # Ignore files with syntax errors
            logger.debug(f"Syntax error parsing {file_path}, skipping import analysis")
            return []
        except Exception as e:
            logger.debug(f"Error parsing {file_path}: {e}")
            return []
    
    def analyze_proposals(self, proposals: List[Proposal]) -> List[ImportWarning]:
        """Analyze MOVE proposals for potential import breakage.
        
        Args:
            proposals: List of proposals to analyze
        
        Returns:
            List of ImportWarning objects
        """
        warnings = []
        
        # Filter for MOVE proposals only
        move_proposals = [p for p in proposals if p.action == ActionType.MOVE]
        
        if not move_proposals:
            return warnings
        
        # Build mapping of files being moved
        move_map: Dict[Path, Path] = {}  # source -> target
        for proposal in move_proposals:
            move_map[proposal.source_path] = proposal.target_path
        
        # Analyze each file being moved
        for proposal in move_proposals:
            source_file = proposal.source_path
            target_file = proposal.target_path
            
            # Extract imports from the source file
            imports = self.extract_imports(source_file)
            self.file_imports[source_file] = imports
            
            # Check each import for potential breakage
            for import_stmt in imports:
                warning = self._check_import_breakage(
                    source_file, target_file, import_stmt, move_map
                )
                if warning:
                    warnings.append(warning)
        
        return warnings
    
    def _check_import_breakage(self, source_file: Path, target_file: Path,
                               import_stmt: ImportStatement, 
                               move_map: Dict[Path, Path]) -> Optional[ImportWarning]:
        """Check if a single import statement will break after the move.
        
        Args:
            source_file: Original file location
            target_file: Proposed new location
            import_stmt: Import statement to check
            move_map: Mapping of source -> target for all moves
        
        Returns:
            ImportWarning if breakage detected, None otherwise
        """
        # Check relative imports
        if import_stmt.is_relative:
            return self._check_relative_import(source_file, target_file, import_stmt, move_map)
        
        # Check same-directory imports
        return self._check_same_directory_import(source_file, target_file, import_stmt, move_map)
    
    def _check_relative_import(self, source_file: Path, target_file: Path,
                               import_stmt: ImportStatement,
                               move_map: Dict[Path, Path]) -> Optional[ImportWarning]:
        """Check if a relative import will break.
        
        Relative imports like 'from .utils import foo' depend on directory structure.
        """
        if not import_stmt.is_relative:
            return None
        
        source_dir = source_file.parent
        target_dir = target_file.parent
        
        # If moving to a different directory, relative imports will break
        if source_dir != target_dir:
            reason = f"Relative import will break when moving from {source_dir}/ to {target_dir}/"
            
            # Try to identify the specific file being imported
            affected_files = []
            if import_stmt.module:
                # from .module import something
                # Resolve relative to source directory
                module_parts = import_stmt.module.split('.')
                potential_file = source_dir / (module_parts[0] + '.py')
                if potential_file in move_map or (self.repo_path / potential_file).exists():
                    affected_files.append(Path(module_parts[0] + '.py'))
            
            return ImportWarning(
                source_file=source_file,
                import_stmt=import_stmt,
                reason=reason,
                affected_files=affected_files
            )
        
        return None
    
    def _check_same_directory_import(self, source_file: Path, target_file: Path,
                                    import_stmt: ImportStatement,
                                    move_map: Dict[Path, Path]) -> Optional[ImportWarning]:
        """Check if a same-directory import will break.
        
        Imports like 'import helpers' or 'from helpers import foo' may refer to
        files in the same directory.
        """
        if import_stmt.is_relative:
            return None
        
        source_dir = source_file.parent
        target_dir = target_file.parent
        
        if source_dir == target_dir:
            # Not moving directories, no risk
            return None
        
        # Check if this might be a local file import
        module_name = import_stmt.module.split('.')[0]
        
        # Check if there's a .py file with this name in the current directory
        potential_local_file = source_dir / (module_name + '.py')
        
        # Check if it exists in repo (but ignore if it's being moved to same target dir)
        if (self.repo_path / potential_local_file).exists():
            # Check if this file is also being moved
            if potential_local_file in move_map:
                moved_target = move_map[potential_local_file]
                if moved_target.parent != target_dir:
                    # Both files moving but to different directories
                    reason = f"Importing '{module_name}' from same directory, but {potential_local_file.name} is moving to {moved_target.parent}/"
                    return ImportWarning(
                        source_file=source_file,
                        import_stmt=import_stmt,
                        reason=reason,
                        affected_files=[potential_local_file]
                    )
            else:
                # File exists but is not moving, so import will break
                reason = f"Importing '{module_name}' from current directory, but moving away from {source_dir}/"
                return ImportWarning(
                    source_file=source_file,
                    import_stmt=import_stmt,
                    reason=reason,
                    affected_files=[potential_local_file]
                )
        
        return None
