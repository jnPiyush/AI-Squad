"""Test AI provider chain for debugging"""
import logging
from ai_squad.core.ai_provider import get_ai_provider

# Enable INFO logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s - %(levelname)s - %(message)s'
)

print("=" * 60)
print("Test 1: Initial provider setup")
print("=" * 60)
provider = get_ai_provider()
print(f"Available providers: {provider.get_available_providers()}")
print(f"Active provider: {provider.active_provider.provider_type.value if provider.active_provider else 'None'}")

print("\n" + "=" * 60)
print("Test 2: First generation")
print("=" * 60)
result1 = provider.generate(
    "You are a PM.",
    "Write one short sentence about PMs."
)
print(f"Result 1 success: {result1 is not None}")
if result1:
    print(f"Provider: {result1.provider.value}")
    print(f"Content: {result1.content[:80]}...")

print("\n" + "=" * 60)
print("Test 3: Second generation (simulating another agent call)")
print("=" * 60)
result2 = provider.generate(
    "You are an Architect.",
    "Write one short sentence about Architects."
)
print(f"Result 2 success: {result2 is not None}")
if result2:
    print(f"Provider: {result2.provider.value}")
    print(f"Content: {result2.content[:80]}...")

print("\n" + "=" * 60)
print("Test 4: Get provider again (simulating agent initialization)")
print("=" * 60)
provider2 = get_ai_provider()
print(f"Same instance: {provider is provider2}")
print(f"Available providers: {provider2.get_available_providers()}")

result3 = provider2.generate(
    "You are an Engineer.",
    "Write one short sentence about Engineers."
)
print(f"Result 3 success: {result3 is not None}")
if result3:
    print(f"Provider: {result3.provider.value}")
    print(f"Content: {result3.content[:80]}...")

print("\nAll tests complete!")
