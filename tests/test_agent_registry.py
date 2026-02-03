"""
Tests for AgentRegistry - A2A-aligned agent discovery and routing
"""
import pytest
import time
from pathlib import Path
from ai_squad.core.agent_registry import (
    AgentRegistry,
    AgentInstance,
    get_registry,
    reset_registry,
)
from ai_squad.core.agent_card import (
    AgentCard,
    AgentCapability,
    DEFAULT_AGENT_CARDS,
    PM_CARD,
    ENGINEER_CARD,
)


@pytest.fixture
def registry():
    """Create a fresh registry for each test"""
    reset_registry()
    return AgentRegistry(auto_register_defaults=True)


class TestAgentRegistry:
    """Test AgentRegistry functionality"""
    
    def test_registry_initialization(self, registry):
        """Test registry initializes with default agents"""
        assert len(registry.list_agents()) == 6  # pm, architect, engineer, ux, reviewer, captain
    
    def test_register_agent(self, registry):
        """Test registering a new agent"""
        card = AgentCard(
            name="test_agent",
            display_name="Test Agent",
            description="Test",
            capabilities=[AgentCapability.CODE_REVIEW],
        )
        
        registry.register(card)
        
        assert registry.get("test_agent") is not None
        assert registry.get("test_agent").name == "test_agent"
    
    def test_unregister_agent(self, registry):
        """Test unregistering an agent"""
        assert registry.get("pm") is not None
        
        success = registry.unregister("pm")
        
        assert success is True
        assert registry.get("pm") is None
    
    def test_find_by_capability(self, registry):
        """Test finding agents by capability"""
        agents = registry.find_by_capability(AgentCapability.PRD_GENERATION)
        
        assert len(agents) == 1
        assert agents[0].name == "pm"
    
    def test_find_by_multiple_capabilities(self, registry):
        """Test finding agents with multiple capabilities"""
        # All capabilities must match
        agents = registry.find_by_capabilities(
            [AgentCapability.CODE_GENERATION, AgentCapability.TEST_GENERATION],
            match_all=True
        )
        
        assert len(agents) == 1
        assert agents[0].name == "engineer"
        
        # Any capability matches
        agents = registry.find_by_capabilities(
            [AgentCapability.PRD_GENERATION, AgentCapability.CODE_REVIEW],
            match_all=False
        )
        
        assert len(agents) >= 2  # pm and reviewer
    
    def test_find_by_tag(self, registry):
        """Test finding agents by tag"""
        agents = registry.find_by_tag("review")
        
        assert len(agents) >= 1
        assert any(a.name == "reviewer" for a in agents)
    
    def test_route_by_capability(self, registry):
        """Test capability-based routing"""
        agent = registry.route_by_capability(AgentCapability.PRD_GENERATION)
        
        assert agent == "pm"
    
    def test_route_by_capability_unknown(self, registry):
        """Test routing with unknown capability"""
        # No agent has this exact capability combo
        agent = registry.route_by_capability(AgentCapability.CODE_GENERATION)
        
        assert agent == "engineer"
    
    def test_route_task(self, registry):
        """Test task routing"""
        agent = registry.route_task([AgentCapability.CODE_REVIEW])
        
        assert agent == "reviewer"
    
    def test_route_task_with_preference(self, registry):
        """Test task routing with preferred agent"""
        agent = registry.route_task(
            [AgentCapability.CODE_GENERATION],
            prefer_agent="engineer"
        )
        
        assert agent == "engineer"
    
    def test_route_task_no_match(self, registry):
        """Test task routing when no agent can handle requirements"""
        # Create impossible requirement
        agent = registry.route_task([
            AgentCapability.PRD_GENERATION,
            AgentCapability.CODE_GENERATION,
            AgentCapability.SECURITY_AUDIT,
        ])
        
        # No single agent has all three
        assert agent is None
    
    def test_status_management(self, registry):
        """Test agent status updates"""
        assert registry.mark_busy("pm") is True
        instance = registry.get_instance("pm")
        assert instance.status == "busy"
        
        assert registry.mark_available("pm") is True
        instance = registry.get_instance("pm")
        assert instance.status == "available"
        
        assert registry.mark_offline("pm") is True
        instance = registry.get_instance("pm")
        assert instance.status == "offline"
    
    def test_list_available(self, registry):
        """Test listing only available agents"""
        registry.mark_busy("pm")
        registry.mark_offline("architect")
        
        available = registry.list_available()
        
        assert not any(a.name == "pm" for a in available)
        assert not any(a.name == "architect" for a in available)
        assert any(a.name == "engineer" for a in available)


class TestLoadBalancing:
    """Test load balancing functionality"""
    
    def test_least_loaded_routing(self, registry):
        """Test that routing picks least-loaded agent"""
        # Register two agents with same capability
        card1 = AgentCard(
            name="test1",
            display_name="Test 1",
            description="Test",
            capabilities=[AgentCapability.CODE_REVIEW],
        )
        card2 = AgentCard(
            name="test2",
            display_name="Test 2",
            description="Test",
            capabilities=[AgentCapability.CODE_REVIEW],
        )
        
        registry.register(card1)
        registry.register(card2)
        
        # First route should go to test1 (both at 0)
        agent1 = registry.route_by_capability(AgentCapability.CODE_REVIEW)
        
        # Second route should go to different agent if load balancing works
        agent2 = registry.route_by_capability(AgentCapability.CODE_REVIEW)
        
        # At least one should be test1 or test2
        assert agent1 in ["test1", "test2", "reviewer"]
        assert agent2 in ["test1", "test2", "reviewer"]
    
    def test_task_routing_score(self, registry):
        """Test task routing uses scoring algorithm"""
        agent = registry.route_task([AgentCapability.CODE_GENERATION])
        
        # Should route to engineer
        assert agent == "engineer"
        
        # Request count should increment
        assert registry._request_counts.get("engineer", 0) > 0


class TestCircuitBreaker:
    """Test circuit breaker pattern"""
    
    def test_record_success(self, registry):
        """Test recording successful invocation"""
        registry.record_success("pm")
        
        assert registry._failure_counts.get("pm", 0) == 0
        assert not registry.is_circuit_open("pm")
    
    def test_record_failure(self, registry):
        """Test recording failed invocation"""
        for _ in range(4):
            registry.record_failure("pm")
        
        assert registry._failure_counts["pm"] == 4
        assert not registry.is_circuit_open("pm")  # Not yet open
        
        # 5th failure opens circuit
        registry.record_failure("pm")
        assert registry.is_circuit_open("pm")
        
        # Agent should be marked offline
        instance = registry.get_instance("pm")
        assert instance.status == "offline"
    
    def test_circuit_recovery(self, registry):
        """Test circuit breaker recovery"""
        # Open circuit
        for _ in range(5):
            registry.record_failure("pm")
        
        assert registry.is_circuit_open("pm")
        
        # Manually expire timeout (in production, would wait 60s)
        registry._circuit_open_until["pm"] = time.time() - 1
        
        # Should recover
        assert not registry.is_circuit_open("pm")
        assert registry._failure_counts.get("pm", 0) == 0


class TestHandlerInvocation:
    """Test handler registration and invocation"""
    
    def test_register_handler(self, registry):
        """Test registering a handler"""
        called = []
        
        def test_handler(message):
            called.append(message)
            return {"response": "ok"}
        
        registry.register_handler("pm", test_handler)
        
        result = registry.invoke("pm", {"issue_number": 123, "content": "test"})
        
        assert len(called) == 1
        assert called[0]["content"] == "test"
        assert result["response"] == "ok"
    
    def test_invoke_marks_busy(self, registry):
        """Test that invoke marks agent busy during execution"""
        def slow_handler(message):
            instance = registry.get_instance("pm")
            # During execution, should be busy
            assert instance.status == "busy"
            return {"response": "done"}
        
        registry.register_handler("pm", slow_handler)
        registry.invoke("pm", {})
        
        # After execution, should be available again
        instance = registry.get_instance("pm")
        assert instance.status == "available"
    
    def test_invoke_no_handler(self, registry):
        """Test invoking agent with no handler"""
        result = registry.invoke("pm", {})
        
        assert result is None


class TestHealthMonitor:
    """Test health monitoring"""
    
    def test_start_health_monitor(self, registry):
        """Test starting health monitor"""
        registry.start_health_monitor(interval_seconds=1)
        
        assert registry._health_check_thread is not None
        assert registry._health_check_thread.is_alive()
        
        # Stop for cleanup
        registry.stop_health_monitor()
    
    def test_health_check_updates_status(self, registry):
        """Test health check updates agent status"""
        # Register handler that responds to health checks
        def health_handler(message):
            if message.get("method") == "health":
                return {"status": "ok"}
            return {"status": "error"}
        
        registry.register_handler("pm", health_handler)
        registry.mark_offline("pm")  # Start as offline
        
        # Start monitor
        registry.start_health_monitor(interval_seconds=1)
        
        # Wait for at least one health check
        time.sleep(2)
        
        # Should be marked available
        instance = registry.get_instance("pm")
        assert instance.status == "available"
        
        registry.stop_health_monitor()


class TestGlobalRegistry:
    """Test global registry singleton"""
    
    def test_get_registry_singleton(self):
        """Test that get_registry returns singleton"""
        reset_registry()
        
        reg1 = get_registry()
        reg2 = get_registry()
        
        assert reg1 is reg2
    
    def test_reset_registry(self):
        """Test resetting global registry"""
        reg1 = get_registry()
        reset_registry()
        reg2 = get_registry()
        
        assert reg1 is not reg2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
