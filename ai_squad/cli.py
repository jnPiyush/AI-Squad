"""
AI-Squad CLI

Main command-line interface for AI-Squad.
"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
import sys

from ai_squad.__version__ import __version__
from ai_squad.core.init_project import initialize_project
from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.doctor import run_doctor_checks
from ai_squad.core.collaboration import run_collaboration

console = Console()


def print_banner():
    """Print AI-Squad banner"""
    banner = Text()
    banner.append(r"""
   ___   ____      _____                      __
  / _ | /  _/____ / __/ /_ ___  ___  ___  ___/ /
 / __ |_/ /_/___/_\ \/ / // / / _ \/ _ \/ _  / 
/_/ |_/___/     /___/_/\_, /_/\_,_/\_,_/\_,_/  
                      /___/                     
""", style="cyan bold")
    console.print(banner)
    console.print(
        Panel(
            "[bold]Your AI Development Squad, One Command Away[/bold]\n"
            f"Version {__version__}",
            style="cyan",
        )
    )
    console.print()


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
def init(force):
    """Initialize AI-Squad in your project"""
    print_banner()
    
    console.print("[bold cyan]Initializing AI-Squad...[/bold cyan]\n")
    
    try:
        result = initialize_project(force=force)
        
        if result["success"]:
            console.print("[bold green]✅ AI-Squad initialized successfully![/bold green]\n")
            
            console.print("[bold]Created:[/bold]")
            for item in result["created"]:
                console.print(f"  ✅ {item}")
            
            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Configure GitHub token: [cyan]export GITHUB_TOKEN=ghp_xxx[/cyan]")
            console.print("  2. Run a command: [cyan]squad pm 123[/cyan]")
            console.print("  3. Or validate setup: [cyan]squad doctor[/cyan]")
        else:
            console.print(f"[bold red]❌ Initialization failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
            console.print(f"[bold green]✅ PRD created: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]❌ Failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
            console.print(f"[bold green]✅ ADR created: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]❌ Failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
            console.print(f"[bold green]✅ Implementation complete[/bold green]")
            for file in result.get("files", []):
                console.print(f"  📄 {file}")
        else:
            console.print(f"[bold red]❌ Failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
            console.print(f"[bold green]✅ UX design created: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]❌ Failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
            console.print(f"[bold green]✅ Review completed: {result['file_path']}[/bold green]")
        else:
            console.print(f"[bold red]❌ Failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
            console.print("[bold green]✅ Collaboration complete![/bold green]")
            for file in result.get("files", []):
                console.print(f"  📄 {file}")
        else:
            console.print(f"[bold red]❌ Failed: {result['error']}[/bold red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("agent_type", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer"]))
def chat(agent_type):
    """Interactive chat with an agent
    
    Example: squad chat engineer
    """
    console.print(f"[bold cyan]Starting chat with {agent_type}...[/bold cyan]")
    console.print("[yellow]Type 'exit' or 'quit' to end conversation[/yellow]\n")
    
    # TODO: Implement interactive chat
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
            status = "✅" if check["passed"] else "❌"
            console.print(f"  {status} {check['name']}: {check['message']}")
        
        console.print()
        
        if result["all_passed"]:
            console.print("[bold green]✅ All checks passed! AI-Squad is ready to use.[/bold green]")
        else:
            console.print("[bold yellow]⚠️  Some checks failed. See messages above.[/bold yellow]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
    except Exception as e:
        console.print(f"[bold red]❌ Error loading config: {e}[/bold red]")
        console.print("[yellow]💡 Run 'squad init' first[/yellow]")
        sys.exit(1)
    
    # Check GitHub token
    import os
    if not os.getenv("GITHUB_TOKEN"):
        console.print("[bold red]❌ GITHUB_TOKEN not set[/bold red]")
        console.print("[yellow]💡 Set it with: export GITHUB_TOKEN=ghp_xxx[/yellow]")
        sys.exit(1)
    
    # Check repo
    if not repo and not config.github_repo:
        console.print("[bold red]❌ GitHub repo not configured[/bold red]")
        console.print("[yellow]💡 Use --repo option or configure in squad.yaml[/yellow]")
        sys.exit(1)
    
    console.print("[bold cyan]Starting AI-Squad Watch Mode...[/bold cyan]\n")
    
    try:
        daemon = WatchDaemon(config, interval=interval, repo=repo)
        daemon.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch mode stopped[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
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
        console.print("[bold green]✅ AI-Squad updated successfully![/bold green]")
    except subprocess.CalledProcessError:
        console.print("[bold red]❌ Update failed. Try: pip install --upgrade ai-squad[/bold red]")
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
        config = Config.load()
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
                    title=f"❓ Question ({msg.timestamp.strftime('%H:%M:%S')})",
                    border_style="yellow"
                ))
            elif msg.message_type.value == "response":
                console.print(Panel(
                    f"[bold]From:[/bold] {msg.from_agent.title()} Agent\n\n"
                    f"{msg.content}",
                    title=f"💬 Response ({msg.timestamp.strftime('%H:%M:%S')})",
                    border_style="green"
                ))
        
        console.print("\n[dim]💡 To respond, use GitHub Copilot Chat in VS Code[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

