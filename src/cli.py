"""Command-line interface for the repo structure tool."""
import click
import logging
from pathlib import Path
import sys

from .analyzer import RepositoryAnalyzer
from .reasoner import StructureReasoner

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='2.0.0')
def cli():
    """Repo Structure Analyzer and Cleanup Tool
    
    A suggest-first tool to organize AI-generated Python project files.
    """
    pass


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True), default='.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def analyze(repo_path, verbose):
    """Analyze repository structure and collect metadata.
    
    REPO_PATH: Path to the repository to analyze (default: current directory)
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        click.echo(f"Analyzing repository: {repo_path}")
        click.echo("-" * 60)
        
        analyzer = RepositoryAnalyzer(repo_path)
        files = analyzer.analyze()
        
        click.echo(f"\nFound {len(files)} files")
        click.echo()
        
        # Show summary
        summary = analyzer.get_summary()
        click.echo("Summary:")
        click.echo(f"  Total files: {summary['total_files']}")
        click.echo(f"  Python files: {summary['python_files']}")
        click.echo(f"  Test files: {summary['test_files']}")
        click.echo(f"  Executables: {summary['executables']}")
        click.echo()
        
        click.echo("File types:")
        for ext, count in sorted(summary['extensions'].items(), key=lambda x: -x[1]):
            click.echo(f"  {ext}: {count}")
        
        click.echo()
        click.echo("[+] Analysis complete")
        click.echo("Run 'repo-tool propose' to see suggested changes")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            raise
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True), default='.')
@click.option('--format', '-f', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--output', '-o', type=click.Path(), help='Write output to file')
def propose(repo_path, format, verbose, output):
    """Generate structural improvement proposals.
    
    REPO_PATH: Path to the repository to analyze (default: current directory)
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        click.echo(f"Analyzing repository: {repo_path}")
        
        # Step 1: Analyze
        analyzer = RepositoryAnalyzer(repo_path)
        files = analyzer.analyze()
        click.echo(f"Found {len(files)} files")
        
        # Step 2: Generate proposals
        click.echo("Generating proposals...")
        reasoner = StructureReasoner(Path(repo_path))
        generator = reasoner.generate_proposals(files)
        
        # Show repository type detection
        repo_type = reasoner.repo_type.value if reasoner.repo_type else "unknown"
        click.echo(f"Repository type: {repo_type}")
        
        if reasoner.repo_type and reasoner.repo_type.value == "non_python":
            click.echo("[!] Non-Python repository: Only duplicate detection active")
        elif reasoner.repo_type and reasoner.repo_type.value == "mixed":
            click.echo("[i] Mixed repository: MOVE proposals limited to Python files")
        
        # Step 3: Output
        if format == 'json':
            result = generator.to_json()
        else:
            result = generator.to_text()
        
        if output:
            with open(output, 'w') as f:
                f.write(result)
            click.echo(f"\n[+] Proposals written to {output}")
        else:
            click.echo("\n" + result)
        
        if format == 'text' and not output:
            click.echo("\nNext steps:")
            if reasoner.repo_type and reasoner.repo_type.value == "python_dominant":
                click.echo("  1. Review the proposals above")
                click.echo("  2. Run 'repo-tool apply' to execute changes (coming soon)")
                click.echo("  3. Use 'repo-tool rollback' to undo if needed (coming soon)")
            else:
                click.echo("  1. Review flagged issues (duplicates, etc.)")
                click.echo("  2. This tool is optimized for Python repositories")
                click.echo("  3. MOVE proposals disabled for safety on non-Python repos")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            raise
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True), default='.')
def apply(repo_path):
    """Apply approved structural changes (COMING SOON).
    
    REPO_PATH: Path to the repository (default: current directory)
    """
    click.echo("[!] Apply functionality coming soon!")
    click.echo()
    click.echo("This will:")
    click.echo("  1. Load proposals from previous 'propose' run")
    click.echo("  2. Ask for confirmation on each change")
    click.echo("  3. Create a rollback snapshot")
    click.echo("  4. Execute approved changes")
    click.echo()
    click.echo("For now, review proposals with 'repo-tool propose'")


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True), default='.')
def rollback(repo_path):
    """Rollback recent changes (COMING SOON).
    
    REPO_PATH: Path to the repository (default: current directory)
    """
    click.echo("[!] Rollback functionality coming soon!")
    click.echo()
    click.echo("This will:")
    click.echo("  1. Find the most recent snapshot")
    click.echo("  2. Show what will be reverted")
    click.echo("  3. Restore files to previous state")
    click.echo()
    click.echo("For now, use Git to manage changes")


if __name__ == '__main__':
    cli()
