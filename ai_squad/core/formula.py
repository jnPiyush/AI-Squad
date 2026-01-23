"""
Formula System

YAML-based workflow definitions for reusable multi-agent orchestration patterns.
Inspired by Gastown's Formula system.
"""
import logging
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
    ALWAYS = "always"           # Always execute
    ON_SUCCESS = "on_success"   # Only if previous succeeded
    ON_FAILURE = "on_failure"   # Only if previous failed
    MANUAL = "manual"           # Requires manual trigger


@dataclass
class FormulaStep:
    """
    A single step in a formula workflow.
    """
    name: str
    agent: str                            # Agent type: pm, architect, engineer, ux, reviewer
    action: str = "execute"               # Action to perform (default: execute)
    description: str = ""
    condition: StepCondition = StepCondition.ALWAYS
    continue_on_error: bool = False       # Whether to continue if this step fails
    timeout_minutes: int = 30
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)  # Expected output artifacts
    depends_on: List[str] = field(default_factory=list)  # Step names this depends on
    parallel_with: List[str] = field(default_factory=list)  # Steps that can run in parallel
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormulaStep":
        """Create from dictionary"""
        data = data.copy()
        if "condition" in data:
            data["condition"] = StepCondition(data["condition"])
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
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
            "continue_on_error": self.continue_on_error
        }


@dataclass
class Formula:
    """
    A reusable workflow formula that orchestrates multiple agents.
    """
    name: str
    description: str
    version: str = "1.0"
    steps: List[FormulaStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    labels: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Formula":
        """Create from dictionary"""
        data = data.copy()
        if "steps" in data:
            data["steps"] = [
                FormulaStep.from_dict(s) for s in data["steps"]
            ]
        return cls(**data)
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "Formula":
        """Load formula from YAML string"""
        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, path: Path) -> "Formula":
        """Load formula from YAML file"""
        content = path.read_text(encoding="utf-8")
        return cls.from_yaml(content)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [s.to_dict() for s in self.steps],
            "variables": self.variables,
            "labels": self.labels,
            "created_at": self.created_at
        }
    
    def to_yaml(self) -> str:
        """Convert to YAML string"""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)
    
    def save(self, path: Path) -> None:
        """Save formula to YAML file"""
        path.write_text(self.to_yaml(), encoding="utf-8")
    
    def get_step(self, name: str) -> Optional[FormulaStep]:
        """Get a step by name"""
        for step in self.steps:
            if step.name == name:
                return step
        return None
    
    def get_entry_steps(self) -> List[FormulaStep]:
        """Get steps with no dependencies (entry points)"""
        return [s for s in self.steps if not s.depends_on]
    
    def get_parallel_groups(self) -> List[List[FormulaStep]]:
        """Get groups of steps that can run in parallel"""
        groups: List[List[FormulaStep]] = []
        processed: set = set()
        
        for step in self.steps:
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


class FormulaManager:
    """
    Manages formula definitions and execution.
    Stores formulas in .squad/formulas/ directory.
    """
    
    FORMULAS_DIR = "formulas"
    BUILTIN_FORMULAS_DIR = Path(__file__).parent.parent / "templates" / "formulas"
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize formula manager.
        
        Args:
            workspace_root: Root directory of the workspace (defaults to cwd)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.squad_dir = self.workspace_root / ".squad"
        self.formulas_dir = self.squad_dir / self.FORMULAS_DIR
        
        self._formulas: Dict[str, Formula] = {}
        self._load_formulas()
    
    def _ensure_formulas_dir(self) -> None:
        """Create formulas directory if it doesn't exist"""
        self.formulas_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_formulas(self) -> None:
        """Load all formulas from disk"""
        # Load built-in formulas
        if self.BUILTIN_FORMULAS_DIR.exists():
            for path in self.BUILTIN_FORMULAS_DIR.glob("*.yaml"):
                try:
                    formula = Formula.from_file(path)
                    self._formulas[formula.name] = formula
                    logger.debug("Loaded built-in formula: %s", formula.name)
                except Exception as e:
                    logger.warning("Failed to load built-in formula %s: %s", path, e)
        
        # Load workspace formulas (override built-ins)
        if self.formulas_dir.exists():
            for path in self.formulas_dir.glob("*.yaml"):
                try:
                    formula = Formula.from_file(path)
                    self._formulas[formula.name] = formula
                    logger.debug("Loaded workspace formula: %s", formula.name)
                except Exception as e:
                    logger.warning("Failed to load formula %s: %s", path, e)
        
        logger.info("Loaded %d formulas", len(self._formulas))
    
    def get_formula(self, name: str) -> Optional[Formula]:
        """Get a formula by name"""
        return self._formulas.get(name)
    
    def list_formulas(self, label: Optional[str] = None) -> List[Formula]:
        """List all available formulas"""
        formulas = list(self._formulas.values())
        
        if label:
            formulas = [f for f in formulas if label in f.labels]
        
        return sorted(formulas, key=lambda f: f.name)
    
    def create_formula(
        self,
        name: str,
        description: str,
        steps: List[FormulaStep],
        variables: Optional[Dict[str, Any]] = None,
        labels: Optional[List[str]] = None
    ) -> Formula:
        """Create and save a new formula"""
        self._ensure_formulas_dir()
        
        formula = Formula(
            name=name,
            description=description,
            steps=steps,
            variables=variables or {},
            labels=labels or []
        )
        
        # Save to file
        path = self.formulas_dir / f"{name}.yaml"
        formula.save(path)
        
        # Cache it
        self._formulas[name] = formula
        
        logger.info("Created formula: %s", name)
        return formula
    
    def delete_formula(self, name: str) -> bool:
        """Delete a formula"""
        if name not in self._formulas:
            return False
        
        path = self.formulas_dir / f"{name}.yaml"
        if path.exists():
            path.unlink()
        
        del self._formulas[name]
        return True


@dataclass
class FormulaExecution:
    """
    Tracks execution of a formula instance.
    """
    id: str
    formula_name: str
    issue_number: Optional[int]
    status: str = "pending"  # pending, running, completed, failed
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    work_items: List[str] = field(default_factory=list)  # Work item IDs created
    variables: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class FormulaExecutor:
    """
    Executes formula workflows by coordinating agents.
    """
    
    def __init__(
        self,
        formula_manager: FormulaManager,
        work_state_manager: WorkStateManager,
        agent_executor: Optional[Callable[[str, int], Dict[str, Any]]] = None
    ):
        """
        Initialize formula executor.
        
        Args:
            formula_manager: Formula manager instance
            work_state_manager: Work state manager instance
            agent_executor: Optional function to execute agents (agent_type, issue_number) -> result
        """
        self.formula_manager = formula_manager
        self.work_state_manager = work_state_manager
        self.agent_executor = agent_executor
        self._executions: Dict[str, FormulaExecution] = {}
    
    def start_execution(
        self,
        formula_name: str,
        issue_number: Optional[int] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Optional[FormulaExecution]:
        """
        Start executing a formula.
        
        Args:
            formula_name: Name of the formula to execute
            issue_number: Optional GitHub issue number
            variables: Variable overrides for the formula
            
        Returns:
            FormulaExecution instance or None if formula not found
        """
        formula = self.formula_manager.get_formula(formula_name)
        if not formula:
            logger.error("Formula not found: %s", formula_name)
            return None
        
        # Merge variables
        merged_vars = {**formula.variables, **(variables or {})}
        
        # Create execution
        import uuid
        execution = FormulaExecution(
            id=f"exec-{uuid.uuid4().hex[:8]}",
            formula_name=formula_name,
            issue_number=issue_number,
            variables=merged_vars,
            started_at=datetime.now().isoformat()
        )
        
        # Create work items for each step
        for step in formula.steps:
            work_item = self.work_state_manager.create_work_item(
                title=f"[{formula_name}] {step.name}",
                description=step.description,
                issue_number=issue_number,
                labels=[formula_name, step.agent, "formula-step"]
            )
            execution.work_items.append(work_item.id)
        
        # Set up dependencies between work items
        for i, step in enumerate(formula.steps):
            if step.depends_on:
                for dep_name in step.depends_on:
                    dep_idx = next(
                        (j for j, s in enumerate(formula.steps) if s.name == dep_name),
                        None
                    )
                    if dep_idx is not None:
                        self.work_state_manager.add_dependency(
                            execution.work_items[i],
                            execution.work_items[dep_idx]
                        )
        
        execution.status = "running"
        self._executions[execution.id] = execution
        
        logger.info(
            "Started formula execution: %s (%s)",
            execution.id, formula_name
        )
        return execution
    
    def get_execution(self, execution_id: str) -> Optional[FormulaExecution]:
        """Get an execution by ID"""
        return self._executions.get(execution_id)
    
    def get_next_steps(self, execution_id: str) -> List[FormulaStep]:
        """
        Get the next steps that can be executed.
        
        Returns steps whose dependencies are satisfied.
        """
        execution = self.get_execution(execution_id)
        if not execution:
            return []
        
        formula = self.formula_manager.get_formula(execution.formula_name)
        if not formula:
            return []
        
        ready_steps = []
        for i, step in enumerate(formula.steps):
            if step.name in execution.completed_steps:
                continue
            if step.name in execution.failed_steps:
                continue
            
            # Check work item status
            work_item = self.work_state_manager.get_work_item(
                execution.work_items[i]
            )
            if work_item and work_item.status == WorkStatus.READY:
                ready_steps.append(step)
        
        return ready_steps
    
    def complete_step(
        self,
        execution_id: str,
        step_name: str,
        artifacts: Optional[List[str]] = None
    ) -> bool:
        """Mark a step as completed"""
        execution = self.get_execution(execution_id)
        if not execution:
            return False
        
        formula = self.formula_manager.get_formula(execution.formula_name)
        if not formula:
            return False
        
        # Find the work item for this step
        step_idx = next(
            (i for i, s in enumerate(formula.steps) if s.name == step_name),
            None
        )
        if step_idx is None:
            return False
        
        work_item_id = execution.work_items[step_idx]
        self.work_state_manager.complete_work(work_item_id, artifacts)
        
        execution.completed_steps.append(step_name)
        
        # Check if all steps are complete
        if len(execution.completed_steps) == len(formula.steps):
            execution.status = "completed"
            execution.completed_at = datetime.now().isoformat()
            logger.info("Formula execution completed: %s", execution_id)
        
        return True
    
    def fail_step(
        self,
        execution_id: str,
        step_name: str,
        error: str
    ) -> bool:
        """Mark a step as failed"""
        execution = self.get_execution(execution_id)
        if not execution:
            return False
        
        formula = self.formula_manager.get_formula(execution.formula_name)
        if not formula:
            return False
        
        # Find the work item for this step
        step_idx = next(
            (i for i, s in enumerate(formula.steps) if s.name == step_name),
            None
        )
        if step_idx is None:
            return False
        
        work_item_id = execution.work_items[step_idx]
        self.work_state_manager.transition_status(
            work_item_id,
            WorkStatus.FAILED,
            {"error": error}
        )
        
        execution.failed_steps.append(step_name)
        execution.error = error
        execution.status = "failed"
        
        logger.error(
            "Formula step failed: %s/%s - %s",
            execution_id, step_name, error
        )
        return True
    
    async def execute_formula(
        self,
        formula_name: str,
        issue_number: int,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a formula workflow by running agents through steps.
        
        Args:
            formula_name: Name of the formula to execute
            issue_number: GitHub issue number
            variables: Optional variable overrides
            
        Returns:
            Execution ID for tracking
            
        Raises:
            ValueError: If formula not found or agent_executor not configured
        """
        if not self.agent_executor:
            raise ValueError("FormulaExecutor requires agent_executor to be configured")
        
        # Start execution
        execution = self.start_execution(formula_name, issue_number, variables)
        if not execution:
            raise ValueError(f"Formula not found: {formula_name}")
        
        logger.info(f"Executing formula {formula_name} for issue #{issue_number}")
        
        formula = self.formula_manager.get_formula(formula_name)
        if not formula:
            raise ValueError(f"Formula not found: {formula_name}")
        
        try:
            # Execute steps in order, respecting dependencies
            for i, step in enumerate(formula.steps):
                # Wait for dependencies
                if step.depends_on:
                    logger.info(f"Step {step.name} waiting for dependencies: {step.depends_on}")
                
                # Check if step should run based on condition
                if step.condition and step.condition != StepCondition.ALWAYS:
                    prev_success = i > 0 and formula.steps[i-1].name in execution.completed_steps
                    if step.condition == StepCondition.ON_SUCCESS and not prev_success:
                        logger.info(f"Skipping step {step.name} - condition not met")
                        continue
                    elif step.condition == StepCondition.ON_FAILURE and prev_success:
                        logger.info(f"Skipping step {step.name} - condition not met")
                        continue
                
                # Execute the agent
                logger.info(f"Executing step: {step.name} with agent: {step.agent}")
                try:
                    result = self.agent_executor(step.agent, issue_number)
                    
                    if result.get('success'):
                        artifacts = result.get('artifacts', [])
                        self.complete_step(execution.id, step.name, artifacts)
                        logger.info(f"Step {step.name} completed successfully")
                    else:
                        error = result.get('error', 'Unknown error')
                        self.fail_step(execution.id, step.name, error)
                        logger.error(f"Step {step.name} failed: {error}")
                        
                        if not step.continue_on_error:
                            execution.status = "failed"
                            raise RuntimeError(f"Formula execution failed at step {step.name}: {error}")
                
                except Exception as e:
                    error_msg = str(e)
                    logger.exception(f"Exception executing step {step.name}")
                    self.fail_step(execution.id, step.name, error_msg)
                    
                    if not step.continue_on_error:
                        execution.status = "failed"
                        raise
            
            # All steps completed
            execution.status = "completed"
            execution.completed_at = datetime.now().isoformat()
            logger.info(f"Formula execution {execution.id} completed successfully")
            
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            logger.error(f"Formula execution {execution.id} failed: {e}")
            raise
        
        return execution.id


# Built-in Formula Templates

FEATURE_FORMULA = Formula(
    name="feature",
    description="Standard feature development workflow",
    labels=["standard", "feature"],
    steps=[
        FormulaStep(
            name="requirements",
            agent="pm",
            action="create_prd",
            description="Create Product Requirements Document",
            outputs=["docs/prd/PRD-{issue}.md"]
        ),
        FormulaStep(
            name="architecture",
            agent="architect",
            action="create_spec",
            description="Create Technical Specification and ADR",
            depends_on=["requirements"],
            outputs=["docs/specs/SPEC-{issue}.md", "docs/adr/ADR-{issue}.md"]
        ),
        FormulaStep(
            name="ux_design",
            agent="ux",
            action="create_design",
            description="Create UX Design and Prototype",
            depends_on=["requirements"],
            parallel_with=["architecture"],
            outputs=["docs/ux/UX-{issue}.md", "docs/ux/prototypes/prototype-{issue}.html"]
        ),
        FormulaStep(
            name="implementation",
            agent="engineer",
            action="implement",
            description="Implement the feature with tests",
            depends_on=["architecture", "ux_design"],
            outputs=[]
        ),
        FormulaStep(
            name="review",
            agent="reviewer",
            action="review",
            description="Code review and quality check",
            depends_on=["implementation"],
            outputs=["docs/reviews/REVIEW-{issue}.md"]
        )
    ]
)

BUGFIX_FORMULA = Formula(
    name="bugfix",
    description="Bug fix workflow with analysis and testing",
    labels=["standard", "bugfix"],
    steps=[
        FormulaStep(
            name="analysis",
            agent="engineer",
            action="analyze_bug",
            description="Analyze the bug and identify root cause"
        ),
        FormulaStep(
            name="fix",
            agent="engineer",
            action="implement_fix",
            description="Implement the bug fix with regression tests",
            depends_on=["analysis"]
        ),
        FormulaStep(
            name="review",
            agent="reviewer",
            action="review",
            description="Review the fix for correctness and side effects",
            depends_on=["fix"]
        )
    ]
)

TECH_DEBT_FORMULA = Formula(
    name="tech-debt",
    description="Technical debt resolution workflow",
    labels=["standard", "tech-debt", "refactoring"],
    steps=[
        FormulaStep(
            name="assessment",
            agent="architect",
            action="assess_debt",
            description="Assess the technical debt and create remediation plan"
        ),
        FormulaStep(
            name="refactor",
            agent="engineer",
            action="refactor",
            description="Refactor code according to plan",
            depends_on=["assessment"]
        ),
        FormulaStep(
            name="verify",
            agent="reviewer",
            action="review",
            description="Verify refactoring maintains functionality and improves quality",
            depends_on=["refactor"]
        )
    ]
)
