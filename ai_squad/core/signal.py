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
    
    Persists messages to .squad/Signal/ directory.
    """
    
    Signal_DIR = "Signal"
    MESSAGES_FILE = "messages.json"
    SignalES_FILE = "Signales.json"
    
    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        base_dir: Optional[str] = None,
    ):
        """
        Initialize Signal manager.
        
        Args:
            workspace_root: Root directory of the workspace (defaults to cwd)
        """
        self.workspace_root = workspace_root or Path.cwd()
        runtime_dir = resolve_runtime_dir(self.workspace_root, config=config, base_dir=base_dir)
        self.Signal_dir = runtime_dir / self.Signal_DIR
        
        self._messages: Dict[str, Message] = {}
        self._Signales: Dict[str, Signal] = {}
        self._handlers: Dict[str, List[MessageHandler]] = {}
        
        self._load_state()
    
    def _ensure_Signal_dir(self) -> None:
        """Create Signal directory if it doesn't exist"""
        self.Signal_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> None:
        """Load Signal state from disk"""
        # Load messages
        messages_file = self.Signal_dir / self.MESSAGES_FILE
        if messages_file.exists():
            try:
                data = json.loads(messages_file.read_text(encoding="utf-8"))
                self._messages = {
                    msg_id: Message.from_dict(msg_data)
                    for msg_id, msg_data in data.items()
                }
                logger.info("Loaded %d messages", len(self._messages))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Failed to load messages: %s", e)
                self._messages = {}
        
        # Load Signales
        Signales_file = self.Signal_dir / self.SignalES_FILE
        if Signales_file.exists():
            try:
                data = json.loads(Signales_file.read_text(encoding="utf-8"))
                self._Signales = {
                    owner: Signal.from_dict(mb_data)
                    for owner, mb_data in data.items()
                }
                logger.info("Loaded %d Signales", len(self._Signales))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Failed to load Signales: %s", e)
                self._Signales = {}
    
    def _save_state(self) -> None:
        """Save Signal state to disk"""
        self._ensure_Signal_dir()
        
        # Save messages
        messages_file = self.Signal_dir / self.MESSAGES_FILE
        messages_data = {
            msg_id: msg.to_dict()
            for msg_id, msg in self._messages.items()
        }
        messages_file.write_text(
            json.dumps(messages_data, indent=2),
            encoding="utf-8"
        )
        
        # Save Signales
        Signales_file = self.Signal_dir / self.SignalES_FILE
        Signales_data = {
            owner: mb.to_dict()
            for owner, mb in self._Signales.items()
        }
        Signales_file.write_text(
            json.dumps(Signales_data, indent=2),
            encoding="utf-8"
        )
    
    def _get_or_create_Signal(self, owner: str) -> Signal:
        """Get or create a Signal for an owner"""
        if owner not in self._Signales:
            self._Signales[owner] = Signal(owner=owner)
        return self._Signales[owner]

    def get_or_create_signal(self, owner: str) -> Signal:
        """Public wrapper for creating or retrieving a Signal."""
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
        
        message = Message(
            id=message_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            body=body,
            priority=priority,
            work_item_id=work_item_id,
            convoy_id=convoy_id,
            thread_id=thread_id or message_id,  # Use message ID as thread if not specified
            reply_to=reply_to,
            requires_ack=requires_ack,
            expires_at=expires_at,
            metadata=metadata or {},
            attachments=attachments or []
        )
        
        # Store message
        self._messages[message_id] = message

        sender_signal = self._get_or_create_Signal(sender)
        sender_signal.outbox.append(message_id)
        
        # Route message
        if recipient == "broadcast":
            # Broadcast to all agents
            for owner in self._Signales:
                if owner != sender:
                    signal = self._Signales[owner]
                    signal.inbox.append(message_id)
            message.mark_delivered()
        else:
            # Direct message
            recipient_Signal = self._get_or_create_Signal(recipient)
            recipient_Signal.inbox.append(message_id)
            message.mark_delivered()
        
        self._save_state()
        
        # Trigger handlers
        self._trigger_handlers(recipient, message)
        
        logger.info(
            "Message sent: %s -> %s [%s]",
            sender, recipient, subject
        )
        
        return message
    
    def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message by ID"""
        return self._messages.get(message_id)
    
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
        signal = self._get_or_create_Signal(owner)
        messages = []
        
        for msg_id in signal.inbox:
            msg = self._messages.get(msg_id)
            if not msg:
                continue
            
            # Check expiry
            if msg.is_expired():
                msg.status = MessageStatus.EXPIRED
                continue
            
            # Apply filters
            if unread_only and msg.status not in (
                MessageStatus.PENDING, MessageStatus.DELIVERED
            ):
                continue
            
            if priority and msg.priority != priority:
                continue
            
            messages.append(msg)
        
        # Sort by priority (urgent first) then by created_at
        priority_order = {
            MessagePriority.URGENT: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3
        }
        
        messages.sort(
            key=lambda m: (priority_order[m.priority], m.created_at)
        )
        
        return messages
    
    def get_outbox(self, owner: str) -> List[Message]:
        """Get messages sent by an agent"""
        signal = self._get_or_create_Signal(owner)
        return [
            self._messages[msg_id]
            for msg_id in signal.outbox
            if msg_id in self._messages
        ]
    
    def get_thread(self, thread_id: str) -> List[Message]:
        """Get all messages in a thread"""
        messages = [
            msg for msg in self._messages.values()
            if msg.thread_id == thread_id
        ]
        return sorted(messages, key=lambda m: m.created_at)
    
    def mark_read(self, message_id: str, reader: str) -> bool:
        """Mark a message as read"""
        message = self.get_message(message_id)
        if not message:
            return False
        
        # Verify reader has access
        signal = self._get_or_create_Signal(reader)
        if message_id not in signal.inbox:
            return False
        
        message.mark_read()
        self._save_state()
        return True
    
    def acknowledge(self, message_id: str, acknowledger: str) -> bool:
        """Acknowledge a message"""
        message = self.get_message(message_id)
        if not message:
            return False
        
        # Verify acknowledger has access
        signal = self._get_or_create_Signal(acknowledger)
        if message_id not in signal.inbox:
            return False
        
        message.mark_acknowledged()
        self._save_state()
        
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
        """Archive a message"""
        signal = self._get_or_create_Signal(owner)
        
        if message_id in signal.inbox:
            signal.inbox.remove(message_id)
            signal.archived.append(message_id)
            self._save_state()
            return True
        
        return False
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message permanently"""
        if message_id not in self._messages:
            return False
        
        # Remove from all Signales
        for signal in self._Signales.values():
            if message_id in signal.inbox:
                signal.inbox.remove(message_id)
            if message_id in signal.outbox:
                signal.outbox.remove(message_id)
            if message_id in signal.archived:
                signal.archived.remove(message_id)
        
        del self._messages[message_id]
        self._save_state()
        return True
    
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
        """Clean up expired messages"""
        expired_count = 0
        
        for msg in list(self._messages.values()):
            if msg.is_expired():
                msg.status = MessageStatus.EXPIRED
                expired_count += 1
        
        if expired_count > 0:
            self._save_state()
            logger.info("Marked %d messages as expired", expired_count)
        
        return expired_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Signal statistics"""
        total_messages = len(self._messages)
        
        status_counts = {}
        for status in MessageStatus:
            status_counts[status.value] = len([
                m for m in self._messages.values()
                if m.status == status
            ])
        
        Signal_stats = {}
        for owner, signal in self._Signales.items():
            Signal_stats[owner] = {
                "inbox": len(signal.inbox),
                "outbox": len(signal.outbox),
                "archived": len(signal.archived),
                "unread": self.get_unread_count(owner)
            }
        
        return {
            "total_messages": total_messages,
            "by_status": status_counts,
            "by_signal": Signal_stats
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

