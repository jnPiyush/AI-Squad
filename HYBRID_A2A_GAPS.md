# Hybrid A2A Implementation - Gaps & Improvements

**Date**: February 3, 2026  
**Status**: Implementation Complete, Gaps Identified

---

## ✅ What We Built

| Component | Status | A2A Alignment |
|-----------|--------|---------------|
| **AgentCard** | ✅ Complete | Schema matches A2A Agent Card (JSON-LD) |
| **AgentRegistry** | ✅ Complete | Discovery, capability routing |
| **WorkItem → Task** | ✅ Complete | `to_a2a_task()`, `from_a2a_task()` |
| **Message Routing** | ✅ Fixed | Uses registry instead of placeholder |
| **Auto-Registration** | ✅ Complete | Agents register on init |

---

## 🔴 Critical Gaps (Blocking Production)

### 1. **No A2A Protocol Transport Layer**
**Issue**: We have schema but no wire protocol (JSON-RPC 2.0 + SSE).

**Impact**: 
- Cannot communicate with external A2A agents
- No streaming support for long-running tasks
- No webhook callbacks

**Solution**:
```python
# NEW FILE: ai_squad/core/a2a_protocol.py
class A2AProtocolHandler:
    """JSON-RPC 2.0 handler for A2A protocol"""
    
    def handle_rpc_request(self, request: dict) -> dict:
        """
        Handle A2A JSON-RPC 2.0 request
        
        Methods:
        - tasks.create
        - tasks.get
        - tasks.update
        - tasks.cancel
        - agents.list
        - agents.get
        """
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "tasks.create":
            return self._create_task(params)
        elif method == "agents.list":
            return self._list_agents(params)
        # ... etc

class A2AStreamHandler:
    """Server-Sent Events (SSE) for A2A streaming"""
    
    async def stream_task_updates(self, task_id: str):
        """Stream task status updates via SSE"""
        while not task.is_complete():
            yield f"data: {json.dumps(task.to_a2a_task())}\n\n"
            await asyncio.sleep(1)
```

**Priority**: 🔥 High (needed for interop)

---

### 2. **No Authentication/Authorization**
**Issue**: `AgentCard.authentication` field exists but not enforced.

**Impact**: 
- Security risk - any code can invoke agents
- No rate limiting
- No audit trail for access

**Solution**:
```python
# Add to AgentRegistry
class AgentRegistry:
    def __init__(self, ...):
        self._auth_tokens: Dict[str, str] = {}  # agent_name -> token
        self._rate_limits: Dict[str, int] = {}   # agent_name -> requests/min
    
    def authenticate(self, agent_name: str, token: str) -> bool:
        """Verify agent access token"""
        card = self.get(agent_name)
        if not card:
            return False
        
        if card.authentication == "oauth2":
            return self._verify_oauth2_token(token)
        elif card.authentication == "api_key":
            return self._auth_tokens.get(agent_name) == token
        elif card.authentication is None:
            return True  # Public agent
        
        return False
    
    def invoke(self, agent_name: str, message: dict, auth_token: str = None):
        # Authenticate before invoking
        if not self.authenticate(agent_name, auth_token):
            return {"error": "unauthorized", "code": 401}
        
        # Rate limit check
        if self._is_rate_limited(agent_name):
            return {"error": "rate_limit_exceeded", "code": 429}
        
        # Existing invoke logic...
```

**Priority**: 🔥 Critical (security)

---

### 3. **No Retry Logic or Circuit Breaker**
**Issue**: Transient failures in `_route_message()` cause message loss.

**Impact**: 
- Messages lost on network blips
- No graceful degradation
- Cascading failures

**Solution**:
```python
# Add to agent_comm.py
from tenacity import retry, stop_after_attempt, wait_exponential
from circuitbreaker import circuit

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
@circuit(failure_threshold=5, recovery_timeout=60)
def _route_message(self, message: AgentMessage) -> Optional[str]:
    """Route with retry and circuit breaker"""
    # Existing logic...
```

**Dependencies**: `pip install tenacity circuitbreaker`

**Priority**: 🟡 High (reliability)

---

### 4. **Load Balancing TODOs**
**Issue**: Lines 275 & 315 in `agent_registry.py` - round-robin not implemented.

**Impact**: 
- All requests to first agent
- No parallelism
- Single point of failure

**Solution**:
```python
class AgentRegistry:
    def __init__(self, ...):
        self._request_counts: Dict[str, int] = {}  # Track load
    
    def route_by_capability(self, capability: AgentCapability) -> Optional[str]:
        agents = self.find_by_capability(capability)
        if not agents:
            return None
        
        # Load balancing: least-loaded agent
        def get_load(card):
            return self._request_counts.get(card.name, 0)
        
        return min(agents, key=get_load).name
    
    def route_task(self, required_capabilities: List[AgentCapability], ...):
        candidates = self.find_by_capabilities(...)
        
        # Scoring: capability match + load + latency
        scored = []
        for card in candidates:
            score = 0
            score += len(set(card.capabilities) & set(required_capabilities)) * 10
            score -= self._request_counts.get(card.name, 0)  # Penalize busy agents
            score += card.metadata.get("priority", 0)
            scored.append((score, card.name))
        
        return max(scored, key=lambda x: x[0])[1] if scored else None
```

**Priority**: 🟡 Medium (performance)

---

### 5. **No Health Checks**
**Issue**: Agent status in registry never updates automatically.

**Impact**: 
- Routes to dead agents
- No auto-recovery
- Manual intervention required

**Solution**:
```python
class AgentRegistry:
    def start_health_monitor(self, interval_seconds: int = 30):
        """Background thread to ping agents"""
        def health_check_loop():
            while True:
                for name, instance in self._agents.items():
                    try:
                        # Ping agent
                        result = self.invoke(name, {"method": "health"})
                        if result and result.get("status") == "ok":
                            self.mark_available(name)
                        else:
                            self.mark_offline(name)
                    except Exception:
                        self.mark_offline(name)
                
                time.sleep(interval_seconds)
        
        threading.Thread(target=health_check_loop, daemon=True).start()
```

**Priority**: 🟢 Medium (observability)

---

### 6. **ClarificationMixin Not Integrated**
**Issue**: Lines 390-473 in `agent_comm.py` - still uses old pattern, not registry-aware.

**Impact**: 
- Inconsistent routing
- Bypasses registry
- No capability checking

**Solution**: Update `ask_clarification()` to use registry:
```python
class ClarificationMixin:
    def ask_clarification(self, question: str, target_agent: Optional[str] = None, ...):
        from ai_squad.core.agent_registry import get_registry
        
        # Automated mode: use registry for routing
        if getattr(self, 'execution_mode', 'manual') == "automated":
            registry = get_registry()
            
            # If no target, find best agent via capability
            if not target_agent:
                from ai_squad.core.agent_card import AgentCapability
                target_agent = registry.route_by_capability(
                    AgentCapability.REQUIREMENTS_ANALYSIS
                )
            
            # Validate target exists
            if not registry.get(target_agent):
                logger.warning("Unknown target agent: %s", target_agent)
                target_agent = "pm"  # Fallback
        
        # Existing logic...
```

**Priority**: 🟢 Low (refactoring)

---

## 🟡 Non-Critical Improvements

### 7. **No Metrics/Observability**
**Current**: No tracking of agent invocations, latency, errors.

**Add**:
```python
@dataclass
class AgentMetrics:
    total_invocations: int = 0
    successful: int = 0
    failed: int = 0
    avg_latency_ms: float = 0.0
    last_invoked: Optional[str] = None

# Update AgentInstance
instance.metrics = AgentMetrics()

# Track in invoke()
start = time.time()
result = handler(message)
latency = (time.time() - start) * 1000
instance.metrics.total_invocations += 1
instance.metrics.avg_latency_ms = (
    (instance.metrics.avg_latency_ms * (instance.metrics.total_invocations - 1) + latency)
    / instance.metrics.total_invocations
)
```

**Priority**: 🟢 Low (nice-to-have)

---

### 8. **No Broadcast Message Support**
**Issue**: `SignalManager` has broadcast, but `AgentCommunicator` doesn't use it.

**Fix**: Add to `agent_comm.py`:
```python
def broadcast(self, from_agent: str, message: str, context: Dict = None):
    """Send message to all agents"""
    from ai_squad.core.agent_registry import get_registry
    
    registry = get_registry()
    for card in registry.list_available():
        if card.name != from_agent:
            self.ask(
                from_agent=from_agent,
                to_agent=card.name,
                question=message,
                context=context or {},
            )
```

**Priority**: 🟢 Low (feature)

---

### 9. **No Version Compatibility Checks**
**Issue**: `AgentCard.version` exists but not validated.

**Fix**:
```python
from packaging import version

def is_compatible(self, required_version: str) -> bool:
    """Check if agent version meets requirement"""
    return version.parse(self.card.version) >= version.parse(required_version)

# Use in routing
def route_task(self, ..., min_version: str = None):
    candidates = self.find_by_capabilities(...)
    if min_version:
        candidates = [c for c in candidates if c.is_compatible(min_version)]
```

**Priority**: 🟢 Low (future-proofing)

---

### 10. **No A2A Task Lifecycle Events**
**Issue**: WorkItem has `history`, but no event emission.

**Fix**: Add event hooks:
```python
class WorkItem:
    def update_status(self, new_status: WorkStatus):
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.now().isoformat()
        
        # Emit A2A-compliant event
        self._emit_status_change(old_status, new_status)
    
    def _emit_status_change(self, old, new):
        """Emit task status change event (A2A webhook)"""
        event = {
            "type": "task.status.changed",
            "taskId": self.id,
            "oldStatus": old.value,
            "newStatus": new.value,
            "timestamp": self.updated_at,
        }
        # Post to webhook if configured
        webhook_url = self.metadata.get("webhook_url")
        if webhook_url:
            requests.post(webhook_url, json=event)
```

**Priority**: 🟢 Low (webhooks)

---

## 📊 Implementation Roadmap

### Phase 1: Critical (Week 1)
- [ ] Add authentication/authorization to AgentRegistry
- [ ] Implement retry logic with circuit breaker
- [ ] Add health check monitoring

### Phase 2: Core Protocol (Week 2)
- [ ] Implement A2A JSON-RPC 2.0 handler
- [ ] Add SSE streaming for task updates
- [ ] Create REST API endpoints for A2A protocol

### Phase 3: Reliability (Week 3)
- [ ] Implement load balancing (least-loaded)
- [ ] Add metrics collection
- [ ] Integrate ClarificationMixin with registry

### Phase 4: Polish (Week 4)
- [ ] Add broadcast message support
- [ ] Implement version compatibility checks
- [ ] Add task lifecycle webhooks
- [ ] Write integration tests

---

## 🧪 Missing Tests

Current implementation has **no tests** for:
- AgentCard validation
- AgentRegistry routing logic
- WorkItem A2A conversion
- Agent message handling

**Add**:
```python
# tests/test_agent_card.py
def test_agent_card_validation():
    card = PM_CARD
    errors = card.validate_input({"issue_number": "not_an_int"})
    assert "Field 'issue_number' expected int" in str(errors)

# tests/test_agent_registry.py
def test_capability_routing():
    registry = get_registry()
    agent = registry.route_by_capability(AgentCapability.PRD_GENERATION)
    assert agent == "pm"

# tests/test_workitem_a2a.py
def test_a2a_task_roundtrip():
    item = WorkItem(id="test-1", title="Test", description="Desc")
    a2a_task = item.to_a2a_task()
    restored = WorkItem.from_a2a_task(a2a_task)
    assert restored.id == item.id
    assert restored.title == item.title
```

---

## 📚 Missing Documentation

**Need**:
1. **Architecture doc**: Explain hybrid approach (when to use internal vs A2A)
2. **Migration guide**: How to update existing agents
3. **API reference**: AgentCard, AgentRegistry, WorkItem A2A methods
4. **Examples**:
   ```python
   # docs/examples/a2a_agent_discovery.py
   from ai_squad.core import get_registry, AgentCapability
   
   # Find all agents that can review code
   registry = get_registry()
   reviewers = registry.find_by_capability(AgentCapability.CODE_REVIEW)
   print(f"Available reviewers: {[r.name for r in reviewers]}")
   
   # Route a task
   agent = registry.route_task([AgentCapability.PRD_GENERATION])
   print(f"Routing to: {agent}")
   ```

5. **Interop guide**: How to register external A2A agents

---

## 🎯 Recommended Next Actions

### Immediate (Do Now)
1. ✅ Add authentication to `AgentRegistry.invoke()`
2. ✅ Implement retry logic in `agent_comm._route_message()`
3. ✅ Write basic tests for new modules

### Short-term (This Sprint)
4. ⏳ Implement load balancing in routing
5. ⏳ Add health check monitoring
6. ⏳ Document the hybrid approach

### Long-term (Next Sprint)
7. 🔮 Build A2A JSON-RPC handler for external agents
8. 🔮 Add SSE streaming support
9. 🔮 Create REST API for A2A protocol

---

## Summary

**Current State**: 
- ✅ Agent discovery works
- ✅ Capability routing works
- ✅ A2A task schema aligned
- ⚠️ Missing production-critical features

**Recommendation**: 
**Ship current implementation for internal use**, but add authentication + retry logic before exposing to external agents.

**Biggest Wins**:
1. Discovery eliminates hardcoded agent names
2. Capability routing enables dynamic workflows
3. A2A schema enables future interop

**Biggest Risks**:
1. No authentication = security hole
2. No retry = message loss
3. No health checks = routes to dead agents

**Effort Estimate**:
- Phase 1 (Critical): **3-5 days**
- Phase 2 (Protocol): **1-2 weeks**
- Phase 3 (Reliability): **1 week**
- Phase 4 (Polish): **3-5 days**

**Total**: ~4-5 weeks for production-ready A2A hybrid system
