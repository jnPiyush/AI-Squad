"""
Diagnostic script to verify Copilot enterprise license detection
"""
import logging
import sys
from ai_squad.core.ai_provider import AIProviderChain, CopilotProvider

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    print("=" * 70)
    print("Copilot Enterprise License Detection Diagnostic")
    print("=" * 70)
    
    # Test CopilotProvider directly
    print("\n1. Testing CopilotProvider directly...")
    print("-" * 70)
    copilot = CopilotProvider()
    
    available = copilot.is_available()
    print(f"✓ Copilot Available: {available}")
    
    if available:
        print(f"✓ Enterprise License Detected: {copilot._enterprise_detected}")
        if copilot._vscode_session:
            print(f"✓ VS Code Session: {copilot._vscode_session[:16]}...")
        print(f"✓ CLI Path: {copilot._cli_path}")
    
    # Test AIProviderChain
    print("\n2. Testing AIProviderChain...")
    print("-" * 70)
    chain = AIProviderChain()
    
    print(f"✓ AI Available: {chain.is_ai_available()}")
    print(f"✓ Active Provider: {chain.provider_type.value}")
    print(f"✓ Available Providers: {', '.join(chain.get_available_providers())}")
    
    if chain._active_provider and hasattr(chain._active_provider, '_enterprise_detected'):
        print(f"✓ Active Provider Enterprise: {chain._active_provider._enterprise_detected}")
    
    # Test generation (small test)
    print("\n3. Testing Copilot generation...")
    print("-" * 70)
    if available:
        try:
            result = copilot.generate(
                system_prompt="You are a helpful assistant.",
                user_prompt="Say 'Hello from enterprise Copilot!' in 5 words or less.",
                temperature=0.3,
                max_tokens=50
            )
            
            if result:
                print(f"✓ Generation Success!")
                print(f"  Provider: {result.provider.value}")
                print(f"  Model: {result.model}")
                print(f"  Content: {result.content[:100]}")
            else:
                print("❌ Generation returned None")
                
        except Exception as e:
            print(f"❌ Generation Error: {e}")
    else:
        print("⚠ Skipping generation test (Copilot not available)")
    
    print("\n" + "=" * 70)
    print("Diagnostic Complete")
    print("=" * 70)
    
    if available and copilot._enterprise_detected:
        print("\n✅ SUCCESS: Copilot with enterprise license detected!")
        return 0
    elif available:
        print("\n⚠ WARNING: Copilot available but enterprise license not detected")
        return 1
    else:
        print("\n❌ ERROR: Copilot not available")
        return 2

if __name__ == "__main__":
    sys.exit(main())
