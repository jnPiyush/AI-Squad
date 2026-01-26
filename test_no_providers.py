"""Test that proper error is shown when no AI providers available"""
import os
os.chdir(r"c:\Piyush - Personal\GenAI\AI-Squad-Test")

from ai_squad.agents.product_manager import ProductManagerAgent
from ai_squad.core.config import Config

# Load config
config = Config.load()

# Create PM agent but break AI provider
pm = ProductManagerAgent(config)
pm.ai_provider._providers = []  # Remove all providers to simulate none available

try:
    # Try to execute - should fail with helpful error
    result = pm.execute(21)
    print("ERROR: Should have failed but didn't!")
    print(result)
except RuntimeError as e:
    print("✓ Got expected RuntimeError:")
    print(f"  {e}")
    if "AI generation failed" in str(e):
        print("\n✓ Error message contains 'AI generation failed'")
    if "GitHub Copilot" in str(e) and "OpenAI" in str(e):
        print("✓ Error message provides setup instructions")
    print("\n✓ TEST PASSED: Proper error handling works!")
except Exception as e:
    print(f"✗ Got unexpected error: {type(e).__name__}: {e}")
