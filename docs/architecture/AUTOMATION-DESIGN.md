# AI-Squad Automatic Orchestration Design (Deprecated)

> **Status**: Deprecated  
> This document described legacy watch-mode automation and is no longer maintained.  
> See [docs/ORCHESTRATION.md](../ORCHESTRATION.md) for current orchestration and Battle Plan guidance.

---

## 🎯 Design Goals

**Keep Both Modes**:
- ✅ Manual CLI (current) - Quick testing, local control
- ✅ Automatic Mode (new) - Label-based orchestration like AgentX

**Implementation**:
- ✅ **Watch Mode** - Local daemon monitoring GitHub (IMPLEMENTED)
- 🔄 **GitHub Actions** - Cloud-based automation (planned)
- 🔄 **Hybrid** - Combine both approaches (planned)

---

## 🚀 Implemented: Watch Mode

### Overview
`squad watch` command monitors GitHub for label changes and triggers agents automatically.

### Orchestration Flow
```
PM Agent completes
  ↓ (adds orch:pm-done label)
Watch detects label
  ↓
Triggers Architect automatically
  ↓ (adds orch:architect-done label)
Watch detects label
  ↓
Triggers Engineer automatically
  ↓ (adds orch:engineer-done label)
Watch detects label
  ↓
Triggers Reviewer automatically
  ↓
Complete! 🎉
```

**Simplified Flow**: PM → Architect → Engineer → Reviewer  
**Note**: UX Designer is optional (run manually if needed)

### Implementation

#### New Command: `squad watch`

```python
# ai_squad/cli.py

@main.command()
@click.option("--interval", default=30, help="Polling interval in seconds")
@click.option("--repo", help="GitHub repo (owner/repo)")
def watch(interval, repo):
    """
    Watch GitHub for label changes and auto-trigger agents
    
    Example:
        squad watch --repo jnPiyush/MyProject
        squad watch --interval 60
    """
    print_banner()
    console.print("[bold cyan]Starting AI-Squad Watch Mode...[/bold cyan]\n")
    console.print(f"Monitoring: {repo or config.github_repo}")
    console.print(f"Interval: {interval}s")
    console.print("\n[yellow]Press Ctrl+C to stop[/yellow]\n")
    
    try:
        from ai_squad.core.watch import WatchDaemon
        daemon = WatchDaemon(config, interval=interval, repo=repo)
        daemon.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watch mode...[/yellow]")
```

#### New Module: `ai_squad/core/watch.py`

```python
"""
Watch daemon for automatic agent orchestration
"""
import time
from typing import Dict, List, Set
from datetime import datetime, timedelta
from rich.live import Live
from rich.table import Table

from ai_squad.core.config import Config
from ai_squad.tools.github import GitHubTool
from ai_squad.core.agent_executor import AgentExecutor


class WatchDaemon:
    """Monitors GitHub and triggers agents automatically"""
    
    def __init__(self, config: Config, interval: int = 30, repo: str = None):
        self.config = config
        self.interval = interval
        self.github = GitHubTool(config, repo=repo)
        self.executor = AgentExecutor(config)
        self.processed_events: Set[str] = set()  # Track processed label additions
        
    def run(self):
        """Main watch loop"""
        with Live(self._create_status_table(), refresh_per_second=1) as live:
            while True:
                try:
                    # Check for label changes
                    events = self._check_for_triggers()
                    
                    for event in events:
                        self._handle_event(event, live)
                    
                    # Update status display
                    live.update(self._create_status_table())
                    
                    time.sleep(self.interval)
                    
                except Exception as e:
                    print(f"Error in watch loop: {e}")
                    time.sleep(self.interval)
    
    def _check_for_triggers(self) -> List[Dict]:
        """Check for orchestration labels on issues"""
        events = []
        
        # Get recent issues with orchestration labels
        issues = self.github.search_issues(
            query='is:open label:"orch:pm-done","orch:ux-done","orch:architect-done","orch:engineer-done"',
            since=datetime.now() - timedelta(minutes=self.interval)
        )
        
        for issue in issues:
            labels = [l["name"] for l in issue.get("labels", [])]
            
            # Check which agent should run next
            next_agent = self._determine_next_agent(labels)
            
            if next_agent:
                event_key = f"{issue['number']}:{next_agent}"
                
                if event_key not in self.processed_events:
                    events.append({
                        "issue": issue,
                        "agent": next_agent,
                        "trigger_label": self._get_trigger_label(labels)
                    })
                    self.processed_events.add(event_key)
        
        return events
    
    def _determine_next_agent(self, labels: List[str]) -> str:
        """Determine which agent should run based on labels"""
        # Sequential flow: PM → UX → Architect → Engineer → Reviewer
        
        if "orch:pm-done" in labels and "orch:ux-done" not in labels:
            return "ux"
        
        if "orch:ux-done" in labels and "orch:architect-done" not in labels:
            return "architect"
        
        if "orch:architect-done" in labels and "orch:engineer-done" not in labels:
            return "engineer"
        
        if "orch:engineer-done" in labels and "orch:reviewer-done" not in labels:
            return "reviewer"
        
        return None
    
    def _handle_event(self, event: Dict, live: Live):
        """Handle orchestration event"""
        issue = event["issue"]
        agent = event["agent"]
        
        live.console.print(f"\n[bold green]🚀 Triggering {agent.upper()} for issue #{issue['number']}[/bold green]")
        
        try:
            # Execute agent
            result = self.executor.execute(agent, issue["number"])
            
            if result["success"]:
                # Add completion label
                completion_label = f"orch:{agent}-done"
                self.github.add_labels(issue["number"], [completion_label])
                
                # Add comment
                self.github.add_comment(
                    issue["number"],
                    f"✅ {agent.title()} agent completed automatically.\n\n"
                    f"**Output**: {result.get('output_path', 'N/A')}\n"
                    f"**Next**: {self._get_next_step(agent)}"
                )
                
                live.console.print(f"[green]✅ {agent.upper()} completed successfully[/green]")
            else:
                live.console.print(f"[red]❌ {agent.upper()} failed: {result.get('error')}[/red]")
                
        except Exception as e:
            live.console.print(f"[red]❌ Error executing {agent}: {e}[/red]")
    
    def _get_next_step(self, completed_agent: str) -> str:
        """Get next step message"""
        next_agent_map = {
            "pm": "UX Designer will design wireframes",
            "ux": "Architect will create technical design",
            "architect": "Engineer will implement features",
            "engineer": "Reviewer will review the PR",
            "reviewer": "Issue complete!"
        }
        return next_agent_map.get(completed_agent, "Next step TBD")
    
    def _create_status_table(self) -> Table:
        """Create status display table"""
        table = Table(title="AI-Squad Watch Status")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Status", "🟢 Active")
        table.add_row("Interval", f"{self.interval}s")
        table.add_row("Monitored Repo", self.github.repo or "N/A")
        table.add_row("Events Processed", str(len(self.processed_events)))
        table.add_row("Last Check", datetime.now().strftime("%H:%M:%S"))
        
        return table
```

### Usage

```bash
# Start watch daemon
squad watch

# With custom settings
squad watch --interval 60 --repo jnPiyush/MyProject

# Output:
🔍 Monitoring: jnPiyush/MyProject
⏱️  Interval: 30s
🔄 Flow: PM → Architect → Engineer → Reviewer

Press Ctrl+C to stop

┌─────────────── AI-Squad Watch Mode ───────────────┐
│ Status         │ 🟢 Active                        │
│ Repository     │ jnPiyush/MyProject               │
│ Poll Interval  │ 30s                              │
│ Checks         │ 15                               │
│ Events         │ 3                                │
│ Successes      │ 3                                │
│ Last Check     │ 14:23:45                         │
└────────────────────────────────────────────────────┘

🚀 Triggering ARCHITECT for issue #123
   Title: [Feature] Add health check
✅ ARCHITECT completed successfully
   Output: docs/adr/ADR-123.md

🚀 Triggering ENGINEER for issue #123
   Title: [Feature] Add health check
✅ ENGINEER completed successfully
   Output: Implementation committed
```

### Complete Example Workflow

```bash
# Terminal 1: Start watch mode
cd my-project
squad watch

# Terminal 2: Create and work on issue
# 1. Create epic
gh issue create --title "[Epic] Auth System" --label "type:epic"
# Issue #100 created

# 2. Run PM manually
squad pm 100
# Creates PRD, adds orch:pm-done label

# 3. Watch mode automatically detects orch:pm-done
# → Triggers Architect
# → Creates ADR + Spec
# → Adds orch:architect-done label

# 4. Watch mode detects orch:architect-done
# → Triggers Engineer  
# → Implements code
# → Adds orch:engineer-done label

# 5. Watch mode detects orch:engineer-done
# → Triggers Reviewer
# → Reviews code
# → Done!
```

### Benefits
- ✅ Runs locally (no GitHub Actions needed)
- ✅ Real-time monitoring
- ✅ Full visibility in terminal
- ✅ Easy to start/stop
- ✅ Works with existing CLI commands

---

## 🔄 Option 2: GitHub Actions (Cloud Automation)

### Overview
Add optional GitHub Actions workflows that mirror AgentX's automation.

### Implementation

Create `.github/workflows/ai-squad-orchestrator.yml`:

```yaml
name: AI-Squad Orchestrator

on:
  issues:
    types: [labeled]

jobs:
  orchestrate:
    runs-on: ubuntu-latest
    if: |
      contains(github.event.label.name, 'orch:') ||
      contains(github.event.label.name, 'type:epic') ||
      contains(github.event.label.name, 'type:feature')
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install AI-Squad
        run: |
          pip install ai-squad
          # Or: pip install -e . for repo installs
      
      - name: Configure
        run: |
          echo "GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}" >> $GITHUB_ENV
      
      - name: Determine Next Agent
        id: next-agent
        run: |
          LABELS="${{ join(github.event.issue.labels.*.name, ',') }}"
          
          if [[ "$LABELS" == *"type:epic"* ]] && [[ "$LABELS" != *"orch:pm-done"* ]]; then
            echo "agent=pm" >> $GITHUB_OUTPUT
          elif [[ "$LABELS" == *"orch:pm-done"* ]] && [[ "$LABELS" != *"orch:ux-done"* ]]; then
            echo "agent=ux" >> $GITHUB_OUTPUT
          elif [[ "$LABELS" == *"orch:ux-done"* ]] && [[ "$LABELS" != *"orch:architect-done"* ]]; then
            echo "agent=architect" >> $GITHUB_OUTPUT
          elif [[ "$LABELS" == *"orch:architect-done"* ]] && [[ "$LABELS" != *"orch:engineer-done"* ]]; then
            echo "agent=engineer" >> $GITHUB_OUTPUT
          elif [[ "$LABELS" == *"orch:engineer-done"* ]] && [[ "$LABELS" != *"orch:reviewer-done"* ]]; then
            echo "agent=reviewer" >> $GITHUB_OUTPUT
          fi
      
      - name: Run Agent
        if: steps.next-agent.outputs.agent != ''
        run: |
          squad ${{ steps.next-agent.outputs.agent }} ${{ github.event.issue.number }}
      
      - name: Add Completion Label
        if: success() && steps.next-agent.outputs.agent != ''
        uses: actions-ecosystem/action-add-labels@v1
        with:
          labels: "orch:${{ steps.next-agent.outputs.agent }}-done"
      
      - name: Comment on Issue
        if: success() && steps.next-agent.outputs.agent != ''
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `✅ ${{ steps.next-agent.outputs.agent }} agent completed automatically.`
            });
```

### Usage

```bash
# 1. Install workflow in your repo
cp .github/workflows/ai-squad-orchestrator.yml /your/repo/.github/workflows/

# 2. Push to GitHub
git add .github/workflows/ai-squad-orchestrator.yml
git commit -m "Add AI-Squad orchestration"
git push

# 3. Create issue with label
gh issue create --title "[Epic] New Feature" --label "type:epic"

# 4. Workflow automatically triggers PM agent
# 5. PM adds orch:pm-done label
# 6. Workflow automatically triggers UX agent
# ... continues automatically
```

### Benefits
- ✅ Fully automated like AgentX
- ✅ Runs on GitHub infrastructure
- ✅ No local process needed
- ✅ Integrated with GitHub UI

---

## ⚡ Option 3: Hybrid Mode (Best of Both)

### Overview
Combine local CLI, watch mode, and GitHub Actions for maximum flexibility.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   AI-Squad Modes                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Manual CLI (Current)                            │
│     squad pm 123                                    │
│     ↓ User controls everything                      │
│                                                     │
│  2. Watch Mode (New - Local Automation)             │
│     squad watch                                     │
│     ↓ Monitors GitHub, triggers locally             │
│                                                     │
│  3. GitHub Actions (New - Cloud Automation)         │
│     .github/workflows/ai-squad-orchestrator.yml     │
│     ↓ Fully automated on GitHub                     │
│                                                     │
│  4. Hybrid (New - Mix & Match)                      │
│     - Use CLI for testing                           │
│     - Use watch for active development              │
│     - Use Actions for production                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Configuration

Add to `squad.yaml`:

```yaml
automation:
  mode: "manual"  # manual | watch | actions | hybrid
  
  watch:
    enabled: false
    interval: 30  # seconds
    labels:
      - "orch:pm-done"
      - "orch:ux-done"
      - "orch:architect-done"
      - "orch:engineer-done"
  
  actions:
    enabled: false
    workflows:
      - ".github/workflows/ai-squad-orchestrator.yml"
  
  # Hybrid: Run PM/UX locally, Architect/Engineer/Reviewer in Actions
  hybrid:
    local_agents: ["pm", "ux"]
    cloud_agents: ["architect", "engineer", "reviewer"]
```

### New Command: `squad mode`

```bash
# Check current mode
squad mode

# Set mode
squad mode set watch
squad mode set actions
squad mode set hybrid

# Enable specific features
squad mode enable watch
squad mode disable actions
```

---

## 📊 Comparison: Manual vs Automatic

| Feature | Manual CLI | Watch Mode | GitHub Actions | Hybrid |
|---------|------------|------------|----------------|--------|
| **Setup** | None | Run command | Install workflow | Both |
| **Control** | Full | Automatic | Automatic | Mixed |
| **Speed** | Instant | 30s delay | GitHub queue | Mixed |
| **Visibility** | Terminal | Terminal | GitHub UI | Both |
| **Cost** | Free | Free | Free (GitHub) | Free |
| **Network** | Per command | Continuous | Event-driven | Mixed |
| **Testing** | ✅ Best | ✅ Good | ⚠️ Harder | ✅ Good |
| **Production** | ⚠️ Manual | ✅ Good | ✅ Best | ✅ Best |

---

## 🎯 Recommended Implementation Plan

### Phase 1: Watch Mode (v0.2.0)
1. ✅ Implement `WatchDaemon` class
2. ✅ Add `squad watch` command
3. ✅ Add label-based triggering logic
4. ✅ Add real-time status display
5. ✅ Test with mock GitHub data
6. ✅ Test with real GitHub repo

**Timeline**: 2-3 days  
**Effort**: Medium

### Phase 2: GitHub Actions (v0.3.0)
1. ✅ Create orchestrator workflow
2. ✅ Add agent-specific workflows (optional)
3. ✅ Add setup documentation
4. ✅ Test in real repository
5. ✅ Add workflow templates to package

**Timeline**: 1-2 days  
**Effort**: Low (mostly YAML)

### Phase 3: Hybrid Mode (v0.4.0)
1. ✅ Add mode configuration to `squad.yaml`
2. ✅ Implement `squad mode` command
3. ✅ Add mode switching logic
4. ✅ Update documentation
5. ✅ Add examples for each mode

**Timeline**: 1 day  
**Effort**: Low

---

## 🚀 Quick Start Examples

### Example 1: Local Development with Watch Mode

```bash
# Terminal 1: Start watch mode
cd my-project
squad watch

# Terminal 2: Create issues
gh issue create --title "[Epic] Auth System" --label "type:epic"

# Watch mode automatically:
# 1. Detects new epic
# 2. Runs PM agent
# 3. Adds orch:pm-done label
# 4. Runs UX agent
# 5. ... continues
```

### Example 2: Production with GitHub Actions

```bash
# One-time setup
squad init --with-actions

# Creates:
# - squad.yaml
# - .github/workflows/ai-squad-orchestrator.yml

# Commit and push
git add .
git commit -m "Add AI-Squad automation"
git push

# From now on, everything is automatic:
gh issue create --title "[Feature] Login" --label "type:feature"
# → Architect automatically runs
# → Engineer automatically runs
# → Reviewer automatically runs
```

### Example 3: Hybrid Development

```bash
# Configure hybrid mode
squad mode set hybrid

# Edit squad.yaml:
# hybrid:
#   local_agents: ["pm", "ux"]      # Manual control
#   cloud_agents: ["architect", "engineer", "reviewer"]  # Automatic

# Workflow:
# 1. You run: squad pm 123 (manual)
# 2. You run: squad ux 123 (manual)
# 3. You add: orch:ux-done label
# 4. GitHub Actions automatically runs architect
# 5. GitHub Actions automatically runs engineer
# 6. GitHub Actions automatically runs reviewer
```

---

## 🎯 Benefits Summary

### Why Add Automation?

**For Development Teams**:
- ✅ Reduce manual steps
- ✅ Faster iteration cycles
- ✅ Consistent execution
- ✅ Better collaboration

**For Solo Developers**:
- ✅ Work on multiple issues in parallel
- ✅ Automatic progress while focusing on code
- ✅ No need to remember which agent to run next

**For Organizations**:
- ✅ Standardized workflows
- ✅ Audit trail in GitHub
- ✅ Scalable across teams
- ✅ Lower cognitive load

### Why Keep Manual Mode?

- ✅ Quick testing and debugging
- ✅ Learning how agents work
- ✅ One-off tasks
- ✅ Full control when needed
- ✅ Works without network

---

## 📝 Documentation Updates Needed

1. **README.md** - Add automation section
2. **docs/automation.md** - New guide for watch/actions
3. **docs/configuration.md** - Add automation config
4. **QUICK-START.md** - Add watch mode example
5. **examples/automated-workflow/** - New example

---

## ✅ Next Steps

**To implement this:**

1. **Review this design** - Approve approach
2. **Implement Watch Mode** - Start with Phase 1
3. **Add GitHub Actions** - Phase 2 (simple)
4. **Test thoroughly** - Both modes
5. **Update documentation** - All guides
6. **Release v0.2.0** - With automation

**Would you like me to implement the Watch Mode now?**

I can start by creating:
- `ai_squad/core/watch.py` - Watch daemon
- `ai_squad/cli.py` - Add `squad watch` command  
- `tests/test_watch.py` - Tests for watch mode
- `docs/automation.md` - Usage guide

---

**Design By**: GitHub Copilot  
**Date**: January 22, 2026  
**Version**: AI-Squad 0.2.0 (Planned)  
**Status**: Ready for Implementation
