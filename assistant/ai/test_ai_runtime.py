
import asyncio
from assistant.ai.router import AIRouter
from assistant.config.manager import ConfigManager

async def test_real_ai():
    config = ConfigManager()
    router = AIRouter(config)
    
    print(f"Testing with model: {config.config.ai.default_local_model}")
    
    messages = [{"role": "user", "content": "hi"}]
    response = await router.chat_completion(messages)
    
    print("\nAI Response:")
    print(response)

if __name__ == "__main__":
    asyncio.run(test_real_ai())
