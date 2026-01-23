"""
Watch daemon for automatic agent orchestration

Monitors GitHub for label changes and triggers agents automatically.
"""
# ruff: noqa: BLE001
# pylint: disable=broad-except
import time
from typing import Dict, List, Set, Optional
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.console import Console

from ai_squad.core.config import Config
from ai_squad.tools.github import GitHubTool, GitHubCommandError
from ai_squad.core.agent_executor import AgentExecutor


class WatchDaemon:
    """Monitors GitHub and triggers agents automatically"""
    
    # Sequential flow: PM → Architect → Engineer → Reviewer
    AGENT_FLOW = {
        "orch:pm-done": "architect",
        "orch:architect-done": "engineer",
        "orch:engineer-done": "reviewer",
    }
    
    # Status-based triggers
    STATUS_TRIGGERS = {
        "status:ready": ["architect", "ux"],
        "status:in-review": ["reviewer"],
    }
    
    def __init__(self, config: Config, interval: int = 30, repo: Optional[str] = None):
        """
        Initialize watch daemon
        
        Args:
            config: AI-Squad configuration
            interval: Polling interval in seconds
            repo: GitHub repo (owner/repo) - overrides config
        """
        self.config = config
        self.interval = interval
        self.repo = repo or config.github_repo
        self.github = GitHubTool(config)
        self.executor = AgentExecutor(config)
        self.processed_events: Set[str] = set()  # Track processed triggers
        self.console = Console()
        self.stats = {
            "checks": 0,
            "events": 0,
            "successes": 0,
            "failures": 0,
        }
        
        # Initialize status manager
        from ai_squad.core.status import StatusManager
        self.status_manager = StatusManager(self.github)
        
    def run(self):
        """Main watch loop"""
        self.console.print(f"[bold cyan]🔍 Monitoring:[/bold cyan] {self.repo}")
        self.console.print(f"[bold cyan]⏱️  Interval:[/bold cyan] {self.interval}s")
        self.console.print("[bold cyan]🔄 Flow:[/bold cyan] PM → Architect → Engineer → Reviewer\n")
        self.console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")
        
        with Live(self._create_status_table(), refresh_per_second=4) as live:
            try:
                while True:
                    self.stats["checks"] += 1
                    
                    # Check for triggers
                    events = self._check_for_triggers()
                    
                    if events:
                        self.stats["events"] += len(events)
                        
                        for event in events:
                            success = self._handle_event(event, live)
                            if success:
                                self.stats["successes"] += 1
                            else:
                                self.stats["failures"] += 1
                    
                    # Update status display
                    live.update(self._create_status_table())
                    
                    time.sleep(self.interval)
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Stopping watch mode...[/yellow]")
                self._print_summary()
    
    def _check_for_triggers(self) -> List[Dict]:
        """Check for orchestration labels and status changes on issues"""
        events = []
        
        if not self.github.is_configured():
            # Skip if GitHub not configured
            return events
        
        try:
            # Check label-based triggers (existing flow)
            for trigger_label, next_agent in self.AGENT_FLOW.items():
                completion_label = f"orch:{next_agent}-done"
                
                # Search for issues with trigger but not completion
                issues = self.github.search_issues_by_labels(
                    include_labels=[trigger_label],
                    exclude_labels=[completion_label],
                )
                
                for issue in issues:
                    event_key = f"{issue['number']}:{next_agent}"
                    
                    # Only process if not already handled
                    if event_key not in self.processed_events:
                        events.append({
                            "issue": issue,
                            "agent": next_agent,
                            "trigger_label": trigger_label,
                            "trigger_type": "label"
                        })
                        self.processed_events.add(event_key)
            
            # Check status-based triggers (new)
            for status_label, agents in self.STATUS_TRIGGERS.items():
                issues = self.github.search_issues_by_labels([status_label])
                
                for issue in issues:
                    for agent in agents:
                        # Check if agent already ran
                        completion_label = f"orch:{agent}-done"
                        issue_labels = [
                            label.get("name", "") if isinstance(label, dict) else str(label)
                            for label in issue.get("labels", [])
                        ]
                        
                        if completion_label not in issue_labels:
                            event_key = f"{issue['number']}:{agent}:status"
                            
                            if event_key not in self.processed_events:
                                events.append({
                                    "issue": issue,
                                    "agent": agent,
                                    "trigger_label": status_label,
                                    "trigger_type": "status"
                                })
                                self.processed_events.add(event_key)
                        
        except (GitHubCommandError, TimeoutError, ValueError) as e:
            self.console.print(f"[red]Error checking triggers: {e}[/red]")
        
        return events
    
    def _handle_event(self, event: Dict, live: Live) -> bool:
        """
        Handle orchestration event
        
        Args:
            event: Event details
            live: Rich Live display
            
        Returns:
            True if successful, False otherwise
        """
        issue = event["issue"]
        agent = event["agent"]
        
        live.console.print(f"\n[bold green]🚀 Triggering {agent.upper()} for issue #{issue['number']}[/bold green]")
        live.console.print(f"   Title: {issue.get('title', 'N/A')}")
        
        try:
            # Set execution mode to automated for the agent
            agent_instance = self.executor.agents.get(agent)
            if agent_instance:
                agent_instance.execution_mode = "automated"
            
            # Execute agent
            result = self.executor.execute(agent, issue["number"])
            
            if result.get("success"):
                # Add completion label
                completion_label = f"orch:{agent}-done"
                self.github.add_labels(issue["number"], [completion_label])
                
                # Add comment with results
                comment_body = self._create_completion_comment(agent, result)
                self.github.add_comment(issue["number"], comment_body)
                
                live.console.print(f"[green]✅ {agent.upper()} completed successfully[/green]")
                live.console.print(f"   Output: {result.get('output_path', 'N/A')}")
                
                return True
            else:
                error = result.get("error", "Unknown error")
                live.console.print(f"[red]❌ {agent.upper()} failed: {error}[/red]")
                
                # Add failure comment
                self.github.add_comment(
                    issue["number"],
                    f"⚠️ {agent.title()} agent failed automatically.\n\n"
                    f"**Error**: {error}\n\n"
                    f"Please review and retry manually: `squad {agent} {issue['number']}`"
                )
                
                return False
                
        except (GitHubCommandError, TimeoutError, RuntimeError) as e:
            live.console.print(f"[red]❌ Error executing {agent}: {e}[/red]")
            return False
    
    def _create_completion_comment(self, agent: str, result: Dict) -> str:
        """Create GitHub comment for completed agent"""
        next_step = self._get_next_step(agent)
        
        comment = f"✅ **{agent.title()} agent completed automatically**\n\n"
        
        if result.get("output_path"):
            comment += f"**Output**: `{result['output_path']}`\n\n"
        
        comment += f"**Next Step**: {next_step}\n\n"
        comment += f"*Executed by AI-Squad Watch Mode at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return comment
    
    def _get_next_step(self, completed_agent: str) -> str:
        """Get next step message"""
        next_steps = {
            "pm": "Architect will design the technical solution",
            "architect": "Engineer will implement the features",
            "engineer": "Reviewer will review the code",
            "reviewer": "All agents completed! 🎉",
        }
        return next_steps.get(completed_agent, "Check issue for next steps")
    
    def _create_status_table(self) -> Table:
        """Create status display table"""
        table = Table(
            title="AI-Squad Watch Mode",
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green", width=30)
        
        # Status
        status = "🟢 Active" if self.stats["checks"] > 0 else "🟡 Starting"
        table.add_row("Status", status)
        
        # Configuration
        table.add_row("Repository", self.repo or "[red]Not configured[/red]")
        table.add_row("Poll Interval", f"{self.interval}s")
        
        # Statistics
        table.add_row("", "")  # Separator
        table.add_row("Checks Performed", str(self.stats["checks"]))
        table.add_row("Events Detected", str(self.stats["events"]))
        table.add_row("Successes", f"[green]{self.stats['successes']}[/green]")
        
        if self.stats["failures"] > 0:
            table.add_row("Failures", f"[red]{self.stats['failures']}[/red]")
        
        # Timing
        table.add_row("", "")  # Separator
        table.add_row("Last Check", datetime.now().strftime("%H:%M:%S"))
        
        return table
    
    def _print_summary(self):
        """Print summary statistics"""
        self.console.print("\n[bold cyan]📊 Watch Mode Summary[/bold cyan]")
        self.console.print(f"   Total checks: {self.stats['checks']}")
        self.console.print(f"   Events processed: {self.stats['events']}")
        self.console.print(f"   [green]Successes: {self.stats['successes']}[/green]")
        if self.stats["failures"] > 0:
            self.console.print(f"   [red]Failures: {self.stats['failures']}[/red]")
        self.console.print()


class WatchConfig:
    """Configuration for watch mode"""
    
    DEFAULT_INTERVAL = 30  # seconds
    MIN_INTERVAL = 10
    MAX_INTERVAL = 300
    
    @classmethod
    def validate_interval(cls, interval: int) -> int:
        """Validate and clamp interval"""
        if interval < cls.MIN_INTERVAL:
            return cls.MIN_INTERVAL
        if interval > cls.MAX_INTERVAL:
            return cls.MAX_INTERVAL
        return interval
