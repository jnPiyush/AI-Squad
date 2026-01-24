"""
Persistent Storage for Message History and Status Transitions

SQLite-based storage for agent communications and workflow audit trail.
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import lru_cache

from ai_squad.core.agent_comm import AgentMessage, MessageType
from ai_squad.core.status import StatusTransition, IssueStatus


class PersistentStorage:
    """SQLite-based persistent storage"""
    
    def __init__(self, db_path: str = ".ai_squad/history.db"):
        """
        Initialize persistent storage
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:  # noqa: BLE001 - rollback should run on any failure
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    response_to TEXT,
                    issue_number INTEGER,
                    FOREIGN KEY (response_to) REFERENCES messages(id)
                )
            """)
            
            # Status transitions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS status_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_number INTEGER NOT NULL,
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    reason TEXT
                )
            """)
            
            # Agent executions table (audit trail)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_number INTEGER NOT NULL,
                    agent TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    success INTEGER NOT NULL,
                    error TEXT,
                    output_file TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_issue 
                ON messages(issue_number)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_agents 
                ON messages(from_agent, to_agent)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transitions_issue 
                ON status_transitions(issue_number)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_issue 
                ON agent_executions(issue_number)
            """)
    
    # Message Operations
    
    def save_message(self, message: AgentMessage) -> bool:
        """
        Save a message to database
        
        Args:
            message: AgentMessage to save
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO messages 
                    (id, from_agent, to_agent, message_type, content, 
                     context, timestamp, response_to, issue_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.id,
                    message.from_agent,
                    message.to_agent,
                    message.message_type.value,
                    message.content,
                    json.dumps(message.context),
                    message.timestamp.isoformat(),
                    message.response_to,
                    message.issue_number
                ))
            return True
        except sqlite3.Error as e:
            print(f"Error saving message: {e}")
            return False
    
    def get_messages_for_issue(self, issue_number: int) -> List[AgentMessage]:
        """
        Get all messages for an issue
        
        Args:
            issue_number: Issue number
            
        Returns:
            List of messages
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages 
                WHERE issue_number = ?
                ORDER BY timestamp ASC
            """, (issue_number,))
            
            rows = cursor.fetchall()
            return [self._row_to_message(row) for row in rows]
    
    def get_pending_questions(self, agent: str) -> List[AgentMessage]:
        """
        Get pending questions for an agent
        
        Args:
            agent: Agent name
            
        Returns:
            List of unanswered questions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT m.* FROM messages m
                WHERE m.to_agent = ?
                AND m.message_type = ?
                AND NOT EXISTS (
                    SELECT 1 FROM messages r
                    WHERE r.response_to = m.id
                )
                ORDER BY m.timestamp ASC
            """, (agent, MessageType.QUESTION.value))
            
            rows = cursor.fetchall()
            return [self._row_to_message(row) for row in rows]
    
    def _row_to_message(self, row: sqlite3.Row) -> AgentMessage:
        """Convert database row to AgentMessage"""
        return AgentMessage(
            id=row["id"],
            from_agent=row["from_agent"],
            to_agent=row["to_agent"],
            message_type=MessageType(row["message_type"]),
            content=row["content"],
            context=json.loads(row["context"]) if row["context"] else {},
            timestamp=datetime.fromisoformat(row["timestamp"]),
            response_to=row["response_to"],
            issue_number=row["issue_number"]
        )
    
    # Status Transition Operations
    
    def save_transition(self, transition: StatusTransition) -> bool:
        """
        Save a status transition
        
        Args:
            transition: StatusTransition to save
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO status_transitions 
                    (issue_number, from_status, to_status, agent, timestamp, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    transition.issue_number,
                    transition.from_status.value,
                    transition.to_status.value,
                    transition.agent,
                    transition.timestamp.isoformat(),
                    transition.reason
                ))
            return True
        except sqlite3.Error as e:
            print(f"Error saving transition: {e}")
            return False
    
    def get_transitions_for_issue(self, issue_number: int) -> List[StatusTransition]:
        """
        Get all status transitions for an issue
        
        Args:
            issue_number: Issue number
            
        Returns:
            List of transitions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM status_transitions 
                WHERE issue_number = ?
                ORDER BY timestamp ASC
            """, (issue_number,))
            
            rows = cursor.fetchall()
            return [self._row_to_transition(row) for row in rows]
    
    def _row_to_transition(self, row: sqlite3.Row) -> StatusTransition:
        """Convert database row to StatusTransition"""
        return StatusTransition(
            issue_number=row["issue_number"],
            from_status=IssueStatus.from_string(row["from_status"]),
            to_status=IssueStatus.from_string(row["to_status"]),
            agent=row["agent"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            reason=row["reason"]
        )
    
    # Agent Execution Operations
    
    def start_execution(
        self,
        issue_number: int,
        agent: str,
        execution_mode: str
    ) -> int:
        """
        Record the start of an agent execution
        
        Args:
            issue_number: Issue number
            agent: Agent name
            execution_mode: "manual" or "automated"
            
        Returns:
            Execution ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_executions 
                (issue_number, agent, execution_mode, started_at, success)
                VALUES (?, ?, ?, ?, 0)
            """, (
                issue_number,
                agent,
                execution_mode,
                datetime.now().isoformat()
            ))
            return cursor.lastrowid
    
    def complete_execution(
        self,
        execution_id: int,
        success: bool,
        error: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> bool:
        """
        Record completion of an agent execution
        
        Args:
            execution_id: Execution ID from start_execution
            success: Whether execution succeeded
            error: Error message if failed
            output_file: Path to output file
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE agent_executions 
                    SET completed_at = ?,
                        success = ?,
                        error = ?,
                        output_file = ?
                    WHERE id = ?
                """, (
                    datetime.now().isoformat(),
                    1 if success else 0,
                    error,
                    output_file,
                    execution_id
                ))
            return True
        except sqlite3.Error as e:
            print(f"Error completing execution: {e}")
            return False
    
    def get_executions_for_issue(self, issue_number: int) -> List[Dict[str, Any]]:
        """
        Get all executions for an issue
        
        Args:
            issue_number: Issue number
            
        Returns:
            List of execution records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_executions 
                WHERE issue_number = ?
                ORDER BY started_at ASC
            """, (issue_number,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Statistics and Reporting
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics
        
        Returns:
            Dict with statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Message stats
            cursor.execute("SELECT COUNT(*) as count FROM messages")
            total_messages = cursor.fetchone()["count"]
            
            # Transition stats
            cursor.execute("SELECT COUNT(*) as count FROM status_transitions")
            total_transitions = cursor.fetchone()["count"]
            
            # Execution stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(success) as successful,
                    COUNT(*) - SUM(success) as failed
                FROM agent_executions
            """)
            exec_stats = cursor.fetchone()
            
            # Agent activity
            cursor.execute("""
                SELECT agent, COUNT(*) as executions
                FROM agent_executions
                GROUP BY agent
                ORDER BY executions DESC
            """)
            agent_activity = [dict(row) for row in cursor.fetchall()]
            
            return {
                "total_messages": total_messages,
                "total_transitions": total_transitions,
                "total_executions": exec_stats["total"],
                "successful_executions": exec_stats["successful"],
                "failed_executions": exec_stats["failed"],
                "agent_activity": agent_activity
            }
    
    def cleanup_old_data(self, days: int = 90) -> int:
        """
        Remove data older than specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of records deleted
        """
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete old messages
            cursor.execute("""
                DELETE FROM messages 
                WHERE timestamp < ?
            """, (cutoff.isoformat(),))
            deleted += cursor.rowcount
            
            # Delete old transitions
            cursor.execute("""
                DELETE FROM status_transitions 
                WHERE timestamp < ?
            """, (cutoff.isoformat(),))
            deleted += cursor.rowcount
            
            # Delete old executions
            cursor.execute("""
                DELETE FROM agent_executions 
                WHERE started_at < ?
            """, (cutoff.isoformat(),))
            deleted += cursor.rowcount
        
        return deleted


@lru_cache(maxsize=None)
def get_storage(db_path: str = ".ai_squad/history.db") -> PersistentStorage:
    """Get or create storage instance"""
    return PersistentStorage(db_path)
