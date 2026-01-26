import asyncio
from copilot import CopilotClient

async def test():
    try:
        print("Creating client...")
        # Specify copilot path explicitly (first one from where.exe copilot)
        cli_path = r"c:\Users\piyushj\AppData\Roaming\Code\User\globalStorage\github.copilot-chat\copilotCli\copilot.bat"
        client = CopilotClient({"cli_path": cli_path})
        print(f"Using CLI path: {cli_path}")
        print("Starting client...")
        await client.start()
        print("Client started successfully!")
        
        print("Creating session...")
        session = await client.create_session({"model": "gpt-5.2-codex"})
        print("Session created!")
        
        done = asyncio.Event()
        response_content = []
        
        def on_event(event):
            if event.type.value == "assistant.message":
                response_content.append(event.data.content)
                print(f"Response: {event.data.content[:100]}")
            elif event.type.value == "session.idle":
                done.set()
        
        session.on(on_event)
        await session.send({"prompt": "Say hello in one sentence"})
        await done.wait()
        
        await session.destroy()
        await client.stop()
        print("[SUCCESS] Test successful!")
        return True
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    exit(0 if success else 1)
