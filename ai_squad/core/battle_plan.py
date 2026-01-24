"""
Battle Plan System

YAML-based workflow definitions for reusable multi-agent orchestration patterns.
"""
import logging
import inspect
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from .workstate import WorkItem, WorkStateManager, WorkStatus

logger = logging.getLogger(__name__)


class StepCondition(str, Enum):
    """Conditions for step execution"""

    ALWAYS = "always"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    MANUAL = "manual"


@dataclass
class BattlePlanPhase:
    """Single step in a battle plan workflow."""

    name: str
    agent: str
    action: str = "execute"
    description: str = ""
    condition: StepCondition = StepCondition.ALWAYS
    continue_on_error: bool = False
    timeout_minutes: int = 30
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    parallel_with: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BattlePlanPhase":
        data = data.copy()
        if "condition" in data:
            data["condition"] = StepCondition(data["condition"])
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "agent": self.agent,
            "action": self.action,
            "description": self.description,
            "condition": self.condition.value,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "depends_on": self.depends_on,
            "parallel_with": self.parallel_with,
            "timeout_minutes": self.timeout_minutes,
            "continue_on_error": self.continue_on_error,
        }


@dataclass
class BattlePlan:
    """A reusable battle plan that orchestrates multiple agents."""

    name: str
    description: str
    version: str = "1.0"
    phases: List[BattlePlanPhase] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BattlePlan":
        data = data.copy()
        # Support both "steps" (backward compatibility) and "phases" (new)
        if "steps" in data:
            data["phases"] = [BattlePlanPhase.from_dict(s) for s in data.pop("steps")]
        elif "phases" in data:
            data["phases"] = [BattlePlanPhase.from_dict(s) for s in data["phases"]]
        return cls(**data)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "BattlePlan":
        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, path: Path) -> "BattlePlan":
        content = path.read_text(encoding="utf-8")
        return cls.from_yaml(content)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [s.to_dict() for s in self.phases],
            "variables": self.variables,
            "labels": self.labels,
            "created_at": self.created_at,
        }

    def to_yaml(self) -> str:
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def save(self, path: Path) -> None:
        path.write_text(self.to_yaml(), encoding="utf-8")

    def get_step(self, name: str) -> Optional[BattlePlanPhase]:
        for step in self.phases:
            if step.name == name:
                return step
        return None

    def get_entry_steps(self) -> List[BattlePlanPhase]:
        return [s for s in self.phases if not s.depends_on]

    def get_parallel_groups(self) -> List[List[BattlePlanPhase]]:
        groups: List[List[BattlePlanPhase]] = []
        processed: set = set()

        for step in self.phases:
            if step.name in processed:
                continue

            if step.parallel_with:
                group = [step]
                for parallel_name in step.parallel_with:
                    parallel_step = self.get_step(parallel_name)
                    if parallel_step and parallel_step.name not in processed:
                        group.append(parallel_step)
                        processed.add(parallel_step.name)
                groups.append(group)
            else:
                groups.append([step])

            processed.add(step.name)

        return groups


class BattlePlanManager:
    """Manages battle plan definitions and execution."""

    STRATEGIES_DIR = "strategies"
    BUILTIN_STRATEGIES_DIR = Path(__file__).parent.parent / "templates" / "strategies"

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.squad_dir = self.workspace_root / ".squad"
        self.strategies_dir = self.squad_dir / self.STRATEGIES_DIR
        self._strategies: Dict[str, BattlePlan] = {}
        self._load_strategies()

    def _ensure_strategies_dir(self) -> None:
        self.strategies_dir.mkdir(parents=True, exist_ok=True)

    def _load_strategies(self) -> None:
        if self.BUILTIN_STRATEGIES_DIR.exists():
            for path in self.BUILTIN_STRATEGIES_DIR.glob("*.yaml"):
                try:
                    strategy = BattlePlan.from_file(path)
                    self._strategies[strategy.name] = strategy
                    logger.debug("Loaded built-in battle plan: %s", strategy.name)
                except Exception as exc:
                    logger.warning("Failed to load built-in battle plan %s: %s", path, exc)

        if self.strategies_dir.exists():
            for path in self.strategies_dir.glob("*.yaml"):
                try:
                    strategy = BattlePlan.from_file(path)
                    self._strategies[strategy.name] = strategy
                    logger.debug("Loaded workspace battle plan: %s", strategy.name)
                except Exception as exc:
                    logger.warning("Failed to load battle plan %s: %s", path, exc)

        logger.info("Loaded %d battle plans", len(self._strategies))

    def get_strategy(self, name: str) -> Optional[BattlePlan]:
        return self._strategies.get(name)

    def list_strategies(self, label: Optional[str] = None) -> List[BattlePlan]:
        strategies = list(self._strategies.values())
        if label:
            strategies = [s for s in strategies if label in s.labels]
        return sorted(strategies, key=lambda s: s.name)

    def create_strategy(
        self,
        name: str,
        description: str,
        phases: List[BattlePlanPhase],
        variables: Optional[Dict[str, Any]] = None,
        labels: Optional[List[str]] = None,
    ) -> BattlePlan:
        self._ensure_strategies_dir()

        strategy = BattlePlan(
            name=name,
            description=description,
            phases=phases,
            variables=variables or {},
            labels=labels or [],
        )

        path = self.strategies_dir / f"{name}.yaml"
        strategy.save(path)
        self._strategies[name] = strategy
        logger.info("Created battle plan: %s", name)
        return strategy

    def delete_strategy(self, name: str) -> bool:
        if name not in self._strategies:
            return False

        path = self.strategies_dir / f"{name}.yaml"
        if path.exists():
            path.unlink()

        del self._strategies[name]
        return True


@dataclass
class BattlePlanExecution:
    """Tracks execution of a battle plan instance."""

    id: str
    strategy_name: str
    issue_number: Optional[int]
    status: str = "pending"
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    work_items: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class BattlePlanExecutor:
    """Executes battle plans by coordinating agents."""

    def __init__(
        self,
        strategy_manager: BattlePlanManager,
        work_state_manager: WorkStateManager,
        agent_executor: Optional[Callable[[str, int], Dict[str, Any]]] = None,
    ):
        self.strategy_manager = strategy_manager
        self.work_state_manager = work_state_manager
        self.agent_executor = agent_executor
        self._executions: Dict[str, BattlePlanExecution] = {}

    def start_execution(
        self,
        strategy_name: str,
        issue_number: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Optional[BattlePlanExecution]:
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if not strategy:
            logger.error("Battle plan not found: %s", strategy_name)
            return None

        merged_vars = {**strategy.variables, **(variables or {})}

        import uuid

        execution = BattlePlanExecution(
            id=f"exec-{uuid.uuid4().hex[:8]}",
            strategy_name=strategy_name,
            issue_number=issue_number,
            variables=merged_vars,
            started_at=datetime.now().isoformat(),
        )

        for step in strategy.phases:
            work_item = self.work_state_manager.create_work_item(
                title=f"[{strategy_name}] {step.name}",
                description=step.description,
                issue_number=issue_number,
                labels=[strategy_name, step.agent, "strategy-step"],
            )
            execution.work_items.append(work_item.id)

        for i, step in enumerate(strategy.phases):
            if step.depends_on:
                for dep_name in step.depends_on:
                    dep_idx = next(
                        (j for j, s in enumerate(strategy.phases) if s.name == dep_name),
                        None,
                    )
                    if dep_idx is not None:
                        self.work_state_manager.add_dependency(
                            execution.work_items[i], execution.work_items[dep_idx]
                        )

        execution.status = "running"
        self._executions[execution.id] = execution

        logger.info("Started battle plan execution: %s (%s)", execution.id, strategy_name)
        return execution

    def get_execution(self, execution_id: str) -> Optional[BattlePlanExecution]:
        return self._executions.get(execution_id)

    def get_next_steps(self, execution_id: str) -> List[BattlePlanPhase]:
        execution = self.get_execution(execution_id)
        if not execution:
            return []

        strategy = self.strategy_manager.get_strategy(execution.strategy_name)
        if not strategy:
            return []

        ready_steps: List[BattlePlanPhase] = []
        for i, step in enumerate(strategy.phases):
            if step.name in execution.completed_steps:
                continue
            if step.name in execution.failed_steps:
                continue

            work_item = self.work_state_manager.get_work_item(execution.work_items[i])
            if work_item and work_item.status == WorkStatus.READY:
                ready_steps.append(step)

        return ready_steps

    def complete_step(
        self, execution_id: str, step_name: str, artifacts: Optional[List[str]] = None
    ) -> bool:
        execution = self.get_execution(execution_id)
        if not execution:
            return False

        strategy = self.strategy_manager.get_strategy(execution.strategy_name)
        if not strategy:
            return False

        step_idx = next((i for i, s in enumerate(strategy.phases) if s.name == step_name), None)
        if step_idx is None:
            return False

        work_item_id = execution.work_items[step_idx]
        self.work_state_manager.complete_work(work_item_id, artifacts)

        execution.completed_steps.append(step_name)

        if len(execution.completed_steps) == len(strategy.phases):
            execution.status = "completed"
            execution.completed_at = datetime.now().isoformat()
            logger.info("Battle plan execution completed: %s", execution_id)

        return True

    def fail_step(self, execution_id: str, step_name: str, error: str) -> bool:
        execution = self.get_execution(execution_id)
        if not execution:
            return False

        strategy = self.strategy_manager.get_strategy(execution.strategy_name)
        if not strategy:
            return False

        step_idx = next((i for i, s in enumerate(strategy.phases) if s.name == step_name), None)
        if step_idx is None:
            return False

        work_item_id = execution.work_items[step_idx]
        self.work_state_manager.transition_status(
            work_item_id, WorkStatus.FAILED, {"error": error}
        )

        execution.failed_steps.append(step_name)
        execution.error = error
        execution.status = "failed"

        logger.error("Battle plan step failed: %s/%s - %s", execution_id, step_name, error)
        return True

    async def execute_strategy(
        self, strategy_name: str, issue_number: int, variables: Optional[Dict[str, Any]] = None
    ) -> str:
        if not self.agent_executor:
            raise ValueError("BattlePlanExecutor requires agent_executor to be configured")

        execution = self.start_execution(strategy_name, issue_number, variables)
        if not execution:
            raise ValueError(f"Battle plan not found: {strategy_name}")

        logger.info("Executing battle plan %s for issue #%s", strategy_name, issue_number)

        strategy = self.strategy_manager.get_strategy(strategy_name)
        if not strategy:
            raise ValueError(f"Battle plan not found: {strategy_name}")

        while True:
            ready_steps = self.get_next_steps(execution.id)
            if not ready_steps:
                break

            for step in ready_steps:
                try:
                    result = await self._run_step(step, issue_number)
                    artifacts = result.get("artifacts") if isinstance(result, dict) else None
                    self.complete_step(execution.id, step.name, artifacts)
                except Exception as exc:
                    self.fail_step(execution.id, step.name, str(exc))
                    if not step.continue_on_error:
                        raise

        return execution.id

    async def _run_step(self, step: BattlePlanPhase, issue_number: int) -> Dict[str, Any]:
        if not self.agent_executor:
            raise ValueError("BattlePlanExecutor requires agent_executor to be configured")

        sig = inspect.signature(self.agent_executor)
        kwargs: Dict[str, Any] = {}
        if "issue_number" in sig.parameters:
            kwargs["issue_number"] = issue_number
        if "agent_type" in sig.parameters:
            kwargs["agent_type"] = step.agent
        if "action" in sig.parameters:
            kwargs["action"] = step.action
        if "step" in sig.parameters:
            kwargs["step"] = step.to_dict()

        return await self.agent_executor(**kwargs)  # type: ignore[arg-type]


