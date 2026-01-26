"""Test that AI generation works with working providers"""
import os
os.chdir(r"c:\Piyush - Personal\GenAI\AI-Squad-Test")

from ai_squad.agents.product_manager import ProductManagerAgent
from ai_squad.core.config import Config

# Load config
config = Config.load()

# Create PM agent
pm = ProductManagerAgent(config)

print("Testing AI generation with working Copilot provider...")
print(f"AI Provider available: {pm.ai_provider is not None}")
print(f"Number of providers: {len(pm.ai_provider._providers)}")

# Test with a simple prompt directly
from ai_squad.core.ai_provider import CopilotProvider
provider = CopilotProvider()
print(f"\nCopilot available: {provider.is_available()}")

if provider.is_available():
    print("\n✓ Testing simple generation...")
    response = provider.generate(
        "You are a helpful assistant", 
        "Write exactly 2 sentences about what a Product Manager does",
        "gpt-5.2-codex",
        0.5,
        200
    )
    
    if response and response.content:
        print(f"✓ Got response: {response.content[:150]}...")
        print(f"✓ Provider used: {response.provider.value}")
        print("\n✓ TEST PASSED: AI generation works!")
    else:
        print("✗ No response received")
else:
    print("✗ Copilot not available")
