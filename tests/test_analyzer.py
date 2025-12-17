"""Tests for the repository analyzer."""
import pytest
from pathlib import Path
import tempfile
import os

from src.analyzer import RepositoryAnalyzer, FileMetadata


class TestRepositoryAnalyzer:
    """Test suite for RepositoryAnalyzer."""
    
    def setup_method(self):
        """Set up test repository."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test structure
        (self.temp_dir / 'src').mkdir()
        (self.temp_dir / 'tests').mkdir()
        (self.temp_dir / 'venv').mkdir()  # Should be ignored
        
        # Create test files
        (self.temp_dir / 'README.md').touch()
        (self.temp_dir / 'src' / 'app.py').write_text('import os\n\nprint("hello")')
        (self.temp_dir / 'tests' / 'test_app.py').write_text('def test_foo():\n    pass')
        (self.temp_dir / 'venv' / 'script.py').touch()  # Should be ignored
    
    def test_analyzer_initialization(self):
        """Test that analyzer initializes correctly."""
        analyzer = RepositoryAnalyzer(str(self.temp_dir))
        assert analyzer.repo_path == self.temp_dir
    
    def test_invalid_path_raises_error(self):
        """Test that invalid paths raise errors."""
        with pytest.raises(ValueError):
            RepositoryAnalyzer('/nonexistent/path')
    
    def test_analyze_finds_files(self):
        """Test that analyze finds all non-ignored files."""
        analyzer = RepositoryAnalyzer(str(self.temp_dir))
        files = analyzer.analyze()
        
        # Should find README, app.py, test_app.py
        # Should NOT find venv/script.py
        assert len(files) >= 3
        
        filenames = {f.name for f in files}
        assert 'README.md' in filenames
        assert 'app.py' in filenames
        assert 'test_app.py' in filenames
        assert 'script.py' not in filenames  # In venv, should be ignored
    
    def test_ignore_patterns(self):
        """Test that ignore patterns work correctly."""
        analyzer = RepositoryAnalyzer(str(self.temp_dir))
        
        # Should ignore venv directory
        assert analyzer.should_ignore(self.temp_dir / 'venv')
        assert analyzer.should_ignore(self.temp_dir / 'venv' / 'script.py')
        
        # Should ignore .pyc files
        assert analyzer.should_ignore(self.temp_dir / 'test.pyc')
        
        # Should NOT ignore normal files
        assert not analyzer.should_ignore(self.temp_dir / 'app.py')
    
    def test_path_containment_exclusion(self):
        """Test that path containment correctly excludes vendored directories."""
        analyzer = RepositoryAnalyzer(str(self.temp_dir))
        
        # Should ignore paths CONTAINING venv-related strings
        assert analyzer.should_ignore(self.temp_dir / 'venv_new' / 'lib' / 'script.py')
        assert analyzer.should_ignore(self.temp_dir / 'my_venv' / 'script.py')
        assert analyzer.should_ignore(self.temp_dir / '.venv' / 'script.py')
        
        # Should ignore paths containing site-packages
        assert analyzer.should_ignore(self.temp_dir / 'venv_new' / 'Lib' / 'site-packages' / 'torch' / 'nn.py')
        assert analyzer.should_ignore(self.temp_dir / 'lib' / 'site-packages' / 'numpy' / 'core.py')
        
        # Should ignore paths containing node_modules
        assert analyzer.should_ignore(self.temp_dir / 'node_modules' / 'react' / 'index.js')
        assert analyzer.should_ignore(self.temp_dir / 'frontend' / 'node_modules' / 'package.json')
        
        # Should ignore paths containing build/dist
        assert analyzer.should_ignore(self.temp_dir / 'build' / 'output.js')
        assert analyzer.should_ignore(self.temp_dir / 'dist' / 'bundle.js')
        
        # Should NOT ignore normal paths with similar but different names
        assert not analyzer.should_ignore(self.temp_dir / 'environment.py')
        assert not analyzer.should_ignore(self.temp_dir / 'convention.py')
    
    def test_python_file_analysis(self):
        """Test that Python files are analyzed for imports."""
        analyzer = RepositoryAnalyzer(str(self.temp_dir))
        files = analyzer.analyze()
        
        # Find the app.py file
        app_file = next((f for f in files if f.name == 'app.py'), None)
        assert app_file is not None
        assert 'os' in app_file.imports
    
    def test_test_file_detection(self):
        """Test that test files are detected."""
        analyzer = RepositoryAnalyzer(str(self.temp_dir))
        files = analyzer.analyze()
        
        # Find test_app.py
        test_file = next((f for f in files if f.name == 'test_app.py'), None)
        assert test_file is not None
        assert test_file.has_tests
    
    def test_get_summary(self):
        """Test summary statistics."""
        analyzer = RepositoryAnalyzer(str(self.temp_dir))
        analyzer.analyze()
        summary = analyzer.get_summary()
        
        assert 'total_files' in summary
        assert summary['total_files'] >= 3
        assert 'python_files' in summary
        assert summary['python_files'] >= 2
        assert 'extensions' in summary


class TestFileMetadata:
    """Test FileMetadata class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def test_metadata_initialization(self):
        """Test FileMetadata initialization."""
        file_path = self.temp_dir / 'test.py'
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        
        assert metadata.path == file_path
        assert metadata.name == 'test.py'
        assert metadata.extension == '.py'
        assert metadata.relative_path == Path('test.py')
    
    def test_metadata_to_dict(self):
        """Test metadata conversion to dictionary."""
        file_path = self.temp_dir / 'test.py'
        file_path.touch()
        
        metadata = FileMetadata(file_path, self.temp_dir)
        metadata.imports = ['os', 'sys']
        
        data = metadata.to_dict()
        
        assert data['name'] == 'test.py'
        assert data['extension'] == '.py'
        assert data['imports'] == ['os', 'sys']
