"""Repository type detection module."""
from pathlib import Path
from typing import Dict, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RepoType(Enum):
    """Repository type classification."""
    PYTHON_DOMINANT = "python_dominant"
    NON_PYTHON = "non_python"
    MIXED = "mixed"


class RepoTypeDetector:
    """Detects repository type using simple heuristics."""
    
    # Python-specific indicators
    PYTHON_ROOT_FILES = {
        'setup.py', 'setup.cfg', 'pyproject.toml',
        'requirements.txt', 'Pipfile', 'poetry.lock',
        'tox.ini', 'pytest.ini',
    }
    
    # Non-Python framework indicators
    FRONTEND_FILES = {
        'package.json', 'package-lock.json', 'yarn.lock',
        'angular.json', 'tsconfig.json', 'webpack.config.js',
        'vite.config.js', 'next.config.js',
    }
    
    JAVA_FILES = {'pom.xml', 'build.gradle', 'gradlew'}
    DOTNET_FILES = {'.csproj', '.sln', '.fsproj', '.vbproj'}
    RUBY_FILES = {'Gemfile', 'Rakefile'}
    GO_FILES = {'go.mod', 'go.sum'}
    
    def __init__(self):
        """Initialize detector."""
        self.extension_counts: Dict[str, int] = {}
        self.root_files: set = set()
    
    def detect(self, files: List) -> RepoType:
        """Detect repository type from file list.
        
        Args:
            files: List of FileMetadata objects
            
        Returns:
            RepoType classification
        """
        # Count extensions
        self.extension_counts = {}
        self.root_files = set()
        
        for file in files:
            ext = file.extension or 'no_extension'
            self.extension_counts[ext] = self.extension_counts.get(ext, 0) + 1
            
            # Track root-level files
            if len(file.relative_path.parts) == 1:
                self.root_files.add(file.name)
        
        # Check for Python indicators
        python_score = self._calculate_python_score()
        
        # Check for non-Python framework indicators
        non_python_score = self._calculate_non_python_score()
        
        # Classify
        total_files = sum(self.extension_counts.values())
        py_percentage = self.extension_counts.get('.py', 0) / max(total_files, 1) * 100
        
        logger.info(f"Repository detection: {py_percentage:.1f}% Python files")
        logger.info(f"Python score: {python_score}, Non-Python score: {non_python_score}")
        
        # Decision logic
        if python_score >= 3 and py_percentage >= 50:
            return RepoType.PYTHON_DOMINANT
        elif non_python_score >= 2 and py_percentage < 20:
            return RepoType.NON_PYTHON
        elif py_percentage >= 30:
            return RepoType.MIXED
        else:
            return RepoType.NON_PYTHON
    
    def _calculate_python_score(self) -> int:
        """Calculate Python-specific score."""
        score = 0
        
        # Root-level Python files
        python_root_matches = self.root_files & self.PYTHON_ROOT_FILES
        score += len(python_root_matches) * 2
        
        # .py file count
        py_count = self.extension_counts.get('.py', 0)
        if py_count > 10:
            score += 3
        elif py_count > 5:
            score += 2
        elif py_count > 0:
            score += 1
        
        return score
    
    def _calculate_non_python_score(self) -> int:
        """Calculate non-Python framework score."""
        score = 0
        
        # Frontend frameworks
        if self.root_files & self.FRONTEND_FILES:
            score += 3
        
        # Other languages
        if self.root_files & self.JAVA_FILES:
            score += 3
        if self.root_files & self.GO_FILES:
            score += 3
        if self.root_files & self.RUBY_FILES:
            score += 3
        
        # Check for .NET in any file
        if any(ext in ['.csproj', '.sln', '.fsproj', '.vbproj'] 
               for ext in self.extension_counts.keys()):
            score += 3
        
        # TypeScript/JavaScript dominance
        ts_js_count = (self.extension_counts.get('.ts', 0) + 
                       self.extension_counts.get('.js', 0) + 
                       self.extension_counts.get('.tsx', 0) + 
                       self.extension_counts.get('.jsx', 0))
        
        if ts_js_count > 20:
            score += 2
        elif ts_js_count > 10:
            score += 1
        
        return score
    
    def get_summary(self) -> Dict:
        """Get detection summary for debugging."""
        return {
            "extension_counts": dict(self.extension_counts),
            "root_files": list(self.root_files),
            "python_root_files": list(self.root_files & self.PYTHON_ROOT_FILES),
            "non_python_indicators": list(self.root_files & self.FRONTEND_FILES),
        }
