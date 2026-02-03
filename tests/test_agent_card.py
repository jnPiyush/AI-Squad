"""
Tests for AgentCard - A2A-aligned agent capability discovery
"""
import pytest
from ai_squad.core.agent_card import (
    AgentCard,
    AgentCapability,
    InputSchema,
    OutputSchema,
    DEFAULT_AGENT_CARDS,
    PM_CARD,
    ARCHITECT_CARD,
    ENGINEER_CARD,
)


class TestInputSchema:
    """Test InputSchema validation"""
    
    def test_validate_required_fields(self):
        """Test validation of required fields"""
        schema = InputSchema(
            required_fields=["issue_number", "title"],
            field_types={"issue_number": "int", "title": "str"}
        )
        
        # Missing required field
        errors = schema.validate({"title": "Test"})
        assert len(errors) == 1
        assert "Missing required field: issue_number" in errors[0]
        
        # All required fields present
        errors = schema.validate({"issue_number": 123, "title": "Test"})
        assert len(errors) == 0
    
    def test_validate_field_types(self):
        """Test validation of field types"""
        schema = InputSchema(
            required_fields=["issue_number"],
            field_types={"issue_number": "int"}
        )
        
        # Wrong type
        errors = schema.validate({"issue_number": "not_an_int"})
        assert len(errors) == 1
        assert "expected int, got str" in errors[0]
        
        # Correct type
        errors = schema.validate({"issue_number": 123})
        assert len(errors) == 0
    
    def test_to_from_dict(self):
        """Test serialization/deserialization"""
        schema = InputSchema(
            required_fields=["field1"],
            optional_fields=["field2"],
            field_types={"field1": "str"}
        )
        
        data = schema.to_dict()
        restored = InputSchema.from_dict(data)
        
        assert restored.required_fields == schema.required_fields
        assert restored.optional_fields == schema.optional_fields
        assert restored.field_types == schema.field_types


class TestAgentCard:
    """Test AgentCard functionality"""
    
    def test_card_creation(self):
        """Test creating an agent card"""
        card = AgentCard(
            name="test_agent",
            display_name="Test Agent",
            description="Test description",
            version="1.0.0",
            capabilities=[AgentCapability.CODE_REVIEW],
        )
        
        assert card.name == "test_agent"
        assert card.display_name == "Test Agent"
        assert card.version == "1.0.0"
        assert AgentCapability.CODE_REVIEW in card.capabilities
    
    def test_has_capability(self):
        """Test capability checking"""
        card = PM_CARD
        
        assert card.has_capability(AgentCapability.PRD_GENERATION)
        assert not card.has_capability(AgentCapability.CODE_REVIEW)
    
    def test_can_handle(self):
        """Test checking multiple capabilities"""
        card = ENGINEER_CARD
        
        # Can handle all
        assert card.can_handle([
            AgentCapability.CODE_GENERATION,
            AgentCapability.TEST_GENERATION,
        ])
        
        # Missing one capability
        assert not card.can_handle([
            AgentCapability.CODE_GENERATION,
            AgentCapability.PRD_GENERATION,  # PM capability
        ])
    
    def test_validate_input(self):
        """Test input validation"""
        card = PM_CARD
        
        # Invalid input
        errors = card.validate_input({"issue_number": "not_an_int"})
        assert len(errors) > 0
        
        # Valid input
        errors = card.validate_input({"issue_number": 123})
        assert len(errors) == 0
    
    def test_to_dict(self):
        """Test A2A-compatible JSON-LD format"""
        card = PM_CARD
        data = card.to_dict()
        
        # Check A2A fields
        assert data["@context"] == "https://schema.org/"
        assert data["@type"] == "SoftwareAgent"
        assert data["name"] == "pm"
        assert data["displayName"] == "Product Manager"
        assert "capabilities" in data
        assert "inputSchema" in data
        assert "outputSchema" in data
    
    def test_from_dict(self):
        """Test deserialization"""
        original = ARCHITECT_CARD
        data = original.to_dict()
        restored = AgentCard.from_dict(data)
        
        assert restored.name == original.name
        assert restored.display_name == original.display_name
        assert restored.version == original.version
        assert len(restored.capabilities) == len(original.capabilities)
    
    def test_to_from_json(self):
        """Test JSON serialization roundtrip"""
        original = ENGINEER_CARD
        json_str = original.to_json()
        restored = AgentCard.from_json(json_str)
        
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.capabilities == original.capabilities


class TestDefaultCards:
    """Test default agent cards"""
    
    def test_all_default_cards_present(self):
        """Test that all default cards are registered"""
        expected = ["pm", "architect", "engineer", "ux", "reviewer", "captain"]
        assert set(DEFAULT_AGENT_CARDS.keys()) == set(expected)
    
    def test_pm_card(self):
        """Test Product Manager card"""
        card = DEFAULT_AGENT_CARDS["pm"]
        
        assert card.name == "pm"
        assert AgentCapability.PRD_GENERATION in card.capabilities
        assert AgentCapability.USER_STORY_CREATION in card.capabilities
        assert "issue_number" in card.input_schema.required_fields
        assert len(card.depends_on) == 0  # PM has no dependencies
    
    def test_architect_card(self):
        """Test Architect card"""
        card = DEFAULT_AGENT_CARDS["architect"]
        
        assert card.name == "architect"
        assert AgentCapability.ADR_GENERATION in card.capabilities
        assert AgentCapability.SYSTEM_DESIGN in card.capabilities
        assert "pm" in card.depends_on  # Architect depends on PM
    
    def test_engineer_card(self):
        """Test Engineer card"""
        card = DEFAULT_AGENT_CARDS["engineer"]
        
        assert card.name == "engineer"
        assert AgentCapability.CODE_GENERATION in card.capabilities
        assert AgentCapability.TEST_GENERATION in card.capabilities
        assert "pm" in card.depends_on
        assert "architect" in card.depends_on
    
    def test_reviewer_card(self):
        """Test Reviewer card"""
        card = DEFAULT_AGENT_CARDS["reviewer"]
        
        assert card.name == "reviewer"
        assert AgentCapability.CODE_REVIEW in card.capabilities
        assert AgentCapability.SECURITY_AUDIT in card.capabilities
        assert "pr_number" in card.input_schema.required_fields
    
    def test_capability_coverage(self):
        """Test that key capabilities are covered"""
        all_caps = set()
        for card in DEFAULT_AGENT_CARDS.values():
            all_caps.update(card.capabilities)
        
        # Should have core capabilities covered
        assert AgentCapability.PRD_GENERATION in all_caps
        assert AgentCapability.CODE_GENERATION in all_caps
        assert AgentCapability.CODE_REVIEW in all_caps
        assert AgentCapability.ADR_GENERATION in all_caps


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
