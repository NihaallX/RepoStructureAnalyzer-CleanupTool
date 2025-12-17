"""Quick demo script showing clean output."""
import logging
import sys
from pathlib import Path

# Disable logging for clean output
logging.disable(logging.CRITICAL)

from src.analyzer import RepositoryAnalyzer
from src.reasoner import StructureReasoner

def main():
    print("=" * 70)
    print("REPO STRUCTURE ANALYZER - DEMO")
    print("=" * 70)
    
    repo_path = Path(".")
    
    # Analyze
    print("\n📊 ANALYZING REPOSITORY...")
    analyzer = RepositoryAnalyzer(str(repo_path))
    files = analyzer.analyze()
    
    summary = analyzer.get_summary()
    print(f"   Found {summary['total_files']} files")
    print(f"   - Python files: {summary['python_files']}")
    print(f"   - Test files: {summary['test_files']}")
    
    # Generate proposals
    print("\n💡 GENERATING PROPOSALS...")
    reasoner = StructureReasoner(repo_path)
    generator = reasoner.generate_proposals(files)
    
    print(f"   Generated {generator.get_count()} proposals")
    
    # Show summary
    print("\n" + "=" * 70)
    print("PROPOSAL SUMMARY")
    print("=" * 70)
    
    by_action = {}
    by_risk = {}
    for p in generator.proposals:
        by_action[p.action.value] = by_action.get(p.action.value, 0) + 1
        by_risk[p.risk_level.value] = by_risk.get(p.risk_level.value, 0) + 1
    
    print("\nBy Action:")
    for action, count in sorted(by_action.items()):
        print(f"  • {action}: {count}")
    
    print("\nBy Risk Level:")
    for risk, count in sorted(by_risk.items()):
        print(f"  • {risk}: {count}")
    
    # Show first 3 proposals
    print("\n" + "=" * 70)
    print("SAMPLE PROPOSALS (first 3)")
    print("=" * 70)
    
    for i, proposal in enumerate(generator.proposals[:3], 1):
        print(f"\n[{i}] {proposal.action.value.upper()}: {proposal.source_path}")
        if proposal.target_path:
            print(f"    → {proposal.target_path}")
        print(f"    Reason: {proposal.reason}")
        print(f"    Risk: {proposal.risk_level.value.upper()}")
    
    print("\n" + "=" * 70)
    print("✓ Demo complete! Run 'repo-tool propose .' for full output")
    print("=" * 70)

if __name__ == "__main__":
    main()
