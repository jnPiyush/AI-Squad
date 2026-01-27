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
            
            # Signal messages table (for SignalManager)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signal_messages (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'normal',
                    status TEXT NOT NULL DEFAULT 'pending',
                    work_item_id TEXT,
                    convoy_id TEXT,
                    thread_id TEXT,
                    metadata TEXT,
                    attachments TEXT,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT,
                    read_at TEXT,
                    acknowledged_at TEXT,
                    expires_at TEXT,
                    reply_to TEXT,
                    requires_ack INTEGER DEFAULT 0,
                    FOREIGN KEY (reply_to) REFERENCES signal_messages(id)
                )
            """)
            
            # Agent signals (inbox/outbox tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    box_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(owner, message_id, box_type),
                    FOREIGN KEY (message_id) REFERENCES signal_messages(id)
                )
            """)
            
            # Registered signal owners (for broadcast support)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS signal_owners (
                    owner TEXT PRIMARY KEY,
                    registered_at TEXT NOT NULL
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
                CREATE INDEX IF NOT EXISTS idx_signal_messages_sender 
                ON signal_messages(sender)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signal_messages_recipient 
                ON signal_messages(recipient)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signal_messages_thread 
                ON signal_messages(thread_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_signal_messages_status 
                ON signal_messages(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_signals_owner 
                ON agent_signals(owner, box_type)
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
            
            # Delete old signal messages
            cursor.execute("""
                DELETE FROM signal_messages 
                WHERE created_at < ?
            """, (cutoff.isoformat(),))
            deleted += cursor.rowcount
            
            # Delete orphaned agent_signals entries
            cursor.execute("""
                DELETE FROM agent_signals 
                WHERE message_id NOT IN (SELECT id FROM signal_messages)
            """)
            deleted += cursor.rowcount
        
        return deleted

    # ============================================================
    # Signal Message Operations (for SignalManager SQLite backend)
    # ============================================================
    
    def save_signal_message(self, message: "SignalMessage") -> bool:
        """
        Save a signal message to database
        
        Args:
            message: SignalMessage dict or object with to_dict()
            
        Returns:
            True if successful
        """
        try:
            data = message if isinstance(message, dict) else message.to_dict()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO signal_messages 
                    (id, sender, recipient, subject, body, priority, status,
                     work_item_id, convoy_id, thread_id, metadata, attachments,
                     created_at, delivered_at, read_at, acknowledged_at, 
                     expires_at, reply_to, requires_ack)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["id"],
                    data["sender"],
                    data["recipient"],
                    data["subject"],
                    data["body"],
                    data["priority"],
                    data["status"],
                    data.get("work_item_id"),
                    data.get("convoy_id"),
                    data.get("thread_id"),
                    json.dumps(data.get("metadata", {})),
                    json.dumps(data.get("attachments", [])),
                    data["created_at"],
                    data.get("delivered_at"),
                    data.get("read_at"),
                    data.get("acknowledged_at"),
                    data.get("expires_at"),
                    data.get("reply_to"),
                    1 if data.get("requires_ack") else 0
                ))
            return True
        except sqlite3.Error as e:
            print(f"Error saving signal message: {e}")
            return False
    
    def get_signal_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a signal message by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM signal_messages WHERE id = ?
            """, (message_id,))
            row = cursor.fetchone()
            return self._row_to_signal_message(row) if row else None
    
    def update_signal_message_status(
        self, 
        message_id: str, 
        status: str,
        timestamp_field: Optional[str] = None
    ) -> bool:
        """
        Update signal message status
        
        Args:
            message_id: Message ID
            status: New status value
            timestamp_field: Optional timestamp field to update (delivered_at, read_at, acknowledged_at)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if timestamp_field:
                    cursor.execute(f"""
                        UPDATE signal_messages 
                        SET status = ?, {timestamp_field} = ?
                        WHERE id = ?
                    """, (status, datetime.now().isoformat(), message_id))
                else:
                    cursor.execute("""
                        UPDATE signal_messages 
                        SET status = ?
                        WHERE id = ?
                    """, (status, message_id))
            return True
        except sqlite3.Error as e:
            print(f"Error updating signal message: {e}")
            return False
    
    def add_to_signal_box(
        self, 
        owner: str, 
        message_id: str, 
        box_type: str
    ) -> bool:
        """
        Add message to agent's inbox/outbox/archived
        
        Args:
            owner: Agent name
            message_id: Message ID
            box_type: 'inbox', 'outbox', or 'archived'
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO agent_signals 
                    (owner, message_id, box_type, created_at)
                    VALUES (?, ?, ?, ?)
                """, (owner, message_id, box_type, datetime.now().isoformat()))
            return True
        except sqlite3.Error as e:
            print(f"Error adding to signal box: {e}")
            return False
    
    def remove_from_signal_box(
        self, 
        owner: str, 
        message_id: str, 
        box_type: str
    ) -> bool:
        """Remove message from agent's inbox/outbox/archived"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM agent_signals 
                    WHERE owner = ? AND message_id = ? AND box_type = ?
                """, (owner, message_id, box_type))
            return True
        except sqlite3.Error as e:
            print(f"Error removing from signal box: {e}")
            return False
    
    def move_signal_box(
        self, 
        owner: str, 
        message_id: str, 
        from_box: str, 
        to_box: str
    ) -> bool:
        """Move message between boxes (e.g., inbox -> archived)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Remove from source
                cursor.execute("""
                    DELETE FROM agent_signals 
                    WHERE owner = ? AND message_id = ? AND box_type = ?
                """, (owner, message_id, from_box))
                # Add to destination
                cursor.execute("""
                    INSERT OR IGNORE INTO agent_signals 
                    (owner, message_id, box_type, created_at)
                    VALUES (?, ?, ?, ?)
                """, (owner, message_id, to_box, datetime.now().isoformat()))
            return True
        except sqlite3.Error as e:
            print(f"Error moving signal: {e}")
            return False
    
    def get_signal_box(
        self, 
        owner: str, 
        box_type: str,
        unread_only: bool = False,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages in an agent's inbox/outbox/archived
        
        Args:
            owner: Agent name
            box_type: 'inbox', 'outbox', or 'archived'
            unread_only: Only return unread messages
            priority: Filter by priority
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT sm.* FROM signal_messages sm
                JOIN agent_signals asig ON sm.id = asig.message_id
                WHERE asig.owner = ? AND asig.box_type = ?
            """
            params: List[Any] = [owner, box_type]
            
            if unread_only:
                query += " AND sm.status IN ('pending', 'delivered')"
            
            if priority:
                query += " AND sm.priority = ?"
                params.append(priority)
            
            # Sort: urgent first, then by created_at
            query += """
                ORDER BY 
                    CASE sm.priority 
                        WHEN 'urgent' THEN 0 
                        WHEN 'high' THEN 1 
                        WHEN 'normal' THEN 2 
                        WHEN 'low' THEN 3 
                    END,
                    sm.created_at ASC
            """
            
            cursor.execute(query, params)
            return [self._row_to_signal_message(row) for row in cursor.fetchall()]
    
    def get_signal_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a thread"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM signal_messages 
                WHERE thread_id = ?
                ORDER BY created_at ASC
            """, (thread_id,))
            return [self._row_to_signal_message(row) for row in cursor.fetchall()]
    
    def register_signal_owner(self, owner: str) -> bool:
        """Register an agent as a signal owner (for broadcast support)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO signal_owners (owner, registered_at)
                    VALUES (?, ?)
                """, (owner, datetime.now().isoformat()))
            return True
        except sqlite3.Error as e:
            print(f"Error registering signal owner: {e}")
            return False
    
    def get_signal_owners(self) -> List[str]:
        """Get all registered signal owners"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Get from both registered owners and those with messages
            cursor.execute("""
                SELECT owner FROM signal_owners
                UNION
                SELECT DISTINCT owner FROM agent_signals
            """)
            return [row["owner"] for row in cursor.fetchall()]
    
    def delete_signal_message(self, message_id: str) -> bool:
        """Delete a signal message and all references"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Delete from agent_signals first (foreign key)
                cursor.execute("""
                    DELETE FROM agent_signals WHERE message_id = ?
                """, (message_id,))
                # Delete the message
                cursor.execute("""
                    DELETE FROM signal_messages WHERE id = ?
                """, (message_id,))
            return True
        except sqlite3.Error as e:
            print(f"Error deleting signal message: {e}")
            return False
    
    def get_signal_stats(self) -> Dict[str, Any]:
        """Get signal system statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total messages
            cursor.execute("SELECT COUNT(*) as count FROM signal_messages")
            total = cursor.fetchone()["count"]
            
            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM signal_messages 
                GROUP BY status
            """)
            by_status = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            # By owner
            cursor.execute("""
                SELECT owner, box_type, COUNT(*) as count 
                FROM agent_signals 
                GROUP BY owner, box_type
            """)
            by_owner: Dict[str, Dict[str, int]] = {}
            for row in cursor.fetchall():
                owner = row["owner"]
                if owner not in by_owner:
                    by_owner[owner] = {"inbox": 0, "outbox": 0, "archived": 0}
                by_owner[owner][row["box_type"]] = row["count"]
            
            return {
                "total_messages": total,
                "by_status": by_status,
                "by_owner": by_owner
            }
    
    def _row_to_signal_message(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to signal message dict"""
        return {
            "id": row["id"],
            "sender": row["sender"],
            "recipient": row["recipient"],
            "subject": row["subject"],
            "body": row["body"],
            "priority": row["priority"],
            "status": row["status"],
            "work_item_id": row["work_item_id"],
            "convoy_id": row["convoy_id"],
            "thread_id": row["thread_id"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "attachments": json.loads(row["attachments"]) if row["attachments"] else [],
            "created_at": row["created_at"],
            "delivered_at": row["delivered_at"],
            "read_at": row["read_at"],
            "acknowledged_at": row["acknowledged_at"],
            "expires_at": row["expires_at"],
            "reply_to": row["reply_to"],
            "requires_ack": bool(row["requires_ack"])
        }


@lru_cache(maxsize=None)
def get_storage(db_path: str = ".ai_squad/history.db") -> PersistentStorage:
    """Get or create storage instance"""
    return PersistentStorage(db_path)
