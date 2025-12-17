"""Tests for repository type detection."""
import pytest
from pathlib import Path
import tempfile

from src.analyzer import FileMetadata
from src.repo_type import RepoTypeDetector, RepoType


class TestRepoTypeDetector:
    """Test suite for RepoTypeDetector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = RepoTypeDetector()
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
    
    def test_python_dominant_detection(self):
        """Test detection of Python-dominant repository."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('requirements.txt'),
            self.create_metadata('src/app.py'),
            self.create_metadata('src/utils.py'),
            self.create_metadata('src/models.py'),
            self.create_metadata('tests/test_app.py'),
            self.create_metadata('tests/test_utils.py'),
            self.create_metadata('README.md'),
        ]
        
        repo_type = self.detector.detect(files)
        assert repo_type == RepoType.PYTHON_DOMINANT
    
    def test_non_python_frontend_detection(self):
        """Test detection of non-Python frontend repository."""
        files = [
            self.create_metadata('package.json'),
            self.create_metadata('angular.json'),
            self.create_metadata('tsconfig.json'),
            self.create_metadata('src/app/app.component.ts'),
            self.create_metadata('src/app/app.component.html'),
            self.create_metadata('src/app/app.module.ts'),
            self.create_metadata('src/environments/environment.ts'),
            self.create_metadata('README.md'),
        ]
        
        repo_type = self.detector.detect(files)
        assert repo_type == RepoType.NON_PYTHON
    
    def test_mixed_repository_detection(self):
        """Test detection of mixed repository."""
        files = [
            # Python backend
            self.create_metadata('requirements.txt'),
            self.create_metadata('backend/app.py'),
            self.create_metadata('backend/models.py'),
            self.create_metadata('backend/utils.py'),
            # Frontend
            self.create_metadata('package.json'),
            self.create_metadata('frontend/index.html'),
            self.create_metadata('frontend/app.js'),
            self.create_metadata('frontend/styles.css'),
            # Common
            self.create_metadata('README.md'),
        ]
        
        repo_type = self.detector.detect(files)
        assert repo_type == RepoType.MIXED
    
    def test_empty_repository(self):
        """Test detection with empty repository."""
        files = []
        
        repo_type = self.detector.detect(files)
        assert repo_type == RepoType.NON_PYTHON
    
    def test_java_repository_detection(self):
        """Test detection of Java repository."""
        files = [
            self.create_metadata('pom.xml'),
            self.create_metadata('src/main/java/App.java'),
            self.create_metadata('src/main/java/Utils.java'),
            self.create_metadata('src/test/java/AppTest.java'),
            self.create_metadata('README.md'),
        ]
        
        repo_type = self.detector.detect(files)
        assert repo_type == RepoType.NON_PYTHON
    
    def test_minimal_python_repo(self):
        """Test detection with minimal Python files."""
        files = [
            self.create_metadata('main.py'),
            self.create_metadata('utils.py'),
            self.create_metadata('README.md'),
        ]
        
        repo_type = self.detector.detect(files)
        # Should be NON_PYTHON or MIXED due to lack of Python-specific files
        assert repo_type in (RepoType.NON_PYTHON, RepoType.MIXED)
    
    def test_python_with_pyproject_toml(self):
        """Test detection with modern Python project."""
        files = [
            self.create_metadata('pyproject.toml'),
            self.create_metadata('src/mypackage/__init__.py'),
            self.create_metadata('src/mypackage/main.py'),
            self.create_metadata('src/mypackage/utils.py'),
            self.create_metadata('tests/test_main.py'),
            self.create_metadata('README.md'),
        ]
        
        repo_type = self.detector.detect(files)
        assert repo_type == RepoType.PYTHON_DOMINANT
    
    def test_detection_summary(self):
        """Test that detection summary provides useful info."""
        files = [
            self.create_metadata('setup.py'),
            self.create_metadata('app.py'),
            self.create_metadata('README.md'),
        ]
        
        self.detector.detect(files)
        summary = self.detector.get_summary()
        
        assert 'extension_counts' in summary
        assert 'root_files' in summary
        assert 'setup.py' in summary['root_files']
        assert '.py' in summary['extension_counts']
    
    def test_typescript_heavy_mixed_repo(self):
        """Test TypeScript-heavy repo with some Python."""
        files = []
        
        # Add many TypeScript files
        for i in range(25):
            files.append(self.create_metadata(f'src/component{i}.ts'))
        
        # Add a few Python files
        files.append(self.create_metadata('scripts/deploy.py'))
        files.append(self.create_metadata('scripts/build.py'))
        
        # Add package.json
        files.append(self.create_metadata('package.json'))
        
        repo_type = self.detector.detect(files)
        # Should be NON_PYTHON due to TypeScript dominance and package.json
        assert repo_type == RepoType.NON_PYTHON


class TestRepoTypeScoring:
    """Test scoring logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = RepoTypeDetector()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def create_metadata(self, filename: str) -> FileMetadata:
        """Helper to create FileMetadata for testing."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        return FileMetadata(file_path, self.temp_dir)
    
    def test_python_score_with_many_py_files(self):
        """Test Python score increases with more .py files."""
        files = [self.create_metadata(f'file{i}.py') for i in range(15)]
        files.append(self.create_metadata('setup.py'))
        
        self.detector.detect(files)
        score = self.detector._calculate_python_score()
        
        # Should have high score: many .py files + setup.py
        assert score >= 5
    
    def test_non_python_score_with_frontend_files(self):
        """Test non-Python score with frontend indicators."""
        files = [
            self.create_metadata('package.json'),
            self.create_metadata('angular.json'),
            self.create_metadata('tsconfig.json'),
        ]
        
        self.detector.detect(files)
        score = self.detector._calculate_non_python_score()
        
        # Should have high score from frontend files
        assert score >= 3
