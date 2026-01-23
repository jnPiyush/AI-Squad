"""
Agent Mailbox System

Persistent asynchronous message passing between agents.
Inspired by Gastown's message-based coordination pattern.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
class Mailbox:
    """
    A mailbox for an agent or system component.
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
    def from_dict(cls, data: Dict[str, Any]) -> "Mailbox":
        """Create from dictionary"""
        return cls(**data)


# Type alias for message handler callback
MessageHandler = Callable[[Message], None]


class MailboxManager:
    """
    Manages agent mailboxes and message routing.
    
    Persists messages to .squad/mailbox/ directory.
    """
    
    MAILBOX_DIR = "mailbox"
    MESSAGES_FILE = "messages.json"
    MAILBOXES_FILE = "mailboxes.json"
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """
        Initialize mailbox manager.
        
        Args:
            workspace_root: Root directory of the workspace (defaults to cwd)
        """
        self.workspace_root = workspace_root or Path.cwd()
        self.squad_dir = self.workspace_root / ".squad"
        self.mailbox_dir = self.squad_dir / self.MAILBOX_DIR
        
        self._messages: Dict[str, Message] = {}
        self._mailboxes: Dict[str, Mailbox] = {}
        self._handlers: Dict[str, List[MessageHandler]] = {}
        
        self._load_state()
    
    def _ensure_mailbox_dir(self) -> None:
        """Create mailbox directory if it doesn't exist"""
        self.mailbox_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> None:
        """Load mailbox state from disk"""
        # Load messages
        messages_file = self.mailbox_dir / self.MESSAGES_FILE
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
        
        # Load mailboxes
        mailboxes_file = self.mailbox_dir / self.MAILBOXES_FILE
        if mailboxes_file.exists():
            try:
                data = json.loads(mailboxes_file.read_text(encoding="utf-8"))
                self._mailboxes = {
                    owner: Mailbox.from_dict(mb_data)
                    for owner, mb_data in data.items()
                }
                logger.info("Loaded %d mailboxes", len(self._mailboxes))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Failed to load mailboxes: %s", e)
                self._mailboxes = {}
    
    def _save_state(self) -> None:
        """Save mailbox state to disk"""
        self._ensure_mailbox_dir()
        
        # Save messages
        messages_file = self.mailbox_dir / self.MESSAGES_FILE
        messages_data = {
            msg_id: msg.to_dict()
            for msg_id, msg in self._messages.items()
        }
        messages_file.write_text(
            json.dumps(messages_data, indent=2),
            encoding="utf-8"
        )
        
        # Save mailboxes
        mailboxes_file = self.mailbox_dir / self.MAILBOXES_FILE
        mailboxes_data = {
            owner: mb.to_dict()
            for owner, mb in self._mailboxes.items()
        }
        mailboxes_file.write_text(
            json.dumps(mailboxes_data, indent=2),
            encoding="utf-8"
        )
    
    def _get_or_create_mailbox(self, owner: str) -> Mailbox:
        """Get or create a mailbox for an owner"""
        if owner not in self._mailboxes:
            self._mailboxes[owner] = Mailbox(owner=owner)
        return self._mailboxes[owner]
    
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
        
        # Add to sender's outbox
        sender_mailbox = self._get_or_create_mailbox(sender)
        sender_mailbox.outbox.append(message_id)
        
        # Route message
        if recipient == "broadcast":
            # Broadcast to all agents
            for owner in self._mailboxes:
                if owner != sender:
                    mailbox = self._mailboxes[owner]
                    mailbox.inbox.append(message_id)
            message.mark_delivered()
        else:
            # Direct message
            recipient_mailbox = self._get_or_create_mailbox(recipient)
            recipient_mailbox.inbox.append(message_id)
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
            owner: Mailbox owner
            unread_only: Only return unread messages
            priority: Filter by priority
            
        Returns:
            List of messages
        """
        mailbox = self._get_or_create_mailbox(owner)
        messages = []
        
        for msg_id in mailbox.inbox:
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
        mailbox = self._get_or_create_mailbox(owner)
        return [
            self._messages[msg_id]
            for msg_id in mailbox.outbox
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
        mailbox = self._get_or_create_mailbox(reader)
        if message_id not in mailbox.inbox:
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
        mailbox = self._get_or_create_mailbox(acknowledger)
        if message_id not in mailbox.inbox:
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
        mailbox = self._get_or_create_mailbox(owner)
        
        if message_id in mailbox.inbox:
            mailbox.inbox.remove(message_id)
            mailbox.archived.append(message_id)
            self._save_state()
            return True
        
        return False
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message permanently"""
        if message_id not in self._messages:
            return False
        
        # Remove from all mailboxes
        for mailbox in self._mailboxes.values():
            if message_id in mailbox.inbox:
                mailbox.inbox.remove(message_id)
            if message_id in mailbox.outbox:
                mailbox.outbox.remove(message_id)
            if message_id in mailbox.archived:
                mailbox.archived.remove(message_id)
        
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
            except Exception as e:
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
                except Exception as e:
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
        
        for msg_id, msg in list(self._messages.items()):
            if msg.is_expired():
                msg.status = MessageStatus.EXPIRED
                expired_count += 1
        
        if expired_count > 0:
            self._save_state()
            logger.info("Marked %d messages as expired", expired_count)
        
        return expired_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get mailbox statistics"""
        total_messages = len(self._messages)
        
        status_counts = {}
        for status in MessageStatus:
            status_counts[status.value] = len([
                m for m in self._messages.values()
                if m.status == status
            ])
        
        mailbox_stats = {}
        for owner, mailbox in self._mailboxes.items():
            mailbox_stats[owner] = {
                "inbox": len(mailbox.inbox),
                "outbox": len(mailbox.outbox),
                "archived": len(mailbox.archived),
                "unread": self.get_unread_count(owner)
            }
        
        return {
            "total_messages": total_messages,
            "by_status": status_counts,
            "by_mailbox": mailbox_stats
        }


# Convenience functions for common message patterns

def notify_agent(
    mailbox_manager: MailboxManager,
    recipient: str,
    subject: str,
    body: str,
    work_item_id: Optional[str] = None
) -> Message:
    """Send a notification to an agent"""
    return mailbox_manager.send_message(
        sender="system",
        recipient=recipient,
        subject=subject,
        body=body,
        work_item_id=work_item_id
    )


def request_clarification(
    mailbox_manager: MailboxManager,
    sender: str,
    recipient: str,
    question: str,
    work_item_id: Optional[str] = None
) -> Message:
    """Send a clarification request"""
    return mailbox_manager.send_message(
        sender=sender,
        recipient=recipient,
        subject="Clarification Needed",
        body=question,
        priority=MessagePriority.HIGH,
        requires_ack=True,
        work_item_id=work_item_id
    )


def broadcast_status(
    mailbox_manager: MailboxManager,
    sender: str,
    status: str,
    work_item_id: Optional[str] = None
) -> Message:
    """Broadcast a status update to all agents"""
    return mailbox_manager.send_message(
        sender=sender,
        recipient="broadcast",
        subject="Status Update",
        body=status,
        priority=MessagePriority.NORMAL,
        work_item_id=work_item_id
    )
