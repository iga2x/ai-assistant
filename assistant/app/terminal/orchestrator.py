from typing import Dict, Any, List, Optional
import re
from assistant.context.normalizer import InputNormalizer
from assistant.context.resolver import ContextResolver
from assistant.memory import MemoryManager
from assistant.brain.prompt_builder import PromptBuilder
from assistant.ai.router import AIRouter
from assistant.tasks.planner import Planner
from assistant.tools.registry import get_global_registry
from assistant.safety.gate import SafetyGate
from assistant.ai.schemas import AIResponse, ActionType
from assistant.tasks.task_types import NON_EXECUTABLE_INTENTS
from assistant.utils.logger import get_logger
from rich.console import Console
from rich.panel import Panel
import json

logger = get_logger(__name__)
console = Console()

class Orchestrator:
    """The central brain that coordinates the request lifecycle.
    
    Phases:
    1. Understand: Normalize and resolve context.
    2. Plan: AI identifies intents and creates execution steps.
    3. Validate: Safety Gate checks all proposed actions.
    4. Execute: Action Router or Tool Registry runs the commands.
    5. Learn: Memory update based on results.
    """
    
    def __init__(self, db_manager, config_manager, sys_info):
        self.db = db_manager
        self.config = config_manager.config
        self.sys_info = sys_info
        
        # Components
        self.normalizer = InputNormalizer()
        self.memory = MemoryManager()
        self.context_resolver = ContextResolver(self.memory.entities)
        self.prompt_builder = PromptBuilder(self.sys_info, self.config)
        self.ai_router = AIRouter(config_manager)
        self.planner = Planner(self.db, self.sys_info)
        self.safety_gate = SafetyGate(config_manager)
        self.registry = get_global_registry()

    async def run(self, user_input: str, conversation_id: int) -> Dict[str, Any]:
        """Execute a full request lifecycle with multi-task support."""
        from assistant.db.services import ConversationService
        conv_service = ConversationService(self.db) if self.db else None

        # 1. UNDERSTAND
        normalized = self.normalizer.normalize(user_input)

        # Phase 6.2: Multi-task decomposition - handled by AI in one plan
        # We no longer split before sending to AI to maintain context and intent.

        # Single task: process normally
        step_outputs = []

        # Resolve context for this input
        # Only extract entities from input if it looks like technical content (IPs, paths, etc)
        # This avoids storing noise from greetings and chat messages
        import re as _re
        _has_technical_content = bool(
            _re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', normalized) or
            _re.search(r'https?://', normalized) or
            _re.search(r'/[a-zA-Z0-9\._/-]{3,}', normalized)
        )
        if _has_technical_content:
            self.memory.auto_extract(normalized)
        resolved = self.context_resolver.resolve(normalized)

        # 2. PLAN (LLM-based)
        entities = {e['name']: e['value'] for e in self.memory.entities.list_all()}
        facts = self.memory.get_all_facts()
        system_prompt = self.prompt_builder.build_system_prompt(entities, facts, resolved)

        # Fetch history
        history = []
        if conversation_id and conv_service:
            history = conv_service.get_history(conversation_id)

        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": resolved})

        raw_ai_output = await self.ai_router.chat_completion(messages)
        plan_response = self.planner.create_plan(raw_ai_output, resolved)

        # 3. VALIDATE & EXECUTE
        if plan_response.plan and plan_response.plan.steps:
            # Phase 1: Execution disabled to prevent duplicate execution
            # Orchestrator now only plans; Executor handles the actual running
            step_outputs = []
            output = plan_response.content
            final_plan = plan_response.plan

        else:
            # No plan or empty steps - pure chat
            output = plan_response.content
            final_plan = None

        final_content = output

        # LEARN — only extract entities from meaningful task output, not chat responses
        # Prevents memory noise from greetings, explanations, and generic AI responses
        if final_plan and final_plan.steps:
            self.memory.auto_extract(output)

        # 4. SYNTHESIZE (AI-driven only when plan explicitly requests it)
        # synthesis is gated on plan.needs_analysis — NOT on user input keywords
        needs_synthesis = bool(
            plan_response.plan and getattr(plan_response.plan, 'needs_analysis', False)
        )

        if needs_synthesis and step_outputs:
            try:
                synth_role = "security analyst" if "security" in str(plan_response.plan.intent) else "technical assistant"
                synth_prompt = f"""
                You are an expert {synth_role}. Summarize the following technical results for the user.
                Provide a clear, concise answer to their original request based ONLY on the data found.

                USER REQUEST: {user_input}
                TECHNICAL RESULTS:
                {final_content}

                Format: Provide a 1-2 sentence direct answer unless a full report was explicitly requested.
                """
                synth_messages = [{"role": "system", "content": synth_prompt}]

                final_synth = await self.ai_router.chat_completion(synth_messages, json_mode=False)

                display_synth = final_synth
                if final_synth.startswith("{"):
                    try:
                        err_data = json.loads(final_synth)
                        if "content" in err_data:
                            display_synth = err_data["content"]
                    except: pass

                if "failed to respond" not in display_synth.lower():
                    report_panel = Panel(
                        display_synth,
                        title="[bold green]Assistant Answer[/bold green]",
                        border_style="green",
                        padding=(1, 2)
                    )
                    console.print("\n")
                    console.print(report_panel)
                    final_content += f"\n\n### Analysis\n{display_synth}"
            except Exception as e:
                logger.error(f"Error during synthesis: {e}")


        # Persistence
        if conversation_id and conv_service:
            conv_service.save_message(conversation_id, "user", user_input)
            conv_service.save_message(conversation_id, "assistant", final_content)


        return {
            "output": final_content,
            "plan": final_plan,
            "reasoning": plan_response.reasoning,
            "action_request": plan_response.action_request,
            "status": "completed"
        }

    def _split_multi_task(self, text: str) -> List[str]:
        """Split multi-task input into separate tasks.

        Uses the same pattern as the multi-task comma test.
        """
        # Pattern from tests/integration/test_multi_task_comma.py
        task_pattern = r'(?:\s+(?:and|then|followed by|after that)[,\s]*|,\s+)'

        sub_inputs = re.split(task_pattern, text, flags=re.IGNORECASE)

        # Clean up: strip whitespace and trailing punctuation, filter empty
        cleaned_tasks = []
        for task in sub_inputs:
            # Strip trailing punctuation more aggressively
            cleaned = task.strip().rstrip(',;:?!')
            # Remove any trailing separators that might remain
            cleaned = re.sub(r'[,;:?!]+$', '', cleaned).strip()
            if cleaned:
                cleaned_tasks.append(cleaned)

        # If we only have one task after cleaning, return the cleaned version
        # (not the original text, which might have trailing punctuation)
        if len(cleaned_tasks) == 1:
            return cleaned_tasks
        # If no tasks after cleaning (shouldn't happen), return original
        elif not cleaned_tasks:
            return [text]
        # Multiple tasks found, return all
        else:
            return cleaned_tasks

    async def _process_multi_task(self, sub_tasks: List[str], original_input: str,
                                   conversation_id: int, conv_service) -> Dict[str, Any]:
        """Process multiple tasks separately and combine results."""

        all_results = []
        all_plans = []
        all_reasonings = []

        for task in sub_tasks:
            # Process each sub-task recursively (but without re-splitting)
            # To avoid infinite recursion, we process directly
            result = await self._process_single_task(task, conversation_id, conv_service)
            all_results.append(result)
            if result.get("plan"):
                all_plans.append(result["plan"])
            if result.get("reasoning"):
                all_reasonings.append(result["reasoning"])

        # Combine all outputs
        combined_output = "\n\n".join([
            f"Task {i+1}: {task}\n{r.get('output', 'No output')}"
            for i, (task, r) in enumerate(zip(sub_tasks, all_results))
        ])

        # Create a combined plan if any tasks had plans
        combined_plan = None
        if all_plans:
            from assistant.tasks.task_types import Plan, PlanStep
            combined_steps = []
            for plan in all_plans:
                if plan and plan.steps:
                    combined_steps.extend(plan.steps)

            if combined_steps:
                combined_plan = Plan(
                    title=f"Multi-task: {', '.join(sub_tasks[:2])}" + ("..." if len(sub_tasks) > 2 else ""),
                    intent="multi_task",
                    risk_level="low",
                    steps=combined_steps[:10]  # Limit to 10 steps total
                )

        return {
            "output": combined_output,
            "plan": combined_plan,
            "reasoning": " | ".join(all_reasonings) if all_reasonings else "Processed multiple tasks",
            "action_request": all_results[0].get("action_request") if all_results else None,
            "status": "completed"
        }

    async def _process_single_task(self, task: str, conversation_id: int,
                                   conv_service) -> Dict[str, Any]:
        """Process a single task (internal helper for multi-task)."""

        # Resolve context for this task
        resolved = self.context_resolver.resolve(task)

        # PLAN (LLM-based)
        entities = {e['name']: e['value'] for e in self.memory.entities.list_all()}
        facts = self.memory.get_all_facts()
        system_prompt = self.prompt_builder.build_system_prompt(entities, facts, resolved)

        # Fetch history
        history = []
        if conversation_id and conv_service:
            history = conv_service.get_history(conversation_id)

        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": m.role, "content": m.content})
        messages.append({"role": "user", "content": resolved})

        raw_ai_output = await self.ai_router.chat_completion(messages)
        plan_response = self.planner.create_plan(raw_ai_output, resolved)

        # VALIDATE & EXECUTE
        if plan_response.plan and plan_response.plan.steps:
            output = plan_response.content
            final_plan = plan_response.plan
        else:
            output = plan_response.content
            final_plan = None

        # LEARN
        if final_plan and final_plan.steps:
            self.memory.auto_extract(output)

        return {
            "output": output,
            "plan": final_plan,
            "reasoning": plan_response.reasoning,
            "action_request": plan_response.action_request,
            "status": "completed"
        }

    def _allows_system_context(self, user_input: str, plan_response, execution_result) -> bool:
        """Determine if system context may appear in user-facing answer."""
        import re

        # Pattern 1: User explicitly asks for system info
        system_info_patterns = [
            r'\b(?:what\'?s?\s*(?:my|your|the)\s*(?:hostname|os|operating\s+system|username|user|ip(?:\s+address)?|interface))',
            r'\b(?:show|list|tell\s+me|display)\s*(?:system\s*info|hostname|os|ip|interface)',
            r'\b(?:hostname|whoami|id|uname)\b',  # Command names
            r'\b(?:find|get|show|what\s+(?:is|are|are))\s*(?:my|your|the)\s*(?:hostname|os|username|ip|address)',
        ]

        for pattern in system_info_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                logger.debug(f"User explicitly requested system info: {user_input}")
                return True

        # Pattern 2: Command was executed and result is being summarized
        if execution_result and execution_result.success:
            logger.debug(f"System context allowed: command executed successfully")
            return True

        # Pattern 3: Plan exists with steps (task execution context)
        if plan_response.plan and plan_response.plan.steps:
            logger.debug(f"System context allowed: plan with steps exists")
            return True

        logger.debug(f"System context not allowed: {user_input}")
        return False

