"""
Agent Signal System

Persistent asynchronous message passing between agents.
Inspired by military tactical communications and signals.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ai_squad.core.runtime_paths import resolve_runtime_dir

logger = logging.getLogger(__name__)


class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(str, Enum):
    """Message delivery status"""
    PENDING = "pending"       # Not yet delivered
    DELIVERED = "delivered"   # Delivered to recipient
    READ = "read"             # Read by recipient
    ACKNOWLEDGED = "acknowledged"  # Recipient acknowledged
    EXPIRED = "expired"       # TTL expired
    FAILED = "failed"         # Delivery failed


@dataclass
class Message:
    """
    A message between agents.
    """
    id: str
    sender: str              # Agent type or "system"
    recipient: str           # Agent type or "broadcast"
    subject: str
    body: str
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    
    # Context
    work_item_id: Optional[str] = None
    convoy_id: Optional[str] = None
    thread_id: Optional[str] = None  # For conversation threads
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    attachments: List[str] = field(default_factory=list)  # File paths
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    expires_at: Optional[str] = None  # TTL
    
    # Reply handling
    reply_to: Optional[str] = None  # Original message ID
    requires_ack: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "priority": self.priority.value,
            "status": self.status.value,
            "work_item_id": self.work_item_id,
            "convoy_id": self.convoy_id,
            "thread_id": self.thread_id,
            "metadata": self.metadata,
            "attachments": self.attachments,
            "created_at": self.created_at,
            "delivered_at": self.delivered_at,
            "read_at": self.read_at,
            "acknowledged_at": self.acknowledged_at,
            "expires_at": self.expires_at,
            "reply_to": self.reply_to,
            "requires_ack": self.requires_ack
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary"""
        data = data.copy()
        if "priority" in data:
            data["priority"] = MessagePriority(data["priority"])
        if "status" in data:
            data["status"] = MessageStatus(data["status"])
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if message has expired"""
        if not self.expires_at:
            return False
        return datetime.now().isoformat() > self.expires_at
    
    def mark_delivered(self) -> None:
        """Mark message as delivered"""
        self.status = MessageStatus.DELIVERED
        self.delivered_at = datetime.now().isoformat()
    
    def mark_read(self) -> None:
        """Mark message as read"""
        self.status = MessageStatus.READ
        self.read_at = datetime.now().isoformat()
    
    def mark_acknowledged(self) -> None:
        """Mark message as acknowledged"""
        self.status = MessageStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now().isoformat()


@dataclass
class Signal:
    """
    A Signal for an agent or system component.
    """
    owner: str
    inbox: List[str] = field(default_factory=list)    # Message IDs
    outbox: List[str] = field(default_factory=list)   # Message IDs
    archived: List[str] = field(default_factory=list)  # Archived message IDs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "owner": self.owner,
            "inbox": self.inbox,
            "outbox": self.outbox,
            "archived": self.archived
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Signal":
        """Create from dictionary"""
        return cls(**data)


# Type alias for message handler callback
MessageHandler = Callable[[Message], None]


class SignalManager:
    """
    Manages agent Signales and message routing.
    
    Uses SQLite for persistent storage via PersistentStorage.
    Falls back to JSON for migration of legacy data.
    """
    
    # Legacy JSON paths (for migration only)
    Signal_DIR = "Signal"
    MESSAGES_FILE = "messages.json"
    SignalES_FILE = "Signales.json"
    
    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        base_dir: Optional[str] = None,
        storage: Optional["PersistentStorage"] = None,
    ):
        """
        Initialize Signal manager.
        
        Args:
            workspace_root: Root directory of the workspace (defaults to cwd)
            config: Optional configuration dict
            base_dir: Optional base directory override
            storage: Optional PersistentStorage instance (for testing/DI)
        """
        self.workspace_root = workspace_root or Path.cwd()
        runtime_dir = resolve_runtime_dir(self.workspace_root, config=config, base_dir=base_dir)
        self.Signal_dir = runtime_dir / self.Signal_DIR
        
        # Use SQLite storage
        if storage:
            self._storage = storage
        else:
            from ai_squad.core.storage import get_storage
            db_path = str(runtime_dir / "history.db")
            self._storage = get_storage(db_path)
        
        # In-memory cache for handlers only
        self._handlers: Dict[str, List[MessageHandler]] = {}
        
        # Migrate legacy JSON data if present
        self._migrate_legacy_data()
    
    def _migrate_legacy_data(self) -> None:
        """Migrate legacy JSON data to SQLite (one-time operation)"""
        messages_file = self.Signal_dir / self.MESSAGES_FILE
        signales_file = self.Signal_dir / self.SignalES_FILE
        
        if not messages_file.exists() and not signales_file.exists():
            return  # No legacy data
        
        migrated_marker = self.Signal_dir / ".migrated_to_sqlite"
        if migrated_marker.exists():
            return  # Already migrated
        
        logger.info("Migrating legacy JSON data to SQLite...")
        
        try:
            # Migrate messages
            if messages_file.exists():
                data = json.loads(messages_file.read_text(encoding="utf-8"))
                for msg_id, msg_data in data.items():
                    # Convert to new format
                    self._storage.save_signal_message(msg_data)
                logger.info("Migrated %d messages", len(data))
            
            # Migrate signals (inbox/outbox)
            if signales_file.exists():
                data = json.loads(signales_file.read_text(encoding="utf-8"))
                for owner, signal_data in data.items():
                    for msg_id in signal_data.get("inbox", []):
                        self._storage.add_to_signal_box(owner, msg_id, "inbox")
                    for msg_id in signal_data.get("outbox", []):
                        self._storage.add_to_signal_box(owner, msg_id, "outbox")
                    for msg_id in signal_data.get("archived", []):
                        self._storage.add_to_signal_box(owner, msg_id, "archived")
                logger.info("Migrated %d signal boxes", len(data))
            
            # Mark as migrated
            self.Signal_dir.mkdir(parents=True, exist_ok=True)
            migrated_marker.write_text("Migrated on " + datetime.now().isoformat())
            
            # Optionally backup and remove old files
            if messages_file.exists():
                messages_file.rename(messages_file.with_suffix(".json.bak"))
            if signales_file.exists():
                signales_file.rename(signales_file.with_suffix(".json.bak"))
            
            logger.info("Legacy data migration complete")
            
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.error("Migration failed: %s", e)
    
    def _get_or_create_Signal(self, owner: str) -> Signal:
        """Get or create a Signal for an owner (returns in-memory representation)"""
        # Build Signal from database
        inbox_msgs = self._storage.get_signal_box(owner, "inbox")
        outbox_msgs = self._storage.get_signal_box(owner, "outbox")
        archived_msgs = self._storage.get_signal_box(owner, "archived")
        
        return Signal(
            owner=owner,
            inbox=[m["id"] for m in inbox_msgs],
            outbox=[m["id"] for m in outbox_msgs],
            archived=[m["id"] for m in archived_msgs]
        )

    def get_or_create_signal(self, owner: str) -> Signal:
        """Public wrapper for creating or retrieving a Signal.
        
        This also registers the owner as a known agent for broadcast purposes.
        """
        # Register the owner in the database by creating a placeholder entry
        # This ensures get_signal_owners() returns this owner for broadcasts
        self._storage.register_signal_owner(owner)
        return self._get_or_create_Signal(owner)
    
    # Message Operations
    
    def send_message(
        self,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        work_item_id: Optional[str] = None,
        convoy_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        reply_to: Optional[str] = None,
        requires_ack: bool = False,
        ttl_minutes: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[str]] = None
    ) -> Message:
        """
        Send a message from one agent to another.
        
        Args:
            sender: Sender agent type or "system"
            recipient: Recipient agent type or "broadcast"
            subject: Message subject
            body: Message body
            priority: Message priority
            work_item_id: Associated work item ID
            convoy_id: Associated convoy ID
            thread_id: Thread ID for conversations
            reply_to: ID of message being replied to
            requires_ack: Whether acknowledgment is required
            ttl_minutes: Time to live in minutes (None = no expiry)
            metadata: Additional metadata
            attachments: List of file paths
            
        Returns:
            Created Message
        """
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        
        # Calculate expiry
        expires_at = None
        if ttl_minutes:
            from datetime import timedelta
            expires_at = (
                datetime.now() + timedelta(minutes=ttl_minutes)
            ).isoformat()
        
        effective_thread_id = thread_id or message_id
        
        message = Message(
            id=message_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority,
            work_item_id=work_item_id,
            convoy_id=convoy_id,
            thread_id=effective_thread_id,
            reply_to=reply_to,
            requires_ack=requires_ack,
            expires_at=expires_at,
            metadata=metadata or {},
            attachments=attachments or []
        )
        
        # Store message in SQLite
        self._storage.save_signal_message(message.to_dict())
        
        # Add to sender's outbox
        self._storage.add_to_signal_box(sender, message_id, "outbox")
        
        # Route message
        if recipient == "broadcast":
            # Broadcast to all known agents
            for owner in self._storage.get_signal_owners():
                if owner != sender:
                    self._storage.add_to_signal_box(owner, message_id, "inbox")
            # Mark as delivered
            self._storage.update_signal_message_status(
                message_id, MessageStatus.DELIVERED.value, "delivered_at"
            )
            message.mark_delivered()
        else:
            # Direct message
            self._storage.add_to_signal_box(recipient, message_id, "inbox")
            self._storage.update_signal_message_status(
                message_id, MessageStatus.DELIVERED.value, "delivered_at"
            )
            message.mark_delivered()
        
        # Trigger handlers
        self._trigger_handlers(recipient, message)
        
        logger.info(
            "Message sent: %s -> %s [%s]",
            sender, recipient, subject
        )
        
        return message
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message by ID"""
        data = self._storage.get_signal_message(message_id)
        if not data:
            return None
        return Message.from_dict(data)
    
    def get_inbox(
        self,
        owner: str,
        unread_only: bool = False,
        priority: Optional[MessagePriority] = None
    ) -> List[Message]:
        """
        Get messages in an agent's inbox.
        
        Args:
            owner: Signal owner
            unread_only: Only return unread messages
            priority: Filter by priority
            
        Returns:
            List of messages
        """
        priority_val = priority.value if priority else None
        messages_data = self._storage.get_signal_box(
            owner, "inbox", unread_only=unread_only, priority=priority_val
        )
        
        messages = []
        for data in messages_data:
            msg = Message.from_dict(data)
            # Check expiry
            if msg.is_expired():
                self._storage.update_signal_message_status(
                    msg.id, MessageStatus.EXPIRED.value
                )
                continue
            messages.append(msg)
        
        return messages
    
    def get_outbox(self, owner: str) -> List[Message]:
        """Get messages sent by an agent"""
        messages_data = self._storage.get_signal_box(owner, "outbox")
        return [Message.from_dict(data) for data in messages_data]
    
    def get_thread(self, thread_id: str) -> List[Message]:
        """Get all messages in a thread"""
        messages_data = self._storage.get_signal_thread(thread_id)
        return [Message.from_dict(data) for data in messages_data]
    
    def mark_read(self, message_id: str, reader: str) -> bool:
        """Mark a message as read"""
        # Verify reader has access (message in their inbox)
        inbox = self._storage.get_signal_box(reader, "inbox")
        if not any(m["id"] == message_id for m in inbox):
            return False
        
        self._storage.update_signal_message_status(
            message_id, MessageStatus.READ.value, "read_at"
        )
        return True
    
    def acknowledge(self, message_id: str, acknowledger: str) -> bool:
        """Acknowledge a message"""
        # Verify acknowledger has access
        inbox = self._storage.get_signal_box(acknowledger, "inbox")
        if not any(m["id"] == message_id for m in inbox):
            return False
        
        self._storage.update_signal_message_status(
            message_id, MessageStatus.ACKNOWLEDGED.value, "acknowledged_at"
        )
        
        logger.info(
            "Message acknowledged: %s by %s",
            message_id, acknowledger
        )
        return True
    
    def reply(
        self,
        original_message_id: str,
        sender: str,
        body: str,
        subject_prefix: str = "Re: "
    ) -> Optional[Message]:
        """
        Reply to a message.
        
        Args:
            original_message_id: ID of message to reply to
            sender: Sender of the reply
            body: Reply body
            subject_prefix: Prefix for subject line
            
        Returns:
            Created reply message or None
        """
        original = self.get_message(original_message_id)
        if not original:
            return None
        
        return self.send_message(
            sender=sender,
            recipient=original.sender,  # Reply to sender
            subject=f"{subject_prefix}{original.subject}",
            body=body,
            thread_id=original.thread_id,
            reply_to=original_message_id,
            work_item_id=original.work_item_id,
            convoy_id=original.convoy_id
        )
    
    def archive(self, owner: str, message_id: str) -> bool:
        """Archive a message (move from inbox to archived)"""
        return self._storage.move_signal_box(owner, message_id, "inbox", "archived")
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message permanently"""
        return self._storage.delete_signal_message(message_id)
    
    # Handler Registration
    
    def register_handler(
        self,
        recipient: str,
        handler: MessageHandler
    ) -> None:
        """
        Register a message handler for a recipient.
        
        Args:
            recipient: Recipient to handle messages for
            handler: Callback function(message) -> None
        """
        if recipient not in self._handlers:
            self._handlers[recipient] = []
        self._handlers[recipient].append(handler)
    
    def unregister_handler(
        self,
        recipient: str,
        handler: MessageHandler
    ) -> bool:
        """Unregister a message handler"""
        if recipient not in self._handlers:
            return False
        
        try:
            self._handlers[recipient].remove(handler)
            return True
        except ValueError:
            return False
    
    def _trigger_handlers(self, recipient: str, message: Message) -> None:
        """Trigger registered handlers for a message"""
        handlers = self._handlers.get(recipient, [])
        for handler in handlers:
            try:
                handler(message)
            except (RuntimeError, ValueError, TypeError) as e:
                logger.error(
                    "Handler error for %s: %s",
                    recipient, e
                )
        
        # Also trigger broadcast handlers
        if recipient != "broadcast":
            broadcast_handlers = self._handlers.get("broadcast", [])
            for handler in broadcast_handlers:
                try:
                    handler(message)
                except (RuntimeError, ValueError, TypeError) as e:
                    logger.error("Broadcast handler error: %s", e)
    
    # Utility Methods
    
    def get_pending_acks(self, sender: str) -> List[Message]:
        """Get messages sent by agent that require acknowledgment"""
        return [
            msg for msg in self.get_outbox(sender)
            if msg.requires_ack and msg.status != MessageStatus.ACKNOWLEDGED
        ]
    
    def get_unread_count(self, owner: str) -> int:
        """Get count of unread messages"""
        return len(self.get_inbox(owner, unread_only=True))
    
    def cleanup_expired(self) -> int:
        """Clean up expired messages by marking them as expired in SQLite"""
        # This is now handled automatically during get_inbox queries
        # But we can do a batch cleanup here for efficiency
        expired_count = 0
        
        for owner in self._storage.get_signal_owners():
            inbox_msgs = self._storage.get_signal_box(owner, "inbox")
            for data in inbox_msgs:
                msg = Message.from_dict(data)
                if msg.is_expired() and msg.status != MessageStatus.EXPIRED:
                    self._storage.update_signal_message_status(
                        msg.id, MessageStatus.EXPIRED.value
                    )
                    expired_count += 1
        
        if expired_count > 0:
            logger.info("Marked %d messages as expired", expired_count)
        
        return expired_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Signal statistics from SQLite"""
        stats = self._storage.get_signal_stats()
        
        # Add unread counts
        by_signal = {}
        for owner, box_counts in stats.get("by_owner", {}).items():
            by_signal[owner] = {
                **box_counts,
                "unread": self.get_unread_count(owner)
            }
        
        return {
            "total_messages": stats.get("total_messages", 0),
            "by_status": stats.get("by_status", {}),
            "by_signal": by_signal
        }


# Convenience functions for common message patterns

def notify_agent(
    Signal_manager: SignalManager,
    recipient: str,
    subject: str,
    body: str,
    work_item_id: Optional[str] = None
) -> Message:
    """Send a notification to an agent"""
    return Signal_manager.send_message(
        sender="system",
        recipient=recipient,
        subject=subject,
        body=body,
        work_item_id=work_item_id
    )


def request_clarification(
    Signal_manager: SignalManager,
    sender: str,
    recipient: str,
    question: str,
    work_item_id: Optional[str] = None
) -> Message:
    """Send a clarification request"""
    return Signal_manager.send_message(
        sender=sender,
        recipient=recipient,
        subject="Clarification Needed",
        body=question,
        priority=MessagePriority.HIGH,
        requires_ack=True,
        work_item_id=work_item_id
    )


def broadcast_status(
    Signal_manager: SignalManager,
    sender: str,
    status: str,
    work_item_id: Optional[str] = None
) -> Message:
    """Broadcast a status update to all agents"""
    return Signal_manager.send_message(
        sender=sender,
        recipient="broadcast",
        subject="Status Update",
        body=status,
        priority=MessagePriority.NORMAL,
        work_item_id=work_item_id
    )

