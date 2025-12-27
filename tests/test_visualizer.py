"""Tests for the visualizer module (V2.2 Phase 2)."""
import pytest
from pathlib import Path

from src.visualizer import TreeDiffVisualizer, TreeNode
from src.proposal import Proposal, ActionType, RiskLevel


class TestTreeNode:
    """Test TreeNode construction and rendering."""
    
    def test_tree_node_creation(self):
        """Test creating a tree node."""
        node = TreeNode("test.py", is_file=True)
        assert node.name == "test.py"
        assert node.is_file is True
        assert len(node.children) == 0
    
    def test_add_single_path(self):
        """Test adding a single file path."""
        root = TreeNode(".")
        root.add_path(Path("test.py"))
        
        assert "test.py" in root.children
        assert root.children["test.py"].is_file is True
    
    def test_add_nested_path(self):
        """Test adding a nested file path."""
        root = TreeNode(".")
        root.add_path(Path("src/app.py"))
        
        assert "src" in root.children
        assert root.children["src"].is_file is False
        assert "app.py" in root.children["src"].children
        assert root.children["src"].children["app.py"].is_file is True
    
    def test_render_simple_tree(self):
        """Test rendering a simple tree."""
        root = TreeNode(".")
        root.add_path(Path("test.py"))
        root.add_path(Path("app.py"))
        
        lines = root.render()
        rendered = "\n".join(lines)
        
        assert "test.py" in rendered
        assert "app.py" in rendered
    
    def test_render_nested_tree(self):
        """Test rendering a nested tree."""
        root = TreeNode(".")
        root.add_path(Path("src/app.py"))
        root.add_path(Path("tests/test_app.py"))
        
        lines = root.render()
        rendered = "\n".join(lines)
        
        assert "src/" in rendered
        assert "app.py" in rendered
        assert "tests/" in rendered
        assert "test_app.py" in rendered


class TestTreeDiffVisualizer:
    """Test TreeDiffVisualizer functionality."""
    
    def test_visualizer_initialization(self):
        """Test visualizer initialization."""
        proposals = []
        current_files = [Path("test.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        
        assert visualizer.proposals == proposals
        assert visualizer.current_files == current_files
        assert visualizer.move_proposals == []
        assert visualizer.flag_proposals == []
    
    def test_move_proposal_filtering(self):
        """Test that visualizer correctly filters MOVE proposals."""
        move_proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path("test.py"),
            target_path=Path("tests/test.py"),
            reason="Test file",
            risk_level=RiskLevel.LOW
        )
        
        flag_proposal = Proposal(
            action=ActionType.FLAG,
            source_path=Path("utils.py"),
            target_path=None,
            reason="Review needed",
            risk_level=RiskLevel.MEDIUM
        )
        
        proposals = [move_proposal, flag_proposal]
        current_files = [Path("test.py"), Path("utils.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        
        assert len(visualizer.move_proposals) == 1
        assert len(visualizer.flag_proposals) == 1
        assert visualizer.move_proposals[0] == move_proposal
        assert visualizer.flag_proposals[0] == flag_proposal
    
    def test_generate_tree_diff(self):
        """Test generating before/after tree diff."""
        move_proposal = Proposal(
            action=ActionType.MOVE,
            source_path=Path("test.py"),
            target_path=Path("tests/test.py"),
            reason="Test file",
            risk_level=RiskLevel.LOW
        )
        
        proposals = [move_proposal]
        current_files = [Path("test.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        diff = visualizer.generate_tree_diff()
        
        assert 'before' in diff
        assert 'after' in diff
        assert isinstance(diff['before'], str)
        assert isinstance(diff['after'], str)
        assert "test.py" in diff['before']
        assert "tests/" in diff['after']
        assert "test.py" in diff['after']
    
    def test_simulate_after_state(self):
        """Test simulating file structure after moves."""
        move1 = Proposal(
            action=ActionType.MOVE,
            source_path=Path("test.py"),
            target_path=Path("tests/test.py"),
            reason="Test",
            risk_level=RiskLevel.LOW
        )
        
        move2 = Proposal(
            action=ActionType.MOVE,
            source_path=Path("app.py"),
            target_path=Path("src/app.py"),
            reason="Source",
            risk_level=RiskLevel.MEDIUM
        )
        
        proposals = [move1, move2]
        current_files = [Path("test.py"), Path("app.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        after_state = visualizer._simulate_after_state()
        
        assert Path("tests/test.py") in after_state
        assert Path("src/app.py") in after_state
        assert Path("test.py") not in after_state
        assert Path("app.py") not in after_state
    
    def test_generate_impact_summary(self):
        """Test generating impact summary."""
        move1 = Proposal(
            action=ActionType.MOVE,
            source_path=Path("test.py"),
            target_path=Path("tests/test.py"),
            reason="Test",
            risk_level=RiskLevel.LOW
        )
        
        move2 = Proposal(
            action=ActionType.MOVE,
            source_path=Path("app.py"),
            target_path=Path("src/app.py"),
            reason="Source",
            risk_level=RiskLevel.HIGH
        )
        
        flag = Proposal(
            action=ActionType.FLAG,
            source_path=Path("utils.py"),
            target_path=None,
            reason="Duplicate filename: 2 files named 'utils.py'",
            risk_level=RiskLevel.MEDIUM
        )
        
        proposals = [move1, move2, flag]
        current_files = [Path("test.py"), Path("app.py"), Path("utils.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        summary = visualizer.generate_impact_summary()
        
        assert summary['total_moves'] == 2
        assert summary['total_flags'] == 1
        assert summary['duplicate_groups'] == 1
        assert summary['risk_breakdown']['high'] == 1
        assert summary['risk_breakdown']['medium'] == 0
        assert summary['risk_breakdown']['low'] == 1
        assert 'tests' in summary['new_directories']
        assert 'src' in summary['new_directories']
    
    def test_impact_summary_with_no_moves(self):
        """Test impact summary when only flags exist (advisory mode)."""
        flag = Proposal(
            action=ActionType.FLAG,
            source_path=Path("config.json"),
            target_path=None,
            reason="Duplicate filename: 3 files named 'config.json'",
            risk_level=RiskLevel.HIGH
        )
        
        proposals = [flag]
        current_files = [Path("config.json")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        summary = visualizer.generate_impact_summary()
        
        assert summary['total_moves'] == 0
        assert summary['total_flags'] == 1
        assert summary['duplicate_groups'] == 1
        assert len(summary['new_directories']) == 0
    
    def test_render_impact_summary(self):
        """Test rendering impact summary as text."""
        move = Proposal(
            action=ActionType.MOVE,
            source_path=Path("test.py"),
            target_path=Path("tests/test.py"),
            reason="Test",
            risk_level=RiskLevel.LOW
        )
        
        proposals = [move]
        current_files = [Path("test.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        rendered = visualizer.render_impact_summary()
        
        assert "IMPACT SUMMARY" in rendered
        assert "Files to be moved:" in rendered
        assert "1" in rendered
        assert "New directories:" in rendered
        assert "tests" in rendered
    
    def test_render_impact_summary_advisory_mode(self):
        """Test rendering impact summary for advisory-only mode."""
        flag = Proposal(
            action=ActionType.FLAG,
            source_path=Path("config.json"),
            target_path=None,
            reason="Review needed",
            risk_level=RiskLevel.MEDIUM
        )
        
        proposals = [flag]
        current_files = [Path("config.json")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        rendered = visualizer.render_impact_summary()
        
        assert "IMPACT SUMMARY" in rendered
        assert "ADVISORY MODE" in rendered
        assert "No moves proposed" in rendered
    
    def test_render_tree_diff(self):
        """Test rendering complete tree diff."""
        move = Proposal(
            action=ActionType.MOVE,
            source_path=Path("test.py"),
            target_path=Path("tests/test.py"),
            reason="Test",
            risk_level=RiskLevel.LOW
        )
        
        proposals = [move]
        current_files = [Path("test.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        rendered = visualizer.render_tree_diff()
        
        assert "DIRECTORY STRUCTURE PREVIEW" in rendered
        assert "BEFORE (current):" in rendered
        assert "AFTER (if proposals applied):" in rendered
        assert "test.py" in rendered
        assert "tests/" in rendered
    
    def test_affected_files_includes_flags(self):
        """Test that affected files include both moves and flags."""
        move = Proposal(
            action=ActionType.MOVE,
            source_path=Path("app.py"),
            target_path=Path("src/app.py"),
            reason="Source",
            risk_level=RiskLevel.MEDIUM
        )
        
        flag = Proposal(
            action=ActionType.FLAG,
            source_path=Path("config.py"),
            target_path=None,
            reason="Review",
            risk_level=RiskLevel.LOW
        )
        
        proposals = [move, flag]
        current_files = [Path("app.py"), Path("config.py")]
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        affected = visualizer._get_affected_files()
        
        assert Path("app.py") in affected
        assert Path("config.py") in affected
        assert len(affected) == 2
    
    def test_new_directories_extraction(self):
        """Test extraction of new directories from proposals."""
        move1 = Proposal(
            action=ActionType.MOVE,
            source_path=Path("test.py"),
            target_path=Path("tests/unit/test.py"),
            reason="Test",
            risk_level=RiskLevel.LOW
        )
        
        move2 = Proposal(
            action=ActionType.MOVE,
            source_path=Path("app.py"),
            target_path=Path("src/services/app.py"),
            reason="Source",
            risk_level=RiskLevel.MEDIUM
        )
        
        proposals = [move1, move2]
        current_files = []
        
        visualizer = TreeDiffVisualizer(proposals, current_files)
        summary = visualizer.generate_impact_summary()
        
        new_dirs = summary['new_directories']
        assert 'tests' in new_dirs
        assert 'tests/unit' in new_dirs or 'tests\\unit' in new_dirs
        assert 'src' in new_dirs
        assert 'src/services' in new_dirs or 'src\\services' in new_dirs
