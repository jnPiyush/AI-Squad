"""
Agent Card - A2A-Inspired Agent Capability Discovery

Provides standardized agent capability declaration following
Google's Agent-to-Agent (A2A) protocol concepts.

This enables:
- Dynamic agent discovery
- Capability-based routing
- Schema validation for inputs/outputs
- Version compatibility checks
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class AgentCapability(str, Enum):
    """Standard agent capabilities (A2A-aligned)"""
    # Product Management
    PRD_GENERATION = "prd-generation"
    REQUIREMENTS_ANALYSIS = "requirements-analysis"
    EPIC_BREAKDOWN = "epic-breakdown"
    USER_STORY_CREATION = "user-story-creation"
    
    # Architecture
    ADR_GENERATION = "adr-generation"
    TECHNICAL_SPEC = "technical-spec"
    API_DESIGN = "api-design"
    SYSTEM_DESIGN = "system-design"
    
    # Engineering
    CODE_GENERATION = "code-generation"
    CODE_IMPLEMENTATION = "code-implementation"
    TEST_GENERATION = "test-generation"
    REFACTORING = "refactoring"
    BUG_FIX = "bug-fix"
    
    # UX Design
    WIREFRAME_GENERATION = "wireframe-generation"
    USER_FLOW_DESIGN = "user-flow-design"
    PROTOTYPE_GENERATION = "prototype-generation"
    ACCESSIBILITY_REVIEW = "accessibility-review"
    
    # Review
    CODE_REVIEW = "code-review"
    SECURITY_AUDIT = "security-audit"
    PERFORMANCE_REVIEW = "performance-review"
    DOCUMENTATION_REVIEW = "documentation-review"
    
    # Orchestration
    TASK_COORDINATION = "task-coordination"
    WORKFLOW_MANAGEMENT = "workflow-management"
    AGENT_DELEGATION = "agent-delegation"


@dataclass
class InputSchema:
    """Schema for agent input validation"""
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    field_types: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "required": self.required_fields,
            "optional": self.optional_fields,
            "types": self.field_types,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputSchema":
        return cls(
            required_fields=data.get("required", []),
            optional_fields=data.get("optional", []),
            field_types=data.get("types", {}),
        )
    
    def validate(self, data: Dict[str, Any]) -> List[str]:
        """Validate input data against schema, return list of errors"""
        errors = []
        for field_name in self.required_fields:
            if field_name not in data:
                errors.append(f"Missing required field: {field_name}")
        
        for field_name, expected_type in self.field_types.items():
            if field_name in data:
                actual_type = type(data[field_name]).__name__
                if actual_type != expected_type:
                    errors.append(
                        f"Field '{field_name}' expected {expected_type}, got {actual_type}"
                    )
        return errors


@dataclass
class OutputSchema:
    """Schema for agent output declaration"""
    artifacts: List[str] = field(default_factory=list)  # File types produced
    fields: Dict[str, str] = field(default_factory=dict)  # Output field types
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifacts": self.artifacts,
            "fields": self.fields,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutputSchema":
        return cls(
            artifacts=data.get("artifacts", []),
            fields=data.get("fields", {}),
        )


@dataclass
class AgentCard:
    """
    A2A-Inspired Agent Capability Card
    
    Declares an agent's identity, capabilities, and interface schema.
    Used for:
    - Agent discovery and registration
    - Capability-based task routing
    - Input/output validation
    - Version compatibility
    
    Example:
        card = AgentCard(
            name="pm",
            display_name="Product Manager",
            description="Creates PRDs and breaks down epics",
            capabilities=[AgentCapability.PRD_GENERATION],
            input_schema=InputSchema(required_fields=["issue_number"]),
            output_schema=OutputSchema(artifacts=["PRD-{issue}.md"]),
        )
    """
    # Identity
    name: str                          # Unique agent identifier (e.g., "pm", "architect")
    display_name: str                  # Human-readable name
    description: str                   # Agent description
    version: str = "1.0.0"             # Agent version (semver)
    
    # Capabilities
    capabilities: List[AgentCapability] = field(default_factory=list)
    
    # Schemas
    input_schema: InputSchema = field(default_factory=InputSchema)
    output_schema: OutputSchema = field(default_factory=OutputSchema)
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Agent names this depends on
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # A2A Protocol fields
    url: Optional[str] = None          # Agent endpoint URL (for remote agents)
    authentication: Optional[str] = None  # Auth method (e.g., "oauth2", "api_key")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to A2A-compatible JSON-LD format"""
        return {
            "@context": "https://schema.org/",
            "@type": "SoftwareAgent",
            "name": self.name,
            "displayName": self.display_name,
            "description": self.description,
            "version": self.version,
            "capabilities": [c.value for c in self.capabilities],
            "inputSchema": self.input_schema.to_dict(),
            "outputSchema": self.output_schema.to_dict(),
            "dependsOn": self.depends_on,
            "tags": self.tags,
            "metadata": self.metadata,
            "url": self.url,
            "authentication": self.authentication,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCard":
        """Create from dictionary"""
        capabilities = []
        for cap in data.get("capabilities", []):
            try:
                capabilities.append(AgentCapability(cap))
            except ValueError:
                pass  # Skip unknown capabilities
        
        return cls(
            name=data.get("name", ""),
            display_name=data.get("displayName", data.get("display_name", "")),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            capabilities=capabilities,
            input_schema=InputSchema.from_dict(data.get("inputSchema", data.get("input_schema", {}))),
            output_schema=OutputSchema.from_dict(data.get("outputSchema", data.get("output_schema", {}))),
            depends_on=data.get("dependsOn", data.get("depends_on", [])),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            url=data.get("url"),
            authentication=data.get("authentication"),
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentCard":
        """Deserialize from JSON"""
        return cls.from_dict(json.loads(json_str))
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities
    
    def can_handle(self, required_capabilities: List[AgentCapability]) -> bool:
        """Check if agent can handle all required capabilities"""
        return all(cap in self.capabilities for cap in required_capabilities)
    
    def validate_input(self, data: Dict[str, Any]) -> List[str]:
        """Validate input data against schema"""
        return self.input_schema.validate(data)


# Pre-defined agent cards for AI-Squad agents
PM_CARD = AgentCard(
    name="pm",
    display_name="Product Manager",
    description="Expert Product Manager specializing in PRDs, user stories, and requirements analysis",
    version="1.0.0",
    capabilities=[
        AgentCapability.PRD_GENERATION,
        AgentCapability.REQUIREMENTS_ANALYSIS,
        AgentCapability.EPIC_BREAKDOWN,
        AgentCapability.USER_STORY_CREATION,
    ],
    input_schema=InputSchema(
        required_fields=["issue_number"],
        optional_fields=["context", "requirements"],
        field_types={"issue_number": "int", "context": "dict"},
    ),
    output_schema=OutputSchema(
        artifacts=["docs/prd/PRD-{issue}.md"],
        fields={"prd_path": "str", "user_stories": "list"},
    ),
    depends_on=[],
    tags=["product", "requirements", "planning"],
)

ARCHITECT_CARD = AgentCard(
    name="architect",
    display_name="Software Architect",
    description="Expert Software Architect specializing in system design, ADRs, and technical specifications",
    version="1.0.0",
    capabilities=[
        AgentCapability.ADR_GENERATION,
        AgentCapability.TECHNICAL_SPEC,
        AgentCapability.API_DESIGN,
        AgentCapability.SYSTEM_DESIGN,
    ],
    input_schema=InputSchema(
        required_fields=["issue_number"],
        optional_fields=["prd_path", "context"],
        field_types={"issue_number": "int"},
    ),
    output_schema=OutputSchema(
        artifacts=["docs/adr/ADR-{issue}.md", "docs/specs/SPEC-{issue}.md"],
        fields={"adr_path": "str", "spec_path": "str"},
    ),
    depends_on=["pm"],
    tags=["architecture", "design", "technical"],
)

ENGINEER_CARD = AgentCard(
    name="engineer",
    display_name="Software Engineer",
    description="Expert Software Engineer specializing in implementation, testing, and code quality",
    version="1.0.0",
    capabilities=[
        AgentCapability.CODE_GENERATION,
        AgentCapability.CODE_IMPLEMENTATION,
        AgentCapability.TEST_GENERATION,
        AgentCapability.REFACTORING,
        AgentCapability.BUG_FIX,
    ],
    input_schema=InputSchema(
        required_fields=["issue_number"],
        optional_fields=["spec_path", "adr_path", "context"],
        field_types={"issue_number": "int"},
    ),
    output_schema=OutputSchema(
        artifacts=["src/**/*.py", "tests/**/*.py"],
        fields={"files_created": "list", "pr_number": "int"},
    ),
    depends_on=["pm", "architect"],
    tags=["engineering", "implementation", "testing"],
)

UX_CARD = AgentCard(
    name="ux",
    display_name="UX Designer",
    description="Expert UX Designer specializing in user flows, wireframes, and accessibility",
    version="1.0.0",
    capabilities=[
        AgentCapability.WIREFRAME_GENERATION,
        AgentCapability.USER_FLOW_DESIGN,
        AgentCapability.PROTOTYPE_GENERATION,
        AgentCapability.ACCESSIBILITY_REVIEW,
    ],
    input_schema=InputSchema(
        required_fields=["issue_number"],
        optional_fields=["prd_path", "context"],
        field_types={"issue_number": "int"},
    ),
    output_schema=OutputSchema(
        artifacts=["docs/ux/UX-{issue}.md", "docs/ux/prototypes/prototype-{issue}.html"],
        fields={"ux_path": "str", "prototype_path": "str"},
    ),
    depends_on=["pm"],
    tags=["ux", "design", "accessibility"],
)

REVIEWER_CARD = AgentCard(
    name="reviewer",
    display_name="Code Reviewer",
    description="Expert Code Reviewer specializing in code quality, security, and performance",
    version="1.0.0",
    capabilities=[
        AgentCapability.CODE_REVIEW,
        AgentCapability.SECURITY_AUDIT,
        AgentCapability.PERFORMANCE_REVIEW,
        AgentCapability.DOCUMENTATION_REVIEW,
    ],
    input_schema=InputSchema(
        required_fields=["pr_number"],
        optional_fields=["context", "focus_areas"],
        field_types={"pr_number": "int"},
    ),
    output_schema=OutputSchema(
        artifacts=["docs/reviews/REVIEW-{pr}.md"],
        fields={"review_path": "str", "approved": "bool"},
    ),
    depends_on=[],
    tags=["review", "quality", "security"],
)

CAPTAIN_CARD = AgentCard(
    name="captain",
    display_name="Squad Captain",
    description="Meta-agent that orchestrates other agents and manages workflows",
    version="1.0.0",
    capabilities=[
        AgentCapability.TASK_COORDINATION,
        AgentCapability.WORKFLOW_MANAGEMENT,
        AgentCapability.AGENT_DELEGATION,
    ],
    input_schema=InputSchema(
        required_fields=["mission"],
        optional_fields=["agents", "strategy"],
        field_types={"mission": "str"},
    ),
    output_schema=OutputSchema(
        artifacts=[],
        fields={"work_items": "list", "delegations": "list"},
    ),
    depends_on=[],
    tags=["orchestration", "coordination", "meta-agent"],
)

# Default cards registry
DEFAULT_AGENT_CARDS: Dict[str, AgentCard] = {
    "pm": PM_CARD,
    "architect": ARCHITECT_CARD,
    "engineer": ENGINEER_CARD,
    "ux": UX_CARD,
    "reviewer": REVIEWER_CARD,
    "captain": CAPTAIN_CARD,
}
