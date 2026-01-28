"""
Convoy System

Parallel work execution batching for AI-Squad.
Convoys allow multiple agents to work simultaneously on independent tasks.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .workstate import WorkStateManager, WorkStatus
from .resource_monitor import get_global_monitor
from .metrics import get_global_collector, ConvoyMetrics, AgentMetrics, ResourceMetrics

logger = logging.getLogger(__name__)


class ConvoyStatus(str, Enum):
    """Convoy execution status"""
    PENDING = "pending"       # Not started
    RUNNING = "running"       # Agents working
    COMPLETED = "completed"   # All work done
    PARTIAL = "partial"       # Some work failed
    FAILED = "failed"         # Critical failure
    CANCELLED = "cancelled"   # User cancelled


@dataclass
class ConvoyMember:
    """
    A member of a convoy (agent + work assignment).
    """
    agent_type: str
    work_item_id: str
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_type": self.agent_type,
            "work_item_id": self.work_item_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error
        }


@dataclass
class Convoy:
    """
    A convoy groups multiple work items for parallel execution.
    
    A batch of independent tasks that can be executed simultaneously
    by different agents.
    """
    id: str
    name: str
    description: str = ""
    status: ConvoyStatus = ConvoyStatus.PENDING
    members: List[ConvoyMember] = field(default_factory=list)
    
    # Execution settings
    max_parallel: int = 5            # Max concurrent agents
    timeout_minutes: int = 60        # Overall timeout
    stop_on_first_failure: bool = False  # Fail fast mode
    
    # Auto-tuning settings
    enable_auto_tuning: bool = True   # Enable resource-based auto-tuning
    baseline_parallel: int = 5         # Minimum parallelism (safety floor)
    cpu_threshold: float = 80.0        # CPU threshold for throttling (%)
    memory_threshold: float = 85.0     # Memory threshold for throttling (%)
    
    # Metadata
    issue_number: Optional[int] = None
    plan_execution_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "members": [m.to_dict() for m in self.members],
            "max_parallel": self.max_parallel,
            "timeout_minutes": self.timeout_minutes,
            "stop_on_first_failure": self.stop_on_first_failure,
            "issue_number": self.issue_number,
            "plan_execution_id": self.plan_execution_id,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": self.results,
            "errors": self.errors
        }
    
    def add_member(
        self,
        agent_type: str,
        work_item_id: str
    ) -> ConvoyMember:
        """Add a member to the convoy"""
        member = ConvoyMember(
            agent_type=agent_type,
            work_item_id=work_item_id
        )
        self.members.append(member)
        return member
    
    def get_member(self, work_item_id: str) -> Optional[ConvoyMember]:
        """Get a member by work item ID"""
        for member in self.members:
            if member.work_item_id == work_item_id:
                return member
        return None
    
    def is_complete(self) -> bool:
        """Check if all members have completed"""
        return all(
            m.status in ("completed", "failed", "skipped")
            for m in self.members
        )
    
    def get_progress(self) -> Dict[str, Any]:
        """Get convoy progress"""
        total = len(self.members)
        completed = len([m for m in self.members if m.status == "completed"])
        failed = len([m for m in self.members if m.status == "failed"])
        running = len([m for m in self.members if m.status == "running"])
        pending = len([m for m in self.members if m.status == "pending"])
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "progress_percent": (completed + failed) * 100 // total if total > 0 else 0
        }


# Type alias for agent executor function
AgentExecutorFunc = Callable[
    [str, str, Optional[Dict[str, Any]]],
    Coroutine[Any, Any, str]
]


class ConvoyManager:
    """
    Manages convoy creation and execution.
    """
    
    def __init__(
        self,
        work_state_manager: Any,
        agent_executor: Optional[AgentExecutorFunc] = None,
        report_manager: Optional[Any] = None
    ):
        """
        Initialize convoy manager.
        
        Args:
            work_state_manager: Work state manager instance
            agent_executor: Function to execute agent work
                           Signature: async (agent_type, work_item_id, context) -> result
        """
        # Accept either a manager instance or a workspace path
        if isinstance(work_state_manager, WorkStateManager):
            self.work_state_manager = work_state_manager
        else:
            from pathlib import Path
            self.work_state_manager = WorkStateManager(Path(work_state_manager))
        self.agent_executor = agent_executor
        self.report_manager = report_manager
        self._convoys: Dict[str, Convoy] = {}
    
    def create_convoy(
        self,
        name: str,
        work_items: List[Dict[str, str]],
        description: str = "",
        max_parallel: int = 5,
        timeout_minutes: int = 60,
        stop_on_first_failure: bool = False,
        enable_auto_tuning: bool = True,
        baseline_parallel: int = 5,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        issue_number: Optional[int] = None,
        plan_execution_id: Optional[str] = None
    ) -> Convoy:
        """
        Create a new convoy.
        
        Args:
            name: Convoy name
            work_items: List of dicts with 'agent_type' and 'work_item_id'
            description: Convoy description
            max_parallel: Maximum concurrent agents
            timeout_minutes: Timeout in minutes
            stop_on_first_failure: Whether to stop on first failure
            enable_auto_tuning: Enable resource-based auto-tuning
            baseline_parallel: Minimum safe parallelism (safety floor)
            cpu_threshold: CPU threshold for throttling (%)
            memory_threshold: Memory threshold for throttling (%)
            issue_number: Optional GitHub issue number
            plan_execution_id: Optional battle plan execution ID
            
        Returns:
            Created Convoy instance
        """
        convoy_id = f"convoy-{uuid.uuid4().hex[:8]}"
        
        convoy = Convoy(
            id=convoy_id,
            name=name,
            description=description,
            max_parallel=max_parallel,
            timeout_minutes=timeout_minutes,
            stop_on_first_failure=stop_on_first_failure,
            enable_auto_tuning=enable_auto_tuning,
            baseline_parallel=baseline_parallel,
            cpu_threshold=cpu_threshold,
            memory_threshold=memory_threshold,
            issue_number=issue_number,
            plan_execution_id=plan_execution_id
        )
        
        # Add members
        for item in work_items:
            convoy.add_member(
                agent_type=item["agent_type"],
                work_item_id=item["work_item_id"]
            )
            
            # Associate work item with convoy
            self.work_state_manager.set_convoy(
                item["work_item_id"],
                convoy_id
            )
        
        self._convoys[convoy_id] = convoy
        
        logger.info(
            "Created convoy %s with %d members",
            convoy_id, len(work_items)
        )
        return convoy
    
    def get_convoy(self, convoy_id: str) -> Optional[Convoy]:
        """Get a convoy by ID"""
        return self._convoys.get(convoy_id)
    
    def list_convoys(
        self,
        status: Optional[ConvoyStatus] = None,
        issue_number: Optional[int] = None
    ) -> List[Convoy]:
        """List convoys with optional filters"""
        convoys = list(self._convoys.values())
        
        if status:
            convoys = [c for c in convoys if c.status == status]
        if issue_number:
            convoys = [c for c in convoys if c.issue_number == issue_number]
        
        return sorted(convoys, key=lambda c: c.created_at, reverse=True)
    
    async def execute_convoy(
        self,
        convoy_id: str,
        tasks: Optional[List[tuple]] = None,
        context: Optional[Dict[str, Any]] = None,
        max_parallel: Optional[int] = None
    ) -> Any:
        """
        Execute a convoy (run all members in parallel).
        
        Supports two modes:
        - Legacy: run an existing Convoy object by ID
        - Direct: run ad-hoc tasks list [(agent_type, issue_number), ...]
        """
        if tasks is not None:
            if not self.agent_executor:
                raise ValueError("No agent executor configured")

            errors: List[str] = []
            results: List[Any] = []
            semaphore = asyncio.Semaphore(max_parallel or 5)

            async def _run_task(agent: str, issue: Any) -> None:
                async with semaphore:
                    try:
                        try:
                            res = await self.agent_executor(agent, issue, context)
                        except TypeError:
                            res = await self.agent_executor(agent, issue)
                        results.append({"agent": agent, "issue": issue, "result": res})
                    except (RuntimeError, ValueError, TypeError) as exc:
                        errors.append(f"{agent}-{issue}: {exc}")

            await asyncio.gather(*[_run_task(agent, issue) for agent, issue in tasks])

            completed = len(results)
            failed = len(errors)
            result_payload = {
                "convoy_id": convoy_id,
                "completed": completed,
                "failed": failed,
                "errors": errors,
                "results": results,
            }
            if self.report_manager:
                try:
                    self.report_manager.write_direct_report(convoy_id, result_payload)
                except (OSError, ValueError, TypeError) as exc:
                    logger.warning("Failed to write direct report: %s", exc)
            return result_payload

        # Legacy convoy execution path
        convoy = self.get_convoy(convoy_id)
        if not convoy:
            raise ValueError(f"Convoy not found: {convoy_id}")
        
        if not self.agent_executor:
            raise ValueError("No agent executor configured")
        
        logger.info("Executing convoy %s (%s)", convoy_id, convoy.name)
        
        convoy.status = ConvoyStatus.RUNNING
        convoy.started_at = datetime.now().isoformat()
        
        # Initialize metrics collection
        metrics_collector = get_global_collector()
        convoy_metrics = ConvoyMetrics(
            convoy_id=convoy_id,
            convoy_name=convoy.name,
            started_at=datetime.now().timestamp(),
            total_members=len(convoy.members)
        )
        
        # Determine initial parallelism
        if convoy.enable_auto_tuning:
            # Get resource monitor
            monitor = get_global_monitor(auto_sample=True, sample_interval=5.0)
            
            # Calculate optimal parallelism based on current resources
            optimal_parallel = monitor.calculate_optimal_parallelism(
                max_parallel=convoy.max_parallel,
                baseline=convoy.baseline_parallel
            )
            
            convoy_metrics.initial_parallelism = optimal_parallel
            convoy_metrics.max_parallelism_used = optimal_parallel
            
            logger.info(
                "Auto-tuning enabled: using %d parallel workers (max=%d, baseline=%d)",
                optimal_parallel, convoy.max_parallel, convoy.baseline_parallel
            )
        else:
            optimal_parallel = convoy.max_parallel
            convoy_metrics.initial_parallelism = optimal_parallel
            convoy_metrics.max_parallelism_used = optimal_parallel
            logger.info("Using fixed parallelism: %d workers", optimal_parallel)
        
        # Record convoy start
        metrics_collector.record_convoy_start(convoy_metrics)
        
        # Create semaphore for parallel limit
        semaphore = asyncio.Semaphore(optimal_parallel)
        
        async def execute_member(member: ConvoyMember) -> None:
            """Execute a single member with semaphore control and adaptive throttling"""
            async with semaphore:
                try:
                    # Dynamic throttling check (if auto-tuning enabled)
                    if convoy.enable_auto_tuning:
                        monitor = get_global_monitor()
                        
                        # Check if system is under load
                        if monitor.should_throttle(
                            cpu_threshold=convoy.cpu_threshold,
                            memory_threshold=convoy.memory_threshold
                        ):
                            throttle_factor = monitor.get_throttle_factor(
                                cpu_threshold=convoy.cpu_threshold,
                                memory_threshold=convoy.memory_threshold
                            )
                            
                            # Add delay based on throttle factor
                            # 0.0 (full throttle) = 5s delay, 1.0 (no throttle) = 0s delay
                            delay = (1.0 - throttle_factor) * 5.0
                            
                            if delay > 0.1:
                                logger.warning(
                                    "System under load (throttle=%.2f), delaying %s by %.1fs",
                                    throttle_factor, member.work_item_id, delay
                                )
                                await asyncio.sleep(delay)
                    
                    member.status = "running"
                    member.started_at = datetime.now().isoformat()
                    
                    # Update work item status
                    self.work_state_manager.transition_status(
                        member.work_item_id,
                        WorkStatus.IN_PROGRESS
                    )
                    
                    # Execute the agent
                    result = await self.agent_executor(
                        member.agent_type,
                        member.work_item_id,
                        context
                    )
                    
                    member.status = "completed"
                    member.result = result
                    member.completed_at = datetime.now().isoformat()
                    
                    # Update work item
                    self.work_state_manager.transition_status(
                        member.work_item_id,
                        WorkStatus.DONE
                    )
                    
                    logger.info(
                        "Convoy member completed: %s (%s)",
                        member.work_item_id, member.agent_type
                    )
                    
                except (RuntimeError, ValueError, TypeError) as e:
                    member.status = "failed"
                    member.error = str(e)
                    member.completed_at = datetime.now().isoformat()
                    
                    # Update work item
                    self.work_state_manager.transition_status(
                        member.work_item_id,
                        WorkStatus.FAILED,
                        {"error": str(e)}
                    )
                    
                    convoy.errors.append(
                        f"{member.agent_type}/{member.work_item_id}: {e}"
                    )
                    
                    logger.error(
                        "Convoy member failed: %s - %s",
                        member.work_item_id, e
                    )
                    
                    if convoy.stop_on_first_failure:
                        raise
        
        try:
            # Create timeout for entire convoy
            timeout = convoy.timeout_minutes * 60
            
            # Execute all members in parallel
            tasks_list = [
                asyncio.create_task(execute_member(member))
                for member in convoy.members
            ]
            
            await asyncio.wait_for(
                asyncio.gather(*tasks_list, return_exceptions=True),
                timeout=timeout
            )
            
        except asyncio.TimeoutError:
            convoy.errors.append(
                f"Convoy timed out after {convoy.timeout_minutes} minutes"
            )
            convoy.status = ConvoyStatus.FAILED
            
        except (RuntimeError, ValueError, TypeError) as e:
            convoy.errors.append(f"Convoy execution error: {e}")
            convoy.status = ConvoyStatus.FAILED
        
        # Determine final status
        convoy.completed_at = datetime.now().isoformat()
        
        if convoy.status != ConvoyStatus.FAILED:
            progress = convoy.get_progress()
            if progress["failed"] == 0:
                convoy.status = ConvoyStatus.COMPLETED
            elif progress["completed"] > 0:
                convoy.status = ConvoyStatus.PARTIAL
            else:
                convoy.status = ConvoyStatus.FAILED
        
        # Update convoy metrics
        convoy_metrics.completed_members = progress["completed"]
        convoy_metrics.failed_members = progress["failed"]
        convoy_metrics.status = convoy.status.value
        
        # Get final resource usage
        if convoy.enable_auto_tuning:
            monitor = get_global_monitor()
            current_metrics = monitor.get_current_metrics()
            convoy_metrics.peak_cpu_percent = max(
                convoy_metrics.peak_cpu_percent,
                current_metrics.cpu_percent
            )
            convoy_metrics.peak_memory_percent = max(
                convoy_metrics.peak_memory_percent,
                current_metrics.memory_percent
            )
        
        # Mark metrics as complete
        convoy_metrics.mark_complete()
        metrics_collector.record_convoy_complete(convoy_metrics)
        
        # Collect results
        for member in convoy.members:
            if member.result:
                convoy.results[member.work_item_id] = member.result
        
        logger.info(
            "Convoy %s finished with status %s (duration=%.2fs, completed=%d/%d)",
            convoy_id, convoy.status.value, convoy_metrics.duration_seconds or 0,
            convoy_metrics.completed_members, convoy_metrics.total_members
        )

        if self.report_manager:
            try:
                self.report_manager.write_convoy_report(convoy)
            except (OSError, ValueError, TypeError) as exc:
                logger.warning("Failed to write convoy report: %s", exc)
        
        return convoy
    
    async def cancel_convoy(self, convoy_id: str) -> bool:
        """
        Cancel a running convoy.
        
        Args:
            convoy_id: Convoy ID
            
        Returns:
            True if cancelled successfully
        """
        convoy = self.get_convoy(convoy_id)
        if not convoy:
            return False
        
        if convoy.status not in (ConvoyStatus.PENDING, ConvoyStatus.RUNNING):
            return False
        
        convoy.status = ConvoyStatus.CANCELLED
        convoy.completed_at = datetime.now().isoformat()
        
        # Update pending work items
        for member in convoy.members:
            if member.status == "pending":
                member.status = "skipped"
                self.work_state_manager.transition_status(
                    member.work_item_id,
                    WorkStatus.READY  # Return to ready state
                )
        
        logger.info("Convoy %s cancelled", convoy_id)
        return True
    
    def get_convoy_summary(self, convoy_id: str) -> Optional[str]:
        """
        Get a human-readable summary of convoy status.
        
        Args:
            convoy_id: Convoy ID
            
        Returns:
            Summary string or None if not found
        """
        convoy = self.get_convoy(convoy_id)
        if not convoy:
            return None
        
        progress = convoy.get_progress()
        
        summary = f"""
## Convoy: {convoy.name}
**ID**: {convoy.id}
**Status**: {convoy.status.value}

### Progress
- Total Members: {progress['total']}
- Completed: {progress['completed']}
- Running: {progress['running']}
- Pending: {progress['pending']}
- Failed: {progress['failed']}
- Progress: {progress['progress_percent']}%

### Members
"""
        for member in convoy.members:
            status_label = {
                "pending": "PENDING",
                "running": "RUNNING",
                "completed": "COMPLETED",
                "failed": "FAILED",
                "skipped": "SKIPPED"
            }.get(member.status, "UNKNOWN")
            
            summary += f"- {status_label} [{member.agent_type}] {member.work_item_id}\n"
            if member.error:
                summary += f"  - Error: {member.error}\n"
        
        if convoy.errors:
            summary += "\n### Errors\n"
            for error in convoy.errors:
                summary += f"- {error}\n"
        
        return summary


class ConvoyBuilder:
    """
    Builder pattern for creating convoys with fluent API.
    """
    
    def __init__(
        self,
        convoy_manager: ConvoyManager,
        work_state_manager: WorkStateManager
    ):
        self.convoy_manager = convoy_manager
        self.work_state_manager = work_state_manager
        
        # Builder state
        self._name: str = ""
        self._description: str = ""
        self._work_items: List[Dict[str, str]] = []
        self._max_parallel: int = 5
        self._timeout_minutes: int = 60
        self._stop_on_first_failure: bool = False
        self._issue_number: Optional[int] = None
        self._plan_execution_id: Optional[str] = None
    
    def name(self, name: str) -> "ConvoyBuilder":
        """Set convoy name"""
        self._name = name
        return self
    
    def description(self, description: str) -> "ConvoyBuilder":
        """Set convoy description"""
        self._description = description
        return self
    
    def add_work(
        self,
        agent_type: str,
        title: str,
        description: str = "",
        issue_number: Optional[int] = None
    ) -> "ConvoyBuilder":
        """Add a new work item to the convoy"""
        work_item = self.work_state_manager.create_work_item(
            title=f"[{agent_type}] {title}",
            description=description,
            issue_number=issue_number or self._issue_number,
            labels=[agent_type, "convoy"]
        )
        
        self._work_items.append({
            "agent_type": agent_type,
            "work_item_id": work_item.id
        })
        return self
    
    def add_existing_work(
        self,
        agent_type: str,
        work_item_id: str
    ) -> "ConvoyBuilder":
        """Add an existing work item to the convoy"""
        self._work_items.append({
            "agent_type": agent_type,
            "work_item_id": work_item_id
        })
        return self
    
    def max_parallel(self, max_parallel: int) -> "ConvoyBuilder":
        """Set max parallel workers"""
        self._max_parallel = max_parallel
        return self
    
    def timeout(self, minutes: int) -> "ConvoyBuilder":
        """Set timeout in minutes"""
        self._timeout_minutes = minutes
        return self
    
    def fail_fast(self, enabled: bool = True) -> "ConvoyBuilder":
        """Enable/disable fail fast mode"""
        self._stop_on_first_failure = enabled
        return self
    
    def for_issue(self, issue_number: int) -> "ConvoyBuilder":
        """Associate with a GitHub issue"""
        self._issue_number = issue_number
        return self
    
    def for_plan(self, execution_id: str) -> "ConvoyBuilder":
        """Associate with a battle plan execution"""
        self._plan_execution_id = execution_id
        return self
    
    def build(self) -> Convoy:
        """Build the convoy"""
        if not self._name:
            self._name = f"Convoy {datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        return self.convoy_manager.create_convoy(
            name=self._name,
            work_items=self._work_items,
            description=self._description,
            max_parallel=self._max_parallel,
            timeout_minutes=self._timeout_minutes,
            stop_on_first_failure=self._stop_on_first_failure,
            issue_number=self._issue_number,
            plan_execution_id=self._plan_execution_id
        )

