# Scalability Implementation Plan

**Date**: January 28, 2026  
**Status**: 🟢 **READY FOR IMPLEMENTATION**  
**Quality Priority**: Production-ready, cautious implementation

---

## Phase 0: Design & Planning (CURRENT PHASE)

### Objective
Establish design decisions and validation strategy before implementation

### 1. Consistency Model Design ✅

**Decision**: **Optimistic Concurrency Control** with version column

**Rationale**:
- Prevents lost updates in concurrent scenarios
- Better scalability than pessimistic locking
- Clear conflict detection and resolution
- Industry standard for distributed systems

**Implementation Strategy**:
```python
# Add to WorkItem dataclass
@dataclass
class WorkItem:
    # ... existing fields ...
    version: int = 1  # Optimistic lock version
    
    def increment_version(self):
        """Increment version on each update"""
        self.version += 1
        self.updated_at = datetime.now().isoformat()
```

**Conflict Resolution**:
1. **Automatic retry** (3 attempts) with exponential backoff
2. **Merge strategy**: 
   - Status changes: Last-write-wins
   - Artifacts: Union (append new artifacts)
   - Context: Deep merge (non-overlapping keys)
3. **Manual resolution** for critical conflicts (status transitions)

**Error Handling**:
```python
class ConcurrentUpdateError(Exception):
    """Raised when optimistic lock version mismatch detected"""
    def __init__(self, item_id, expected_version, actual_version):
        self.item_id = item_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Work item {item_id} version mismatch: "
            f"expected {expected_version}, got {actual_version}"
        )
```

---

### 2. Backpressure & Rate Limiting Design ✅

**Objectives**:
- Prevent queue saturation
- Protect system resources
- Fair resource allocation across agents

**Strategy 1: Queue Depth Monitoring**
```python
class StorageBackpressure:
    """Monitor and control queue depth"""
    
    MAX_QUEUE_DEPTH = 100  # Configurable
    BACKPRESSURE_THRESHOLD = 80  # 80% of max
    
    def __init__(self):
        self._queue_depth = 0
        self._queue_lock = threading.Lock()
    
    def acquire(self, timeout=30):
        """Acquire slot in queue, block if full"""
        with self._queue_lock:
            if self._queue_depth >= self.MAX_QUEUE_DEPTH:
                raise BackpressureError("Storage queue saturated")
            self._queue_depth += 1
    
    def release(self):
        """Release slot"""
        with self._queue_lock:
            self._queue_depth -= 1
    
    def is_under_pressure(self) -> bool:
        """Check if approaching saturation"""
        return self._queue_depth >= self.BACKPRESSURE_THRESHOLD
```

**Strategy 2: Per-Agent Rate Limiting**
```python
class RateLimiter:
    """Token bucket rate limiter per agent"""
    
    def __init__(self, rate_per_minute=100, burst=20):
        self.rate = rate_per_minute
        self.burst = burst
        self.tokens: Dict[str, List[float]] = defaultdict(list)
    
    def allow(self, agent: str) -> bool:
        """Check if agent can perform operation"""
        now = time.time()
        window_start = now - 60  # 1 minute window
        
        # Remove old tokens
        self.tokens[agent] = [
            t for t in self.tokens[agent] 
            if t > window_start
        ]
        
        if len(self.tokens[agent]) >= self.rate:
            return False
        
        self.tokens[agent].append(now)
        return True
    
    def wait_time(self, agent: str) -> float:
        """Calculate wait time until next token available"""
        if self.allow(agent):
            return 0.0
        
        # Return time until oldest token expires
        oldest = self.tokens[agent][0]
        return max(0, 60 - (time.time() - oldest))
```

**Strategy 3: Broadcast Optimization (Fan-out on Read)**
```sql
-- Current: N writes for N agents
-- Optimized: 1 write + read-time expansion

CREATE TABLE IF NOT EXISTS broadcast_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    expires_at REAL,
    FOREIGN KEY (message_id) REFERENCES signal_messages(id)
);

CREATE TABLE IF NOT EXISTS agent_broadcast_cursors (
    agent_name TEXT PRIMARY KEY,
    last_checked_at REAL NOT NULL
);
```

---

### 3. SQLite Optimization Configuration ✅

**PRAGMA Settings**:
```python
SQLITE_PRAGMAS = {
    # WAL mode for concurrent reads
    "journal_mode": "WAL",
    
    # Balance between safety and speed
    "synchronous": "NORMAL",  # FULL is slower but safer
    
    # Don't wait forever on locks
    "busy_timeout": "30000",  # 30 seconds
    
    # Larger cache (64MB)
    "cache_size": "-64000",  # Negative = KB
    
    # Allow multiple connections
    "locking_mode": "NORMAL",  # Not EXCLUSIVE
    
    # Auto-checkpoint WAL at 1000 pages
    "wal_autocheckpoint": "1000",
    
    # Optimize for many small transactions
    "temp_store": "MEMORY",
    
    # Enable foreign keys
    "foreign_keys": "ON"
}
```

**Connection Pool Configuration**:
```python
class ConnectionPool:
    """Thread-safe SQLite connection pool"""
    
    def __init__(self, db_path: str, pool_size: int = 20):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool = Queue(maxsize=pool_size)
        self._init_pool()
    
    def _init_pool(self):
        """Initialize pool with configured connections"""
        for i in range(self.pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _create_connection(self):
        """Create optimized SQLite connection"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # CRITICAL for threading
            timeout=30.0,
            isolation_level=None  # Autocommit for WAL
        )
        
        # Apply optimizations
        for pragma, value in SQLITE_PRAGMAS.items():
            conn.execute(f"PRAGMA {pragma}={value}")
        
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        conn = self._pool.get(timeout=30)
        try:
            yield conn
            # Auto-commit (isolation_level=None)
        except Exception:
            # Rollback on error
            conn.rollback()
            raise
        finally:
            self._pool.put(conn)
```

---

### 4. Observability & Metrics Design ✅

**Metrics to Collect**:
```python
CORE_METRICS = {
    # WorkState metrics
    "workstate.create.latency": "histogram",
    "workstate.update.latency": "histogram",
    "workstate.transaction.duration": "histogram",
    "workstate.lock.wait_time": "histogram",
    "workstate.version_conflicts": "counter",
    
    # Signal metrics
    "signal.send.latency": "histogram",
    "signal.inbox.depth": "gauge",
    "signal.broadcast.fanout": "histogram",
    "signal.rate_limit_hits": "counter",
    
    # Convoy metrics
    "convoy.active_agents": "gauge",
    "convoy.execution.duration": "histogram",
    "convoy.parallelism": "gauge",
    
    # Storage metrics
    "storage.queue_depth": "gauge",
    "storage.connection_pool.utilization": "gauge",
    "storage.backpressure_events": "counter",
    
    # Resource metrics
    "system.memory_usage_mb": "gauge",
    "system.cpu_percent": "gauge",
}
```

**Metrics Collection System**:
```python
class MetricsCollector:
    """Simple in-memory metrics collector"""
    
    def __init__(self, retention_seconds=3600):
        self.retention = retention_seconds
        self._metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=10000)
        )
        self._lock = threading.Lock()
    
    def record(self, name: str, value: float, **labels):
        """Record metric value"""
        with self._lock:
            self._metrics[name].append({
                "value": value,
                "timestamp": time.time(),
                "labels": labels
            })
    
    def get_histogram(self, name: str, window_sec=60):
        """Get P50, P95, P99 for histogram metric"""
        now = time.time()
        cutoff = now - window_sec
        
        with self._lock:
            values = [
                m["value"] for m in self._metrics[name]
                if m["timestamp"] > cutoff
            ]
        
        if not values:
            return None
        
        values.sort()
        n = len(values)
        
        return {
            "count": n,
            "min": values[0],
            "max": values[-1],
            "p50": values[int(n * 0.5)],
            "p95": values[int(n * 0.95)],
            "p99": values[int(n * 0.99)],
        }
    
    def get_counter(self, name: str, window_sec=60):
        """Get sum for counter metric"""
        now = time.time()
        cutoff = now - window_sec
        
        with self._lock:
            count = len([
                m for m in self._metrics[name]
                if m["timestamp"] > cutoff
            ])
        
        return count
    
    def get_gauge(self, name: str):
        """Get latest value for gauge metric"""
        with self._lock:
            if not self._metrics[name]:
                return None
            return self._metrics[name][-1]["value"]

# Global singleton
metrics = MetricsCollector()
```

**Instrumentation Decorators**:
```python
def instrument(metric_name: str):
    """Decorator to instrument function with metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            success = False
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                duration = time.time() - start
                metrics.record(
                    f"{metric_name}.latency",
                    duration,
                    status="success" if success else "error"
                )
        return wrapper
    return decorator
```

---

### 5. Benchmark Harness Design ✅

**Benchmark Framework**:
```python
class ScalabilityBenchmark:
    """Benchmark suite for scalability testing"""
    
    def __init__(self, workstate_mgr, signal_mgr):
        self.workstate = workstate_mgr
        self.signal = signal_mgr
        self.results = []
    
    async def benchmark_concurrent_workstate(
        self,
        num_agents: int,
        ops_per_agent: int
    ):
        """Benchmark concurrent WorkState operations"""
        
        async def agent_workload(agent_id: int):
            """Simulate agent workload"""
            latencies = []
            
            for i in range(ops_per_agent):
                # Create work item
                start = time.time()
                item = self.workstate.create_work_item(
                    title=f"Agent {agent_id} Task {i}",
                    description="Benchmark task",
                    agent=f"agent-{agent_id}"
                )
                latencies.append(("create", time.time() - start))
                
                # Update status
                start = time.time()
                self.workstate.transition_status(
                    item.id,
                    WorkStatus.IN_PROGRESS
                )
                latencies.append(("update", time.time() - start))
                
                # Add artifact
                start = time.time()
                item.add_artifact(f"output-{i}.md")
                self.workstate.update_work_item(item)
                latencies.append(("artifact", time.time() - start))
                
                # Complete
                start = time.time()
                self.workstate.transition_status(item.id, WorkStatus.DONE)
                latencies.append(("complete", time.time() - start))
            
            return latencies
        
        # Run agents concurrently
        print(f"Starting {num_agents} concurrent agents...")
        start_time = time.time()
        
        tasks = [agent_workload(i) for i in range(num_agents)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Aggregate results
        all_latencies = {}
        for agent_results in results:
            for op_type, latency in agent_results:
                if op_type not in all_latencies:
                    all_latencies[op_type] = []
                all_latencies[op_type].append(latency)
        
        # Calculate statistics
        stats = {}
        for op_type, latencies in all_latencies.items():
            latencies.sort()
            n = len(latencies)
            stats[op_type] = {
                "count": n,
                "p50_ms": latencies[int(n * 0.5)] * 1000,
                "p95_ms": latencies[int(n * 0.95)] * 1000,
                "p99_ms": latencies[int(n * 0.99)] * 1000,
                "max_ms": max(latencies) * 1000
            }
        
        return {
            "num_agents": num_agents,
            "ops_per_agent": ops_per_agent,
            "total_time_sec": total_time,
            "throughput_ops_sec": (num_agents * ops_per_agent * 4) / total_time,
            "operation_stats": stats
        }
    
    async def run_suite(self):
        """Run complete benchmark suite"""
        configs = [
            (1, 100),    # Baseline
            (10, 50),    # Light load
            (50, 20),    # Medium load
            (100, 10),   # Heavy load
        ]
        
        results = []
        for num_agents, ops_per_agent in configs:
            print(f"\n{'='*60}")
            print(f"Benchmark: {num_agents} agents × {ops_per_agent} ops")
            print(f"{'='*60}")
            
            result = await self.benchmark_concurrent_workstate(
                num_agents,
                ops_per_agent
            )
            
            results.append(result)
            
            print(f"\nResults:")
            print(f"  Total time: {result['total_time_sec']:.2f}s")
            print(f"  Throughput: {result['throughput_ops_sec']:.1f} ops/sec")
            print(f"\nOperation Latencies:")
            for op, stats in result['operation_stats'].items():
                print(f"  {op:12} P99: {stats['p99_ms']:6.2f}ms  "
                      f"Max: {stats['max_ms']:6.2f}ms")
        
        return results

# Success criteria validation
def validate_results(results):
    """Validate against success criteria"""
    failures = []
    
    for result in results:
        num_agents = result['num_agents']
        
        if num_agents == 100:
            # Check 100-agent criteria
            for op, stats in result['operation_stats'].items():
                if stats['p99_ms'] > 200:  # 200ms threshold
                    failures.append(
                        f"P99 latency too high: {op} = {stats['p99_ms']:.2f}ms"
                    )
            
            if result['throughput_ops_sec'] < 100:
                failures.append(
                    f"Throughput too low: {result['throughput_ops_sec']:.1f} ops/sec"
                )
    
    if failures:
        print("\n❌ Benchmark FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return False
    else:
        print("\n✅ All benchmarks PASSED")
        return True
```

---

## Implementation Phases Summary

### Phase 1: SQLite WorkState (1 week)
**Days 1-3**: Implementation
- Create SQLite backend with optimizations
- Add optimistic locking
- Implement compare-and-swap
- Add retry logic

**Days 4-5**: Testing
- Unit tests
- Concurrency tests
- Benchmark execution
- Documentation

### Phase 2: Signal Optimizations (1 week)
- Connection pooling
- Backpressure & rate limiting
- Broadcast optimization
- Performance testing

### Phase 3: Convoy Auto-tuning (1 week)
- Resource monitoring
- Dynamic parallelism
- Memory profiling
- Integration testing

### Phase 4: Production Readiness (1 week)
- Observability & metrics
- Monitoring dashboard
- Storage maintenance
- Documentation & runbooks

---

## Quality Assurance Checklist

### Code Quality
- [ ] Type hints for all public APIs
- [ ] Docstrings following Google style
- [ ] Error handling for all edge cases
- [ ] Logging at appropriate levels
- [ ] No hard-coded values (use config)

### Testing
- [ ] Unit tests (≥80% coverage)
- [ ] Integration tests for workflows
- [ ] Concurrency tests (race conditions)
- [ ] Performance tests (benchmarks)
- [ ] Error scenario tests

### Documentation
- [ ] API documentation complete
- [ ] Architecture diagrams updated
- [ ] Migration guide (even if not needed)
- [ ] Troubleshooting guide
- [ ] Performance tuning guide

### Production Readiness
- [ ] Metrics & monitoring in place
- [ ] Alerting configured
- [ ] Runbooks created
- [ ] Disaster recovery tested
- [ ] Performance validated

---

## Risk Mitigation

### Risk Matrix
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Version conflicts frequent | Medium | High | Exponential backoff retry |
| Queue saturation | High | Medium | Backpressure + rate limits |
| Memory leaks | Low | High | Profiling + monitoring |
| Data corruption | Very Low | Critical | WAL + backups + validation |
| Performance regression | Medium | High | Continuous benchmarking |

### Rollback Plan
1. Keep current JSON implementation as fallback (configurable)
2. Add feature flag: `USE_SQLITE_BACKEND=true|false`
3. Monitor metrics closely during rollout
4. Gradual rollout: 10% → 50% → 100%
5. Automated rollback on metric thresholds

---

## Next Steps

1. ✅ Review and approve this implementation plan
2. ⏳ Begin Phase 1 implementation (SQLite WorkState)
3. ⏳ Set up continuous benchmarking
4. ⏳ Implement metrics collection
5. ⏳ Create production runbooks

**Estimated Total Time**: 3-4 weeks for production-ready implementation

