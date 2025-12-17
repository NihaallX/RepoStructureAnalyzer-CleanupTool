"""File classification engine using rule-based heuristics."""
from enum import Enum
from pathlib import Path
from typing import List, Set
import logging

from .analyzer import FileMetadata

logger = logging.getLogger(__name__)


class FileCategory(Enum):
    """File categories for organization."""
    SRC = "src"
    TESTS = "tests"
    CONFIGS = "configs"
    SCRIPTS = "scripts"
    DOCS = "docs"
    MARKDOWN = "markdown"
    DATA = "data"
    EXPERIMENTS = "experiments"
    TRASH = "trash"
    UNKNOWN = "unknown"


class FileClassifier:
    """Rule-based file classification engine."""
    
    # Configuration file patterns
    CONFIG_PATTERNS = {
        'setup.py', 'setup.cfg', 'pyproject.toml',
        'requirements.txt', 'requirements-dev.txt',
        'Pipfile', 'poetry.lock',
        '.gitignore', '.dockerignore',
        'Dockerfile', 'docker-compose.yml',
        '.env', '.env.example',
        'tox.ini', 'pytest.ini',
        '.flake8', '.pylintrc', 'mypy.ini',
    }
    
    CONFIG_EXTENSIONS = {'.ini', '.cfg', '.conf', '.yaml', '.yml', '.toml', '.json'}
    
    # Data file extensions
    DATA_EXTENSIONS = {
        '.csv', '.tsv', '.json', '.xml',
        '.db', '.sqlite', '.sqlite3',
        '.pkl', '.pickle', '.npy', '.npz',
        '.parquet', '.feather',
    }
    
    # Documentation extensions
    DOC_EXTENSIONS = {'.rst', '.txt', '.pdf', '.html', '.htm'}
    
    # Script indicators
    SCRIPT_KEYWORDS = {'run_', 'main_', 'cli_', 'script_', 'setup_', 'deploy_', 'build_'}
    
    # Experiment indicators
    EXPERIMENT_KEYWORDS = {
        'experiment', 'test_run', 'playground', 'scratch',
        'temp_', 'tmp_', 'demo_', 'example_', 'prototype_',
    }
    
    # Import patterns for source code
    APP_IMPORT_PATTERNS = {
        'fastapi', 'flask', 'django',
        'sqlalchemy', 'pydantic',
        'numpy', 'pandas', 'scikit-learn',
        'torch', 'tensorflow',
    }
    
    TEST_IMPORT_PATTERNS = {
        'pytest', 'unittest', 'mock', 'testify',
        'hypothesis', 'nose', 'doctest',
    }
    
    def __init__(self):
        """Initialize classifier."""
        self.classifications = {}
    
    def classify(self, metadata: FileMetadata) -> FileCategory:
        """Classify a file based on rules."""
        # Markdown files
        if metadata.extension == '.md':
            return FileCategory.MARKDOWN
        
        # Non-Python files
        if metadata.extension != '.py':
            return self._classify_non_python(metadata)
        
        # Python files - apply rules in order of specificity
        category = self._classify_python(metadata)
        
        # Cache classification
        self.classifications[str(metadata.path)] = category
        return category
    
    def _classify_non_python(self, metadata: FileMetadata) -> FileCategory:
        """Classify non-Python files."""
        name_lower = metadata.name.lower()
        
        # Configuration files (before data files to catch config.json, etc.)
        if metadata.name in self.CONFIG_PATTERNS:
            return FileCategory.CONFIGS
        
        # Data files (check before general config extensions)
        if metadata.extension in self.DATA_EXTENSIONS:
            return FileCategory.DATA
        
        # Configuration extensions (after data check)
        if metadata.extension in self.CONFIG_EXTENSIONS:
            return FileCategory.CONFIGS
        
        # Documentation
        if metadata.extension in self.DOC_EXTENSIONS:
            return FileCategory.DOCS
        
        return FileCategory.UNKNOWN
    
    def _classify_python(self, metadata: FileMetadata) -> FileCategory:
        """Classify Python files using heuristics."""
        name_lower = metadata.name.lower()
        path_lower = str(metadata.relative_path).lower()
        
        # Rule 1: Experimental/temporary files (check before tests to avoid misclassification)
        if self._is_experiment_file(metadata, name_lower, path_lower):
            return FileCategory.EXPERIMENTS
        
        # Rule 2: Test files
        if self._is_test_file(metadata, name_lower, path_lower):
            return FileCategory.TESTS
        
        # Rule 3: Configuration/setup files
        if self._is_config_file(metadata, name_lower):
            return FileCategory.CONFIGS
        
        # Rule 4: Executable scripts
        if self._is_script_file(metadata, name_lower, path_lower):
            return FileCategory.SCRIPTS
        
        # Rule 5: Source code
        if self._is_source_file(metadata, path_lower):
            return FileCategory.SRC
        
        # Default: needs review
        return FileCategory.TRASH
    
    def _is_test_file(self, metadata: FileMetadata, name_lower: str, path_lower: str) -> bool:
        """Check if file is a test file."""
        # Path contains 'test' or 'tests' directory (highest priority for path-based)
        path_parts = [p.lower() for p in metadata.relative_path.parts]
        if any('test' in part for part in path_parts):
            return True
        
        # Has test functions/classes
        if metadata.has_tests:
            return True
        
        # Name patterns
        if name_lower.startswith('test_'):
            return True
        if name_lower.endswith('_test.py'):
            return True
        
        # Imports test frameworks
        if any(imp in self.TEST_IMPORT_PATTERNS for imp in metadata.imports):
            return True
        
        return False
    
    def _is_config_file(self, metadata: FileMetadata, name_lower: str) -> bool:
        """Check if file is a configuration file."""
        if metadata.name in self.CONFIG_PATTERNS:
            return True
        
        if name_lower.endswith('_config.py') or name_lower == 'config.py':
            return True
        
        if name_lower == 'settings.py' or name_lower.endswith('_settings.py'):
            return True
        
        return False
    
    def _is_script_file(self, metadata: FileMetadata, name_lower: str, path_lower: str) -> bool:
        """Check if file is an executable script."""
        # Has main block
        if metadata.is_executable:
            return True
        
        # Name starts with script keywords
        if any(name_lower.startswith(kw) for kw in self.SCRIPT_KEYWORDS):
            return True
        
        # In scripts directory
        if 'scripts' in path_lower.split(os.sep):
            return True
        
        return False
    
    def _is_experiment_file(self, metadata: FileMetadata, name_lower: str, path_lower: str) -> bool:
        """Check if file is experimental/temporary."""
        # Specific keyword patterns (use more precise matching)
        experiment_prefixes = ['temp_', 'tmp_', 'demo_', 'example_', 'prototype_']
        experiment_names = ['experiment', 'playground', 'scratch', 'test_run']
        
        # Check for prefixes
        if any(name_lower.startswith(prefix) for prefix in experiment_prefixes):
            return True
        
        # Check for exact matches or as whole words
        if any(keyword == name_lower.replace('.py', '') for keyword in experiment_names):
            return True
        
        # Check if experiment/playground/scratch appears in the name
        if any(kw in name_lower for kw in ['experiment', 'playground', 'scratch']):
            return True
        
        # Path patterns
        path_parts = [p.lower() for p in metadata.relative_path.parts]
        if any(kw in part for part in path_parts for kw in ['experiment', 'playground', 'scratch', 'temp', 'tmp']):
            return True
        
        # Untitled or backup patterns
        if name_lower.startswith('untitled') or name_lower.endswith('.bak'):
            return True
        
        return False
    
    def _is_source_file(self, metadata: FileMetadata, path_lower: str) -> bool:
        """Check if file is application source code."""
        # In src directory
        if 'src' in path_lower.split(os.sep):
            return True
        
        # Has __init__.py nearby (package structure)
        if metadata.relative_path.parts and len(metadata.relative_path.parts) > 1:
            parent = metadata.path.parent
            if (parent / '__init__.py').exists():
                return True
        
        # Imports application frameworks
        if any(any(pattern in imp for pattern in self.APP_IMPORT_PATTERNS) 
               for imp in metadata.imports):
            return True
        
        # Has meaningful imports (not just stdlib)
        if len(metadata.imports) > 2:
            return True
        
        return False
    
    def classify_all(self, files: List[FileMetadata]) -> dict:
        """Classify all files and return summary."""
        results = {}
        category_counts = {cat: 0 for cat in FileCategory}
        
        for file in files:
            category = self.classify(file)
            results[str(file.relative_path)] = category
            category_counts[category] += 1
        
        logger.info(f"Classified {len(files)} files")
        for category, count in category_counts.items():
            if count > 0:
                logger.info(f"  {category.value}: {count}")
        
        return results


import os  # Add missing import
