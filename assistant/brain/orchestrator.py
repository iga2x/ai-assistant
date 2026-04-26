from typing import List, Dict, Any
from assistant.ai.router import AIRouter
from assistant.brain.prompt_builder import PromptBuilder
from assistant.db.database import DatabaseManager

class Orchestrator:
    def __init__(self, db: DatabaseManager, router: AIRouter, prompt_builder: PromptBuilder):
        self.db = db
        self.router = router
        self.pb = prompt_builder

    async def get_audit(self, scan_output: str) -> str:
        """Call the Auditor agent to review results."""
        prompt = self.pb.build_auditor_prompt(scan_output)
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": "Analyze these results."}]
        return await self.router.chat_completion(messages)

    async def get_research(self, topic: str) -> str:
        """Call the Researcher agent for info."""
        prompt = self.pb.build_researcher_prompt(topic)
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": f"Research: {topic}"}]
        return await self.router.chat_completion(messages)

    async def get_plan(self, user_request: str, context_entities: Dict[str, str]) -> str:
        """Call the Planner agent to create a plan."""
        prompt = self.pb.build_planner_prompt(context_entities, user_request)
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": user_request}]
        return await self.router.chat_completion(messages)

