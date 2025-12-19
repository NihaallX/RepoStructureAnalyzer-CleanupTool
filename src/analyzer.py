"""Repository analyzer module."""
import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class FileMetadata:
    """Metadata for a single file."""
    
    def __init__(self, path: Path, root: Path):
        self.path = path
        self.relative_path = path.relative_to(root)
        self.name = path.name
        self.extension = path.suffix
        self.size = path.stat().st_size if path.exists() else 0
        self.imports: List[str] = []
        self.is_executable = False
        self.has_main = False
        self.has_tests = False
        self.content_sample = ""
        
    def to_dict(self) -> Dict:
        """Convert metadata to dictionary."""
        return {
            "path": str(self.path),
            "relative_path": str(self.relative_path),
            "name": self.name,
            "extension": self.extension,
            "size": self.size,
            "imports": self.imports,
            "is_executable": self.is_executable,
            "has_main": self.has_main,
            "has_tests": self.has_tests,
        }


class RepositoryAnalyzer:
    """Analyzes a repository and collects file metadata."""
    
    # Directories to ignore (path containment check)
    IGNORE_DIRS = {
        '.git', '.svn', '.hg',
        '__pycache__', '.pytest_cache',
        'venv', 'env', '.venv', 'ENV',
        'node_modules', 'site-packages',
        'build', 'dist', '.eggs', '*.egg-info',
        '.tox', '.coverage',
    }
    
    # Artifact directories (exact match, recursively excluded)
    # V2: These are build outputs and generated files that should never be analyzed
    # V2: Prevents noise from .next/, out/, dist/, etc. in frontend repositories
    ARTIFACT_DIRS = {
        '.next',           # Next.js build output
        'out',             # Next.js static export
        '_next',           # Next.js runtime
        'dist',            # Common build output
        'build',           # Common build output
        'coverage',        # Test coverage reports
        '.nuxt',           # Nuxt.js
        '.output',         # Nuxt 3
        '.vercel',         # Vercel build cache
        '.netlify',        # Netlify build cache
        'public/build',    # Rails/Vite
        'static/chunks',   # Webpack chunks
    }
    
    # File patterns to ignore
    IGNORE_PATTERNS = {
        '*.pyc', '*.pyo', '*.pyd',
        '*.so', '*.dll', '*.dylib',
        '.DS_Store', 'Thumbs.db',
        '*.swp', '*.swo', '*~',
    }
    
    def __init__(self, repo_path: str):
        """Initialize analyzer with repository path."""
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
        if not self.repo_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repo_path}")
        
        self.files: List[FileMetadata] = []
        logger.info(f"Initialized analyzer for: {self.repo_path}")
    
    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored (path containment + artifact check)."""
        # Check all directory parts of the path
        # For a file: check all parts except the filename (to avoid 'env' matching 'environment.py')
        # For a directory: check all parts including the directory itself
        
        # Heuristic: if path has an extension, treat as file; otherwise treat as directory
        is_likely_file = bool(path.suffix)
        
        if is_likely_file:
            # For files, check directory parts only (exclude filename)
            parts_to_check = path.parts[:-1] if len(path.parts) > 1 else []
        else:
            # For directories, check all parts including the directory name
            parts_to_check = path.parts
        
        # V2 ARTIFACT CHECK: Exact match on artifact directories (highest priority)
        # V2: If any path part is an exact artifact directory, exclude the entire subtree
        # V2: This prevents analyzing .next/out/dist and their contents entirely
        for part in parts_to_check:
            if part in self.ARTIFACT_DIRS:
                return True
        
        # PATH CONTAINMENT CHECK: Check if any directory part contains an ignored directory name
        for part in parts_to_check:
            part_lower = part.lower()
            for ignored in self.IGNORE_DIRS:
                if '*' in ignored:
                    # Pattern matching for wildcard ignore dirs
                    if self._match_pattern(part, ignored):
                        return True
                else:
                    # Path containment: check if ignored string is in the directory part
                    # This catches venv_new, my_venv, site-packages, etc.
                    if ignored.lower() in part_lower:
                        return True
        
        # Check file patterns (only for likely files)
        if is_likely_file:
            for pattern in self.IGNORE_PATTERNS:
                if self._match_pattern(path.name, pattern):
                    return True
        
        return False
    
    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Simple pattern matching for wildcards."""
        if '*' not in pattern:
            return name == pattern
        
        # Convert glob pattern to regex
        regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
        return bool(re.match(f'^{regex_pattern}$', name))
    
    def analyze(self) -> List[FileMetadata]:
        """Recursively scan repository and collect metadata."""
        logger.info("Starting repository analysis...")
        self.files = []
        
        for root, dirs, files in os.walk(self.repo_path):
            root_path = Path(root)
            
            # Filter out ignored directories in-place
            dirs[:] = [d for d in dirs if not self.should_ignore(root_path / d)]
            
            for file in files:
                file_path = root_path / file
                
                if self.should_ignore(file_path):
                    continue
                
                try:
                    metadata = FileMetadata(file_path, self.repo_path)
                    self._collect_metadata(metadata)
                    self.files.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")
        
        logger.info(f"Analysis complete. Found {len(self.files)} files.")
        return self.files
    
    def _collect_metadata(self, metadata: FileMetadata):
        """Collect detailed metadata for a file."""
        # Python files get extra analysis
        if metadata.extension == '.py':
            self._analyze_python_file(metadata)
        
        # Check for common patterns
        self._check_patterns(metadata)
    
    def _analyze_python_file(self, metadata: FileMetadata):
        """Analyze Python file for imports and structure."""
        try:
            with open(metadata.path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                metadata.content_sample = content[:500]  # First 500 chars
            
            # Parse AST to find imports
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            metadata.imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            metadata.imports.append(node.module)
                
                # Check for if __name__ == '__main__'
                for node in ast.walk(tree):
                    if isinstance(node, ast.If):
                        if isinstance(node.test, ast.Compare):
                            if (isinstance(node.test.left, ast.Name) and 
                                node.test.left.id == '__name__'):
                                metadata.has_main = True
                                metadata.is_executable = True
                                break
                
                # Check for test functions/classes
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name.startswith('test_'):
                            metadata.has_tests = True
                            break
                    elif isinstance(node, ast.ClassDef):
                        if node.name.startswith('Test'):
                            metadata.has_tests = True
                            break
            
            except SyntaxError:
                logger.debug(f"Syntax error parsing {metadata.path}")
        
        except Exception as e:
            logger.debug(f"Failed to read {metadata.path}: {e}")
    
    def _check_patterns(self, metadata: FileMetadata):
        """Check for common naming patterns."""
        name_lower = metadata.name.lower()
        
        # Executable patterns
        if name_lower.startswith(('run_', 'main_', 'cli_')):
            metadata.is_executable = True
        
        # Test patterns
        if name_lower.startswith('test_') or name_lower.endswith('_test.py'):
            metadata.has_tests = True
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        extensions = {}
        for file in self.files:
            ext = file.extension or 'no_extension'
            extensions[ext] = extensions.get(ext, 0) + 1
        
        return {
            "total_files": len(self.files),
            "extensions": extensions,
            "python_files": sum(1 for f in self.files if f.extension == '.py'),
            "executables": sum(1 for f in self.files if f.is_executable),
            "test_files": sum(1 for f in self.files if f.has_tests),
        }
