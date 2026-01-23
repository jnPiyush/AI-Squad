"""
AI-Squad CLI

Main command-line interface for AI-Squad.
"""
import asyncio
import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from pathlib import Path
import sys

from ai_squad.__version__ import __version__
from ai_squad.core.init_project import initialize_project
from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.doctor import run_doctor_checks
from ai_squad.core.collaboration import run_collaboration

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
            "[bold cyan]Your AI Development Squad, One Command Away[/bold cyan]\n\n"
            "[dim]Five Expert AI Agents:[/dim]\n"
            "🎨 [bold]Product Manager[/bold] • 🏗️  [bold]Architect[/bold] • "
            "💻 [bold]Engineer[/bold] • 🎭 [bold]UX Designer[/bold] • "
            "✅ [bold]Reviewer[/bold]\n\n"
            f"[dim]Version {__version__}[/dim]",
            style="cyan",
            border_style="bright_cyan"
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


# ============================================================
# GASTOWN-INSPIRED ORCHESTRATION COMMANDS
# ============================================================

@main.command()
@click.argument("issue_number", type=int)
def captain(issue_number):
    """
    Run Captain (Coordinator) agent to orchestrate work on an issue
    
    The Captain analyzes the issue, breaks it down into work items,
    selects appropriate formulas, and coordinates agents.
    
    Example:
        squad captain 123
    """
    console.print(f"[bold cyan]🎖️  Captain coordinating issue #{issue_number}...[/bold cyan]\n")
    
    try:
        from ai_squad.core.agent_executor import AgentExecutor
        
        executor = AgentExecutor()
        result = executor.execute('captain', issue_number)
        
        if result.get('success'):
            console.print(result.get('output', 'Coordination complete'))
            console.print("\n[bold green]✅ Captain coordination complete[/bold green]")
        else:
            console.print(f"[bold red]❌ Error: {result.get('error')}[/bold red]")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        logger.exception("Captain command failed")
        sys.exit(1)


@main.command()
@click.option("--status", type=click.Choice(["ready", "in-progress", "blocked", "done"]),
              help="Filter by status")
@click.option("--agent", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer"]),
              help="Filter by assigned agent")
def work(status, agent):
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
        if status:
            status_map = {
                "ready": WorkStatus.READY,
                "in-progress": WorkStatus.IN_PROGRESS,
                "blocked": WorkStatus.BLOCKED,
                "done": WorkStatus.DONE,
            }
            status_filter = status_map.get(status)
        
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
            status_emoji = {
                "backlog": "📋",
                "ready": "🟢",
                "in_progress": "🔄",
                "hooked": "🪝",
                "blocked": "🔴",
                "in_review": "👀",
                "done": "✅",
                "failed": "❌",
            }.get(item.status.value, "❓")
            
            table.add_row(
                item.id,
                f"{status_emoji} {item.status.value}",
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
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--label", help="Filter formulas by label")
def formulas(label):
    """
    List available workflow formulas
    
    Formulas are reusable workflow templates that define
    multi-agent orchestration patterns.
    
    Examples:
        squad formulas
        squad formulas --label bugfix
    """
    try:
        from ai_squad.core.formula import FormulaManager
        
        manager = FormulaManager()
        formula_list = manager.list_formulas(label=label)
        
        if not formula_list:
            console.print("[yellow]No formulas found[/yellow]")
            console.print("[dim]💡 Create custom formulas in .squad/formulas/[/dim]")
            return
        
        console.print("[bold cyan]📜 Available Formulas[/bold cyan]\n")
        
        for formula in formula_list:
            console.print(Panel(
                f"[bold]Description:[/bold] {formula.description}\n"
                f"[bold]Steps:[/bold] {len(formula.steps)}\n"
                f"[bold]Labels:[/bold] {', '.join(formula.labels) if formula.labels else 'none'}\n\n"
                f"[dim]Steps: {' → '.join(s.name for s in formula.steps)}[/dim]",
                title=f"📋 {formula.name}",
                border_style="cyan"
            ))
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("formula_name")
@click.argument("issue_number", type=int)
def run_formula(formula_name, issue_number):
    """
    Execute a workflow formula on an issue
    
    Runs the specified formula, creating work items and
    coordinating agents according to the workflow definition.
    
    Example:
        squad run-formula feature 123
        squad run-formula bugfix 456
    """
    console.print(f"[bold cyan]🚀 Running formula '{formula_name}' for issue #{issue_number}...[/bold cyan]\n")
    
    try:
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.formula import FormulaManager, FormulaExecutor
        
        work_manager = WorkStateManager()
        formula_manager = FormulaManager()
        executor = FormulaExecutor(formula_manager, work_manager)
        
        # Start execution
        execution = executor.start_execution(formula_name, issue_number)
        
        if not execution:
            console.print(f"[bold red]❌ Formula '{formula_name}' not found[/bold red]")
            console.print("[dim]💡 Run 'squad formulas' to see available formulas[/dim]")
            sys.exit(1)
        
        console.print(f"[green]✅ Formula execution started: {execution.id}[/green]\n")
        
        # Show next steps
        next_steps = executor.get_next_steps(execution.id)
        if next_steps:
            console.print("[bold]Next steps:[/bold]")
            for step in next_steps:
                console.print(f"  • [{step.agent}] {step.name}: {step.description}")
        
        console.print("\n[dim]💡 Run 'squad work' to see created work items[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


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
        
        console.print("[bold cyan]🚛 Active Convoys[/bold cyan]\n")
        
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
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("agent", type=click.Choice(["pm", "architect", "engineer", "ux", "reviewer", "system"]))
@click.option("--unread", is_flag=True, help="Show only unread messages")
def mailbox(agent, unread):
    """
    View agent mailbox (messages and notifications)
    
    Shows messages sent to/from the specified agent.
    
    Examples:
        squad mailbox engineer
        squad mailbox pm --unread
    """
    try:
        from ai_squad.core.mailbox import MailboxManager
        
        manager = MailboxManager()
        
        # Get inbox
        messages = manager.get_inbox(agent, unread_only=unread)
        
        console.print(f"[bold cyan]📬 Mailbox for {agent.upper()}[/bold cyan]\n")
        
        if not messages:
            console.print("[yellow]No messages[/yellow]")
            return
        
        for msg in messages:
            status_emoji = {
                "pending": "📩",
                "delivered": "📨",
                "read": "📖",
                "acknowledged": "✅",
                "expired": "⏰",
            }.get(msg.status.value, "📧")
            
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
                title=f"{status_emoji} {msg.subject}",
                border_style="cyan" if msg.status.value in ("pending", "delivered") else "dim"
            ))
        
        # Show stats
        stats = manager.get_stats()
        mailbox_stats = stats["by_mailbox"].get(agent, {})
        console.print(f"\n[dim]Inbox: {mailbox_stats.get('inbox', 0)} | "
                     f"Unread: {mailbox_stats.get('unread', 0)} | "
                     f"Sent: {mailbox_stats.get('outbox', 0)}[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
    console.print(f"[bold cyan]🤝 Initiating handoff: {from_agent} → {to_agent}[/bold cyan]\n")
    
    try:
        from ai_squad.core.workstate import WorkStateManager
        from ai_squad.core.mailbox import MailboxManager
        from ai_squad.core.handoff import HandoffManager, HandoffReason, HandoffContext
        
        work_manager = WorkStateManager()
        mailbox_manager = MailboxManager()
        handoff_manager = HandoffManager(work_manager, mailbox_manager)
        
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
            console.print(f"[green]✅ Handoff initiated: {handoff_obj.id}[/green]")
            console.print(f"[dim]Status: {handoff_obj.status.value}[/dim]")
            console.print(f"\n[dim]💡 {to_agent.upper()} agent will receive notification[/dim]")
        else:
            console.print("[bold red]❌ Failed to initiate handoff[/bold red]")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
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
        from ai_squad.core.workstate import WorkStateManager, WorkStatus
        from ai_squad.core.convoy import ConvoyManager, ConvoyStatus
        from ai_squad.core.mailbox import MailboxManager
        from ai_squad.core.handoff import HandoffManager, HandoffStatus
        
        work_manager = WorkStateManager()
        convoy_manager = ConvoyManager(work_manager)
        mailbox_manager = MailboxManager()
        handoff_manager = HandoffManager(work_manager, mailbox_manager)
        
        console.print("[bold cyan]📊 AI-Squad Orchestration Status[/bold cyan]\n")
        
        # Work Items Summary
        work_stats = work_manager.get_stats()
        console.print(Panel(
            f"[bold]Total:[/bold] {work_stats['total']}\n"
            f"[green]In Progress:[/green] {work_stats['in_progress']}\n"
            f"[red]Blocked:[/red] {work_stats['blocked']}\n"
            f"[cyan]Completed:[/cyan] {work_stats['completed']}",
            title="📋 Work Items",
            border_style="cyan"
        ))
        
        # Active Convoys
        active_convoys = convoy_manager.list_convoys(status=ConvoyStatus.RUNNING)
        pending_convoys = convoy_manager.list_convoys(status=ConvoyStatus.PENDING)
        console.print(Panel(
            f"[bold]Running:[/bold] {len(active_convoys)}\n"
            f"[bold]Pending:[/bold] {len(pending_convoys)}",
            title="🚛 Convoys",
            border_style="yellow"
        ))
        
        # Pending Handoffs
        handoff_stats = handoff_manager.get_stats()
        console.print(Panel(
            f"[bold]Pending:[/bold] {handoff_stats['pending']}\n"
            f"[bold]Completed:[/bold] {handoff_stats['completed']}\n"
            f"[bold]Rejected:[/bold] {handoff_stats['rejected']}",
            title="🤝 Handoffs",
            border_style="green"
        ))
        
        # Mailbox Summary
        mailbox_stats = mailbox_manager.get_stats()
        total_unread = sum(
            mb.get("unread", 0) 
            for mb in mailbox_stats["by_mailbox"].values()
        )
        console.print(Panel(
            f"[bold]Total Messages:[/bold] {mailbox_stats['total_messages']}\n"
            f"[bold]Unread:[/bold] {total_unread}",
            title="📬 Mailbox",
            border_style="magenta"
        ))
        
        # Quick Tips
        console.print("\n[dim]Quick commands:[/dim]")
        console.print("[dim]  • squad work            - View work items[/dim]")
        console.print("[dim]  • squad convoys         - View convoys[/dim]")
        console.print("[dim]  • squad mailbox <agent> - View agent mailbox[/dim]")
        console.print("[dim]  • squad captain <issue> - Coordinate issue[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

