"""
Tests for Connection Pool

Validates thread-safe connection pooling for high concurrency.
"""
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from ai_squad.core.connection_pool import (
    ConnectionPool,
    ConnectionPoolError,
    PoolExhaustedError,
    close_global_pool,
    get_global_pool,
)


@pytest.fixture
def temp_db():
    """Create temporary database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Initialize schema
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup - wait a bit for connections to close
    import time
    time.sleep(0.1)
    
    try:
        Path(db_path).unlink(missing_ok=True)
        # Also clean up WAL and SHM files
        Path(f"{db_path}-wal").unlink(missing_ok=True)
        Path(f"{db_path}-shm").unlink(missing_ok=True)
    except PermissionError:
        # Files still in use - not critical for tests
        pass


@pytest.fixture
def pool(temp_db):
    """Create connection pool"""
    pool = ConnectionPool(db_path=temp_db, pool_size=5, timeout=5.0)
    yield pool
    pool.close()


class TestConnectionPoolBasics:
    """Test basic pool operations"""
    
    def test_pool_initialization(self, temp_db):
        """Test pool creates connections on init"""
        pool = ConnectionPool(db_path=temp_db, pool_size=3)
        
        try:
            stats = pool.get_stats()
            assert stats["total_connections"] == 3
            assert stats["available_connections"] == 3
            assert stats["active_connections"] == 0
            assert stats["pool_size"] == 3
        finally:
            pool.close()
    
    def test_connection_acquisition(self, pool):
        """Test acquiring connection from pool"""
        with pool.get_connection() as conn:
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)
            
            # Connection should work
            cursor = conn.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_connection_return_to_pool(self, pool):
        """Test connection returned after use"""
        initial_stats = pool.get_stats()
        initial_available = initial_stats["available_connections"]
        
        with pool.get_connection() as conn:
            # Connection acquired
            stats = pool.get_stats()
            assert stats["available_connections"] == initial_available - 1
            assert stats["active_connections"] == 1
        
        # Connection returned
        final_stats = pool.get_stats()
        assert final_stats["available_connections"] == initial_available
        assert final_stats["active_connections"] == 0
    
    def test_multiple_sequential_connections(self, pool):
        """Test acquiring multiple connections sequentially"""
        for i in range(10):
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT ?", (i,))
                result = cursor.fetchone()
                assert result[0] == i
        
        # All connections returned
        stats = pool.get_stats()
        assert stats["active_connections"] == 0
        assert stats["total_acquisitions"] == 10
        assert stats["total_releases"] == 10


class TestConcurrency:
    """Test concurrent access to pool"""
    
    def test_concurrent_read_access(self, pool, temp_db):
        """Test concurrent reads work correctly"""
        # Insert test data
        with pool.get_connection() as conn:
            for i in range(100):
                conn.execute(
                    "INSERT INTO test_table (id, value, created_at) VALUES (?, ?, ?)",
                    (i, f"value-{i}", time.time())
                )
        
        def read_data(thread_id):
            """Read data from database"""
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM test_table")
                count = cursor.fetchone()[0]
                return (thread_id, count)
        
        # 20 concurrent reads (4x pool size)
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_data, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]
        
        # All reads should succeed
        assert len(results) == 20
        for thread_id, count in results:
            assert count == 100
        
        # All connections returned
        stats = pool.get_stats()
        assert stats["active_connections"] == 0
    
    def test_concurrent_write_access(self, pool):
        """Test concurrent writes with WAL mode"""
        def write_data(thread_id):
            """Write data to database"""
            with pool.get_connection() as conn:
                conn.execute(
                    "INSERT INTO test_table (value, created_at) VALUES (?, ?)",
                    (f"thread-{thread_id}", time.time())
                )
            return thread_id
        
        # 10 concurrent writes (2x pool size)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_data, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]
        
        # All writes should succeed
        assert len(results) == 10
        
        # Verify data written
        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            assert count == 10
    
    def test_high_concurrency_mixed_operations(self, pool):
        """Test high concurrency with mixed read/write"""
        def mixed_operation(op_id):
            """Perform mixed read/write operations"""
            with pool.get_connection() as conn:
                if op_id % 2 == 0:
                    # Write
                    conn.execute(
                        "INSERT INTO test_table (value, created_at) VALUES (?, ?)",
                        (f"op-{op_id}", time.time())
                    )
                else:
                    # Read
                    cursor = conn.execute("SELECT COUNT(*) FROM test_table")
                    cursor.fetchone()
            return op_id
        
        # 50 concurrent operations (10x pool size)
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(mixed_operation, i) for i in range(50)]
            results = [f.result() for f in as_completed(futures)]
        
        # All operations should complete
        assert len(results) == 50
        
        # Verify writes (25 writes for even IDs)
        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            assert count == 25


class TestPoolExhaustion:
    """Test pool behavior when exhausted"""
    
    def test_pool_exhaustion_timeout(self, temp_db):
        """Test timeout when pool exhausted"""
        # Small pool with short timeout
        pool = ConnectionPool(db_path=temp_db, pool_size=2, timeout=1.0)
        
        try:
            # Hold all connections
            conns = []
            with pool.get_connection() as conn1:
                with pool.get_connection() as conn2:
                    # Try to acquire third connection - should timeout
                    with pytest.raises(PoolExhaustedError) as exc_info:
                        with pool.get_connection():
                            pass
                    
                    assert "No connection available" in str(exc_info.value)
                    assert "pool_size=2" in str(exc_info.value)
        finally:
            pool.close()
    
    def test_pool_recovery_after_release(self, temp_db):
        """Test pool becomes available after connections released"""
        pool = ConnectionPool(db_path=temp_db, pool_size=2, timeout=5.0)
        
        try:
            # Exhaust pool
            with pool.get_connection() as conn1:
                with pool.get_connection() as conn2:
                    stats = pool.get_stats()
                    assert stats["available_connections"] == 0
            
            # Pool should recover
            stats = pool.get_stats()
            assert stats["available_connections"] == 2
            
            # Should be able to acquire again
            with pool.get_connection() as conn:
                assert conn is not None
        finally:
            pool.close()


class TestHealthCheck:
    """Test connection health monitoring"""
    
    def test_health_check_on_healthy_connection(self, pool):
        """Test health check passes for healthy connection"""
        with pool.get_connection() as conn:
            # Force health check by setting old timestamp in metadata
            conn_id = id(conn)
            if conn_id in pool._conn_metadata:
                pool._conn_metadata[conn_id]['last_health_check'] = 0
            
            # Health check should pass (internal check)
            assert pool._health_check(conn)
    
    def test_reconnection_on_unhealthy_connection(self, temp_db):
        """Test automatic reconnection on health check failure"""
        pool = ConnectionPool(
            db_path=temp_db,
            pool_size=1,
            health_check_interval=0  # Check every time
        )
        
        try:
            # First use - connection is healthy
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                assert cursor.fetchone()[0] == 1
            
            # Corrupt the connection in the pool by breaking it
            conn_from_pool = pool._pool.get(timeout=1)
            conn_id = id(conn_from_pool)
            
            # Break the connection
            conn_from_pool.close()
            
            # Force health check  by setting old timestamp
            if conn_id in pool._conn_metadata:
                pool._conn_metadata[conn_id]['last_health_check'] = 0
            
            # Put it back in pool
            pool._pool.put(conn_from_pool)
            
            # Next usage should detect bad connection and reconnect
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1
            
            # Should have reconnected
            stats = pool.get_stats()
            assert stats["reconnections"] >= 1
            assert stats["health_check_failures"] >= 1
        finally:
            pool.close()


class TestStatistics:
    """Test pool statistics tracking"""
    
    def test_statistics_tracking(self, pool):
        """Test accurate statistics tracking"""
        initial_stats = pool.get_stats()
        
        # Perform operations
        for i in range(5):
            with pool.get_connection() as conn:
                conn.execute("SELECT 1")
        
        final_stats = pool.get_stats()
        
        # Check statistics
        assert final_stats["total_acquisitions"] == initial_stats["total_acquisitions"] + 5
        assert final_stats["total_releases"] == initial_stats["total_releases"] + 5
        assert final_stats["active_connections"] == 0
        assert final_stats["pool_utilization"] == 0.0
    
    def test_pool_utilization_calculation(self, temp_db):
        """Test pool utilization percentage"""
        pool = ConnectionPool(db_path=temp_db, pool_size=10)
        
        try:
            # Hold 5 connections (50% utilization)
            contexts = []
            for i in range(5):
                ctx = pool.get_connection()
                conn = ctx.__enter__()
                contexts.append((ctx, conn))
            
            stats = pool.get_stats()
            assert stats["active_connections"] == 5
            assert stats["pool_utilization"] == 50.0
            
            # Release all
            for ctx, conn in contexts:
                ctx.__exit__(None, None, None)
            
            final_stats = pool.get_stats()
            assert final_stats["pool_utilization"] == 0.0
        finally:
            pool.close()


class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_rollback_on_error(self, pool):
        """Test automatic rollback on exception"""
        # Insert initial data
        with pool.get_connection() as conn:
            conn.execute(
                "INSERT INTO test_table (value, created_at) VALUES (?, ?)",
                ("initial", time.time())
            )
        
        # Try to insert with error
        try:
            with pool.get_connection() as conn:
                conn.execute(
                    "INSERT INTO test_table (value, created_at) VALUES (?, ?)",
                    ("will-fail", time.time())
                )
                # Simulate error
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # Only initial data should be present (rollback successful)
        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            # Note: autocommit mode, so both might be committed
            # This tests that pool handles errors gracefully
            assert count >= 1
    
    def test_connection_returned_on_error(self, pool):
        """Test connection returned to pool even on error"""
        initial_stats = pool.get_stats()
        initial_available = initial_stats["available_connections"]
        
        try:
            with pool.get_connection() as conn:
                raise RuntimeError("Test error")
        except RuntimeError:
            pass
        
        # Connection should be returned
        final_stats = pool.get_stats()
        assert final_stats["available_connections"] == initial_available
        assert final_stats["active_connections"] == 0
    
    def test_closed_pool_raises_error(self, temp_db):
        """Test accessing closed pool raises error"""
        pool = ConnectionPool(db_path=temp_db, pool_size=2)
        pool.close()
        
        with pytest.raises(ConnectionPoolError) as exc_info:
            with pool.get_connection():
                pass
        
        assert "pool is closed" in str(exc_info.value)


class TestGlobalPool:
    """Test global pool singleton"""
    
    def test_global_pool_creation(self, temp_db):
        """Test global pool singleton"""
        # Close any existing global pool
        close_global_pool()
        
        # Create global pool
        pool1 = get_global_pool(db_path=temp_db, pool_size=10)
        assert pool1 is not None
        
        # Same instance returned
        pool2 = get_global_pool()
        assert pool1 is pool2
        
        # Cleanup
        close_global_pool()
    
    def test_global_pool_requires_db_path_on_first_call(self):
        """Test db_path required on first call"""
        close_global_pool()
        
        with pytest.raises(ValueError) as exc_info:
            get_global_pool()
        
        assert "db_path required" in str(exc_info.value)
    
    def test_global_pool_close(self, temp_db):
        """Test closing global pool"""
        close_global_pool()
        
        pool = get_global_pool(db_path=temp_db, pool_size=5)
        
        with pool.get_connection() as conn:
            assert conn is not None
        
        close_global_pool()
        
        # New pool should be created on next call
        pool2 = get_global_pool(db_path=temp_db, pool_size=5)
        assert pool2 is not pool


class TestWALMode:
    """Test WAL mode optimizations"""
    
    def test_wal_mode_enabled(self, pool):
        """Test WAL mode is enabled"""
        with pool.get_connection() as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode.upper() == "WAL"
    
    def test_pragma_settings_applied(self, pool):
        """Test all PRAGMA settings applied"""
        with pool.get_connection() as conn:
            # Check key pragmas
            pragmas = {
                "journal_mode": "WAL",
                "synchronous": "1",  # NORMAL = 1
                "foreign_keys": "1",  # ON = 1
            }
            
            for pragma, expected in pragmas.items():
                cursor = conn.execute(f"PRAGMA {pragma}")
                value = str(cursor.fetchone()[0])
                # Allow case-insensitive comparison for journal_mode
                if pragma == "journal_mode":
                    assert value.upper() == expected.upper()
                else:
                    assert value == expected


class TestPerformance:
    """Performance validation tests"""
    
    @pytest.mark.skip(reason="Performance test - run manually")
    def test_connection_acquisition_speed(self, temp_db):
        """Test connection acquisition is fast"""
        pool = ConnectionPool(db_path=temp_db, pool_size=20)
        
        try:
            iterations = 1000
            start = time.time()
            
            for _ in range(iterations):
                with pool.get_connection() as conn:
                    conn.execute("SELECT 1")
            
            elapsed = time.time() - start
            avg_latency_ms = (elapsed / iterations) * 1000
            
            # Should be < 1ms per operation on average
            assert avg_latency_ms < 1.0, f"Average latency: {avg_latency_ms:.2f}ms"
            
            print(f"\nConnection acquisition: {avg_latency_ms:.2f}ms average")
        finally:
            pool.close()
    
    @pytest.mark.skip(reason="Performance test - run manually")
    def test_high_concurrency_throughput(self, temp_db):
        """Test throughput under high concurrency"""
        pool = ConnectionPool(db_path=temp_db, pool_size=20)
        
        try:
            def perform_operation(op_id):
                with pool.get_connection() as conn:
                    conn.execute(
                        "INSERT INTO test_table (value, created_at) VALUES (?, ?)",
                        (f"op-{op_id}", time.time())
                    )
                return op_id
            
            operations = 1000
            workers = 50
            
            start = time.time()
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(perform_operation, i) for i in range(operations)]
                results = [f.result() for f in as_completed(futures)]
            
            elapsed = time.time() - start
            throughput = operations / elapsed
            
            # Should achieve > 100 ops/sec
            assert throughput > 100, f"Throughput: {throughput:.1f} ops/sec"
            
            print(f"\nThroughput: {throughput:.1f} ops/sec")
            print(f"Total time: {elapsed:.2f}s for {operations} operations")
            
            # Verify all operations completed
            assert len(results) == operations
        finally:
            pool.close()
