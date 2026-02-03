"""
Agent Communication Framework

Enables inter-agent communication for clarifications and collaboration.
Note: Leverages GitHub Copilot Chat window for interactive clarifications.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import time
import logging

from ai_squad.core.events import RoutingEvent, StructuredEventEmitter

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages between agents"""
    QUESTION = "question"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    CLARIFICATION = "clarification"


@dataclass
class AgentMessage:
    """Message between agents"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    message_type: MessageType = MessageType.QUESTION
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    response_to: Optional[str] = None
    issue_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message_type": self.message_type.value,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "response_to": self.response_to,
            "issue_number": self.issue_number,
        }


class AgentCommunicator:
    """
    Handles inter-agent communication
    
    Supports two modes:
    - Automated Mode: Agent-to-agent clarifications (e.g., Architect asks PM)
    - Manual Mode: User-to-agent clarifications via GitHub Copilot Chat
    """
    
    def __init__(self, github_tool=None, execution_mode: str = "manual", event_emitter: Optional[StructuredEventEmitter] = None):
        """
        Initialize communicator
        
        Args:
            github_tool: GitHub tool for storing messages as issue comments
            execution_mode: "automated" (watch mode) or "manual" (CLI)
            event_emitter: Optional structured event emitter for routing telemetry
        """
        self.github = github_tool
        self.execution_mode = execution_mode
        self.message_queue: List[AgentMessage] = []
        self.responses: Dict[str, str] = {}
        self.event_emitter = event_emitter or StructuredEventEmitter()
    
    def ask(
        self,
        from_agent: str,
        to_agent: str,
        question: str,
        context: Dict[str, Any],
        issue_number: Optional[int] = None
    ) -> Optional[str]:
        """
        Ask another agent or user a question
        
        Args:
            from_agent: Asking agent name
            to_agent: Target agent name or "user"
            question: Question to ask
            context: Context information
            issue_number: Related issue number
            
        Returns:
            Response or None if async (GitHub Copilot Chat)
            
        Behavior:
            - Automated Mode: Agent-to-agent (e.g., Architect → PM)
            - Manual Mode: Agent-to-user via GitHub Copilot Chat
        """
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType.QUESTION,
            content=question,
            context=context,
            issue_number=issue_number
        )
        
        # Store message
        self.message_queue.append(message)
        self._emit_routing_event(
            message,
            status="accepted",
            reason="queued",
        )
        
        # Post to GitHub as comment for visibility
        if self.github and issue_number:
            self._post_clarification_request(message)
        
        # Route based on execution mode
        if self.execution_mode == "automated":
            # Automated mode: Agent-to-agent communication
            # For agent-to-agent, route the message
            self._route_message(message)
        else:
            # Manual mode: Agent-to-user via GitHub Copilot Chat
            self._request_user_clarification(message)
        
        # Return message ID for tracking
        return message.id
    
    def respond(
        self,
        message_id: str,
        response: str,
        agent: str
    ) -> bool:
        """
        Respond to a message
        
        Args:
            message_id: Original message ID
            response: Response content
            agent: Responding agent
            
        Returns:
            True if successful
        """
        # Find original message
        original = next(
            (m for m in self.message_queue if m.id == message_id),
            None
        )
        
        if not original:
            return False
        
        # Create response message
        response_msg = AgentMessage(
            from_agent=agent,
            to_agent=original.from_agent,
            message_type=MessageType.RESPONSE,
            content=response,
            context=original.context,
            response_to=message_id,
            issue_number=original.issue_number
        )
        
        self.message_queue.append(response_msg)
        self.responses[message_id] = response
        
        # Post response to GitHub
        if self.github and original.issue_number:
            self._post_response(response_msg, original)
        
        return True
    
    def get_pending_questions(self, agent: str) -> List[AgentMessage]:
        """
        Get pending questions for an agent
        
        Args:
            agent: Agent name
            
        Returns:
            List of pending questions
        """
        return [
            msg for msg in self.message_queue
            if msg.to_agent == agent
            and msg.message_type == MessageType.QUESTION
            and msg.id not in self.responses
        ]
    
    def get_conversation(self, issue_number: int) -> List[AgentMessage]:
        """
        Get all messages for an issue
        
        Args:
            issue_number: Issue number
            
        Returns:
            List of messages
        """
        return [
            msg for msg in self.message_queue
            if msg.issue_number == issue_number
        ]
    
    def _route_message(self, message: AgentMessage) -> Optional[str]:
        """
        Route message to target agent using AgentRegistry.
        
        A2A-aligned: Uses capability-based routing when available.
        Includes retry logic with exponential backoff and circuit breaker.
        
        Args:
            message: Message to route
            
        Returns:
            Response or None if async/unavailable
        """
        from ai_squad.core.agent_registry import get_registry
        
        registry = get_registry()
        
        # Check if target agent has a registered handler
        handler = registry.get_handler(message.to_agent)
        
        if handler:
            # Invoke with retry logic
            max_retries = 3
            base_delay = 1.0  # seconds
            
            for attempt in range(max_retries):
                try:
                    # Check circuit breaker
                    if registry.is_circuit_open(message.to_agent):
                        logger.warning(
                            "Circuit breaker open for %s, skipping",
                            message.to_agent
                        )
                        self._emit_routing_event(
                            message,
                            status="circuit_open",
                            reason="agent_unavailable",
                        )
                        return None
                    
                    result = handler({
                        "message_id": message.id,
                        "from_agent": message.from_agent,
                        "content": message.content,
                        "context": message.context,
                        "issue_number": message.issue_number,
                    })
                    
                    # Success - reset circuit breaker
                    registry.record_success(message.to_agent)
                    
                    self._emit_routing_event(
                        message,
                        status="delivered",
                        reason="handler_invoked",
                    )
                    
                    # Extract response content
                    if isinstance(result, dict):
                        return result.get("response", result.get("content"))
                    return str(result) if result else None
                    
                except Exception as e:
                    # Record failure for circuit breaker
                    registry.record_failure(message.to_agent)
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "Handler failed (attempt %d/%d): %s. Retrying in %.1fs",
                            attempt + 1, max_retries, e, delay
                        )
                        time.sleep(delay)
                    else:
                        # Final attempt failed
                        logger.error(
                            "Handler failed after %d attempts: %s",
                            max_retries, e
                        )
                        self._emit_routing_event(
                            message,
                            status="failed",
                            reason=f"handler_error: {e}",
                        )
                        return None
        
        # Check if agent exists in registry
        agent_card = registry.get(message.to_agent)
        
        if agent_card:
            # Agent exists but no handler - queue for async processing
            self._emit_routing_event(
                message,
                status="queued",
                reason="no_handler_async",
            )
            return None
        
        # Unknown agent
        self._emit_routing_event(
            message,
            status="rejected",
            reason="unknown_agent",
        )
        
        return None

    def _emit_routing_event(
        self,
        message: AgentMessage,
        *,
        status: str,
        reason: Optional[str] = None,
    ) -> None:
        """Emit a structured routing event for observability."""

        if not self.event_emitter:
            return

        event = RoutingEvent.create(
            source=message.from_agent,
            destination=message.to_agent,
            status=status,
            execution_mode=self.execution_mode,
            message_id=message.id,
            issue_number=message.issue_number,
            reason=reason,
            metadata={"context_keys": sorted(message.context.keys()) if message.context else []},
        )
        self.event_emitter.emit_routing(event)
    
    def _request_user_clarification(self, message: AgentMessage) -> Optional[str]:
        """
        Request clarification from user via GitHub Copilot Chat
        
        Args:
            message: Clarification request
            
        Returns:
            None (user should respond via Copilot Chat)
        """
        # Post a comment suggesting the user respond via Copilot Chat
        if self.github and message.issue_number:
            comment = f"""NOTE: **Clarification Needed**

**From**: {message.from_agent.title()} Agent  
**Question**: {message.content}

**To respond**: 
1. Open this issue in VS Code
2. Use GitHub Copilot Chat (`Ctrl+Shift+I` or `Cmd+Shift+I`)
3. Type: `@workspace respond to {message.from_agent} agent for issue #{message.issue_number}`
4. Provide your answer

*Message ID: `{message.id}`*
"""
            self.github.add_comment(message.issue_number, comment)
        
        return None
    
    def _post_clarification_request(self, message: AgentMessage):
        """Post clarification request to GitHub"""
        if not message.issue_number:
            return
        
        if self.execution_mode == "automated":
            # Agent-to-agent in automated mode
            comment = f"""AUTO: **Agent Communication (Automated Mode)**

**From**: {message.from_agent.title()} Agent  
**To**: {message.to_agent.title()} Agent  
**Question**: {message.content}

*This will be handled automatically by the target agent in watch mode.*

*Message ID: `{message.id}`*
*Timestamp: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        else:
            # Agent-to-user in manual mode
            comment = f"""NOTE: **Clarification Needed (Manual Mode)**

**From**: {message.from_agent.title()} Agent  
**Question**: {message.content}

**To respond**:  
1. Open this issue in VS Code
2. Use GitHub Copilot Chat (`Ctrl+Shift+I` or `Cmd+Shift+I`)
3. Type: `@workspace respond to {message.from_agent} agent for issue #{message.issue_number}`
4. Provide your answer

*Message ID: `{message.id}`*
*Timestamp: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        self.github.add_comment(message.issue_number, comment)
    
    def _post_response(self, response: AgentMessage, original: AgentMessage):
        """Post response to GitHub"""
        if not response.issue_number:
            return
        
        comment = f"""NOTE: **Agent Response**

**From**: {response.from_agent.title()} Agent  
**In Response To**: {original.from_agent.title()} Agent  
**Answer**: {response.content}

*Original Question: {original.content}*  
*Message ID: `{response.id}`*  
*Timestamp: {response.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        self.github.add_comment(response.issue_number, comment)


class ClarificationMixin:
    """
    Mixin for agents that need to ask clarifications
    
    Behavior:
    - Automated Mode (watch mode): Agent asks other agents (e.g., Architect → PM)
    - Manual Mode (CLI): Agent asks user via GitHub Copilot Chat
    
    Usage:
        class MyAgent(BaseAgent, ClarificationMixin):
            def _execute_agent(self, issue, context):
                # Ask for clarification
                response = self.ask_clarification(
                    "Should we support OAuth?",
                    context={"feature": "authentication"}
                )
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._communicator = None
    
    @property
    def communicator(self) -> AgentCommunicator:
        """Get communicator instance"""
        if self._communicator is None:
            # Get execution mode from agent
            execution_mode = getattr(self, 'execution_mode', 'manual')
            self._communicator = AgentCommunicator(
                self.github,
                execution_mode=execution_mode
            )
        return self._communicator
    
    def ask_clarification(
        self,
        question: str,
        target_agent: Optional[str] = None,
        context: Dict[str, Any] = None,
        issue_number: Optional[int] = None
    ) -> Optional[str]:
        """
        Ask for clarification
        
        Args:
            question: Question to ask
            target_agent: Agent to ask (automated mode) or None (manual mode asks user)
            context: Additional context
            issue_number: Related issue
            
        Returns:
            Response or None if async
            
        Behavior:
            - Automated Mode: target_agent is required (e.g., "pm", "architect")
            - Manual Mode: target_agent defaults to "user" (asks via Copilot Chat)
        """
        execution_mode = getattr(self, 'execution_mode', 'manual')
        
        # Determine target
        if execution_mode == "automated":
            # In automated mode, must specify target agent
            if not target_agent:
                target_agent = "pm"  # Default to PM in automated mode
        else:
            # In manual mode, ask user
            target_agent = "user"
        
        return self.communicator.ask(
            from_agent=self.agent_type,
            to_agent=target_agent,
            question=question,
            context=context or {},
            issue_number=issue_number
        )
    
    def check_pending_questions(self) -> List[AgentMessage]:
        """Get pending questions for this agent"""
        return self.communicator.get_pending_questions(self.agent_type)
    
    def respond_to_question(self, message_id: str, response: str) -> bool:
        """Respond to a question"""
        return self.communicator.respond(message_id, response, self.agent_type)
