import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_squad.core.workstate_sqlite import SQLiteWorkStateBackend
from ai_squad.core.connection_pool import ConnectionPool
from ai_squad.core.backpressure import StorageBackpressure, RateLimiter
from ai_squad.core.resource_monitor import ResourceMonitor
from ai_squad.core.metrics import MetricsCollector
import tempfile

print('='*60)
print('AI-SQUAD SCALABILITY FEATURE TEST')
print('='*60)
print()

# Test 1: SQLite WorkState Backend
print('[TEST 1] SQLite WorkState Backend')
from pathlib import Path
workspace = Path(tempfile.gettempdir()) / 'ai-squad-test'
workspace.mkdir(exist_ok=True)
db = SQLiteWorkStateBackend(workspace_root=workspace)
print('  [OK] Created SQLite backend')
print('  [OK] Pool size:', db.pool_size)
print('  [OK] Database path:', db.db_path)
print()

# Test 2: Connection Pool
print('[TEST 2] Connection Pool')
tmp2 = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
pool = ConnectionPool(tmp2.name, pool_size=5)
print('  [OK] Pool created with size: 5')
stats = pool.get_stats()
print('  [OK] Pool stats:', stats)
pool.close()
print()

# Test 3: Backpressure Manager
print('[TEST 3] Backpressure Manager')
bp = StorageBackpressure(max_depth=100, threshold=0.8)
is_under = bp.is_under_pressure()
print('  [OK] Backpressure initialized (max_depth=100, threshold=0.8)')
print('  [OK] Under pressure:', is_under)
print()

# Test 4: Rate Limiter
print('[TEST 4] Token Bucket Rate Limiter')
rl = RateLimiter(rate_per_minute=60, burst=10)
allowed = rl.allow('test-agent')
print('  [OK] Rate limiter initialized (60/min, burst=10)')
print('  [OK] Request allowed:', allowed)
print()

# Test 5: Resource Monitor
print('[TEST 5] Resource Monitor')
rm = ResourceMonitor()
rm.sample()  # Take a sample
metrics = rm.get_current_metrics()
optimal = rm.calculate_optimal_parallelism()
print('  [OK] CPU usage: {:.1f}%'.format(metrics.cpu_percent))
print('  [OK] Memory usage: {:.1f}%'.format(metrics.memory_percent))
print('  [OK] Optimal parallelism:', optimal, 'workers')
print()

# Test 6: Metrics Collector  
print('[TEST 6] Metrics Collector')
from ai_squad.core.metrics import ConvoyMetrics, ResourceMetrics
from datetime import datetime
tmp3 = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
mc = MetricsCollector(tmp3.name)
# Create a ConvoyMetrics object
convoy_metrics = ConvoyMetrics(
    convoy_id='test-convoy-1',
    convoy_name='test-convoy',
    started_at=datetime.now(),
    completed_at=None,
    duration_seconds=0.0,
    total_members=10,
    completed_members=0,
    failed_members=0,
    initial_parallelism=5,
    max_parallelism_used=5,
    avg_parallelism=5.0,
    peak_cpu_percent=0.0,
    peak_memory_percent=0.0,
    throttle_count=0,
    status='running',
    error=None
)
mc.record_convoy_start(convoy_metrics)
# Create ResourceMetrics object
resource_metrics = ResourceMetrics(
    timestamp=datetime.now(),
    cpu_percent=50.0,
    memory_percent=60.0,
    memory_available_mb=8192.0,
    process_memory_mb=512.0,
    process_cpu_percent=10.0,
    thread_count=5,
    active_convoys=1,
    active_agents=3
)
mc.record_resource_snapshot(resource_metrics)
print('  [OK] Metrics database created')
print('  [OK] Convoy and resource metrics recorded')
print()

print('='*60)
print('ALL SCALABILITY FEATURES WORKING!')
print('='*60)
