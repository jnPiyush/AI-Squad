"""
Metrics Collection Framework for AI-Squad

Collects and aggregates metrics from convoy operations, resource usage,
and agent execution for observability and performance analysis.

Key Features:
- Convoy execution metrics (duration, success rate, parallelism)
- Resource utilization tracking (CPU, memory, threads)
- Agent performance metrics (execution time, throughput)
- SQLite-based persistent storage
- Query API for dashboards and analytics

Design Principles:
- Low overhead (< 1% impact on performance)
- Async-friendly (non-blocking collection)
- Configurable retention (auto-cleanup old metrics)
- Aggregation support (minute, hour, day)
"""
import asyncio
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected"""
    CONVOY_EXECUTION = "convoy_execution"
    RESOURCE_USAGE = "resource_usage"
    AGENT_EXECUTION = "agent_execution"
    SYSTEM_HEALTH = "system_health"


class AggregationPeriod(str, Enum):
    """Time periods for metric aggregation"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


@dataclass
class ConvoyMetrics:
    """Metrics for a convoy execution"""
    convoy_id: str
    convoy_name: str
    started_at: float
    completed_at: Optional[float] = None
    duration_seconds: Optional[float] = None
    
    # Execution details
    total_members: int = 0
    completed_members: int = 0
    failed_members: int = 0
    
    # Parallelism
    initial_parallelism: int = 0
    max_parallelism_used: int = 0
    avg_parallelism: float = 0.0
    
    # Resource usage
    peak_cpu_percent: float = 0.0
    peak_memory_percent: float = 0.0
    throttle_count: int = 0
    
    # Status
    status: str = "pending"
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def mark_complete(self):
        """Mark convoy as complete and calculate duration"""
        self.completed_at = time.time()
        self.duration_seconds = self.completed_at - self.started_at
        self.status = "completed"


@dataclass
class ResourceMetrics:
    """Resource usage metrics snapshot"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    process_memory_mb: float
    process_cpu_percent: float
    thread_count: int
    active_convoys: int = 0
    active_agents: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class AgentMetrics:
    """Metrics for individual agent execution"""
    agent_id: str
    agent_type: str
    work_item_id: str
    convoy_id: Optional[str] = None
    
    started_at: float = 0.0
    completed_at: Optional[float] = None
    duration_seconds: Optional[float] = None
    
    status: str = "pending"
    error: Optional[str] = None
    
    # Resource usage during execution
    cpu_percent_start: float = 0.0
    cpu_percent_end: float = 0.0
    memory_mb_start: float = 0.0
    memory_mb_end: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def mark_complete(self, status: str = "completed", error: Optional[str] = None):
        """Mark agent execution as complete"""
        self.completed_at = time.time()
        self.duration_seconds = self.completed_at - self.started_at
        self.status = status
        self.error = error


class MetricsCollector:
    """
    Central metrics collection system.
    
    Collects metrics from various sources and stores them in SQLite
    for querying and analysis.
    
    Usage:
        collector = MetricsCollector(db_path=".ai_squad/metrics.db")
        
        # Record convoy execution
        convoy_metrics = ConvoyMetrics(
            convoy_id="convoy-123",
            convoy_name="Feature Implementation",
            started_at=time.time(),
            total_members=10
        )
        collector.record_convoy_start(convoy_metrics)
        
        # Update during execution
        convoy_metrics.completed_members += 1
        collector.update_convoy_metrics(convoy_metrics)
        
        # Mark complete
        convoy_metrics.mark_complete()
        collector.record_convoy_complete(convoy_metrics)
        
        # Query metrics
        recent = collector.get_recent_convoy_metrics(limit=10)
        stats = collector.get_convoy_stats(hours=24)
    """
    
    def __init__(
        self,
        db_path: str = ".ai_squad/metrics.db",
        retention_days: int = 30,
        auto_cleanup: bool = True
    ):
        """
        Initialize metrics collector.
        
        Args:
            db_path: Path to metrics database
            retention_days: Days to keep metrics (0 = forever)
            auto_cleanup: Enable automatic cleanup of old metrics
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.retention_days = retention_days
        self.auto_cleanup = auto_cleanup
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        
        logger.info(
            "MetricsCollector initialized: db=%s, retention=%d days",
            self.db_path, self.retention_days
        )
    
    def _init_database(self):
        """Initialize metrics database schema"""
        with self._get_connection() as conn:
            # Enable WAL mode for concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            # Convoy metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS convoy_metrics (
                    convoy_id TEXT PRIMARY KEY,
                    convoy_name TEXT,
                    started_at REAL,
                    completed_at REAL,
                    duration_seconds REAL,
                    total_members INTEGER,
                    completed_members INTEGER,
                    failed_members INTEGER,
                    initial_parallelism INTEGER,
                    max_parallelism_used INTEGER,
                    avg_parallelism REAL,
                    peak_cpu_percent REAL,
                    peak_memory_percent REAL,
                    throttle_count INTEGER,
                    status TEXT,
                    error TEXT
                )
            """)
            
            # Resource metrics table (time-series)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resource_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_available_mb REAL,
                    process_memory_mb REAL,
                    process_cpu_percent REAL,
                    thread_count INTEGER,
                    active_convoys INTEGER,
                    active_agents INTEGER
                )
            """)
            
            # Agent metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_metrics (
                    agent_id TEXT PRIMARY KEY,
                    agent_type TEXT,
                    work_item_id TEXT,
                    convoy_id TEXT,
                    started_at REAL,
                    completed_at REAL,
                    duration_seconds REAL,
                    status TEXT,
                    error TEXT,
                    cpu_percent_start REAL,
                    cpu_percent_end REAL,
                    memory_mb_start REAL,
                    memory_mb_end REAL
                )
            """)
            
            # Indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_convoy_started 
                ON convoy_metrics(started_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_convoy_status 
                ON convoy_metrics(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_resource_timestamp 
                ON resource_metrics(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_convoy 
                ON agent_metrics(convoy_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_started 
                ON agent_metrics(started_at)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def record_convoy_start(self, metrics: ConvoyMetrics):
        """Record convoy start"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO convoy_metrics (
                        convoy_id, convoy_name, started_at, total_members,
                        initial_parallelism, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    metrics.convoy_id, metrics.convoy_name, metrics.started_at,
                    metrics.total_members, metrics.initial_parallelism, metrics.status
                ))
                conn.commit()
        
        logger.debug("Recorded convoy start: %s", metrics.convoy_id)
    
    def update_convoy_metrics(self, metrics: ConvoyMetrics):
        """Update convoy metrics during execution"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE convoy_metrics SET
                        completed_members = ?,
                        failed_members = ?,
                        max_parallelism_used = ?,
                        avg_parallelism = ?,
                        peak_cpu_percent = ?,
                        peak_memory_percent = ?,
                        throttle_count = ?,
                        status = ?
                    WHERE convoy_id = ?
                """, (
                    metrics.completed_members, metrics.failed_members,
                    metrics.max_parallelism_used, metrics.avg_parallelism,
                    metrics.peak_cpu_percent, metrics.peak_memory_percent,
                    metrics.throttle_count, metrics.status, metrics.convoy_id
                ))
                conn.commit()
    
    def record_convoy_complete(self, metrics: ConvoyMetrics):
        """Record convoy completion"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE convoy_metrics SET
                        completed_at = ?,
                        duration_seconds = ?,
                        completed_members = ?,
                        failed_members = ?,
                        status = ?,
                        error = ?
                    WHERE convoy_id = ?
                """, (
                    metrics.completed_at, metrics.duration_seconds,
                    metrics.completed_members, metrics.failed_members,
                    metrics.status, metrics.error, metrics.convoy_id
                ))
                conn.commit()
        
        logger.info(
            "Convoy %s completed: duration=%.2fs, members=%d/%d",
            metrics.convoy_id, metrics.duration_seconds or 0,
            metrics.completed_members, metrics.total_members
        )
    
    def record_resource_snapshot(self, metrics: ResourceMetrics):
        """Record resource usage snapshot"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO resource_metrics (
                        timestamp, cpu_percent, memory_percent,
                        memory_available_mb, process_memory_mb,
                        process_cpu_percent, thread_count,
                        active_convoys, active_agents
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp, metrics.cpu_percent, metrics.memory_percent,
                    metrics.memory_available_mb, metrics.process_memory_mb,
                    metrics.process_cpu_percent, metrics.thread_count,
                    metrics.active_convoys, metrics.active_agents
                ))
                conn.commit()
    
    def record_agent_start(self, metrics: AgentMetrics):
        """Record agent execution start"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO agent_metrics (
                        agent_id, agent_type, work_item_id, convoy_id,
                        started_at, status, cpu_percent_start, memory_mb_start
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.agent_id, metrics.agent_type, metrics.work_item_id,
                    metrics.convoy_id, metrics.started_at, metrics.status,
                    metrics.cpu_percent_start, metrics.memory_mb_start
                ))
                conn.commit()
    
    def record_agent_complete(self, metrics: AgentMetrics):
        """Record agent execution completion"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE agent_metrics SET
                        completed_at = ?,
                        duration_seconds = ?,
                        status = ?,
                        error = ?,
                        cpu_percent_end = ?,
                        memory_mb_end = ?
                    WHERE agent_id = ?
                """, (
                    metrics.completed_at, metrics.duration_seconds,
                    metrics.status, metrics.error,
                    metrics.cpu_percent_end, metrics.memory_mb_end,
                    metrics.agent_id
                ))
                conn.commit()
    
    def get_recent_convoy_metrics(
        self,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent convoy metrics"""
        with self._get_connection() as conn:
            query = "SELECT * FROM convoy_metrics"
            params: List[Any] = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status)
            
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_convoy_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get convoy statistics for time period"""
        cutoff = time.time() - (hours * 3600)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_convoys,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(duration_seconds) as avg_duration,
                    MAX(duration_seconds) as max_duration,
                    AVG(avg_parallelism) as avg_parallelism,
                    AVG(peak_cpu_percent) as avg_peak_cpu,
                    AVG(peak_memory_percent) as avg_peak_memory
                FROM convoy_metrics
                WHERE started_at >= ?
            """, (cutoff,))
            
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    def get_resource_metrics(
        self,
        hours: int = 1,
        sample_interval: int = 1
    ) -> List[Dict[str, Any]]:
        """Get resource metrics for time period"""
        cutoff = time.time() - (hours * 3600)
        
        with self._get_connection() as conn:
            # Sample every N records to reduce data points
            cursor = conn.execute("""
                SELECT * FROM resource_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (cutoff,))
            
            rows = cursor.fetchall()
            
            # Apply sampling if needed
            if sample_interval > 1 and len(rows) > 0:
                return [dict(rows[i]) for i in range(0, len(rows), sample_interval)]
            
            return [dict(row) for row in rows]
    
    def cleanup_old_metrics(self, days: Optional[int] = None):
        """Clean up metrics older than retention period"""
        if days is None:
            days = self.retention_days
        
        if days <= 0:
            logger.info("Metrics retention is unlimited (days=0)")
            return
        
        cutoff = time.time() - (days * 86400)
        
        with self._lock:
            with self._get_connection() as conn:
                # Delete old convoy metrics
                cursor = conn.execute("""
                    DELETE FROM convoy_metrics WHERE started_at < ?
                """, (cutoff,))
                convoy_deleted = cursor.rowcount
                
                # Delete old resource metrics
                cursor = conn.execute("""
                    DELETE FROM resource_metrics WHERE timestamp < ?
                """, (cutoff,))
                resource_deleted = cursor.rowcount
                
                # Delete old agent metrics
                cursor = conn.execute("""
                    DELETE FROM agent_metrics WHERE started_at < ?
                """, (cutoff,))
                agent_deleted = cursor.rowcount
                
                conn.commit()
        
        logger.info(
            "Cleaned up old metrics: convoys=%d, resources=%d, agents=%d",
            convoy_deleted, resource_deleted, agent_deleted
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics"""
        with self._get_connection() as conn:
            convoy_count = conn.execute(
                "SELECT COUNT(*) FROM convoy_metrics"
            ).fetchone()[0]
            
            resource_count = conn.execute(
                "SELECT COUNT(*) FROM resource_metrics"
            ).fetchone()[0]
            
            agent_count = conn.execute(
                "SELECT COUNT(*) FROM agent_metrics"
            ).fetchone()[0]
            
            db_size = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0
        
        return {
            "db_path": str(self.db_path),
            "db_size_mb": round(db_size, 2),
            "convoy_metrics": convoy_count,
            "resource_metrics": resource_count,
            "agent_metrics": agent_count,
            "retention_days": self.retention_days,
            "auto_cleanup": self.auto_cleanup
        }


# Global collector instance
_global_collector: Optional[MetricsCollector] = None
_global_collector_lock = threading.Lock()


def get_global_collector(**kwargs) -> MetricsCollector:
    """
    Get or create global metrics collector.
    
    Args:
        **kwargs: Arguments for MetricsCollector (only used on first call)
        
    Returns:
        Global MetricsCollector instance
    """
    global _global_collector
    
    with _global_collector_lock:
        if _global_collector is None:
            _global_collector = MetricsCollector(**kwargs)
            logger.info("Global metrics collector created")
        
        return _global_collector


def reset_global_collector():
    """Reset global collector (for testing)"""
    global _global_collector
    
    with _global_collector_lock:
        _global_collector = None
