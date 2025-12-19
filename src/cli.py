"""Command-line interface for the repo structure tool."""
import click
import logging
import json
from pathlib import Path
import sys

from .analyzer import RepositoryAnalyzer
from .reasoner import StructureReasoner
from .proposal import ActionType

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='2.1.0')
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
                click.echo("  2. Run 'repo-tool apply' to execute changes interactively (V2.1)")
                click.echo("  3. Check history with 'repo-tool rollback'")
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
@click.option('--dry-run/--execute', default=True, help='Dry-run mode (default) or real execution')
@click.option('--yes', '-y', is_flag=True, help='Auto-approve all proposals (dangerous!)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def apply(repo_path, dry_run, yes, verbose):
    """Apply structural changes interactively (V2.1).
    
    REPO_PATH: Path to the repository (default: current directory)
    
    Default behavior is DRY-RUN (simulate only, no filesystem changes).
    Use --execute to apply changes for real.
    
    Examples:
      repo-tool apply .                    # Dry-run with interactive approval
      repo-tool apply . --execute          # Real execution with interactive approval
      repo-tool apply . --execute --yes    # Auto-approve all (use with caution!)
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    from .executor import ProposalExecutor
    
    try:
        click.echo(f"Analyzing repository: {repo_path}")
        click.echo()
        
        # Step 1: Analyze and generate proposals
        analyzer = RepositoryAnalyzer(repo_path)
        files = analyzer.analyze()
        
        reasoner = StructureReasoner(Path(repo_path))
        generator = reasoner.generate_proposals(files)
        
        # Get only MOVE proposals
        move_proposals = generator.get_by_action(ActionType.MOVE)
        
        if not move_proposals:
            click.echo("[!] No MOVE proposals found. Nothing to apply.")
            click.echo()
            click.echo("Note: V2.1 only supports applying MOVE proposals.")
            click.echo("Run 'repo-tool propose' to see all proposals.")
            return
        
        # Check repo type safety
        repo_type = reasoner.repo_type.value if reasoner.repo_type else "unknown"
        if repo_type == "non_python" and not yes:
            click.echo(f"[!] Repository type: {repo_type}")
            click.echo("[!] MOVE proposals are disabled for non-Python repositories (safety).")
            click.echo()
            click.echo("Override with --yes flag if you're sure.")
            return
        
        # Step 2: Show summary
        mode_str = "[DRY-RUN]" if dry_run else "[EXECUTE]"
        click.echo(f"{mode_str} Found {len(move_proposals)} MOVE proposals")
        click.echo()
        
        if dry_run:
            click.echo("Running in DRY-RUN mode (no filesystem changes)")
            click.echo("Use --execute to apply changes for real")
        else:
            click.echo("[WARNING] EXECUTE mode - will modify filesystem!")
            if not yes:
                confirm = click.confirm("Continue?", default=False)
                if not confirm:
                    click.echo("Aborted.")
                    return
        
        click.echo()
        
        # Step 3: Initialize executor
        executor = ProposalExecutor(Path(repo_path), dry_run=dry_run)
        
        # Step 4: Interactive approval loop
        applied_count = 0
        skipped_count = 0
        
        for i, proposal in enumerate(move_proposals, 1):
            click.echo(f"--- Proposal {i}/{len(move_proposals)} ---")
            click.echo(f"Action: MOVE")
            click.echo(f"From:   {proposal.source_path}")
            click.echo(f"To:     {proposal.target_path}")
            click.echo(f"Reason: {proposal.reason}")
            click.echo(f"Risk:   {proposal.risk_level.value.upper()}")
            click.echo()
            
            # Auto-approve or ask
            if yes:
                approved = True
                click.echo("[Auto-approved]")
            else:
                while True:
                    response = click.prompt(
                        "Apply this change? [y]es / [n]o / [v]iew details / [q]uit",
                        type=str,
                        default='n'
                    ).lower()
                    
                    if response == 'v':
                        # Show details
                        click.echo()
                        click.echo("Details:")
                        for key, value in proposal.details.items():
                            click.echo(f"  {key}: {value}")
                        click.echo()
                        continue
                    elif response == 'q':
                        click.echo("Quitting...")
                        break
                    elif response in ['y', 'yes']:
                        approved = True
                        break
                    elif response in ['n', 'no']:
                        approved = False
                        break
                    else:
                        click.echo("Invalid response. Please enter y, n, v, or q.")
                
                if response == 'q':
                    break
            
            # Execute if approved
            if approved:
                result = executor.execute_proposal(proposal)
                if result.success:
                    click.echo(f"[+] {result.message}")
                    applied_count += 1
                else:
                    click.echo(f"[!] {result.message}")
            else:
                click.echo("[-] Skipped")
                skipped_count += 1
            
            click.echo()
        
        # Step 5: Summary and save history
        summary = executor.get_summary()
        
        click.echo("="* 60)
        click.echo("SUMMARY")
        click.echo("="* 60)
        click.echo(f"Total proposals:  {len(move_proposals)}")
        click.echo(f"Applied:          {summary['successful']}")
        click.echo(f"Failed:           {summary['failed']}")
        click.echo(f"Skipped:          {skipped_count}")
        click.echo()
        
        if not dry_run and summary['successful'] > 0:
            executor.save_history()
            click.echo(f"[+] Operation log saved to .repo-tool-history.json")
            click.echo()
            click.echo("Changes applied successfully!")
            click.echo("Tip: Use Git to review and commit the changes.")
        elif dry_run:
            click.echo("Dry-run complete. No filesystem changes made.")
            click.echo("Use --execute to apply changes for real.")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            raise
        sys.exit(1)


@cli.command()
@click.argument('repo_path', type=click.Path(exists=True), default='.')
def rollback(repo_path):
    """View execution history (V2.1).
    
    REPO_PATH: Path to the repository (default: current directory)
    
    Shows the history of applied changes from .repo-tool-history.json
    """
    log_file = Path(repo_path) / '.repo-tool-history.json'
    
    if not log_file.exists():
        click.echo("[!] No execution history found.")
        click.echo()
        click.echo("History is created when you apply changes with --execute mode.")
        return
    
    try:
        with open(log_file, 'r') as f:
            history = json.load(f)
        
        if not history:
            click.echo("[!] History file is empty.")
            return
        
        click.echo(f"Execution history: {log_file}")
        click.echo()
        
        for i, entry in enumerate(reversed(history[-20:]), 1):  # Show last 20
            click.echo(f"[{i}] {entry['timestamp']}")
            click.echo(f"    Action: {entry['action'].upper()}")
            click.echo(f"    Source: {entry['source']}")
            if entry.get('target'):
                click.echo(f"    Target: {entry['target']}")
            click.echo(f"    Status: {'SUCCESS' if entry['success'] else 'FAILED'}")
            click.echo(f"    Risk:   {entry['risk'].upper()}")
            click.echo()
        
        if len(history) > 20:
            click.echo(f"... showing last 20 of {len(history)} total entries")
        
    except Exception as e:
        click.echo(f"Error reading history: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
