"""
Live test of Idea Management feature with Product Manager agent
"""
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

def test_idea_management():
    """Test PM agent with Idea Management requirement"""
    print("=" * 80)
    print("LIVE TEST: Idea Management Platform")
    print("=" * 80)
    print()
    
    # Requirement
    requirement = """
Create a centralized Idea Management platform that captures ideas with structured 
business case information including:

1. ROI (Return on Investment) estimation
2. Effort estimation (hours/story points)
3. Risk assessment (low/medium/high)
4. Priority scoring

The platform should enable users to submit ideas with complete business case data
and store them in a searchable, filterable format.
"""
    
    print("REQUIREMENT:")
    print(requirement)
    print("\n" + "=" * 80)
    print("Testing Product Manager Agent")
    print("=" * 80 + "\n")
    
    # Import after setup
    from ai_squad.core.config import Config
    from ai_squad.core.ai_provider import AIProviderChain
    from ai_squad.agents.product_manager import ProductManagerAgent
    
    try:
        # Initialize
        config = Config.load()
        provider_chain = AIProviderChain(config.data)
        
        print(f"✓ Active AI Provider: {provider_chain.provider_type.value}")
        print(f"✓ Available Providers: {', '.join(provider_chain.get_available_providers())}")
        print()
        
        # Create PM agent
        pm_agent = ProductManagerAgent(config, None, {})
        
        # Simulate the issue data
        issue_data = {
            'number': 10,
            'title': 'Idea Management Platform - Capture Ideas with Business Case',
            'body': requirement,
            'labels': ['enhancement']
        }
        
        print("=" * 80)
        print("Generating PRD...")
        print("=" * 80 + "\n")
        
        # Generate PRD using the provider chain
        system_prompt = "You are an expert Product Manager. Create comprehensive PRDs with clear requirements, acceptance criteria, and business value."
        
        user_prompt = f"""
Create a detailed Product Requirements Document (PRD) for:

**Title**: {issue_data['title']}

**Requirements**:
{issue_data['body']}

Please provide a comprehensive PRD with these sections:

## 1. Executive Summary
- High-level overview
- Business value proposition
- Expected outcomes

## 2. Problem Statement
- Current pain points
- User needs
- Market opportunity

## 3. Goals & Success Metrics
- Specific measurable goals
- KPIs and metrics
- Definition of success

## 4. User Stories with Acceptance Criteria
At minimum include stories for:
- Submitting an idea with ROI, effort, and risk data
- Viewing and filtering ideas
- Exporting idea data

## 5. Functional Requirements
Detailed requirements for:
- Idea capture form (fields, validation)
- ROI calculation/input
- Effort estimation
- Risk assessment options
- Search and filter capabilities
- Data export functionality

## 6. Non-Functional Requirements
- Performance expectations
- Security requirements
- Usability standards
- Scalability needs

## 7. Technical Considerations
- Database schema recommendations
- API endpoints needed
- Integration points
- Technology recommendations

## 8. Dependencies & Risks
- External dependencies
- Technical risks
- Mitigation strategies

Be specific and provide actionable details that engineers can implement.
"""
        
        response = provider_chain.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=8000
        )
        
        if response:
            print(f"✓ PRD Generated using {response.provider.value}")
            print(f"✓ Model: {response.model}")
            print("\n" + "=" * 80)
            print("GENERATED PRD (Full Content)")
            print("=" * 80 + "\n")
            
            # Show full content
            print(response.content)
            
            print("\n" + "=" * 80)
            print("✅ TEST SUCCESSFUL")
            print("=" * 80)
            print(f"\nTotal Length: {len(response.content)} characters")
            print("\nKey Points Covered:")
            
            # Check for key elements
            content_lower = response.content.lower()
            checks = [
                ("ROI estimation", "roi" in content_lower),
                ("Effort estimation", "effort" in content_lower),
                ("Risk assessment", "risk" in content_lower),
                ("Business case", "business" in content_lower and "case" in content_lower),
                ("User stories", "user stor" in content_lower),
                ("Acceptance criteria", "acceptance" in content_lower),
            ]
            
            for check_name, check_result in checks:
                status = "✓" if check_result else "✗"
                print(f"  {status} {check_name}")
            
            return True
        else:
            print("❌ No response from AI provider")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_idea_management()
    sys.exit(0 if success else 1)
