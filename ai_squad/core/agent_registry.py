"""
Agent Registry - A2A-Inspired Agent Discovery and Routing

Provides centralized agent registration, discovery, and capability-based routing.
Implements patterns from Google's A2A protocol for agent interoperability.

Usage:
    registry = AgentRegistry()
    
    # Find agents by capability
    agents = registry.find_by_capability(AgentCapability.CODE_REVIEW)
    
    # Route task to best agent
    agent = registry.route_task(task)
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from ai_squad.core.agent_card import (
    AgentCard,
    AgentCapability,
    DEFAULT_AGENT_CARDS,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentInstance:
    """
    Runtime instance of a registered agent.
    
    Combines the static AgentCard with runtime state.
    """
    card: AgentCard
    agent_class: Optional[Type] = None  # Reference to agent class
    instance: Optional[Any] = None      # Cached agent instance
    status: str = "available"           # available, busy, offline
    last_active: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "card": self.card.to_dict(),
            "status": self.status,
            "last_active": self.last_active,
            "metrics": self.metrics,
        }


class AgentRegistry:
    """
    Central registry for agent discovery and routing.
    
    Features:
    - Agent registration with capability cards
    - Capability-based agent lookup
    - Task routing based on required capabilities
    - Agent health tracking
    """
    
    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        auto_register_defaults: bool = True,
    ):
        """
        Initialize the agent registry.
        
        Args:
            workspace_root: Workspace root for persistence
            auto_register_defaults: Whether to register default AI-Squad agents
        """
        self.workspace_root = workspace_root or Path.cwd()
        self._agents: Dict[str, AgentInstance] = {}
        self._capability_index: Dict[AgentCapability, List[str]] = {}
        self._handlers: Dict[str, Callable] = {}
        
        # Load balancing and reliability
        self._request_counts: Dict[str, int] = {}  # Track agent load
        self._failure_counts: Dict[str, int] = {}  # Circuit breaker
        self._circuit_open_until: Dict[str, float] = {}  # Circuit breaker timeout
        self._health_check_thread = None
        
        if auto_register_defaults:
            self._register_default_agents()
    
    def _register_default_agents(self) -> None:
        """Register default AI-Squad agents"""
        for name, card in DEFAULT_AGENT_CARDS.items():
            self.register(card)
    
    # Registration
    
    def register(
        self,
        card: AgentCard,
        agent_class: Optional[Type] = None,
    ) -> None:
        """
        Register an agent with the registry.
        
        Args:
            card: Agent capability card
            agent_class: Optional reference to agent class for instantiation
        """
        instance = AgentInstance(
            card=card,
            agent_class=agent_class,
            status="available",
            last_active=datetime.now().isoformat(),
        )
        
        self._agents[card.name] = instance
        
        # Update capability index
        for capability in card.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if card.name not in self._capability_index[capability]:
                self._capability_index[capability].append(card.name)
        
        logger.info("Registered agent: %s with %d capabilities", 
                    card.name, len(card.capabilities))
    
    def unregister(self, name: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            name: Agent name
            
        Returns:
            True if agent was removed
        """
        if name not in self._agents:
            return False
        
        instance = self._agents.pop(name)
        
        # Update capability index
        for capability in instance.card.capabilities:
            if capability in self._capability_index:
                if name in self._capability_index[capability]:
                    self._capability_index[capability].remove(name)
        
        logger.info("Unregistered agent: %s", name)
        return True
    
    # Discovery
    
    def get(self, name: str) -> Optional[AgentCard]:
        """
        Get an agent card by name.
        
        Args:
            name: Agent name
            
        Returns:
            AgentCard or None
        """
        instance = self._agents.get(name)
        return instance.card if instance else None
    
    def get_instance(self, name: str) -> Optional[AgentInstance]:
        """
        Get an agent instance by name.
        
        Args:
            name: Agent name
            
        Returns:
            AgentInstance or None
        """
        return self._agents.get(name)
    
    def list_agents(self) -> List[AgentCard]:
        """List all registered agent cards"""
        return [inst.card for inst in self._agents.values()]
    
    def list_available(self) -> List[AgentCard]:
        """List agents that are currently available"""
        return [
            inst.card for inst in self._agents.values()
            if inst.status == "available"
        ]
    
    def find_by_capability(
        self,
        capability: AgentCapability,
        available_only: bool = True,
    ) -> List[AgentCard]:
        """
        Find agents with a specific capability.
        
        Args:
            capability: Required capability
            available_only: Only return available agents
            
        Returns:
            List of matching agent cards
        """
        agent_names = self._capability_index.get(capability, [])
        results = []
        
        for name in agent_names:
            instance = self._agents.get(name)
            if instance:
                if available_only and instance.status != "available":
                    continue
                results.append(instance.card)
        
        return results
    
    def find_by_capabilities(
        self,
        capabilities: List[AgentCapability],
        match_all: bool = True,
        available_only: bool = True,
    ) -> List[AgentCard]:
        """
        Find agents with multiple capabilities.
        
        Args:
            capabilities: Required capabilities
            match_all: If True, agent must have ALL capabilities
            available_only: Only return available agents
            
        Returns:
            List of matching agent cards
        """
        if not capabilities:
            return self.list_available() if available_only else self.list_agents()
        
        results = []
        
        for instance in self._agents.values():
            if available_only and instance.status != "available":
                continue
            
            if match_all:
                if instance.card.can_handle(capabilities):
                    results.append(instance.card)
            else:
                if any(cap in instance.card.capabilities for cap in capabilities):
                    results.append(instance.card)
        
        return results
    
    def find_by_tag(self, tag: str) -> List[AgentCard]:
        """Find agents by tag"""
        return [
            inst.card for inst in self._agents.values()
            if tag in inst.card.tags
        ]
    
    # Routing
    
    def route_by_capability(
        self,
        capability: AgentCapability,
    ) -> Optional[str]:
        """
        Route to an agent by capability.
        
        Uses least-loaded algorithm for load balancing.
        
        Args:
            capability: Required capability
            
        Returns:
            Agent name or None
        """
        agents = self.find_by_capability(capability)
        if not agents:
            return None
        
        # Load balancing: select least-loaded agent
        def get_load(card):
            return self._request_counts.get(card.name, 0)
        
        selected = min(agents, key=get_load)
        self._request_counts[selected.name] = self._request_counts.get(selected.name, 0) + 1
        
        return selected.name
    
    def route_task(
        self,
        required_capabilities: List[AgentCapability],
        prefer_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Route a task to the best available agent.
        
        Uses intelligent scoring: capability match + load + priority.
        
        Args:
            required_capabilities: Capabilities needed for the task
            prefer_agent: Preferred agent name (if available)
            
        Returns:
            Agent name or None if no suitable agent found
        """
        # Check preferred agent first
        if prefer_agent:
            instance = self._agents.get(prefer_agent)
            if instance and instance.status == "available":
                if instance.card.can_handle(required_capabilities):
                    self._request_counts[prefer_agent] = \
                        self._request_counts.get(prefer_agent, 0) + 1
                    return prefer_agent
        
        # Find agents that can handle all requirements
        candidates = self.find_by_capabilities(
            required_capabilities,
            match_all=True,
            available_only=True,
        )
        
        if not candidates:
            logger.warning(
                "No agent found for capabilities: %s",
                [c.value for c in required_capabilities]
            )
            return None
        
        # Intelligent scoring: capability match + load + priority
        scored = []
        for card in candidates:
            score = 0.0
            
            # Capability specialization (higher = more specialized)
            matching = len(set(card.capabilities) & set(required_capabilities))
            score += matching * 10.0
            
            # Load (penalize busy agents)
            load = self._request_counts.get(card.name, 0)
            score -= load * 2.0
            
            # Priority from metadata
            priority = card.metadata.get("priority", 0)
            score += priority
            
            scored.append((score, card.name))
        
        # Select highest scoring agent
        selected_name = max(scored, key=lambda x: x[0])[1]
        self._request_counts[selected_name] = \
            self._request_counts.get(selected_name, 0) + 1
        
        return selected_name
    
    def get_workflow_order(self) -> List[str]:
        """
        Get agents in workflow dependency order.
        
        Returns:
            List of agent names in execution order
        """
        # Build dependency graph
        visited = set()
        order = []
        
        def visit(name: str):
            if name in visited:
                return
            visited.add(name)
            
            card = self.get(name)
            if card:
                for dep in card.depends_on:
                    visit(dep)
            order.append(name)
        
        for name in self._agents:
            visit(name)
        
        return order
    
    # Status Management
    
    def set_status(self, name: str, status: str) -> bool:
        """
        Set agent status.
        
        Args:
            name: Agent name
            status: New status (available, busy, offline)
            
        Returns:
            True if status was updated
        """
        instance = self._agents.get(name)
        if not instance:
            return False
        
        instance.status = status
        instance.last_active = datetime.now().isoformat()
        return True
    
    def mark_busy(self, name: str) -> bool:
        """Mark agent as busy"""
        return self.set_status(name, "busy")
    
    def mark_available(self, name: str) -> bool:
        """Mark agent as available"""
        return self.set_status(name, "available")
    
    def mark_offline(self, name: str) -> bool:
        """Mark agent as offline"""
        return self.set_status(name, "offline")
    
    # Handlers
    
    def register_handler(
        self,
        agent_name: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """
        Register a message handler for an agent.
        
        Args:
            agent_name: Agent name
            handler: Handler function that takes message dict and returns response dict
        """
        self._handlers[agent_name] = handler
        logger.debug("Registered handler for agent: %s", agent_name)
    
    def get_handler(self, agent_name: str) -> Optional[Callable]:
        """Get handler for an agent"""
        return self._handlers.get(agent_name)
    
    def invoke(
        self,
        agent_name: str,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Invoke an agent's handler.
        
        Args:
            agent_name: Target agent name
            message: Message to send
            
        Returns:
            Response dict or None if no handler
        """
        handler = self._handlers.get(agent_name)
        if not handler:
            logger.warning("No handler registered for agent: %s", agent_name)
            return None
        
        # Validate input
        card = self.get(agent_name)
        if card:
            errors = card.validate_input(message)
            if errors:
                logger.warning("Input validation failed: %s", errors)
                return {"error": "validation_failed", "details": errors}
        
        # Mark busy during execution
        self.mark_busy(agent_name)
        try:
            result = handler(message)
            return result
        finally:
            self.mark_available(agent_name)
    
    # Serialization
    
    def to_dict(self) -> Dict[str, Any]:
        """Export registry state"""
        return {
            "agents": {
                name: inst.to_dict()
                for name, inst in self._agents.items()
            },
            "capabilities": {
                cap.value: names
                for cap, names in self._capability_index.items()
            },
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Export as JSON"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save registry to file"""
        path = path or (self.workspace_root / ".squad" / "registry.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        logger.info("Saved registry to %s", path)
    
    # Circuit Breaker Pattern
    
    def record_success(self, agent_name: str) -> None:
        """Record successful agent invocation (resets circuit breaker)"""
        self._failure_counts[agent_name] = 0
        if agent_name in self._circuit_open_until:
            del self._circuit_open_until[agent_name]
    
    def record_failure(self, agent_name: str) -> None:
        """Record failed agent invocation (may open circuit breaker)"""
        self._failure_counts[agent_name] = self._failure_counts.get(agent_name, 0) + 1
        
        # Open circuit after 5 consecutive failures
        if self._failure_counts[agent_name] >= 5:
            import time
            # Circuit stays open for 60 seconds
            self._circuit_open_until[agent_name] = time.time() + 60
            self.mark_offline(agent_name)
            logger.warning(
                "Circuit breaker opened for %s (5 failures)",
                agent_name
            )
    
    def is_circuit_open(self, agent_name: str) -> bool:
        """Check if circuit breaker is open for an agent"""
        import time
        
        if agent_name not in self._circuit_open_until:
            return False
        
        # Check if recovery timeout has passed
        if time.time() > self._circuit_open_until[agent_name]:
            # Try to recover
            del self._circuit_open_until[agent_name]
            self._failure_counts[agent_name] = 0
            logger.info("Circuit breaker recovered for %s", agent_name)
            return False
        
        return True
    
    # Health Monitoring
    
    def start_health_monitor(self, interval_seconds: int = 30) -> None:
        """Start background health monitoring thread"""
        import threading
        
        if self._health_check_thread and self._health_check_thread.is_alive():
            logger.warning("Health monitor already running")
            return
        
        def health_check_loop():
            import time
            logger.info("Health monitor started (interval=%ds)", interval_seconds)
            
            while True:
                try:
                    for name in list(self._agents.keys()):
                        handler = self._handlers.get(name)
                        if not handler:
                            continue
                        
                        try:
                            # Ping agent with health check
                            result = handler({"method": "health", "content": "ping"})
                            
                            if result and isinstance(result, dict):
                                status = result.get("status", "unknown")
                                if status in ("ok", "success", "available"):
                                    self.mark_available(name)
                                    self.record_success(name)
                                else:
                                    self.mark_offline(name)
                            else:
                                # No response = offline
                                self.mark_offline(name)
                                
                        except Exception as e:
                            logger.debug("Health check failed for %s: %s", name, e)
                            self.mark_offline(name)
                            self.record_failure(name)
                    
                    time.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error("Health monitor error: %s", e)
                    time.sleep(interval_seconds)
        
        self._health_check_thread = threading.Thread(
            target=health_check_loop,
            daemon=True,
            name="AgentHealthMonitor"
        )
        self._health_check_thread.start()
    
    def stop_health_monitor(self) -> None:
        """Stop health monitoring (for testing)"""
        # Daemon thread will stop when main program exits
        self._health_check_thread = None


# Global registry instance
_global_registry: Optional[AgentRegistry] = None


def get_registry(
    workspace_root: Optional[Path] = None,
    auto_register_defaults: bool = True,
) -> AgentRegistry:
    """
    Get or create the global agent registry.
    
    Args:
        workspace_root: Workspace root path
        auto_register_defaults: Register default agents
        
    Returns:
        Global AgentRegistry instance
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = AgentRegistry(
            workspace_root=workspace_root,
            auto_register_defaults=auto_register_defaults,
        )
    
    return _global_registry


def reset_registry() -> None:
    """Reset the global registry (for testing)"""
    global _global_registry
    _global_registry = None
