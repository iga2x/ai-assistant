from assistant.context.normalizer import InputNormalizer
from assistant.context.resolver import ContextResolver
from assistant.context.entities import EntityStore
from assistant.brain.prompt_builder import PromptBuilder
from assistant.ai.router import AIRouter
from assistant.tasks.planner import Planner
from assistant.db.services import ConversationService
from assistant.actions.router import ActionRouter
from assistant.tools.runner import ToolRunner
from assistant.tasks.task_types import Plan, PlanStep

class ChatPipeline:
    def __init__(self, db_manager, config_manager, sys_info):
        self.db = db_manager
        self.config_manager = config_manager
        self.config = config_manager.config
        self.sys_info = sys_info
        
        self.normalizer = InputNormalizer()
        self.entity_store = EntityStore(self.db)
        self.context_resolver = ContextResolver(self.entity_store)
        self.prompt_builder = PromptBuilder(self.sys_info, self.config)
        self.router = AIRouter(self.config_manager)
        self.planner = Planner(self.db, self.sys_info)
        self.conv_service = ConversationService(self.db.session)
        
        self.tool_runner = ToolRunner()
        self.action_router = ActionRouter(self.sys_info, self.tool_runner)

    async def process(self, user_input: str, conversation_id: int):
        # 1. Normalize
        normalized = self.normalizer.normalize(user_input)
        
        # 2. Resolve
        resolved = self.context_resolver.resolve(normalized)
        
        # 3. Build context-aware prompt
        entities = self.entity_store.get_all()
        system_prompt = self.prompt_builder.build_system_prompt(entities, resolved)
        
        # 4. Get History
        history = self.conv_service.get_history(conversation_id)
        
        # 5. Build message list
        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": resolved})
        
        # 6. AI Router (Get response)
        raw_output = await self.router.chat_completion(messages)
        
        # 7. Planner (Create action request or plan)
        response = self.planner.create_plan(raw_output, resolved)
        
        # 8. Action Execution (Handle read-only actions directly)
        if response.action_request and response.action_request.action_type == "read_only_system_action":
            action_result = await self.action_router.route(response.action_request)
            if action_result.success:
                # Update response content with action output
                response.reasoning = response.action_request.reasoning
                response.plan = Plan(
                    title=f"Action Result: {response.action_request.intent}",
                    intent=response.action_request.intent,
                    risk_level="low",
                    requires_approval=False,
                    steps=[PlanStep(description=action_result.output, tool="assistant", requires_approval=False)]
                )

        # 9. Store (Original input and response)
        self.conv_service.save_message(conversation_id, "user", user_input)
        self.conv_service.save_message(conversation_id, "assistant", response.content)
        
        return response
