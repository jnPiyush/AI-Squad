"""
Work State Management

Persistent work state tracking with Squad Hooks and Work Items.
Work items survive agent crashes and restarts, enabling reliable multi-agent workflows.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, ContextManager

from .hooks import HookManager

# Cross-platform file locking for safe persistence
try:  # POSIX
    import fcntl  # type: ignore
except ImportError:  # Windows
    fcntl = None
    import msvcrt  # type: ignore
else:
    msvcrt = None

logger = logging.getLogger(__name__)


class WorkStatus(str, Enum):
    """Work item status states"""
    BACKLOG = "backlog"          # Not started
    READY = "ready"              # Prerequisites met, can be started
    IN_PROGRESS = "in_progress"  # Agent working on it
    HOOKED = "hooked"            # Attached to an agent's "hook"
    BLOCKED = "blocked"          # Waiting on dependency
    IN_REVIEW = "in_review"      # Under review
    DONE = "done"                # Completed
    FAILED = "failed"            # Failed, needs attention


@dataclass
class WorkItem:
    """
    A unit of work that can be assigned to agents.
    Core AI-Squad Work Item concept.
    """
    id: str
    title: str
    description: str = ""
    status: WorkStatus = WorkStatus.BACKLOG
    issue_number: Optional[int] = None
    agent_assignee: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Context preservation for agent restarts
    context: Dict[str, Any] = field(default_factory=dict)

    # Arbitrary metadata for orchestration
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Related artifacts
    artifacts: List[str] = field(default_factory=list)
    
    # Dependencies (other work item IDs)
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    
    # Convoy membership
    convoy_id: Optional[str] = None
    
    # Metadata
    labels: List[str] = field(default_factory=list)
    priority: int = 0  # Higher = more important

    @property
    def assigned_to(self) -> Optional[str]:
        """Alias for agent assignment (compatibility with tests)."""
        return self.agent_assignee

    @assigned_to.setter
    def assigned_to(self, agent: Optional[str]) -> None:
        self.agent_assignee = agent
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkItem":
        """Create from dictionary"""
        data = data.copy()
        if "status" in data:
            data["status"] = WorkStatus(data["status"])
        return cls(**data)
    
    def update_status(self, new_status: WorkStatus) -> None:
        """Update status with timestamp"""
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
    
    def assign_to(self, agent: str) -> None:
        """Assign work item to an agent"""
        self.agent_assignee = agent
        self.update_status(WorkStatus.HOOKED)
    
    def unassign(self) -> None:
        """Remove agent assignment"""
        self.agent_assignee = None
        if self.status == WorkStatus.HOOKED:
            self.update_status(WorkStatus.READY)
    
    def add_artifact(self, path: str) -> None:
        """Add an artifact (output file) to this work item"""
        if path not in self.artifacts:
            self.artifacts.append(path)
            self.updated_at = datetime.now().isoformat()
    
    def save_context(self, context: Dict[str, Any]) -> None:
        """Save agent context for later resumption"""
        self.context.update(context)
        self.updated_at = datetime.now().isoformat()
    
    def is_ready(self) -> bool:
        """Check if all dependencies are satisfied"""
        # This would be checked by WorkStateManager with full state
        return self.status == WorkStatus.READY
    
    def is_complete(self) -> bool:
        """Check if work is done"""
        return self.status in (WorkStatus.DONE, WorkStatus.FAILED)


class WorkStateManager:
    """
    Manages persistent work state.
    Stores state in .squad/ directory (git-trackable).
    """
    
    SQUAD_DIR = ".squad"
    WORKSTATE_FILE = "workstate.json"
    
    def __init__(self, workspace_root: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize work state manager.
        
        Args:
            workspace_root: Root directory of the workspace (defaults to cwd)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.config = config or {}
        hooks_cfg = self.config.get("hooks", {}) if isinstance(self.config, dict) else {}
        self.hooks_enabled = hooks_cfg.get("enabled", True)
        self.hook_manager = HookManager(
            workspace_root=self.workspace_root,
            hooks_dir=hooks_cfg.get("hooks_dir", ".squad/hooks"),
            use_git_worktree=hooks_cfg.get("use_git_worktree", False),
        )
        self.squad_dir = self.workspace_root / self.SQUAD_DIR
        self.workstate_file = self.squad_dir / self.WORKSTATE_FILE
        self.lock_file = self.squad_dir / f"{self.WORKSTATE_FILE}.lock"
        
        self._work_items: Dict[str, WorkItem] = {}
        self._in_transaction: bool = False
        self._graph = None
        self._load_state()

    # --- Locking helpers -------------------------------------------------
    def _acquire_lock(self) -> ContextManager:
        """Context manager to acquire file lock for state operations."""
        self._ensure_squad_dir()
        lock_handle = open(self.lock_file, "a+", encoding="utf-8")

        class _LockCtx:
            def __enter__(self):
                if fcntl:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                else:  # Windows
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_LOCK, 1)
                return lock_handle

            def __exit__(self, exc_type, exc, tb):
                try:
                    if fcntl:
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                    else:
                        msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                finally:
                    lock_handle.close()

        return _LockCtx()

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write to temp file then replace to avoid partial writes."""
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)

    def _build_state_payload(self) -> str:
        """Serialize current in-memory state to JSON string."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "work_items": {
                item_id: item.to_dict()
                for item_id, item in self._work_items.items()
            }
        }
        return json.dumps(data, indent=2)

    def _load_state_locked(self) -> None:
        """Load state assuming the caller already holds the lock."""
        if not self.workstate_file.exists():
            self._work_items = {}
            return

        try:
            data = json.loads(self.workstate_file.read_text(encoding="utf-8"))
            self._work_items = {
                item_id: WorkItem.from_dict(item_data)
                for item_id, item_data in data.get("work_items", {}).items()
            }
            logger.info("Loaded %d work items from state", len(self._work_items))
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load work state: %s", e)
            self._work_items = {}

    def _save_state_locked(self) -> None:
        """Persist state assuming the caller already holds the lock."""
        payload = self._build_state_payload()
        self._atomic_write(self.workstate_file, payload)
        logger.debug("Saved %d work items to state", len(self._work_items))
    
    def _ensure_squad_dir(self) -> None:
        """Create .squad directory if it doesn't exist"""
        self.squad_dir.mkdir(parents=True, exist_ok=True)
        
        # Create .gitignore for non-trackable files
        gitignore = self.squad_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("# AI-Squad runtime files\n*.lock\n*.tmp\n")
    
    def _load_state(self) -> None:
        """Load work state from disk"""
        if not self.workstate_file.exists():
            self._work_items = {}
            return
        
        with self._acquire_lock():
            self._load_state_locked()

    def reload_state(self) -> None:
        """Public reload of work state from disk."""
        self._load_state()
    
    def _save_state(self) -> None:
        """Persist work state to disk"""
        self._ensure_squad_dir()
        with self._acquire_lock():
            self._save_state_locked()

    # --- Mutation helpers -------------------------------------------------
    def transaction(self, reload: bool = True) -> ContextManager:
        """Lock the state, optionally reload, and save only if marked dirty."""
        self._ensure_squad_dir()
        lock = self._acquire_lock()
        manager = self

        class _TxnCtx:
            def __init__(self):
                self.lock_ctx = None
                self.dirty = False

            def __enter__(self):
                manager._in_transaction = True
                self.lock_ctx = lock.__enter__()
                if reload:
                    manager._load_state_locked()
                self.dirty = False

                def mark_dirty():
                    self.dirty = True

                return mark_dirty

            def __exit__(self, exc_type, exc, tb):
                try:
                    if exc_type is None and self.dirty:
                        manager._save_state_locked()
                finally:
                    manager._in_transaction = False
                    lock.__exit__(exc_type, exc, tb)
                return False  # Do not suppress exceptions

        return _TxnCtx()
    
    def generate_id(self, prefix: str = "sq") -> str:
        """Generate a unique work item ID"""
        short_uuid = uuid.uuid4().hex[:5]
        return f"{prefix}-{short_uuid}"
    
    # CRUD Operations
    
    def create_work_item(
        self,
        title: str,
        description: str = "",
        issue_number: Optional[int] = None,
        agent: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> WorkItem:
        """Create a new work item"""
        with self.transaction() as mark_dirty:
            item = WorkItem(
                id=self.generate_id(),
                title=title,
                description=description,
                issue_number=issue_number,
                agent_assignee=agent,
                depends_on=depends_on or [],
                labels=labels or [],
                metadata=metadata or {},
                priority=priority
            )
            
            # Check if dependencies are satisfied
            if item.depends_on:
                if self._dependencies_satisfied(item):
                    item.status = WorkStatus.READY
                else:
                    item.status = WorkStatus.BLOCKED
            else:
                # No dependencies, ready to start
                item.status = WorkStatus.READY
            
            if agent:
                # Mark as hooked to reflect assignment
                item.status = WorkStatus.HOOKED
                item.assigned_to = agent

            self._work_items[item.id] = item
            mark_dirty()

        if self.hooks_enabled:
            self.hook_manager.ensure_hook(item)
        self._update_operational_graph(item)
        
        logger.info("Created work item: %s (%s)", item.id, title)
        return item
    
    def get_work_item(self, item_id: str) -> Optional[WorkItem]:
        """Get a work item by ID"""
        if not self._in_transaction:
            self._load_state()
        if isinstance(item_id, WorkItem):
            item_id = item_id.id
        return self._work_items.get(item_id)
    
    def get_work_item_by_issue(self, issue_number: int) -> Optional[WorkItem]:
        """Get a work item by GitHub issue number"""
        for item in self._work_items.values():
            if item.issue_number == issue_number:
                return item
        return None
    
    def update_work_item(self, item: WorkItem) -> None:
        """Update a work item"""
        with self.transaction() as mark_dirty:
            item.updated_at = datetime.now().isoformat()
            self._work_items[item.id] = item
            mark_dirty()
        if self.hooks_enabled:
            self.hook_manager.write_metadata(item)
    
    def delete_work_item(self, item_id: str) -> bool:
        """Delete a work item"""
        with self.transaction() as mark_dirty:
            if item_id in self._work_items:
                del self._work_items[item_id]
                mark_dirty()
                if self.hooks_enabled:
                    self.hook_manager.remove_hook(item_id)
                return True
            return False
    
    def list_work_items(
        self,
        status: Optional[WorkStatus] = None,
        agent: Optional[str] = None,
        convoy_id: Optional[str] = None
    ) -> List[WorkItem]:
        """List work items with optional filters"""
        items = list(self._work_items.values())
        
        if status:
            items = [i for i in items if i.status == status]
        if agent:
            items = [i for i in items if i.agent_assignee == agent]
        if convoy_id:
            items = [i for i in items if i.convoy_id == convoy_id]
        
        # Sort by priority (descending) then created_at
        items.sort(key=lambda x: (-x.priority, x.created_at))
        return items
    
    # Agent Operations
    
    def assign_to_agent(self, item_id: str, agent: str) -> bool:
        """Assign a work item to an agent (hook it)"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            if not item:
                return False
            
            item.assign_to(agent)
            mark_dirty()
        
        logger.info("Assigned %s to agent %s", item_id, agent)
        item = self.get_work_item(item_id)
        if item:
            if self.hooks_enabled:
                self.hook_manager.ensure_hook(item)
            self._update_operational_graph(item)
        return True
    
    def unassign_from_agent(self, item_id: str) -> bool:
        """Remove agent assignment (unhook)"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            if not item:
                return False
            
            old_agent = item.agent_assignee
            item.unassign()
            mark_dirty()
        
        if item and self.hooks_enabled:
            self.hook_manager.write_metadata(item)
        logger.info("Unassigned %s from agent %s", item_id, old_agent)
        return True
    
    def get_agent_work(self, agent: str) -> List[WorkItem]:
        """Get all work items assigned to an agent"""
        return self.list_work_items(agent=agent)
    
    def get_agent_hooked_work(self, agent: str) -> Optional[WorkItem]:
        """Get the currently hooked work for an agent"""
        items = self.list_work_items(status=WorkStatus.HOOKED, agent=agent)
        return items[0] if items else None
    
    # Context Preservation
    
    def save_agent_context(
        self,
        item_id: str,
        context: Dict[str, Any]
    ) -> bool:
        """Save agent context for later resumption"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            if not item:
                return False
            
            item.save_context(context)
            mark_dirty()
            if self.hooks_enabled:
                self.hook_manager.write_metadata(item)
            return True
    
    def restore_agent_context(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Restore previously saved agent context"""
        item = self.get_work_item(item_id)
        return item.context if item else None
    
    # Dependency Management
    
    def _dependencies_satisfied(self, item: WorkItem) -> bool:
        """Check if all dependencies are completed"""
        for dep_id in item.depends_on:
            dep = self.get_work_item(dep_id)
            if not dep or not dep.is_complete():
                return False
        return True
    
    def update_blocked_items(self) -> List[WorkItem]:
        """Update status of blocked items whose dependencies are now satisfied"""
        unblocked: List[WorkItem] = []
        with self.transaction() as mark_dirty:
            for item in self._work_items.values():
                if item.status == WorkStatus.BLOCKED and self._dependencies_satisfied(item):
                    item.update_status(WorkStatus.READY)
                    unblocked.append(item)
            if unblocked:
                mark_dirty()
        return unblocked
    
    def add_dependency(self, item_id: str, depends_on_id: str) -> bool:
        """Add a dependency to a work item"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            dep = self.get_work_item(depends_on_id)
            
            if not item or not dep:
                return False
            
            if depends_on_id not in item.depends_on:
                item.depends_on.append(depends_on_id)
                
                # Also track reverse relationship
                if item_id not in dep.blocks:
                    dep.blocks.append(item_id)
                
                # Update status if needed
                if not self._dependencies_satisfied(item):
                    item.update_status(WorkStatus.BLOCKED)
                
                mark_dirty()
            
            return True
        
        if item:
            self._update_operational_graph(item)

    def _update_operational_graph(self, item: WorkItem) -> None:
        """Synchronize work item changes into the operational graph."""
        try:
            from ai_squad.core.operational_graph import OperationalGraph, NodeType, EdgeType

            if self._graph is None:
                self._graph = OperationalGraph(workspace_root=self.workspace_root)

            self._graph.add_node(
                item.id,
                NodeType.WORK_ITEM,
                {
                    "title": item.title,
                    "issue_number": item.issue_number,
                    "labels": item.labels,
                    "status": item.status.value,
                },
            )

            if item.issue_number:
                issue_node_id = f"issue-{item.issue_number}"
                self._graph.add_node(
                    issue_node_id,
                    NodeType.WORK_ITEM,
                    {"issue_number": item.issue_number},
                )
                self._graph.add_edge(issue_node_id, item.id, EdgeType.DEPENDS_ON, {"source": "workstate"})

            if item.agent_assignee:
                self._graph.add_node(item.agent_assignee, NodeType.AGENT, {"agent": item.agent_assignee})
                self._graph.add_edge(item.id, item.agent_assignee, EdgeType.OWNS, {"source": "workstate"})

            for dep_id in item.depends_on:
                self._graph.add_edge(item.id, dep_id, EdgeType.DEPENDS_ON, {"source": "workstate"})
        except (ValueError, OSError, RuntimeError) as e:
            logger.warning("Operational graph update failed for %s: %s", item.id, e)
    
    # Artifact Management
    
    def add_artifact(self, item_id: str, artifact_path: str) -> bool:
        """Add an artifact (output file) to a work item"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            if not item:
                return False
            
            item.add_artifact(artifact_path)
            mark_dirty()
            if self.hooks_enabled:
                self.hook_manager.write_metadata(item)
            return True
    
    # Status Transitions
    
    def transition_status(
        self,
        item_id: str,
        new_status: WorkStatus,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Transition a work item to a new status"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            if not item:
                return False
            
            old_status = item.status
            item.update_status(new_status)
            
            if context:
                item.save_context(context)
            
            mark_dirty()
        
        if item and self.hooks_enabled:
            self.hook_manager.write_metadata(item)
        
        logger.info(
            "Transitioned %s from %s to %s",
            item_id, old_status.value, new_status.value
        )
        
        # Check if this completion unblocks other items
        if new_status == WorkStatus.DONE:
            self.update_blocked_items()
        
        return True
    
    def complete_work(
        self,
        item_id: str,
        artifacts: Optional[List[str]] = None
    ) -> bool:
        """Mark work as complete with optional artifacts"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            if not item:
                return False
            
            if artifacts:
                for artifact in artifacts:
                    item.add_artifact(artifact)
            
            item.unassign()
            item.update_status(WorkStatus.DONE)
            mark_dirty()
        
        if item and self.hooks_enabled:
            self.hook_manager.write_metadata(item)
        
        # Unblock dependent items
        self.update_blocked_items()
        
        return True
    
    # Convoy Support
    
    def set_convoy(self, item_id: str, convoy_id: str) -> bool:
        """Associate a work item with a convoy"""
        with self.transaction() as mark_dirty:
            item = self.get_work_item(item_id)
            if not item:
                return False
            
            item.convoy_id = convoy_id
            mark_dirty()
            return True
    
    # Statistics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get work state statistics"""
        items = list(self._work_items.values())
        
        status_counts = {}
        for status in WorkStatus:
            status_counts[status.value] = len([
                i for i in items if i.status == status
            ])
        
        agent_counts = {}
        for item in items:
            if item.agent_assignee:
                agent_counts[item.agent_assignee] = (
                    agent_counts.get(item.agent_assignee, 0) + 1
                )
        
        return {
            "total": len(items),
            "by_status": status_counts,
            "by_agent": agent_counts,
            "blocked": status_counts.get("blocked", 0),
            "in_progress": status_counts.get("in_progress", 0) + status_counts.get("hooked", 0),
            "completed": status_counts.get("done", 0),
        }
