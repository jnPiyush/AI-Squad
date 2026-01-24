"""
Captain Agent (Coordinator)

The Captain (inspired by Gastown's Mayor) is a meta-agent that coordinates other agents.
It breaks down complex tasks, creates convoys, dispatches work, and monitors progress.
"""
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..agents.base import BaseAgent, SDK_AVAILABLE
from ..core.config import Config
from .convoy import ConvoyManager
from .battle_plan import (
    BattlePlan,
    BattlePlanExecutor,
    BattlePlanManager,
    BattlePlanPhase,
)
from .workstate import WorkItem, WorkStateManager, WorkStatus
from .router import Candidate

if SDK_AVAILABLE:
    try:
        from copilot import CopilotClient
    except ImportError:
        pass

logger = logging.getLogger(__name__)


@dataclass
class TaskBreakdown:
    """
    Result of breaking down a complex task into smaller work items.
    """
    original_task: str
    issue_number: Optional[int]
    work_items: List[WorkItem]
    suggested_strategy: Optional[str] = None
    parallel_groups: List[List[str]] = field(default_factory=list)  # Groups of work item IDs
    estimated_time_minutes: int = 0
    complexity: str = "medium"  # low, medium, high, critical


@dataclass
class ConvoyPlan:
    """
    Plan for a convoy (parallel batch of work).
    """
    id: str
    work_items: List[str]  # Work item IDs
    agents: List[str]      # Agent types involved
    parallel: bool = True
    estimated_time_minutes: int = 0


class Captain(BaseAgent):
    """
    Captain (Coordinator) Agent.
    
    Responsibilities:
    - Analyze complex tasks and break them down
    - Select appropriate battle plans (workflows)
    - Create convoys for parallel execution
    - Dispatch work to appropriate agents
    - Monitor progress and handle blockers
    - Coordinate handoffs between agents
    """
    
    AGENT_NAME = "captain"
    
    def get_system_prompt(self) -> str:
        """Get system prompt for Captain agent"""
        return """
You are the Captain - a meta-agent coordinator for AI-Squad.

Your role:
- Analyze GitHub issues and break them into manageable work items
- Select appropriate battle plans
- Create convoys for parallel execution
- Dispatch work to specialized agents (PM, Architect, Engineer, UX, Reviewer)
- Monitor progress and resolve blockers
- Coordinate handoffs between agents

You have access to:
- WorkStateManager for tracking work
- BattlePlanManager for workflow templates
- ConvoyManager for parallel execution

Always provide clear, structured coordination plans.
"""
    
    def get_output_path(self, issue_number: int) -> str:
        """Captain doesn't create files directly"""
        return f".squad/captain-coordination-{issue_number}.md"
    
    def __init__(
        self,
        config: Config,
        sdk: Optional[Any] = None,
        orchestration: Optional[Dict[str, Any]] = None,
        work_state_manager: Optional[WorkStateManager] = None,
        strategy_manager: Optional[BattlePlanManager] = None,
        convoy_manager: Optional[ConvoyManager] = None,
        signal_manager: Optional[Any] = None,
        handoff_manager: Optional[Any] = None
    ):
        """
        Initialize Captain agent.
        
        Args:
            config: Agent configuration
            sdk: GitHub Copilot SDK instance
            orchestration: Shared orchestration managers
        """
        super().__init__(config, sdk, orchestration)
        
        # Use injected managers (DI pattern) or create local ones as fallback
        self.work_state_manager = work_state_manager or self.workstate or WorkStateManager(
            Path.cwd(),
            config=self.config.data,
        )
        self.strategy_manager = strategy_manager or self.strategy or BattlePlanManager(Path.cwd())
        self.convoy_manager = convoy_manager or self.convoy or None
        self.signal_manager = signal_manager or self.signal
        self.handoff_manager = handoff_manager or self.handoff
        self.org_router = self.orchestration.get("router")
        self.routing_config = self.orchestration.get("routing_config", {}) or {}
        # Keep orchestration in sync for downstream consumers
        self.orchestration.update({
            "workstate": self.work_state_manager,
            "strategy": self.strategy_manager,
            "convoy": self.convoy_manager,
            "signal": self.signal_manager,
            "handoff": self.handoff_manager,
        })

    def _execute_agent(self, issue: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous execution hook required by BaseAgent."""
        issue_number = issue.get("number") or issue.get("id") or "unknown"
        summary = f"Captain coordination initialized for issue #{issue_number}"
        return {
            "success": True,
            "output": summary,
            "artifacts": [],
        }
    
    async def analyze_task(
        self,
        task_description: str,
        issue_number: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskBreakdown:
        """
        Analyze a task and break it down into work items.
        
        Args:
            task_description: Description of the task
            issue_number: Optional GitHub issue number
            context: Additional context (issue body, labels, etc.)
            
        Returns:
            TaskBreakdown with work items and recommendations
        """
        logger.info("Analyzing task: %s", task_description[:50])
        
        # Determine complexity and select strategy
        complexity, strategy_name = await self._assess_task_complexity(
            task_description,
            context
        )
        
        # Get or create work items
        work_items = []
        
        if strategy_name:
            strategy = self.strategy_manager.get_strategy(strategy_name)
            if strategy:
                # Create work items from strategy steps
                for phase in strategy.phases:
                    item = self.work_state_manager.create_work_item(
                        title=f"[{phase.agent}] {phase.name}",
                        description=phase.description,
                        issue_number=issue_number,
                        labels=[strategy_name, phase.agent]
                    )
                    work_items.append(item)
                
                # Set up dependencies
                for i, step in enumerate(strategy.phases):
                    for dep_name in step.depends_on:
                        dep_idx = next(
                            (j for j, s in enumerate(strategy.phases) 
                             if s.name == dep_name),
                            None
                        )
                        if dep_idx is not None:
                            self.work_state_manager.add_dependency(
                                work_items[i].id,
                                work_items[dep_idx].id
                            )
        else:
            # Create generic breakdown
            work_items = await self._create_generic_breakdown(
                task_description,
                issue_number,
                context
            )
        
        # Identify parallel groups
        parallel_groups = self._identify_parallel_groups(work_items)
        
        # Estimate time
        estimated_time = self._estimate_time(work_items, complexity)
        
        breakdown = TaskBreakdown(
            original_task=task_description,
            issue_number=issue_number,
            work_items=work_items,
            suggested_strategy=strategy_name,
            parallel_groups=parallel_groups,
            estimated_time_minutes=estimated_time,
            complexity=complexity
        )
        
        logger.info(
            "Task breakdown: %d work items, complexity=%s, strategy=%s",
            len(work_items), complexity, strategy_name
        )
        
        return breakdown
    
    async def _assess_task_complexity(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]]
    ) -> Tuple[str, Optional[str]]:
        """
        Assess task complexity and suggest a battle plan.
        
        Returns:
            Tuple of (complexity, strategy_name)
        """
        # Use SDK if available for intelligent assessment
        if SDK_AVAILABLE:
            try:
                system_prompt = "You are a task triage assistant. Respond in JSON only."
                user_prompt = (
                    "Assess task complexity and suggest a battle plan name. "
                    "Return JSON with keys: complexity (low|medium|high|critical) and strategy (string or null).\n\n"
                    f"Task: {task_description}\n\n"
                    f"Context: {context or {}}"
                )
                raw = self._call_sdk(system_prompt, user_prompt)
                if raw:
                    try:
                        parsed = json.loads(raw)
                        return parsed.get("complexity", "medium"), parsed.get("strategy")
                    except json.JSONDecodeError:
                        logger.warning("SDK returned non-JSON complexity assessment")
            except Exception as e:
                logger.warning("SDK assessment failed: %s", e)
        
        # Fallback: keyword-based assessment
        task_lower = task_description.lower()
        labels = (context or {}).get("labels", [])
        
        # Check for strategy keywords
        strategy_name = None
        if any(w in task_lower for w in ["feature", "implement", "create", "add"]):
            strategy_name = "feature"
        elif any(w in task_lower for w in ["bug", "fix", "error", "issue"]):
            strategy_name = "bugfix"
        elif any(w in task_lower for w in ["refactor", "debt", "cleanup", "improve"]):
            strategy_name = "tech-debt"
        elif "enhancement" in labels:
            strategy_name = "feature"
        elif "bug" in labels:
            strategy_name = "bugfix"
        
        # Assess complexity
        complexity = "medium"
        if any(w in task_lower for w in ["simple", "quick", "small", "minor"]):
            complexity = "low"
        elif any(w in task_lower for w in ["complex", "large", "major", "critical"]):
            complexity = "high"
        elif any(w in task_lower for w in ["critical", "urgent", "security"]):
            complexity = "critical"
        
        return complexity, strategy_name
    
    async def _create_generic_breakdown(
        self,
        task_description: str,
        issue_number: Optional[int],
        context: Optional[Dict[str, Any]]
    ) -> List[WorkItem]:
        """
        Create a generic breakdown when no battle plan matches.
        """
        work_items = []
        
        # Use SDK for intelligent breakdown
        if SDK_AVAILABLE:
            try:
                result = await self._call_sdk(
                    "breakdown_task",
                    task=task_description,
                    context=context
                )
                if result and "items" in result:
                    for item_data in result["items"]:
                        item = self.work_state_manager.create_work_item(
                            title=item_data.get("title", "Untitled"),
                            description=item_data.get("description", ""),
                            issue_number=issue_number,
                            labels=item_data.get("labels", [])
                        )
                        work_items.append(item)
                    return work_items
            except Exception as e:
                logger.warning("SDK breakdown failed: %s", e)
        
        # Fallback: basic breakdown
        # 1. Analysis/Requirements
        work_items.append(self.work_state_manager.create_work_item(
            title="[pm] Define requirements",
            description=f"Analyze and define requirements for: {task_description}",
            issue_number=issue_number,
            labels=["requirements"]
        ))
        
        # 2. Implementation
        impl_item = self.work_state_manager.create_work_item(
            title="[engineer] Implement solution",
            description="Implement the solution based on requirements",
            issue_number=issue_number,
            labels=["implementation"]
        )
        work_items.append(impl_item)
        
        # 3. Review
        review_item = self.work_state_manager.create_work_item(
            title="[reviewer] Review implementation",
            description="Review code quality, tests, and documentation",
            issue_number=issue_number,
            labels=["review"]
        )
        work_items.append(review_item)
        
        # Set dependencies
        self.work_state_manager.add_dependency(impl_item.id, work_items[0].id)
        self.work_state_manager.add_dependency(review_item.id, impl_item.id)
        
        return work_items
    
    def _identify_parallel_groups(
        self,
        work_items: List[WorkItem]
    ) -> List[List[str]]:
        """
        Identify groups of work items that can run in parallel.
        """
        # Build dependency graph
        dependents: Dict[str, set] = {item.id: set() for item in work_items}
        for item in work_items:
            for dep_id in item.depends_on:
                if dep_id in dependents:
                    dependents[dep_id].add(item.id)
        
        # Group by dependency level
        levels: List[List[str]] = []
        processed: set = set()
        
        while len(processed) < len(work_items):
            # Find items whose dependencies are all processed
            current_level = []
            for item in work_items:
                if item.id in processed:
                    continue
                if all(dep in processed for dep in item.depends_on):
                    current_level.append(item.id)
            
            if current_level:
                levels.append(current_level)
                processed.update(current_level)
            else:
                # Circular dependency or isolated items
                remaining = [i.id for i in work_items if i.id not in processed]
                levels.append(remaining)
                break
        
        return levels
    
    def _estimate_time(
        self,
        work_items: List[WorkItem],
        complexity: str
    ) -> int:
        """
        Estimate total time for completion in minutes.
        """
        base_times = {
            "low": 15,
            "medium": 30,
            "high": 60,
            "critical": 90
        }
        
        base = base_times.get(complexity, 30)
        
        # Account for parallelism
        parallel_groups = self._identify_parallel_groups(work_items)
        return base * len(parallel_groups)
    
    async def create_convoy_plan(
        self,
        breakdown: TaskBreakdown
    ) -> List[ConvoyPlan]:
        """
        Create convoy plans for parallel execution.
        
        Args:
            breakdown: Task breakdown with work items
            
        Returns:
            List of ConvoyPlan for parallel batches
        """
        plans = []
        
        for i, group in enumerate(breakdown.parallel_groups):
            # Determine agents needed
            agents = set()
            for item_id in group:
                item = self.work_state_manager.get_work_item(item_id)
                if item:
                    # Extract agent from title or labels
                    for label in item.labels:
                        if label in ["pm", "architect", "engineer", "ux", "reviewer"]:
                            agents.add(label)
            
            plan = ConvoyPlan(
                id=f"convoy-{i+1}",
                work_items=group,
                agents=list(agents),
                parallel=len(group) > 1,
                estimated_time_minutes=30  # Default estimate per convoy
            )
            plans.append(plan)
        
        return plans
    
    async def dispatch_work(
        self,
        work_item_id: str,
        agent_type: str
    ) -> bool:
        """
        Dispatch a work item to a specific agent.
        
        Args:
            work_item_id: ID of the work item
            agent_type: Type of agent (pm, architect, engineer, ux, reviewer)
            
        Returns:
            True if dispatch successful
        """
        item = self.work_state_manager.get_work_item(work_item_id)
        if not item:
            logger.error("Work item not found: %s", work_item_id)
            return False
        
        if item.status != WorkStatus.READY:
            logger.warning(
                "Work item %s is not ready (status=%s)",
                work_item_id, item.status.value
            )
            return False
        
        # Assign to agent
        self.work_state_manager.assign_to_agent(work_item_id, agent_type)
        
        logger.info("Dispatched %s to agent %s", work_item_id, agent_type)
        return True
    
    async def get_status(
        self,
        issue_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get overall status of work.
        
        Args:
            issue_number: Optional filter by issue number
            
        Returns:
            Status summary
        """
        stats = self.work_state_manager.get_stats()
        
        # Filter by issue if specified
        if issue_number:
            item = self.work_state_manager.get_work_item_by_issue(issue_number)
            if item:
                return {
                    "issue": issue_number,
                    "status": item.status.value,
                    "agent": item.agent_assignee,
                    "artifacts": item.artifacts,
                    "context": item.context
                }
            return {"issue": issue_number, "error": "Not found"}
        
        return {
            "overall": stats,
            "ready_work": [
                i.to_dict() 
                for i in self.work_state_manager.list_work_items(
                    status=WorkStatus.READY
                )
            ],
            "in_progress": [
                i.to_dict()
                for i in self.work_state_manager.list_work_items(
                    status=WorkStatus.IN_PROGRESS
                )
            ] + [
                i.to_dict()
                for i in self.work_state_manager.list_work_items(
                    status=WorkStatus.HOOKED
                )
            ]
        }
    
    async def handle_blocker(
        self,
        work_item_id: str,
        blocker_description: str
    ) -> Dict[str, Any]:
        """
        Handle a blocked work item.
        
        Args:
            work_item_id: ID of the blocked work item
            blocker_description: Description of the blocker
            
        Returns:
            Resolution suggestion
        """
        item = self.work_state_manager.get_work_item(work_item_id)
        if not item:
            return {"error": "Work item not found"}
        
        # Mark as blocked
        self.work_state_manager.transition_status(
            work_item_id,
            WorkStatus.BLOCKED,
            {"blocker": blocker_description}
        )
        
        # Use SDK for suggestions if available
        if SDK_AVAILABLE:
            try:
                result = await self._call_sdk(
                    "resolve_blocker",
                    work_item=item.to_dict(),
                    blocker=blocker_description
                )
                if result:
                    return {
                        "status": "suggestions_available",
                        "suggestions": result.get("suggestions", []),
                        "escalate": result.get("escalate", False)
                    }
            except Exception as e:
                logger.warning("SDK blocker resolution failed: %s", e)
        
        # Fallback: basic suggestions
        return {
            "status": "blocked",
            "suggestions": [
                "Check if required dependencies are complete",
                "Review the work item context for missing information",
                "Consider reaching out to the assigned agent",
                "Break down the task further if too complex"
            ],
            "escalate": True
        }
    
    async def recommend_next_actions(self) -> List[Dict[str, Any]]:
        """
        Recommend next actions based on current work state.
        
        Returns:
            List of recommended actions
        """
        recommendations = []
        
        # Check for ready work
        ready_items = self.work_state_manager.list_work_items(
            status=WorkStatus.READY
        )
        for item in ready_items[:5]:  # Top 5 by priority
            # Determine agent from labels or title
            agent = None
            for label in item.labels:
                if label in ["pm", "architect", "engineer", "ux", "reviewer"]:
                    agent = label
                    break
            
            if not agent and "[" in item.title:
                # Extract from title like "[pm] Define requirements"
                start = item.title.find("[") + 1
                end = item.title.find("]")
                if start > 0 and end > start:
                    agent = item.title[start:end]
            
            recommendations.append({
                "action": "dispatch",
                "work_item_id": item.id,
                "work_item_title": item.title,
                "suggested_agent": agent,
                "priority": item.priority
            })
        
        # Check for blocked work needing attention
        blocked_items = self.work_state_manager.list_work_items(
            status=WorkStatus.BLOCKED
        )
        for item in blocked_items[:3]:
            recommendations.append({
                "action": "resolve_blocker",
                "work_item_id": item.id,
                "work_item_title": item.title,
                "blocker": item.context.get("blocker", "Unknown")
            })
        
        return recommendations
    
    async def run(self, issue_number: int) -> str:
        """
        Run the Captain agent on an issue.
        
        This is the main entry point for coordinating work on an issue.
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Summary of actions taken
        """
        logger.info("Captain coordinating issue #%d", issue_number)
        
        # Check for existing work
        existing = self.work_state_manager.get_work_item_by_issue(issue_number)
        if existing:
            status = await self.get_status(issue_number)
            return f"Issue #{issue_number} already has work in progress:\n{status}"
        
        # Get issue details (would integrate with GitHub)
        # For now, create placeholder breakdown
        breakdown = await self.analyze_task(
            f"Work on issue #{issue_number}",
            issue_number=issue_number
        )
        
        # Create convoy plans
        convoys = await self.create_convoy_plan(breakdown)
        
        # Get recommendations
        recommendations = await self.recommend_next_actions()
        
        summary = f"""
## Captain Coordination Report for Issue #{issue_number}

### Task Breakdown
- **Complexity**: {breakdown.complexity}
    - **Suggested Strategy**: {breakdown.suggested_strategy or 'Custom'}
- **Work Items Created**: {len(breakdown.work_items)}
- **Estimated Time**: {breakdown.estimated_time_minutes} minutes

### Work Items
"""
        for item in breakdown.work_items:
            summary += f"- [{item.status.value}] {item.title} ({item.id})\n"
        
        summary += f"\n### Convoy Plans\n"
        for plan in convoys:
            summary += f"- **{plan.id}**: {len(plan.work_items)} items, agents: {', '.join(plan.agents)}\n"
        
        summary += f"\n### Recommended Next Actions\n"
        for rec in recommendations[:3]:
            summary += f"- {rec['action']}: {rec.get('work_item_title', rec.get('work_item_id'))}\n"
        
        return summary
    
    def coordinate(
        self,
        work_items: List[str],
        workstate_manager: Optional[WorkStateManager] = None,
        strategy_manager: Optional[BattlePlanManager] = None,
        convoy_manager: Optional[ConvoyManager] = None
    ) -> Dict[str, Any]:
        """
        Coordinate multiple work items using available resources.
        
        This method is called by AgentExecutor to coordinate work.
        Uses injected managers if provided, otherwise uses self managers.
        
        Args:
            work_items: List of work item IDs to coordinate
            workstate_manager: WorkState manager (optional, uses self.work_state_manager)
            strategy_manager: Strategy manager (optional, uses self.strategy_manager)
            convoy_manager: Convoy manager (optional, uses self.convoy_manager)
            
        Returns:
            Coordination plan with execution steps
        """
        # Use provided managers or fall back to self managers
        ws_mgr = workstate_manager or self.work_state_manager
        cv_mgr = convoy_manager or self.convoy_manager
        
        logger.info("Captain coordinating %d work items", len(work_items))
        
        # Analyze work items
        normalized_ids = [wid.id if isinstance(wid, WorkItem) else wid for wid in work_items]
        items = [ws_mgr.get_work_item(wid) for wid in normalized_ids]
        
        # Group by agent type and dependencies
        agent_groups: Dict[str, List[WorkItem]] = {}
        for item in items:
            if not item:
                continue
            
            # Determine agent from labels or title
            agent = self._detect_agent(item)
            routed_agent = self._route_agent_for_item(item, agent)
            if routed_agent is None:
                item.metadata["routing_blocked"] = True
                ws_mgr.update_work_item(item)
                agent = "blocked"
            else:
                if routed_agent != agent:
                    item.metadata["routed_agent"] = routed_agent
                    ws_mgr.update_work_item(item)
                agent = routed_agent
            if agent not in agent_groups:
                agent_groups[agent] = []
            agent_groups[agent].append(item)
        
        # Create execution plan
        plan = {
            "total_items": len(items),
            "agent_groups": {},
            "parallel_batches": [],
            "sequential_steps": []
        }
        
        # Build agent summaries
        for agent, group_items in agent_groups.items():
            plan["agent_groups"][agent] = {
                "count": len(group_items),
                "items": [item.id for item in group_items]
            }
        
        # Find parallelizable work
        for agent, group_items in agent_groups.items():
            if len(group_items) > 1:
                # Multiple items for same agent can run in convoy
                convoy_id = f"convoy-{agent}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                plan["parallel_batches"].append({
                    "convoy_id": convoy_id,
                    "agent": agent,
                    "items": [item.id for item in group_items]
                })
            else:
                # Single item runs sequentially
                plan["sequential_steps"].append({
                    "agent": agent,
                    "item_id": group_items[0].id,
                    "title": group_items[0].title
                })
        
        logger.info("Created coordination plan: %d parallel batches, %d sequential steps",
                   len(plan["parallel_batches"]), len(plan["sequential_steps"]))
        
        return plan

    def _route_agent_for_item(self, item: WorkItem, default_agent: str) -> Optional[str]:
        """Use org router to select an agent when configured."""
        if not self.org_router:
            return default_agent

        requested_tags = item.labels or [default_agent]
        trust_level = self.routing_config.get("trust_level", "high")
        data_sensitivity = self.routing_config.get("data_sensitivity", "internal")

        enabled_agents = [
            name for name in ["pm", "architect", "engineer", "ux", "reviewer"]
            if self.config.get(f"agents.{name}.enabled", True)
        ]

        candidates = []
        for name in enabled_agents:
            tags = list({name, *requested_tags})
            candidates.append(
                Candidate(
                    name=name,
                    capability_tags=tags,
                    trust_level=trust_level,
                    data_sensitivity=data_sensitivity,
                )
            )

        priority_label = self._priority_label(item.priority)
        chosen = self.org_router.route(
            candidates=candidates,
            requested_capability_tags=requested_tags,
            data_sensitivity=data_sensitivity,
            trust_level=trust_level,
            priority=priority_label,
            metadata={"work_item_id": item.id},
        )

        return chosen.name if chosen else None

    @staticmethod
    def _priority_label(priority: int) -> str:
        if priority >= 8:
            return "urgent"
        if priority >= 5:
            return "high"
        if priority <= 0:
            return "low"
        return "normal"
    
    async def execute_plan(
        self,
        plan: Dict[str, Any],
        agent_executor: Any,
        execute: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a coordination plan by running agents.
        
        Args:
            plan: Coordination plan from coordinate()
            agent_executor: AgentExecutor instance for running agents
            execute: If True, execute; if False, just return plan
            
        Returns:
            Execution results with status and outcomes
        """
        if not execute:
            return {"status": "planned", "plan": plan}
        
        logger.info("Executing coordination plan")
        
        results = {
            "status": "in_progress",
            "parallel_results": [],
            "sequential_results": [],
            "completed": 0,
            "failed": 0,
            "errors": []
        }
        
        # Execute parallel batches (convoys)
        for batch in plan.get("parallel_batches", []):
            convoy_id = batch["convoy_id"]
            agent = batch["agent"]
            items = batch["items"]
            
            logger.info(f"Executing convoy {convoy_id} with {len(items)} items")
            
            try:
                if self.convoy_manager:
                    convoy_result = await self.convoy_manager.execute_convoy(
                        convoy_id,
                        [(agent, item_id) for item_id in items]
                    )
                    results["parallel_results"].append({
                        "convoy_id": convoy_id,
                        "agent": agent,
                        "status": convoy_result.get("status"),
                        "completed": convoy_result.get("completed", 0),
                        "failed": convoy_result.get("failed", 0)
                    })
                    results["completed"] += convoy_result.get("completed", 0)
                    results["failed"] += convoy_result.get("failed", 0)
                else:
                    # Fall back to sequential execution
                    for item_id in items:
                        try:
                            result = await agent_executor.execute(agent, item_id)
                            if result.get("success"):
                                results["completed"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append({
                                    "item_id": item_id,
                                    "error": result.get("error")
                                })
                        except Exception as e:
                            results["failed"] += 1
                            results["errors"].append({
                                "item_id": item_id,
                                "error": str(e)
                            })
                            logger.exception(f"Failed to execute {agent} for {item_id}")
            except Exception as e:
                results["failed"] += len(items)
                results["errors"].append({
                    "convoy_id": convoy_id,
                    "error": str(e)
                })
                logger.exception(f"Convoy {convoy_id} failed")
        
        # Execute sequential steps
        for phase in plan.get("sequential_steps", []):
            agent = phase["agent"]
            item_id = phase["item_id"]
            
            logger.info(f"Executing {agent} for {item_id}")
            
            try:
                result = await agent_executor.execute(agent, item_id)
                results["sequential_results"].append({
                    "agent": agent,
                    "item_id": item_id,
                    "status": "success" if result.get("success") else "failed",
                    "error": result.get("error")
                })
                
                if result.get("success"):
                    results["completed"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "item_id": item_id,
                        "error": result.get("error")
                    })
            except Exception as e:
                results["failed"] += 1
                results["sequential_results"].append({
                    "agent": agent,
                    "item_id": item_id,
                    "status": "failed",
                    "error": str(e)
                })
                results["errors"].append({
                    "item_id": item_id,
                    "error": str(e)
                })
                logger.exception(f"Failed to execute {agent} for {item_id}")
        
        # Final status
        total = results["completed"] + results["failed"]
        if results["failed"] == 0:
            results["status"] = "completed"
        elif results["completed"] == 0:
            results["status"] = "failed"
        else:
            results["status"] = "partial"
        
        logger.info(f"Coordination complete: {results['completed']}/{total} succeeded")
        
        return results
    
    def _detect_agent(self, item: WorkItem) -> str:
        """Detect which agent should handle this work item"""
        # Check labels first
        for label in item.labels:
            if label in ["pm", "architect", "engineer", "ux", "reviewer"]:
                return label
        
        # Check title
        if "[" in item.title:
            start = item.title.find("[") + 1
            end = item.title.find("]")
            if start > 0 and end > start:
                agent = item.title[start:end]
                if agent in ["pm", "architect", "engineer", "ux", "reviewer"]:
                    return agent
        
        # Default to engineer
        return "engineer"
    
    def execute(self, issue_number: int) -> Dict[str, Any]:
        """
        Execute Captain coordination for an issue (required by BaseAgent interface)
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Dict with success status and output
        """
        try:
            # Run async coordination
            import asyncio
            result = asyncio.run(self.run(issue_number))
            
            return {
                "success": True,
                "output": result,
                "issue_number": issue_number
            }
        except Exception as e:
            logger.error(f"Captain execution failed for issue #{issue_number}: {e}")
            return {
                "success": False,
                "error": str(e),
                "issue_number": issue_number
            }


