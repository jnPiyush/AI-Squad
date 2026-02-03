"""Test Copilot SDK authentication and enterprise detection"""
import asyncio
import json
from copilot import CopilotClient

async def check_auth():
    """Check Copilot authentication status"""
    try:
        # Initialize client
        client = CopilotClient()
        
        # Check auth status
        print("=== Copilot Auth Status ===")
        auth_status = await client.get_auth_status()
        print(f"Auth Status: {auth_status}")
        
        # Check state
        print("\n=== Copilot State ===")
        state = await client.get_state()
        print(f"State: {state}")
        
        # List models
        print("\n=== Available Models ===")
        models = await client.list_models()
        if hasattr(models, 'models'):
            for model in models.models:
                print(f"  - {model.id if hasattr(model, 'id') else model}")
        else:
            print(f"Models: {models}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(check_auth())
    print(f"\n{'✅ Success' if result else '❌ Failed'}")
