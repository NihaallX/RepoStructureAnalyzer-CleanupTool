"""Structure reasoner - generates proposals for file organization."""
from pathlib import Path
from typing import List, Dict, Set
import logging

from .analyzer import FileMetadata
from .classifier import FileClassifier, FileCategory
from .proposal import ProposalGenerator, RiskLevel, ActionType
from .repo_type import RepoTypeDetector, RepoType
from .ecosystem import get_profile_for_repo_type, EcosystemProfile

logger = logging.getLogger(__name__)


class StructureReasoner:
    """Analyzes repository structure and generates improvement proposals."""
    
    # Structural Python files that should not trigger duplicate detection
    DUPLICATE_EXEMPT_FILES = {
        '__init__.py',
        '__main__.py',
        'conftest.py',
    }
    
    def __init__(self, repo_path: Path):
        """Initialize reasoner."""
        self.repo_path = repo_path
        self.classifier = FileClassifier()
        self.generator = ProposalGenerator()
        self.detector = RepoTypeDetector()
        self.repo_type = None
        self.ecosystem_profile: EcosystemProfile = None
    
    def generate_proposals(self, files: List[FileMetadata]) -> ProposalGenerator:
        """Generate all proposals for the repository."""
        logger.info("Generating structural proposals...")
        
        # Step 1: Detect repository type
        self.repo_type = self.detector.detect(files)
        logger.info(f"Repository type: {self.repo_type.value}")
        
        # V2: Select ecosystem profile based on repository type
        # V2: Enables suppression of expected framework duplicates (e.g., index.html in Next.js)
        self.ecosystem_profile = get_profile_for_repo_type(self.repo_type)
        logger.info(f"Using ecosystem profile: {self.ecosystem_profile.name}")
        
        # Step 2: Add informational message for non-Python repos
        if self.repo_type == RepoType.NON_PYTHON:
            logger.warning("Non-Python repository detected. MOVE proposals disabled for safety.")
            logger.info("Only duplicate detection and flagging will be performed.")
        elif self.repo_type == RepoType.MIXED:
            logger.info("Mixed repository detected. MOVE proposals limited to Python files only.")
        
        # Step 3: Classify all files first
        classifications = {}
        for file in files:
            category = self.classifier.classify(file)
            classifications[str(file.relative_path)] = (file, category)
        
        # Step 4: Generate proposals based on repo type
        if self.repo_type == RepoType.PYTHON_DOMINANT:
            # Full proposal generation for Python repos
            for rel_path, (file, category) in classifications.items():
                self._propose_for_file(file, category)
        elif self.repo_type == RepoType.MIXED:
            # Only propose moves for Python files
            for rel_path, (file, category) in classifications.items():
                if file.extension == '.py':
                    self._propose_for_file(file, category)
        # For NON_PYTHON: skip MOVE proposals entirely
        
        # Step 5: Always detect duplicates and orphans (all repo types)
        self._detect_duplicates(files)
        self._detect_orphans(files)
        
        # Step 6: FINAL SAFETY CHECK - Drop MOVE proposals for non-Python repos
        if self.repo_type != RepoType.PYTHON_DOMINANT:
            original_count = self.generator.get_count()
            move_proposals = self.generator.get_by_action(ActionType.MOVE)
            
            # Remove all MOVE proposals
            self.generator.proposals = [
                p for p in self.generator.proposals 
                if p.action != ActionType.MOVE
            ]
            
            if len(move_proposals) > 0:
                logger.info(f"Dropped {len(move_proposals)} MOVE proposals (non-Python repository)")
        
        # Step 7: Suppress redundant FLAG proposals when MOVE exists
        self._suppress_redundant_flags()
        
        logger.info(f"Generated {self.generator.get_count()} proposals")
        return self.generator
    
    def _propose_for_file(self, file: FileMetadata, category: FileCategory):
        """Generate proposal for a single file."""
        current_path = file.relative_path
        current_parts = current_path.parts
        
        # Skip if already in correct location
        if self._is_correctly_placed(current_path, category):
            return
        
        # Generate target path based on category
        target_path = self._generate_target_path(file, category)
        
        if target_path is None:
            return
        
        # Skip no-op moves (source == target)
        # Resolve both paths to normalize separators and compare
        source_resolved = Path(current_path)
        target_resolved = Path(target_path)
        if source_resolved == target_resolved:
            return
        
        # Calculate risk level
        risk = self._assess_risk(file, category)
        
        # Generate reason
        reason = self._generate_reason(file, category)
        
        # Add proposal
        self.generator.add_move(
            source=current_path,
            target=target_path,
            reason=reason,
            risk=risk,
            category=category.value,
            current_location=str(current_path.parent) if current_path.parent != Path('.') else 'root',
        )
    
    def _is_correctly_placed(self, path: Path, category: FileCategory) -> bool:
        """Check if file is already in the correct location."""
        parts = path.parts
        if not parts:
            return False
        
        first_dir = parts[0] if len(parts) > 1 else None
        
        # Check if file is already in the right category directory
        if category == FileCategory.SRC and first_dir == 'src':
            return True
        elif category == FileCategory.TESTS and first_dir in ('tests', 'test'):
            return True
        elif category == FileCategory.CONFIGS and first_dir in ('configs', 'config'):
            return True
        elif category == FileCategory.SCRIPTS and first_dir == 'scripts':
            return True
        elif category == FileCategory.DOCS and first_dir == 'docs':
            return True
        elif category == FileCategory.MARKDOWN and first_dir in ('docs', 'markdown'):
            return True
        elif category == FileCategory.DATA and first_dir == 'data':
            return True
        elif category == FileCategory.EXPERIMENTS and first_dir in ('experiments', 'playground'):
            return True
        
        return False
    
    def _generate_target_path(self, file: FileMetadata, category: FileCategory) -> Path:
        """Generate target path for a file based on its category."""
        name = file.name
        current_path = file.relative_path
        
        if category == FileCategory.SRC:
            # Try to preserve package structure
            if len(current_path.parts) > 1:
                # Has subdirectories, preserve structure
                return Path('src') / current_path
            else:
                return Path('src') / name
        
        elif category == FileCategory.TESTS:
            # Convert to test naming convention
            if not name.startswith('test_'):
                if name.endswith('_test.py'):
                    new_name = name
                else:
                    # Convert foo.py -> test_foo.py
                    new_name = f"test_{name}"
            else:
                new_name = name
            
            # Try to mirror src structure
            if len(current_path.parts) > 1:
                return Path('tests') / current_path.parent / new_name
            else:
                return Path('tests') / new_name
        
        elif category == FileCategory.CONFIGS:
            # Keep configs at root or in configs/
            if name in ('setup.py', 'setup.cfg', 'pyproject.toml', 
                       'requirements.txt', '.gitignore'):
                return Path(name)  # Root level
            else:
                return Path('configs') / name
        
        elif category == FileCategory.SCRIPTS:
            return Path('scripts') / name
        
        elif category == FileCategory.DOCS:
            return Path('docs') / name
        
        elif category == FileCategory.MARKDOWN:
            # README.md at root, others in docs/
            if name.upper() == 'README.MD':
                return Path('README.md')
            else:
                return Path('docs') / name
        
        elif category == FileCategory.DATA:
            return Path('data') / name
        
        elif category == FileCategory.EXPERIMENTS:
            return Path('experiments') / name
        
        elif category == FileCategory.TRASH:
            # Flag for review, don't auto-move
            self.generator.add_flag(
                source=current_path,
                reason="Could not classify - needs manual review",
                risk=RiskLevel.LOW,
                category=category.value,
            )
            return None
        
        return None
    
    def _assess_risk(self, file: FileMetadata, category: FileCategory) -> RiskLevel:
        """Assess risk level for moving a file."""
        # High risk if file has many imports (likely dependencies)
        if len(file.imports) > 10:
            return RiskLevel.HIGH
        
        # Medium risk if file is executable or has main
        if file.is_executable:
            return RiskLevel.MEDIUM
        
        # Medium risk for config files
        if category == FileCategory.CONFIGS:
            return RiskLevel.MEDIUM
        
        # Low risk for tests, docs, data
        if category in (FileCategory.TESTS, FileCategory.DOCS, 
                       FileCategory.MARKDOWN, FileCategory.DATA):
            return RiskLevel.LOW
        
        # Default to low
        return RiskLevel.LOW
    
    def _generate_reason(self, file: FileMetadata, category: FileCategory) -> str:
        """Generate human-readable reason for the proposal.
        
        V2.2: Enhanced explanations for better decision support.
        Maps directly to classification logic - no AI hallucination.
        """
        reasons = []
        current_location = str(file.relative_path.parent) if file.relative_path.parent != Path('.') else 'repository root'
        
        if category == FileCategory.TESTS:
            # Explain why it's a test file
            if file.has_tests:
                reasons.append("Contains test functions or test classes (pytest/unittest pattern detected)")
            if any(imp in self.classifier.TEST_IMPORT_PATTERNS for imp in file.imports):
                test_frameworks = [imp for imp in file.imports if imp in self.classifier.TEST_IMPORT_PATTERNS]
                reasons.append(f"Imports testing frameworks: {', '.join(test_frameworks[:2])}")
            if file.name.startswith('test_') or file.name.endswith('_test.py'):
                reasons.append("Follows test file naming convention")
            
            # Explain why it needs to move
            if current_location not in ['tests', 'test']:
                reasons.append(f"Currently located in {current_location}, should be in tests/ directory")
        
        elif category == FileCategory.SRC:
            # Explain why it's application code
            if file.imports:
                reasons.append(f"Contains {len(file.imports)} imports, indicating application logic")
            if len(file.imports) > 5:
                reasons.append("Multiple dependencies suggest core application module")
            if not file.has_tests and not file.is_executable:
                reasons.append("Non-executable library code (not a script)")
            
            # Explain why it needs to move
            if current_location == 'repository root':
                reasons.append("Python modules should be organized under src/ or package directory")
        
        elif category == FileCategory.SCRIPTS:
            # Explain why it's a script
            if file.is_executable:
                reasons.append("Contains __main__ block, indicating executable entry point")
            if file.name in ['setup.py', 'manage.py', 'run.py']:
                reasons.append("Common script name pattern detected")
            
            # Explain why it needs to move
            if current_location == 'repository root':
                reasons.append("Executable scripts should be organized in scripts/ directory")
        
        elif category == FileCategory.CONFIGS:
            # Explain what kind of config it is
            config_types = {
                '.env': 'environment variables',
                '.yaml': 'YAML configuration',
                '.yml': 'YAML configuration',
                '.toml': 'TOML configuration',
                '.ini': 'INI configuration',
                '.json': 'JSON configuration',
                'requirements.txt': 'Python dependencies',
                'Pipfile': 'Python dependencies',
                'pyproject.toml': 'Python project metadata',
            }
            
            for pattern, config_type in config_types.items():
                if pattern in file.name:
                    reasons.append(f"Configuration file: {config_type}")
                    break
            
            if not reasons:
                reasons.append("Configuration file detected by naming pattern")
            
            # Keep root configs at root
            if file.name in ['setup.py', 'setup.cfg', 'pyproject.toml', 'requirements.txt']:
                reasons.append("Standard root-level configuration file")
            elif current_location not in ['configs', 'config']:
                reasons.append("Should be organized in configs/ directory")
        
        elif category == FileCategory.EXPERIMENTS:
            # Explain why it's experimental
            if 'test' in file.name.lower() or 'temp' in file.name.lower():
                reasons.append("Temporary or experimental file naming pattern")
            if 'playground' in str(file.relative_path).lower():
                reasons.append("Located in experimental/playground area")
            reasons.append("Consider moving to experiments/ or removing if obsolete")
        
        elif category == FileCategory.MARKDOWN:
            # Explain why it's documentation
            if file.name.upper() == 'README.MD':
                reasons.append("Primary project README - should remain at repository root")
            else:
                reasons.append("Markdown documentation file")
                if current_location == 'repository root':
                    reasons.append("Documentation files should be organized in docs/ directory")
        
        elif category == FileCategory.DATA:
            # Explain what kind of data
            data_types = {
                '.json': 'JSON data',
                '.csv': 'CSV data',
                '.txt': 'text data',
                '.xml': 'XML data',
                '.yaml': 'YAML data',
            }
            
            for ext, data_type in data_types.items():
                if file.extension == ext:
                    reasons.append(f"Data file: {data_type}")
                    break
            
            if not reasons:
                reasons.append("Data file detected")
            
            if current_location == 'repository root':
                reasons.append("Data files should be organized in data/ directory")
        
        # Fallback
        if not reasons:
            reasons.append(f"Classified as {category.value} based on file analysis")
        
        return ". ".join(reasons) + "."
    
    def _assess_duplicate_risk(self, filename: str) -> RiskLevel:
        """Assess risk level for duplicate files based on filename patterns.
        
        Heuristics:
        - HIGH: Critical config/dependency files (requirements.txt, .env, Dockerfile, package.json)
        - LOW: Documentation (README.md, *.md), logs (*.log), temporary files
        - MEDIUM: Everything else (default for duplicates)
        """
        filename_lower = filename.lower()
        
        # HIGH risk: Critical configuration and dependency files
        high_risk_patterns = [
            'requirements.txt',
            '.env',
            'dockerfile',
            'docker-compose.yml',
            'docker-compose.yaml',
            'package.json',
            'package-lock.json',
            'yarn.lock',
            'pipfile',
            'pipfile.lock',
            'setup.py',
            'pyproject.toml',
        ]
        
        if filename_lower in high_risk_patterns:
            return RiskLevel.HIGH
        
        # LOW risk: Documentation and logs
        low_risk_patterns = [
            'readme.md',
            'changelog.md',
            'license',
            'license.md',
            'license.txt',
            'contributing.md',
        ]
        
        if filename_lower in low_risk_patterns:
            return RiskLevel.LOW
        
        # LOW risk: Log files and temporary files
        if filename_lower.endswith('.log') or filename_lower.endswith('.tmp'):
            return RiskLevel.LOW
        
        # MEDIUM risk: Default for all other duplicates
        return RiskLevel.MEDIUM
    
    def _detect_duplicates(self, files: List[FileMetadata]):
        """V2: Detect potential duplicate files and emit grouped FLAGs.
        
        V2 Behavior:
        - Emits ONE FLAG per duplicate group (not one per file)
        - Includes total count, examples, and remaining indicator
        - Respects ecosystem profile suppression (e.g., index.html in Next.js)
        - Maintains risk stratification (HIGH/MEDIUM/LOW)
        """
        by_name = {}
        for file in files:
            name = file.name.lower()
            
            # Skip structural Python files
            if file.name in self.DUPLICATE_EXEMPT_FILES:
                continue
            
            if name not in by_name:
                by_name[name] = []
            by_name[name].append(file)
        
        for name, file_list in by_name.items():
            if len(file_list) > 1:
                # V2: Check if ecosystem profile suppresses this duplicate
                if self.ecosystem_profile and self.ecosystem_profile.should_suppress_duplicate(file_list[0].name):
                    logger.debug(f"Suppressing duplicate for {file_list[0].name} (ecosystem: {self.ecosystem_profile.name})")
                    continue
                
                # Assess risk based on filename
                risk = self._assess_duplicate_risk(file_list[0].name)
                
                # V2 GROUPED DUPLICATE FLAG: Emit one FLAG per duplicate group
                # V2: Include up to 3 example paths, indicate remaining count
                total_count = len(file_list)
                example_paths = [str(f.relative_path) for f in file_list[:3]]
                remaining = total_count - 3
                
                # Build the reason with examples
                reason = f"Duplicate filename: {total_count} files named '{file_list[0].name}'"
                
                # Build details with all paths for reference
                all_paths = [str(f.relative_path) for f in file_list]
                details = {
                    'total_count': total_count,
                    'examples': example_paths,
                    'all_duplicates': all_paths,
                }
                
                if remaining > 0:
                    details['remaining'] = f"+{remaining} more"
                
                # Emit single grouped FLAG using first file as the source
                self.generator.add_flag(
                    source=file_list[0].relative_path,
                    reason=reason,
                    risk=risk,
                    **details,
                    )
    
    def _detect_orphans(self, files: List[FileMetadata]):
        """Detect orphaned or isolated files."""
        # Only flag orphans in Python-dominant repos
        if self.repo_type != RepoType.PYTHON_DOMINANT:
            return
        
        # Files at root that shouldn't be there
        for file in files:
            if len(file.relative_path.parts) == 1:  # At root
                if file.extension == '.py':
                    # Python files at root are often misplaced
                    if file.name not in ('setup.py', 'manage.py'):
                        self.generator.add_flag(
                            source=file.relative_path,
                            reason="Python file at repository root",
                            risk=RiskLevel.LOW,
                            suggestion="Consider moving to src/ or scripts/",
                        )
    
    def _suppress_redundant_flags(self):
        """Suppress low-signal FLAG proposals when MOVE proposal exists for same file.
        
        Rules:
        - If a file has a MOVE proposal, suppress informational FLAGs
        - Keep duplicate-detection FLAGs (they provide different signal)
        - Suppression happens at output stage, not during detection
        """
        # Build set of files with MOVE proposals
        files_with_moves = set()
        for proposal in self.generator.proposals:
            if proposal.action == ActionType.MOVE:
                files_with_moves.add(str(proposal.source_path))
        
        # Define redundant FLAG patterns (low-signal informational flags)
        redundant_patterns = [
            "Python file at repository root",
            # Add more patterns here as needed
        ]
        
        # Filter proposals: keep all MOVEs and non-redundant FLAGs
        original_count = len(self.generator.proposals)
        self.generator.proposals = [
            p for p in self.generator.proposals
            if not (
                # Only filter FLAGs (keep all MOVEs and DELETEs)
                p.action == ActionType.FLAG
                # Only if the file also has a MOVE
                and str(p.source_path) in files_with_moves
                # Only if it's a redundant informational FLAG
                and any(pattern in p.reason for pattern in redundant_patterns)
                # Never filter duplicate detection FLAGs
                and not p.reason.startswith("Duplicate filename:")
            )
        ]
        
        suppressed_count = original_count - len(self.generator.proposals)
        if suppressed_count > 0:
            logger.info(f"Suppressed {suppressed_count} redundant FLAG proposals")
