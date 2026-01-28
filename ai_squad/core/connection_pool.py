"""
Connection Pool for SQLite

Thread-safe connection pooling to support high concurrency (100+ agents).
Implements connection reuse, health checks, and automatic recovery.

Key Features:
- Thread-safe connection management
- Configurable pool size (default 20)
- Automatic connection recovery
- WAL mode optimization
- Connection health monitoring
- Graceful shutdown
"""
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, Generator, Optional

logger = logging.getLogger(__name__)


# SQLite optimization settings (from Phase 0 design)
SQLITE_PRAGMAS = {
    # WAL mode for concurrent reads
    "journal_mode": "WAL",
    
    # Balance between safety and speed
    "synchronous": "NORMAL",  # FULL is slower but safer
    
    # Don't wait forever on locks
    "busy_timeout": "30000",  # 30 seconds
    
    # Larger cache (64MB)
    "cache_size": "-64000",  # Negative = kilobytes
    
    # Allow multiple connections
    "locking_mode": "NORMAL",  # Not EXCLUSIVE
    
    # Auto-checkpoint WAL at 1000 pages
    "wal_autocheckpoint": "1000",
    
    # Optimize for many small transactions
    "temp_store": "MEMORY",
    
    # Enable foreign keys
    "foreign_keys": "ON"
}


class ConnectionPoolError(Exception):
    """Base exception for connection pool errors"""
    pass


class PoolExhaustedError(ConnectionPoolError):
    """Raised when pool cannot provide connection within timeout"""
    pass


class ConnectionHealthError(ConnectionPoolError):
    """Raised when connection health check fails"""
    pass


class ConnectionPool:
    """
    Thread-safe SQLite connection pool.
    
    Provides efficient connection reuse for high concurrency scenarios.
    Supports automatic recovery and health monitoring.
    
    Usage:
        pool = ConnectionPool(db_path="data.db", pool_size=20)
        
        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM table")
            results = cursor.fetchall()
        
        pool.close()  # Cleanup on shutdown
    
    Thread Safety:
        All methods are thread-safe. Multiple agents can safely
        acquire connections concurrently.
    """
    
    def __init__(
        self,
        db_path: str,
        pool_size: int = 20,
        timeout: float = 30.0,
        check_same_thread: bool = False,
        health_check_interval: int = 60
    ):
        """
        Initialize connection pool.
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool
            timeout: Max seconds to wait for connection
            check_same_thread: SQLite check_same_thread setting (False for threading)
            health_check_interval: Seconds between health checks per connection
        """
        self.db_path = str(db_path)
        self.pool_size = pool_size
        self.timeout = timeout
        self.check_same_thread = check_same_thread
        self.health_check_interval = health_check_interval
        
        # Thread-safe queue for available connections
        self._pool: Queue = Queue(maxsize=pool_size)
        
        # Track all connections for management
        self._all_connections: list = []
        self._lock = threading.RLock()
        
        # Connection metadata (health checks, creation times)
        self._conn_metadata: Dict[int, Dict[str, float]] = {}
        
        # Pool state
        self._closed = False
        self._initialized = False
        
        # Statistics
        self._stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_acquisitions": 0,
            "total_releases": 0,
            "health_check_failures": 0,
            "reconnections": 0
        }
        self._stats_lock = threading.Lock()
        
        # Initialize pool
        self._init_pool()
        
        logger.info(
            "ConnectionPool initialized: db=%s, size=%d, timeout=%.1fs",
            self.db_path, self.pool_size, self.timeout
        )
    
    def _init_pool(self) -> None:
        """Initialize pool with connections"""
        with self._lock:
            if self._initialized:
                return
            
            for i in range(self.pool_size):
                try:
                    conn = self._create_connection()
                    self._pool.put(conn, block=False)
                    self._all_connections.append(conn)
                    
                    with self._stats_lock:
                        self._stats["total_connections"] += 1
                        
                except Exception as e:
                    logger.error(
                        "Failed to create connection %d/%d: %s",
                        i + 1, self.pool_size, e
                    )
                    raise ConnectionPoolError(f"Pool initialization failed: {e}")
            
            self._initialized = True
            logger.info("Created %d database connections", self.pool_size)
    
    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new optimized SQLite connection.
        
        Returns:
            Configured SQLite connection
            
        Raises:
            ConnectionPoolError: If connection cannot be created
        """
        try:
            # Create connection
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=self.check_same_thread,
                timeout=self.timeout,
                isolation_level=None  # Autocommit mode for WAL
            )
            
            # Apply optimization PRAGMAs
            for pragma, value in SQLITE_PRAGMAS.items():
                conn.execute(f"PRAGMA {pragma}={value}")
            
            # Row factory for dict-like access
            conn.row_factory = sqlite3.Row
            
            # Store metadata separately (can't set attributes on Connection objects)
            # We'll track health check times in a separate dict
            if not hasattr(self, '_conn_metadata'):
                self._conn_metadata = {}
            
            conn_id = id(conn)
            self._conn_metadata[conn_id] = {
                'last_health_check': time.time(),
                'creation_time': time.time()
            }
            
            return conn
            
        except sqlite3.Error as e:
            logger.error("Failed to create connection: %s", e)
            raise ConnectionPoolError(f"Connection creation failed: {e}")
    
    def _health_check(self, conn: sqlite3.Connection) -> bool:
        """
        Check if connection is healthy.
        
        Args:
            conn: Connection to check
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple query to verify connection
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
            
        except (sqlite3.Error, AttributeError):
            return False
    
    def _maybe_reconnect(self, conn: sqlite3.Connection) -> sqlite3.Connection:
        """
        Check connection health and reconnect if needed.
        
        Args:
            conn: Connection to check
            
        Returns:
            Healthy connection (original or new)
        """
        # Check if health check is due
        now = time.time()
        conn_id = id(conn)
        metadata = self._conn_metadata.get(conn_id, {})
        last_check = metadata.get('last_health_check', 0)
        
        if now - last_check < self.health_check_interval:
            return conn  # Too soon to recheck
        
        # Perform health check
        if self._health_check(conn):
            self._conn_metadata[conn_id]['last_health_check'] = now
            return conn
        
        # Connection unhealthy - reconnect
        logger.warning("Connection failed health check, reconnecting...")
        
        try:
            # Remove old metadata
            self._conn_metadata.pop(conn_id, None)
            conn.close()
        except Exception as e:
            logger.debug("Error closing unhealthy connection: %s", e)
        
        try:
            new_conn = self._create_connection()
            
            with self._stats_lock:
                self._stats["reconnections"] += 1
                self._stats["health_check_failures"] += 1
            
            logger.info("Connection reconnected successfully")
            return new_conn
            
        except Exception as e:
            logger.error("Failed to reconnect: %s", e)
            raise ConnectionHealthError(f"Reconnection failed: {e}")
    
    @contextmanager
    def get_connection(self, timeout: Optional[float] = None) -> Generator[sqlite3.Connection, None, None]:
        """
        Get connection from pool (context manager).
        
        Args:
            timeout: Override default timeout (seconds)
            
        Yields:
            SQLite connection
            
        Raises:
            PoolExhaustedError: If no connection available within timeout
            ConnectionPoolError: If pool is closed
            
        Example:
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM users")
                results = cursor.fetchall()
        """
        if self._closed:
            raise ConnectionPoolError("Connection pool is closed")
        
        effective_timeout = timeout if timeout is not None else self.timeout
        conn = None
        
        try:
            # Acquire connection from pool
            try:
                conn = self._pool.get(timeout=effective_timeout)
            except Empty:
                raise PoolExhaustedError(
                    f"No connection available within {effective_timeout}s "
                    f"(pool_size={self.pool_size})"
                )
            
            with self._stats_lock:
                self._stats["total_acquisitions"] += 1
                self._stats["active_connections"] += 1
            
            # Health check and reconnect if needed
            conn = self._maybe_reconnect(conn)
            
            # Yield connection to caller
            yield conn
            
        except Exception as e:
            # Rollback on error
            if conn:
                try:
                    conn.rollback()
                except Exception as rollback_error:
                    logger.error("Rollback failed: %s", rollback_error)
            raise
            
        finally:
            # Always return connection to pool
            if conn:
                try:
                    self._pool.put(conn, block=False)
                    
                    with self._stats_lock:
                        self._stats["total_releases"] += 1
                        self._stats["active_connections"] -= 1
                        
                except Exception as e:
                    logger.error("Failed to return connection to pool: %s", e)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics.
        
        Returns:
            Dictionary of statistics:
                - total_connections: Total connections created
                - active_connections: Currently in use
                - available_connections: Available in pool
                - pool_utilization: Percentage of pool in use
                - total_acquisitions: Total connection checkouts
                - total_releases: Total connection returns
                - health_check_failures: Failed health checks
                - reconnections: Successful reconnections
        """
        with self._stats_lock:
            available = self._pool.qsize()
            utilization = (
                (self._stats["active_connections"] / self.pool_size * 100)
                if self.pool_size > 0 else 0
            )
            
            return {
                **self._stats,
                "available_connections": available,
                "pool_utilization": round(utilization, 2),
                "pool_size": self.pool_size
            }
    
    def close(self) -> None:
        """
        Close all connections and shutdown pool.
        
        Should be called during application shutdown.
        """
        with self._lock:
            if self._closed:
                return
            
            self._closed = True
            
            # Close all connections
            closed_count = 0
            for conn in self._all_connections:
                try:
                    # Remove metadata
                    self._conn_metadata.pop(id(conn), None)
                    conn.close()
                    closed_count += 1
                except Exception as e:
                    logger.error("Error closing connection: %s", e)
            
            self._all_connections.clear()
            self._conn_metadata.clear()
            
            # Clear pool queue
            while not self._pool.empty():
                try:
                    self._pool.get_nowait()
                except Empty:
                    break
            
            logger.info(
                "ConnectionPool closed: %d connections closed",
                closed_count
            )
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close pool"""
        self.close()
        return False
    
    def __del__(self):
        """Cleanup on garbage collection"""
        if not self._closed:
            self.close()


# Global pool instance (initialized on first use)
_global_pool: Optional[ConnectionPool] = None
_global_pool_lock = threading.Lock()


def get_global_pool(
    db_path: Optional[str] = None,
    pool_size: int = 20,
    **kwargs
) -> ConnectionPool:
    """
    Get or create global connection pool singleton.
    
    Args:
        db_path: Database path (required on first call)
        pool_size: Pool size (only used on first initialization)
        **kwargs: Additional ConnectionPool arguments
        
    Returns:
        Global ConnectionPool instance
        
    Raises:
        ValueError: If db_path not provided on first call
    """
    global _global_pool
    
    with _global_pool_lock:
        if _global_pool is None:
            if db_path is None:
                raise ValueError(
                    "db_path required for first get_global_pool() call"
                )
            
            _global_pool = ConnectionPool(
                db_path=db_path,
                pool_size=pool_size,
                **kwargs
            )
            logger.info("Global connection pool created")
        
        return _global_pool


def close_global_pool() -> None:
    """Close global connection pool (for testing/shutdown)"""
    global _global_pool
    
    with _global_pool_lock:
        if _global_pool:
            _global_pool.close()
            _global_pool = None
            logger.info("Global connection pool closed")
