
import asyncio
from assistant.app.terminal.orchestrator import Orchestrator
from assistant.config.manager import ConfigManager
from assistant.system.discovery import discover_system

async def test():
    config_mgr = ConfigManager()
    sys_info = discover_system()
    orch = Orchestrator(None, config_mgr, sys_info)
    
    print("Running 'find my ip'...")
    result = await orch.run("find my ip", None)
    
    print("\n--- RESULT OUTPUT ---")
    print(result['output'])
    print("\n--- REASONING ---")
    print(result['reasoning'])

if __name__ == "__main__":
    asyncio.run(test())
