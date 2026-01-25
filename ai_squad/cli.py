"""
AI-Squad CLI

Main command-line interface for AI-Squad.
"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box
from pathlib import Path
import sys

from ai_squad.__version__ import __version__
from ai_squad.core.init_project import initialize_project
from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.doctor import run_doctor_checks
from ai_squad.core.collaboration import run_collaboration
import yaml
import os

console = Console()


def print_banner():
    """Print enhanced AI-Squad banner with agents"""
    # Main ASCII logo
    banner = Text()
    banner.append(r"""
   ___   ____      _____                      __
  / _ | /  _/____ / __/ /_ ___  ___  ___  ___/ /
 / __ |_/ /_/___/_\ \/ / // / / _ \/ _ \/ _  / 
/_/ |_/___/     /___/_/\_, /_/\_,_/\_,_/\_,_/  
                      /___/                     
""", style="cyan bold")
    console.print(banner)
    
    # Tagline and version in panel
    console.print(
        Panel(
            "[bold cyan]Five expert AI agents orchestrated by a Captain[/bold cyan]\n"
            "[dim italic]Squad Assembled • Mission Ready • Awaiting Orders[/dim italic]\n\n"
            "[bold]Product Manager[/bold] • [bold]Architect[/bold] • "
            "[bold]Engineer[/bold] • [bold]UX Designer[/bold] • "
            "[bold]Reviewer[/bold]\n\n"
            f"[dim]Version {__version__}[/dim]",
            style="cyan",
            border_style="bright_cyan"
        )
    )
    console.print()


def _interactive_setup():
    """Interactive setup for GitHub OAuth authentication"""
    import subprocess
    
    # Check OAuth authentication
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        if result.returncode == 0:
            console.print("[green]✓ GitHub CLI is authenticated via OAuth[/green]")
            console.print("[dim]  AI-Squad is ready to use full AI capabilities[/dim]")
            return
        else:
            # OAuth not configured
            console.print("[yellow]⚠ GitHub authentication required[/yellow]")
            console.print("\n[bold]Authenticate with GitHub CLI:[/bold]")
            console.print("  [cyan]gh auth login[/cyan]")
            console.print("\n[dim]This uses OAuth (secure, no manual tokens)[/dim]")
            console.print("\n[bold cyan]→ Run 'gh auth login' now to get started[/bold cyan]")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # gh CLI not installed
        console.print("[yellow]⚠ GitHub CLI (gh) not installed[/yellow]")
        console.print("\n[bold]Step 1: Install GitHub CLI[/bold]")
        console.print("  Windows: [cyan]winget install GitHub.cli[/cyan]")
        console.print("  Mac: [cyan]brew install gh[/cyan]")
        console.print("  Linux: [cyan]https://github.com/cli/cli#installation[/cyan]")
        console.print("\n[bold]Step 2: Authenticate[/bold]")
        console.print("  [cyan]gh auth login[/cyan]")
    
    # Check repo configuration
    config_file = Path("squad.yaml")
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        repo = config.get("project", {}).get("github_repo")
        owner = config.get("project", {}).get("github_owner")
        
        if repo and owner:
            console.print(f"\n[green]✓ GitHub repo configured: {owner}/{repo}[/green]")
        else:
            console.print("\n[yellow]⚠ GitHub repo not detected[/yellow]")
            console.print("[dim]  You can manually update 'github_repo' and 'github_owner' in squad.yaml[/dim]")
            console.print("[dim]  Or ensure you're in a git repository with a GitHub remote[/dim]")
    
    console.print("\n[dim]Run [cyan]squad doctor[/cyan] to verify your setup[/dim]")


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def main(ctx, version):
    """
    AI-Squad - Your AI Development Squad
    
    Five expert AI agents to accelerate your development:
    
    • Product Manager - Creates PRDs and user stories
    
    • Architect - Designs solutions and writes ADRs
    
    • Engineer - Implements features with tests
    
    • UX Designer - Creates wireframes and flows
    
    • Reviewer - Reviews code and checks quality
    """
    if version:
        console.print(f"AI-Squad version {__version__}")
        sys.exit(0)
    
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("[yellow]Run 'squad --help' for usage information[/yellow]\n")


@main.command()
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--skip-setup", is_flag=True, help="Skip interactive token/repo setup")
def init(force, skip_setup):
    """Initialize AI-Squad in your project"""
    print_banner()
    
    console.print("[bold cyan]Initializing AI-Squad...[/bold cyan]\n")
    
    try:
        result = initialize_project(force=force)
        
        if result["success"]:
            console.print("[bold green]OK AI-Squad initialized successfully![/bold green]\n")
            
            console.print("[bold]Created:[/bold]")
            for item in result["created"]:
                console.print(f"  OK {item}")
            
            # Interactive setup for token and repo
            if not skip_setup:
                console.print("\n[bold cyan]Let's configure your GitHub setup...[/bold cyan]\n")
                _interactive_setup()
            
            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Run a command: [cyan]squad pm 123[/cyan]")
            console.print("  2. Or validate setup: [cyan]squad doctor[/cyan]")
            console.print("  3. View dashboard: [cyan]squad dashboard[/cyan]")
        else:
            console.print(f"[bold red]FAIL Initialization failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("issue_number", type=int)
def pm(issue_number):
    """Run Product Manager agent (creates PRD)"""
    console.print(f"[bold cyan]Running Product Manager for issue #{issue_number}...[/bold cyan]\n")
    
    try:
        executor = AgentExecutor()
        result = executor.execute("pm", issue_number)
        
        if result["success"]:
            console.print(f"[bold green]OK PRD created: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]FAIL: {result['error']}[/bold red]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("issue_number", type=int)
def architect(issue_number):
    """Run Architect agent (creates ADR/Spec)"""
    console.print(f"[bold cyan]Running Architect for issue #{issue_number}...[/bold cyan]\n")
    
    try:
        executor = AgentExecutor()
        result = executor.execute("architect", issue_number)
        
        if result["success"]:
            console.print(f"[bold green]OK ADR created: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]FAIL: {result['error']}[/bold red]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("issue_number", type=int)
def engineer(issue_number):
    """Run Engineer agent (implements feature)"""
    console.print(f"[bold cyan]Running Engineer for issue #{issue_number}...[/bold cyan]\n")
    
    try:
        executor = AgentExecutor()
        result = executor.execute("engineer", issue_number)
        
        if result["success"]:
            console.print("[bold green]OK Implementation complete[/bold green]")
            for file in result.get("files", []):
                console.print(f"  - {file}")
        else:
            console.print(f"[bold red]FAIL: {result['error']}[/bold red]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("issue_number", type=int)
def ux(issue_number):
    """Run UX Designer agent (creates wireframes)"""
    console.print(f"[bold cyan]Running UX Designer for issue #{issue_number}...[/bold cyan]\n")
    
    try:
        executor = AgentExecutor()
        result = executor.execute("ux", issue_number)
        
        if result["success"]:
            console.print(f"[bold green]OK UX design created: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]FAIL: {result['error']}[/bold red]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("pr_number", type=int)
def review(pr_number):
    """Run Reviewer agent (reviews PR)"""
    console.print(f"[bold cyan]Running Reviewer for PR #{pr_number}...[/bold cyan]\n")
    
    try:
        executor = AgentExecutor()
        result = executor.execute("reviewer", pr_number)
        
        if result["success"]:
            console.print(f"[bold green]OK Review completed: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]FAIL: {result['error']}[/bold red]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("issue_number", type=int)
@click.argument("agents", nargs=-1, required=True)
def collab(issue_number, agents):
    """Multi-agent collaboration
    
    Example: squad collab 123 pm architect
    """
    console.print(
        f"[bold cyan]Running collaboration for issue #{issue_number}...[/bold cyan]\n"
        f"[cyan]Participants: {', '.join(agents)}[/cyan]\n"
    )
    
    try:
        result = run_collaboration(issue_number, list(agents))
        
        if result["success"]:
            console.print("[bold green]OK Collaboration complete![/bold green]")
            for file in result.get("files", []):
                console.print(f"  - {file}")
        else:
            console.print(f"[bold red]FAIL: {result['error']}[/bold red]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("agent_type", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer"]))
def chat(agent_type):
    """Interactive chat with an agent
    
    Example: squad chat engineer
    """
    console.print(f"[bold cyan]Starting chat with {agent_type}...[/bold cyan]")
    console.print("[yellow]Type 'exit' or 'quit' to end conversation[/yellow]\n")
    
    console.print("[yellow]Interactive chat coming soon![/yellow]")


@main.command()
def doctor():
    """Validate AI-Squad setup"""
    print_banner()
    
    console.print("[bold cyan]Running diagnostic checks...[/bold cyan]\n")
    
    try:
        result = run_doctor_checks()
        
        console.print("[bold]Check Results:[/bold]")
        for check in result["checks"]:
            check_status = "OK" if check["passed"] else "FAIL"
            console.print(f"  {check_status} {check['name']}: {check['message']}")
        
        console.print()
        
        if result["all_passed"]:
            console.print("[bold green]OK All checks passed! AI-Squad is ready to use.[/bold green]")
        else:
            console.print("[bold yellow]WARN Some checks failed. See messages above.[/bold yellow]")
            sys.exit(1)
            
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--interval", default=30, type=int, help="Polling interval in seconds (default: 30)")
@click.option("--repo", help="GitHub repo (owner/repo) - overrides squad.yaml")
def watch(interval, repo):
    """
    Watch GitHub for label changes and auto-trigger agents
    
    Monitors GitHub issues and automatically triggers agents when
    orchestration labels are detected:
    
    • orch:pm-done → Triggers Architect
    
    • orch:architect-done → Triggers Engineer
    
    • orch:engineer-done → Triggers Reviewer
    
    Example:
    
        squad watch
        
        squad watch --interval 60 --repo jnPiyush/MyProject
    """
    print_banner()
    
    from ai_squad.core.config import Config
    from ai_squad.core.watch import WatchDaemon, WatchConfig
    
    # Validate interval
    interval = WatchConfig.validate_interval(interval)
    
    # Load config
    try:
        config = Config.load()
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error loading config: {e}[/bold red]")
        console.print("[yellow]TIP Run 'squad init' first[/yellow]")
        sys.exit(1)
    
    # Check GitHub OAuth authentication
    import subprocess
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        if result.returncode != 0:
            console.print("[bold red]FAIL GitHub authentication required[/bold red]")
            console.print("[yellow]TIP Run: gh auth login[/yellow]")
            sys.exit(1)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("[bold red]FAIL GitHub CLI (gh) not found[/bold red]")
        console.print("[yellow]TIP Install: winget install GitHub.cli[/yellow]")
        sys.exit(1)
    
    # Check repo
    if not repo and not config.github_repo:
        console.print("[bold red]FAIL GitHub repo not configured[/bold red]")
        console.print("[yellow]TIP Use --repo option or configure in squad.yaml[/yellow]")
        sys.exit(1)
    
    console.print("[bold cyan]Starting AI-Squad Watch Mode...[/bold cyan]\n")
    
    try:
        daemon = WatchDaemon(config, interval=interval, repo=repo)
        daemon.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch mode stopped[/yellow]")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"\n[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
def update():
    """Update AI-Squad to latest version"""
    console.print("[bold cyan]Updating AI-Squad...[/bold cyan]\n")
    
    import subprocess
    try:
        subprocess.run(
            ["pip", "install", "--upgrade", "ai-squad"],
            check=True
        )
        console.print("[bold green]OK AI-Squad updated successfully![/bold green]")
    except subprocess.CalledProcessError:
        console.print("[bold red]FAIL Update failed. Try: pip install --upgrade ai-squad[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("issue_number", type=int)
def clarify(issue_number):
    """
    View and respond to clarification requests for an issue
    
    Example:
        squad clarify 123
    """
    print_banner()
    
    from ai_squad.core.config import Config
    from ai_squad.core.agent_comm import AgentCommunicator
    
    try:
        Config.load()
        communicator = AgentCommunicator()
        
        # Get conversation for issue
        messages = communicator.get_conversation(issue_number)
        
        if not messages:
            console.print(f"[yellow]No clarification requests for issue #{issue_number}[/yellow]")
            return
        
        console.print(f"[bold cyan]Clarifications for Issue #{issue_number}[/bold cyan]\n")
        
        for msg in messages:
            if msg.message_type.value == "question":
                console.print(Panel(
                    f"[bold]From:[/bold] {msg.from_agent.title()} Agent\n"
                    f"[bold]To:[/bold] {msg.to_agent.title()} Agent\n\n"
                    f"{msg.content}\n\n"
                    f"[dim]ID: {msg.id}[/dim]",
                    title=f"Question ({msg.timestamp.strftime('%H:%M:%S')})",
                    border_style="yellow"
                ))
            elif msg.message_type.value == "response":
                console.print(Panel(
                    f"[bold]From:[/bold] {msg.from_agent.title()} Agent\n\n"
                    f"{msg.content}",
                    title=f"Response ({msg.timestamp.strftime('%H:%M:%S')})",
                    border_style="green"
                ))
        
        console.print("\n[dim]TIP To respond, use GitHub Copilot Chat in VS Code[/dim]")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


# ============================================================
# GASTOWN-INSPIRED ORCHESTRATION COMMANDS
# ============================================================

@main.command()
@click.option("--prompt", "-p", help="Inline mission brief")
@click.option("--file", "-f", type=click.Path(exists=True), help="Mission brief file path")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mission briefing")
@click.option("--plan-only", is_flag=True, help="Only create mission brief, don't deploy to Captain")
def auto(prompt, file, interactive, plan_only):
    """
    SQUAD MISSION MODE - Deploy autonomous development missions
    
    Provide your requirements as a "Squad Mission" and AI-Squad:
    1. PM analyzes mission brief (validates as epic or feature)
    2. Creates Mission Brief in GitHub issues
    3. Breaks down into Mission Objectives
    4. DEPLOYS TO CAPTAIN for orchestration
    5. Captain coordinates using Battle Plans and Convoys
    6. Agents execute via handoffs and delegations
    7. Tracks progress and completes the mission
    
    By default, FULL DEPLOYMENT. Use --plan-only to create brief only.
    
    Examples:
        squad auto -p "Create a REST API for user management"
        squad auto -f mission-brief.txt
        squad auto -i
        squad auto -p "Add authentication" --plan-only  # Create brief only
    """
    print_banner()
    
    # Validate input
    input_count = sum([bool(prompt), bool(file), interactive])
    if input_count == 0:
        console.print("[bold red]Error: Must provide mission brief via --prompt, --file, or --interactive[/bold red]")
        console.print("\n[yellow]Examples:[/yellow]")
        console.print("  squad auto -p \"Create user management API\"")
        console.print("  squad auto -f mission-brief.txt")
        console.print("  squad auto -i")
        sys.exit(1)
    
    if input_count > 1:
        console.print("[bold red]Error: Use only ONE input method (--prompt, --file, or --interactive)[/bold red]")
        sys.exit(1)
    
    # Get mission brief
    requirements = None
    if prompt:
        requirements = prompt
        console.print(f"[cyan]📋 Mission Brief:[/cyan] {prompt}\n")
    elif file:
        with open(file, 'r', encoding='utf-8') as f:
            requirements = f.read()
        console.print(f"[cyan]📋 Mission Brief from:[/cyan] {file}\n")
    elif interactive:
        console.print("[bold cyan]📋 Interactive Mission Briefing[/bold cyan]")
        console.print("[dim]Enter your mission requirements (press Ctrl+D or Ctrl+Z when done):[/dim]\n")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            requirements = "\n".join(lines)
        console.print()
    
    if not requirements or not requirements.strip():
        console.print("[bold red]Error: Mission brief cannot be empty[/bold red]")
        sys.exit(1)
    
    console.print("[bold cyan]🎖️ SQUAD MISSION MODE ACTIVATED[/bold cyan]\n")
    console.print("[dim]📋 Step 1: PM analyzing mission brief...[/dim]")
    
    try:
        # Import the autonomous orchestration module
        from ai_squad.core.autonomous import run_autonomous_workflow
        
        result = run_autonomous_workflow(
            requirements=requirements,
            plan_only=plan_only
        )
        
        if result["success"]:
            console.print("\n[bold green]✓ Autonomous workflow completed![/bold green]\n")
            
            # Show created mission
            console.print(f"\n[bold green]✓ Mission Deployed Successfully![/bold green]\n")
            console.print(f"[bold]Mission Type:[/bold] {result.get('mission_type', 'feature').upper()}")
            if "mission_brief" in result:
                console.print(f"[bold]Mission Brief:[/bold] #{result['mission_brief']}")
            if "objectives" in result:
                obj_numbers = [f"#{obj['number']}" for obj in result['objectives']]
                console.print(f"[bold]Mission Objectives:[/bold] {', '.join(obj_numbers)}")
            
            # Show Captain deployment status
            if not plan_only:
                console.print(f"\n[bold]🎖️ Captain Deployment:[/bold]")
                deployment = result.get("captain_deployment", {})
                if deployment.get("success"):
                    console.print(f"  ✓ Captain coordinating mission #{deployment.get('issue_number')}")
                    console.print(f"  • Using Battle Plans for orchestration")
                    console.print(f"  • Agents will execute via handoffs")
                    console.print(f"  • Progress tracked in work items")
                    
                    console.print("\n[bold cyan]Captain's Summary:[/bold cyan]")
                    summary = deployment.get("captain_summary", "").strip()
                    if summary:
                        console.print(Panel(summary, expand=False, border_style="cyan"))
                else:
                    console.print(f"  ✗ Captain deployment failed: {deployment.get('error')}")
                
                console.print("\n[green]✓ Mission successfully deployed to Captain![/green]")
                console.print("[dim]Captain will coordinate agents using Battle Plans and Convoys[/dim]")
            else:
                console.print("\n[yellow]📋 PLAN-ONLY: Mission brief created[/yellow]")
                console.print("[dim]Deploy to Captain with:[/dim]")
                console.print(f"[cyan]  squad captain {result.get('mission_brief')}[/cyan]")
        else:
            console.print(f"[bold red]✗ Squad Mission failed: {result.get('error')}[/bold red]")
            sys.exit(1)
    
    except ImportError:
        console.print("[bold red]✗ Autonomous mode not yet implemented[/bold red]")
        console.print("\n[yellow]Creating autonomous orchestration module...[/yellow]")
        console.print("[dim]This feature will:[/dim]")
        console.print("  1. Use PM agent to analyze requirements")
        console.print("  2. Create epic and story issues in GitHub")
        console.print("  3. Use Captain to orchestrate agents")
        console.print("  4. Track progress and update issues")
        console.print("\n[cyan]For now, you can:[/cyan]")
        console.print("  1. Manually create an issue in GitHub")
        console.print("  2. Run: squad captain <issue-number>")
        sys.exit(1)
    except (RuntimeError, OSError, ValueError) as e:
        console.print(f"[bold red]✗ Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("issue_number", type=int)
def captain(issue_number):
    """
    Run Captain (Coordinator) agent to orchestrate work on an issue
    
    The Captain analyzes the issue, breaks it down into work items,
    selects appropriate battle plans, and coordinates agents.
    
    Example:
        squad captain 123
    """
    console.print(f"[bold cyan]Captain coordinating issue #{issue_number}...[/bold cyan]\n")
    
    try:
        from ai_squad.core.preflight import run_preflight_checks

        preflight = run_preflight_checks(issue_number=issue_number)
        if not preflight.get("all_passed"):
            console.print("[bold red]Preflight checks failed. Fix issues before running Captain.[/bold red]\n")

            table = Table(title="Preflight Checks", box=box.SIMPLE)
            table.add_column("Check", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Message")

            for check in preflight.get("checks", []):
                status_icon = "OK" if check.get("passed") else "FAIL"
                table.add_row(check.get("name", ""), status_icon, check.get("message", ""))

            console.print(table)
            sys.exit(1)

        executor = AgentExecutor()
        result = executor.execute('captain', issue_number)
        
        if result.get('success'):
            console.print(result.get('output', 'Coordination complete'))
            console.print("\n[bold green]Captain coordination complete[/bold green]")
        else:
            console.print(f"[bold red]Error: {result.get('error')}[/bold red]")
            sys.exit(1)
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--status", "status_filter", type=click.Choice(["ready", "in-progress", "blocked", "done"]),
              help="Filter by status")
@click.option("--agent", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer"]),
              help="Filter by assigned agent")
def work(status_filter, agent):
    """
    List work items (persistent work state)
    
    Shows all tracked work items with their status and assignments.
    
    Examples:
        squad work
        squad work --status ready
        squad work --agent engineer
    """
    try:
        from ai_squad.core.workstate import WorkStateManager, WorkStatus
        
        manager = WorkStateManager()
        
        # Map CLI status to enum
        status_filter = None
        if status_filter:
            status_map = {
                "ready": WorkStatus.READY,
                "in-progress": WorkStatus.IN_PROGRESS,
                "blocked": WorkStatus.BLOCKED,
                "done": WorkStatus.DONE,
            }
            status_filter = status_map.get(status_filter)
        
        items = manager.list_work_items(status=status_filter, agent=agent)
        
        if not items:
            console.print("[yellow]No work items found[/yellow]")
            return
        
        # Create table
        table = Table(title="Work Items")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Title")
        table.add_column("Agent", style="green")
        table.add_column("Issue")
        
        for item in items:
            status_label = {
                "backlog": "BACKLOG",
                "ready": "READY",
                "in_progress": "IN_PROGRESS",
                "hooked": "HOOKED",
                "blocked": "BLOCKED",
                "in_review": "IN_REVIEW",
                "done": "DONE",
                "failed": "FAILED",
            }.get(item.status.value, "UNKNOWN")
            
            table.add_row(
                item.id,
                f"{status_label} {item.status.value}",
                item.title[:40] + "..." if len(item.title) > 40 else item.title,
                item.agent_assignee or "-",
                str(item.issue_number) if item.issue_number else "-"
            )
        
        console.print(table)
        
        # Show stats
        stats = manager.get_stats()
        console.print(f"\n[dim]Total: {stats['total']} | "
                     f"In Progress: {stats['in_progress']} | "
                     f"Blocked: {stats['blocked']} | "
                     f"Completed: {stats['completed']}[/dim]")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--label", help="Filter battle plans by label")
def plans(label):
    """
    List available battle plans (workflow templates)
    
    Battle plans are reusable workflow templates that define
    multi-agent orchestration patterns.
    
    Examples:
        squad plans
        squad plans --label bugfix
    """
    try:
        from ai_squad.core.battle_plan import BattlePlanManager
        
        manager = BattlePlanManager()
        plan_list = manager.list_strategies(label=label)
        
        if not plan_list:
            console.print("[yellow]No battle plans found[/yellow]")
            console.print("[dim]TIP Create custom plans in ai_squad/templates/strategies/[/dim]")
            return
        
        console.print("[bold cyan]Available Battle Plans[/bold cyan]\n")
        
        for plan in plan_list:
            console.print(Panel(
                f"[bold]Description:[/bold] {plan.description}\n"
                f"[bold]Phases:[/bold] {len(plan.phases)}\n"
                f"[bold]Labels:[/bold] {', '.join(plan.labels) if plan.labels else 'none'}\n\n"
                f"[bold]Variables:[/bold] {', '.join(plan.variables.keys()) if plan.variables else 'none'}\n\n"
                f"[dim]Phases: {' → '.join(p.name for p in plan.phases)}[/dim]",
                title=f"Plan: {plan.name}",
                border_style="cyan"
            ))
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("plan_name")
@click.argument("issue_number", type=int)
@click.option("--var", "variables", multiple=True, help="Variable override (key=value)")
def run_plan(plan_name, issue_number, variables):
    """
    Execute a battle plan on an issue
    
    Runs the specified battle plan, creating work items and
    coordinating agents according to the workflow definition.
    
    Example:
        squad run-plan feature 123
        squad run-plan bugfix 456
    """
    console.print(f"[bold cyan]Running battle plan '{plan_name}' for issue #{issue_number}...[/bold cyan]\n")
    
    try:
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.battle_plan import BattlePlanManager, BattlePlanExecutor
        
        work_manager = WorkStateManager()
        plan_manager = BattlePlanManager()
        executor = BattlePlanExecutor(plan_manager, work_manager)
        
        variables = _parse_variables(variables)

        # Start execution
        execution = executor.start_execution(plan_name, issue_number, variables)
        
        if not execution:
            console.print(f"[bold red]FAIL Battle plan '{plan_name}' not found[/bold red]")
            console.print("[dim]TIP Run 'squad plans' to see available battle plans[/dim]")
            sys.exit(1)
        
        console.print(f"[green]OK Battle plan execution started: {execution.id}[/green]\n")
        
        # Show next steps
        next_steps = executor.get_next_steps(execution.id)
        if next_steps:
            console.print("[bold]Next phases:[/bold]")
            for step in next_steps:
                console.print(f"  • [{step.agent}] {step.name}: {step.description}")
        
        console.print("\n[dim]TIP Run 'squad work' to see created work items[/dim]")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


def _parse_variables(values):
    variables = {}
    for entry in values or []:
        if "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        variables[key.strip()] = value.strip()
    return variables


@main.command()
@click.option("--convoy-id", help="Convoy ID to show details")
@click.option("--issue", type=int, help="Filter convoys by issue number")
def convoys(convoy_id, issue):
    """
    List or show details of convoys (parallel work batches)
    
    Convoys allow multiple agents to work simultaneously on
    independent tasks.
    
    Examples:
        squad convoys
        squad convoys --convoy-id convoy-abc123
        squad convoys --issue 123
    """
    try:
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.convoy import ConvoyManager
        
        work_manager = WorkStateManager()
        convoy_manager = ConvoyManager(work_manager)
        
        if convoy_id:
            # Show specific convoy
            summary = convoy_manager.get_convoy_summary(convoy_id)
            if summary:
                console.print(summary)
            else:
                console.print(f"[yellow]Convoy '{convoy_id}' not found[/yellow]")
            return
        
        # List convoys
        convoy_list = convoy_manager.list_convoys(issue_number=issue)
        
        if not convoy_list:
            console.print("[yellow]No convoys found[/yellow]")
            return
        
        console.print("[bold cyan]Active Convoys[/bold cyan]\n")
        
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status", style="yellow")
        table.add_column("Members")
        table.add_column("Progress")
        
        for convoy in convoy_list:
            progress = convoy.get_progress()
            table.add_row(
                convoy.id,
                convoy.name,
                convoy.status.value,
                str(progress["total"]),
                f"{progress['progress_percent']}%"
            )
        
        console.print(table)
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("agent", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer", "system"]))
@click.option("--unread", is_flag=True, help="Show only unread messages")
def signal(agent, unread):
    """
    View agent signal messages (notifications and communications)
    
    Shows messages sent to/from the specified agent.
    
    Examples:
        squad signal engineer
        squad signal pm --unread
    """
    try:
        from ai_squad.core.signal import SignalManager
        
        manager = SignalManager()
        
        # Get inbox
        messages = manager.get_inbox(agent, unread_only=unread)
        
        console.print(f"[bold cyan]Signal Messages for {agent.upper()}[/bold cyan]\n")
        
        if not messages:
            console.print("[yellow]No messages[/yellow]")
            return
        
        for msg in messages:
            status_label = {
                "pending": "PENDING",
                "delivered": "DELIVERED",
                "read": "READ",
                "acknowledged": "ACK",
                "expired": "EXPIRED",
            }.get(msg.status.value, "MESSAGE")
            
            priority_color = {
                "urgent": "red",
                "high": "yellow",
                "normal": "white",
                "low": "dim",
            }.get(msg.priority.value, "white")
            
            console.print(Panel(
                f"[bold]From:[/bold] {msg.sender}\n"
                f"[bold]Priority:[/bold] [{priority_color}]{msg.priority.value}[/{priority_color}]\n\n"
                f"{msg.body[:200]}{'...' if len(msg.body) > 200 else ''}\n\n"
                f"[dim]{msg.created_at}[/dim]",
                title=f"{status_label} {msg.subject}",
                border_style="cyan" if msg.status.value in ("pending", "delivered") else "dim"
            ))
        
        # Show stats
        stats = manager.get_stats()
        signal_stats = stats["by_signal"].get(agent, {})
        console.print(f"\n[dim]Inbox: {signal_stats.get('inbox', 0)} | "
                     f"Unread: {signal_stats.get('unread', 0)} | "
                     f"Sent: {signal_stats.get('outbox', 0)}[/dim]")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("work_item_id")
@click.argument("from_agent", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer"]))
@click.argument("to_agent", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer"]))
@click.option("--reason", type=click.Choice(["workflow", "escalation", "specialization", "blocker"]),
              default="workflow", help="Reason for handoff")
@click.option("--summary", help="Summary of work done")
def handoff(work_item_id, from_agent, to_agent, reason, summary):
    """
    Initiate a handoff of work between agents
    
    Transfers a work item from one agent to another with
    context preservation.
    
    Example:
        squad handoff sq-abc12 pm architect --reason workflow --summary "PRD complete"
    """
    console.print(f"[bold cyan]Initiating handoff: {from_agent} → {to_agent}[/bold cyan]\n")
    
    try:
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.signal import SignalManager
        from ai_squad.core.handoff import HandoffManager, HandoffReason, HandoffContext
        
        work_manager = WorkStateManager()
        signal_manager = SignalManager()
        from ai_squad.core.delegation import DelegationManager
        delegation_manager = DelegationManager(workspace_root=Path.cwd(), signal_manager=signal_manager)
        handoff_manager = HandoffManager(work_manager, signal_manager, delegation_manager)
        
        # Map reason string to enum
        reason_map = {
            "workflow": HandoffReason.WORKFLOW,
            "escalation": HandoffReason.ESCALATION,
            "specialization": HandoffReason.SPECIALIZATION,
            "blocker": HandoffReason.BLOCKER,
        }
        
        # Create context
        context = None
        if summary:
            context = HandoffContext(
                summary=summary,
                current_state="Work transferred via CLI"
            )
        
        # Initiate handoff
        handoff_obj = handoff_manager.initiate_handoff(
            work_item_id=work_item_id,
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason_map[reason],
            context=context
        )
        
        if handoff_obj:
            status_value = getattr(handoff_obj.status, "value", str(handoff_obj.status))
            console.print(f"[green]OK Handoff initiated: {handoff_obj.id}[/green]")
            console.print(f"[dim]Status: {status_value}[/dim]")
            console.print(f"\n[dim]TIP {to_agent.upper()} agent will receive notification[/dim]")
        else:
            console.print("[bold red]FAIL Failed to initiate handoff[/bold red]")
            sys.exit(1)
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
def status():
    """
    Show overall AI-Squad orchestration status
    
    Displays work items, active convoys, pending handoffs,
    and unread messages across all agents.
    """
    print_banner()
    
    try:
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.convoy import ConvoyManager, ConvoyStatus
        from ai_squad.core.signal import SignalManager
        from ai_squad.core.handoff import HandoffManager
        
        work_manager = WorkStateManager()
        convoy_manager = ConvoyManager(work_manager)
        signal_manager = SignalManager()
        from ai_squad.core.delegation import DelegationManager
        delegation_manager = DelegationManager(workspace_root=Path.cwd(), signal_manager=signal_manager)
        handoff_manager = HandoffManager(work_manager, signal_manager, delegation_manager)
        
        console.print("[bold cyan]AI-Squad Orchestration Status[/bold cyan]\n")
        
        # Work Items Summary
        work_stats = work_manager.get_stats()
        console.print(Panel(
            f"[bold]Total:[/bold] {work_stats['total']}\n"
            f"[green]In Progress:[/green] {work_stats['in_progress']}\n"
            f"[red]Blocked:[/red] {work_stats['blocked']}\n"
            f"[cyan]Completed:[/cyan] {work_stats['completed']}",
            title="Work Items",
            border_style="cyan"
        ))
        
        # Active Convoys
        active_convoys = convoy_manager.list_convoys(status=ConvoyStatus.RUNNING)
        pending_convoys = convoy_manager.list_convoys(status=ConvoyStatus.PENDING)
        console.print(Panel(
            f"[bold]Running:[/bold] {len(active_convoys)}\n"
            f"[bold]Pending:[/bold] {len(pending_convoys)}",
            title="Convoys",
            border_style="yellow"
        ))
        
        # Pending Handoffs
        handoff_stats = handoff_manager.get_stats()
        console.print(Panel(
            f"[bold]Pending:[/bold] {handoff_stats['pending']}\n"
            f"[bold]Completed:[/bold] {handoff_stats['completed']}\n"
            f"[bold]Rejected:[/bold] {handoff_stats['rejected']}",
            title="Handoffs",
            border_style="green"
        ))
        
        # Signal Summary
        signal_stats = signal_manager.get_stats()
        total_unread = sum(
            sig.get("unread", 0) 
            for sig in signal_stats["by_signal"].values()
        )
        console.print(Panel(
            f"[bold]Total Messages:[/bold] {signal_stats['total_messages']}\n"
            f"[bold]Unread:[/bold] {total_unread}",
            title="Signals",
            border_style="magenta"
        ))
        
        # Quick Tips
        console.print("\n[dim]Quick commands:[/dim]")
        console.print("[dim]  • squad work            - View work items[/dim]")
        console.print("[dim]  • squad convoys         - View convoys[/dim]")
        console.print("[dim]  • squad signal <agent> - View agent signal[/dim]")
        console.print("[dim]  • squad captain <issue> - Coordinate issue[/dim]")
        console.print("[dim]  • squad health          - View routing health[/dim]")
        console.print("[dim]  • squad capabilities    - Manage capability packages[/dim]")
        console.print("[dim]  • squad scout           - View scout runs[/dim]")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
def health():
    """View routing health and circuit breaker status"""
    try:
        from ai_squad.core.router import HealthView, HealthConfig
        
        console.print("[bold cyan]Routing Health Status[/bold cyan]\n")
        
        health_view = HealthView()
        health_cfg = HealthConfig()
        summary = health_view.summarize(config=health_cfg)
        
        # Overall stats
        console.print(Panel(
            f"[bold]Total Events:[/bold] {summary['total']}\n"
            f"[green]Routed:[/green] {summary['routed']}\n"
            f"[red]Blocked:[/red] {summary['blocked']}\n"
            f"[yellow]Block Rate:[/yellow] {summary.get('block_rate', 0):.1%}\n"
            f"[bold]Status:[/bold] {summary.get('overall_status', 'unknown')}",
            title="Overall Health",
            border_style="cyan"
        ))
        
        # By destination
        if summary.get("by_destination"):
            table = Table(title="Destination Health")
            table.add_column("Destination", style="cyan")
            table.add_column("Total", style="white")
            table.add_column("Routed", style="green")
            table.add_column("Blocked", style="red")
            table.add_column("Block Rate", style="yellow")
            
            for dest, stats in summary["by_destination"].items():
                total = stats["total"]
                routed = stats["routed"]
                blocked = stats["blocked"]
                block_rate = (blocked / total * 100) if total else 0
                table.add_row(
                    dest,
                    str(total),
                    str(routed),
                    str(blocked),
                    f"{block_rate:.1f}%"
                )
            
            console.print(table)
        
        # By priority
        if summary.get("by_priority"):
            console.print("\n[bold]By Priority:[/bold]")
            for priority, stats in summary["by_priority"].items():
                console.print(f"  {priority}: {stats['routed']}/{stats['total']} routed")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.group()
def capabilities():
    """Manage capability packages"""


@capabilities.command("list")
def capabilities_list():
    """List installed capability packages"""
    try:
        from ai_squad.core.capability_registry import CapabilityRegistry
        
        registry = CapabilityRegistry()
        packages = registry.list()
        
        if not packages:
            console.print("[yellow]No capability packages installed[/yellow]")
            return
        
        table = Table(title="Installed Capabilities")
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="white")
        table.add_column("Scope", style="yellow")
        table.add_column("Tags", style="green")
        
        for pkg in packages:
            table.add_row(
                pkg.name,
                pkg.version,
                pkg.scope,
                ", ".join(pkg.capability_tags)
            )
        
        console.print(table)
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@capabilities.command("install")
@click.argument("package_path", type=click.Path(exists=True))
def capabilities_install(package_path):
    """Install a capability package from directory or tarball"""
    try:
        from ai_squad.core.capability_registry import CapabilityRegistry
        
        registry = CapabilityRegistry()
        pkg = registry.install(Path(package_path))
        
        console.print(f"[bold green]OK Installed {pkg.name} v{pkg.version}[/bold green]")
        console.print(f"   Scope: {pkg.scope}")
        console.print(f"   Tags: {', '.join(pkg.capability_tags)}")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@capabilities.command("key")
@click.option("--set", "set_key", help="Set signature key for capability verification")
@click.option("--show", "show_key", is_flag=True, help="Show whether a key is configured")
def capabilities_key(set_key, show_key):
    """Manage capability signature key"""
    try:
        key_path = Path.cwd() / ".squad" / "capabilities" / "signature.key"
        key_path.parent.mkdir(parents=True, exist_ok=True)

        if set_key:
            key_path.write_text(set_key.strip(), encoding="utf-8")
            console.print("[bold green]OK Signature key saved[/bold green]")
            return

        if show_key:
            if key_path.exists():
                console.print("[green]Signature key is configured[/green]")
            else:
                console.print("[yellow]No signature key configured[/yellow]")
            return

        console.print("[yellow]Provide --set or --show[/yellow]")

    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.group()
def delegation():
    """Manage delegation links"""


@delegation.command("list")
def delegation_list():
    """List all delegation links"""
    try:
        from ai_squad.core.delegation import DelegationManager
        
        manager = DelegationManager()
        links = manager.list()
        
        if not links:
            console.print("[yellow]No delegation links found[/yellow]")
            return
        
        table = Table(title="Delegation Links")
        table.add_column("ID", style="cyan")
        table.add_column("From", style="white")
        table.add_column("To", style="white")
        table.add_column("Work Item", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Created", style="dim")
        
        for link in links:
            table.add_row(
                link.id,
                link.from_agent,
                link.to_agent,
                link.work_item_id,
                link.status.value,
                link.created_at[:19]  # Trim timestamp
            )
        
        console.print(table)
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.group()
def graph():
    """Manage operational graph"""


@main.group()
def scout():
    """Manage scout worker runs"""


@scout.command("list")
def scout_list():
    """List scout worker runs"""
    try:
        from ai_squad.core.scout_worker import ScoutWorker

        worker = ScoutWorker()
        runs = worker.list_runs()

        if not runs:
            console.print("[yellow]No scout runs found[/yellow]")
            return

        table = Table(title="Scout Runs")
        table.add_column("Run ID", style="cyan")
        table.add_column("Tasks", style="white")
        table.add_column("Completed", style="green")

        for run_id in runs:
            run = worker.load_run(run_id)
            tasks = len(run.tasks) if run else 0
            completed = len([t for t in (run.tasks if run else []) if t.status == "completed"])
            table.add_row(run_id, str(tasks), str(completed))

        console.print(table)

    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@scout.command("show")
@click.argument("run_id")
def scout_show(run_id):
    """Show details for a scout run"""
    try:
        from ai_squad.core.scout_worker import ScoutWorker

        worker = ScoutWorker()
        run = worker.load_run(run_id)

        if not run:
            console.print("[yellow]Scout run not found[/yellow]")
            return

        console.print(Panel(f"Run: {run.run_id}\nCreated: {run.created_at}", title="Scout Run"))
        table = Table(title="Tasks")
        table.add_column("Task", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Error", style="red")

        for task in run.tasks:
            table.add_row(task.name, task.status, task.error or "")

        console.print(table)

    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@scout.command("run")
@click.option("--task", "tasks", multiple=True, help="Scout task to run (repeatable)")
def scout_run(tasks):
    """Run a scout worker task"""
    try:
        from ai_squad.core.scout_worker import ScoutWorker

        selected = list(tasks) or ["noop"]
        def _noop():
            return "ok"

        def _list_squad_files():
            return [p.name for p in (Path.cwd() / ".squad").glob("*")]

        def _check_routing_events():
            return (Path.cwd() / ".squad" / "events" / "routing.jsonl").exists()

        task_map = {
            "noop": _noop,
            "list_squad_files": _list_squad_files,
            "check_routing_events": _check_routing_events,
        }
        run_tasks = {name: task_map[name] for name in selected if name in task_map}
        if not run_tasks:
            console.print("[yellow]No valid tasks selected[/yellow]")
            return

        worker = ScoutWorker()
        run = worker.run(run_tasks, metadata={"tasks": selected})
        console.print(f"[bold green]OK Scout run completed[/bold green] {run.run_id}")

    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@graph.command("export")
@click.option("--format", "export_format", type=click.Choice(["mermaid"]), default="mermaid", help="Export format")
def graph_export(export_format):
    """Export operational graph"""
    try:
        from ai_squad.core.operational_graph import OperationalGraph
        
        op_graph = OperationalGraph()
        
        if export_format == "mermaid":
            diagram = op_graph.export_mermaid()
            console.print(diagram)
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@graph.command("impact")
@click.argument("node_id")
def graph_impact(node_id):
    """Analyze impact of changes to a node"""
    try:
        from ai_squad.core.operational_graph import OperationalGraph
        
        op_graph = OperationalGraph()
        impact = op_graph.impact_analysis(node_id)
        
        if "error" in impact:
            console.print(f"[bold red]FAIL {impact['error']}[/bold red]")
            return
        
        console.print(f"[bold cyan]Impact Analysis for {node_id}[/bold cyan]\n")
        console.print(f"[bold]Direct Dependents:[/bold] {len(impact['direct_dependents'])}")
        console.print(f"[bold]Total Affected:[/bold] {impact['total_affected']}")
        
        if impact['owners']:
            console.print("\n[bold]Owners:[/bold]")
            for owner in impact['owners']:
                console.print(f"  • {owner}")
        
        if impact['affected_nodes']:
            console.print("\n[bold]Affected Nodes:[/bold]")
            for node in impact['affected_nodes'][:10]:  # Limit to first 10
                console.print(f"  • {node}")
            if len(impact['affected_nodes']) > 10:
                console.print(f"  ... and {len(impact['affected_nodes']) - 10} more")
        
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5050, type=int, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def dashboard(host, port, debug):
    """
    Launch the AI-Squad web dashboard
    
    Provides a web UI for monitoring:
    - Routing health and circuit breakers
    - Delegation links and audit trails
    - Operational graph visualization
    - Work items and convoy status
    
    Example:
        squad dashboard
        squad dashboard --port 8080
        squad dashboard --host 0.0.0.0 --debug
    """
    print_banner()
    console.print("[bold cyan]Starting AI-Squad Dashboard...[/bold cyan]\n")
    
    try:
        from ai_squad.dashboard import run_dashboard
        
        console.print(f"[green]Dashboard will be available at: http://{host}:{port}[/green]\n")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        run_dashboard(host=host, port=port, debug=debug)
        
    except ImportError:
        console.print("[bold red]FAIL Flask is not installed[/bold red]")
        console.print("[yellow]Install with: pip install flask[/yellow]")
        sys.exit(1)
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.group()
def theater():
    """Manage theaters, sectors, and routing"""


@theater.command("list")
def theater_list():
    """List theaters and sectors"""
    from ai_squad.core.config import Config
    from ai_squad.core.theater import TheaterRegistry

    try:
        config = Config.load()
        registry = TheaterRegistry(config=config.data)
        theaters = registry.list_theaters()
        if not theaters:
            console.print("[yellow]No theaters configured[/yellow]")
            return
        for t in theaters:
            console.print(f"[bold cyan]{t.name}[/bold cyan]")
            for sector in t.sectors.values():
                console.print(f"  • {sector.name} -> {sector.repo_path}")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@theater.command("add-sector")
@click.argument("theater_name")
@click.argument("sector_name")
@click.argument("repo_path")
@click.option("--staging-path", default=None, help="Optional staging area path")
def theater_add_sector(theater_name, sector_name, repo_path, staging_path):
    """Add a sector to a theater"""
    from ai_squad.core.config import Config
    from ai_squad.core.theater import TheaterRegistry

    try:
        config = Config.load()
        registry = TheaterRegistry(config=config.data)
        sector = registry.add_sector(theater_name, sector_name, repo_path, staging_path)
        console.print(f"[bold green]OK Added sector {sector.name}[/bold green]")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@theater.command("route")
@click.argument("theater_name")
@click.argument("prefix")
@click.argument("sector_name")
def theater_route(theater_name, prefix, sector_name):
    """Set routing prefix to sector"""
    from ai_squad.core.config import Config
    from ai_squad.core.theater import TheaterRegistry

    try:
        config = Config.load()
        registry = TheaterRegistry(config=config.data)
        registry.set_route(theater_name, prefix, sector_name)
        console.print(f"[bold green]OK Routed {prefix} -> {sector_name}[/bold green]")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@theater.command("staging")
@click.argument("theater_name")
def theater_staging(theater_name):
    """Ensure staging areas exist"""
    from ai_squad.core.config import Config
    from ai_squad.core.theater import TheaterRegistry

    try:
        config = Config.load()
        registry = TheaterRegistry(config=config.data)
        paths = registry.ensure_staging_areas(theater_name)
        console.print(f"[bold green]OK Staging areas ready ({len(paths)})[/bold green]")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
def recon():
    """Generate reconnaissance summary"""
    from ai_squad.core.config import Config
    from ai_squad.core.recon import ReconManager

    try:
        config = Config.load()
        recon_manager = ReconManager(routing_config=config.get("routing", {}))
        summary = recon_manager.build_summary()
        path = recon_manager.save_summary(summary)
        console.print(f"[bold green]OK Recon summary saved to {path}[/bold green]")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
def patrol():
    """Run patrol to detect stale work"""
    from ai_squad.core.config import Config
    from ai_squad.core.patrol import PatrolManager

    try:
        config = Config.load()
        patrol_cfg = config.get("patrol", {}) or {}
        manager = PatrolManager(
            stale_minutes=patrol_cfg.get("stale_minutes", 120),
            statuses=patrol_cfg.get("statuses", None),
        )
        events = manager.run()
        console.print(f"[bold green]OK Patrol complete ({len(events)} stale items)[/bold green]")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@main.group()
def report():
    """View after-operation reports"""


@report.command("list")
def report_list():
    """List after-operation reports"""
    from ai_squad.core.reporting import ReportManager

    try:
        mgr = ReportManager()
        if not mgr.reports_dir.exists():
            console.print("[yellow]No reports found[/yellow]")
            return
        for path in sorted(mgr.reports_dir.glob("after-operation-*.md")):
            console.print(f"• {path.name}")
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


@report.command("show")
@click.argument("report_name")
def report_show(report_name):
    """Show an after-operation report"""
    from ai_squad.core.reporting import ReportManager

    try:
        mgr = ReportManager()
        path = mgr.reports_dir / report_name
        if not path.exists():
            console.print(f"[bold red]FAIL Report not found: {report_name}[/bold red]")
            return
        console.print(path.read_text(encoding="utf-8"))
    except (RuntimeError, OSError, ValueError, click.ClickException) as e:
        console.print(f"[bold red]FAIL Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main.main()



