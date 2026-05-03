from assistant.app.terminal.orchestrator import Orchestrator
from types import SimpleNamespace
import time


class ChatPipeline:
    """The ChatPipeline now acts as a thin wrapper around the Orchestrator.
    
    This maintains backward compatibility with the terminal CLI while
    enforcing the new layered architecture.
    """
    def __init__(self, db_manager, config_manager, sys_info):
        self.db = db_manager
        self.config_manager = config_manager
        self.sys_info = sys_info
        
        # Phase 5: Delegating to Orchestrator
        self.orchestrator = Orchestrator(db_manager, config_manager, sys_info)

    @property
    def entity_store(self):
        """Access to memory entities for the terminal UI."""
        return self.orchestrator.memory.entities

    @property
    def router(self):
        """Access to the AI router for backward compatibility."""
        return self.orchestrator.ai_router

    @property
    def memory(self):
        """Access to memory manager for backward compatibility."""
        return self.orchestrator.memory

    @property
    def planner(self):
        """Access to planner for backward compatibility."""
        return self.orchestrator.planner

    @property
    def prompt_builder(self):
        """Access to prompt builder for backward compatibility."""
        return self.orchestrator.prompt_builder



    async def process(self, user_input: str, conversation_id: int):
        """Processes input by classifying it and routing to the appropriate handler."""
        start_time = time.time()
        # 1. ORCHESTRATOR PATH (Unified AI Call)
        # Phase 2.5: Removed legacy `classify_intent` AI call to fix latency (was doing 2 AI calls per input)
        # Orchestrator natively handles Chat (Path A) vs Task (Path B) in a single LLM request.
        
        result = await self.orchestrator.run(user_input, conversation_id)
        
        # If the Orchestrator didn't produce an executable plan, it's natively treated as Chat.
        return SimpleNamespace(
            content=result.get("output", "I understand."),
            plan=result["plan"],
            reasoning=result.get("reasoning", ""),
            action_request=result.get("action_request"),
            latency=time.time() - start_time
        )





    def substitute_context(self, command: str) -> str:
        """Substitute context placeholders using the orchestrator's resolver."""
        return self.orchestrator.context_resolver.resolve(command)
