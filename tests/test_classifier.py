"""Tests for the file classifier."""
import pytest
from pathlib import Path
import tempfile
import os

from src.analyzer import FileMetadata
from src.classifier import FileClassifier, FileCategory


class TestFileClassifier:
    """Test suite for FileClassifier."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = FileClassifier()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, filename: str, **kwargs) -> FileMetadata:
        """Helper to create FileMetadata for testing."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        
        # Apply custom attributes
        for key, value in kwargs.items():
            setattr(metadata, key, value)
        
        return metadata
    
    def test_markdown_classification(self):
        """Test that .md files are classified as MARKDOWN."""
        metadata = self.create_metadata('README.md')
        category = self.classifier.classify(metadata)
        assert category == FileCategory.MARKDOWN
    
    def test_config_file_classification(self):
        """Test configuration file classification."""
        # Test by filename
        for filename in ['setup.py', 'requirements.txt', 'pyproject.toml']:
            metadata = self.create_metadata(filename)
            category = self.classifier.classify(metadata)
            assert category == FileCategory.CONFIGS, f"Failed for {filename}"
        
        # Test by extension
        metadata = self.create_metadata('config.yaml')
        category = self.classifier.classify(metadata)
        assert category == FileCategory.CONFIGS
    
    def test_data_file_classification(self):
        """Test data file classification."""
        for ext in ['.csv', '.json', '.sqlite', '.pkl']:
            filename = f'data{ext}'
            metadata = self.create_metadata(filename)
            category = self.classifier.classify(metadata)
            assert category == FileCategory.DATA, f"Failed for {filename}"
    
    def test_test_file_classification(self):
        """Test file classification by various indicators."""
        # Test by name pattern
        metadata = self.create_metadata('test_something.py')
        category = self.classifier.classify(metadata)
        assert category == FileCategory.TESTS
        
        # Test by has_tests attribute
        metadata = self.create_metadata('foo.py', has_tests=True)
        category = self.classifier.classify(metadata)
        assert category == FileCategory.TESTS
        
        # Test by import
        metadata = self.create_metadata('test_runner.py', imports=['pytest', 'unittest'])
        category = self.classifier.classify(metadata)
        assert category == FileCategory.TESTS
    
    def test_script_file_classification(self):
        """Test script file classification."""
        # Test by executable flag
        metadata = self.create_metadata('run_app.py', is_executable=True)
        category = self.classifier.classify(metadata)
        assert category == FileCategory.SCRIPTS
        
        # Test by name pattern
        metadata = self.create_metadata('main_script.py')
        category = self.classifier.classify(metadata)
        assert category == FileCategory.SCRIPTS
    
    def test_experiment_file_classification(self):
        """Test experimental file classification."""
        for name in ['temp_test.py', 'experiment_1.py', 'playground.py', 'scratch.py']:
            metadata = self.create_metadata(name)
            category = self.classifier.classify(metadata)
            assert category == FileCategory.EXPERIMENTS, f"Failed for {name}"
    
    def test_source_file_classification(self):
        """Test source code classification."""
        # File with meaningful imports
        metadata = self.create_metadata('api.py', imports=['fastapi', 'pydantic', 'sqlalchemy'])
        category = self.classifier.classify(metadata)
        assert category == FileCategory.SRC
    
    def test_priority_test_over_src(self):
        """Test that test classification has priority over src."""
        # File that could be src but has test indicators
        metadata = self.create_metadata(
            'test_api.py',
            imports=['fastapi', 'pytest'],
            has_tests=True
        )
        category = self.classifier.classify(metadata)
        assert category == FileCategory.TESTS
    
    def test_priority_config_over_src(self):
        """Test that config classification has priority over src."""
        metadata = self.create_metadata('setup.py', imports=['setuptools'])
        category = self.classifier.classify(metadata)
        assert category == FileCategory.CONFIGS
    
    def test_classify_all(self):
        """Test classifying multiple files."""
        files = [
            self.create_metadata('test_foo.py', has_tests=True),
            self.create_metadata('app.py', imports=['fastapi']),
            self.create_metadata('README.md'),
            self.create_metadata('config.yaml'),
        ]
        
        results = self.classifier.classify_all(files)
        
        assert len(results) == 4
        # Check that all files were classified
        for file in files:
            rel_path = str(file.relative_path)
            assert rel_path in results


class TestClassificationRules:
    """Test specific classification rules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = FileClassifier()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, filename: str, **kwargs) -> FileMetadata:
        """Helper to create FileMetadata for testing."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        
        for key, value in kwargs.items():
            setattr(metadata, key, value)
        
        return metadata
    
    def test_file_in_test_directory(self):
        """Files in test directories should be classified as tests."""
        file_path = self.temp_dir / 'tests' / 'foo.py'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        category = self.classifier.classify(metadata)
        assert category == FileCategory.TESTS
    
    def test_file_in_src_directory(self):
        """Files in src directory should be classified as source."""
        file_path = self.temp_dir / 'src' / 'app.py'
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        metadata.imports = ['os', 'sys', 'pathlib']  # Some imports
        category = self.classifier.classify(metadata)
        assert category == FileCategory.SRC
