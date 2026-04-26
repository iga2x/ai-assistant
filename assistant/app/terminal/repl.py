import asyncio
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table

from assistant.utils.paths import get_log_file
from assistant.system.discovery import discover_system
from assistant.ai.detector import detect_providers
from assistant.tools.detector import detect_tools
from assistant.config.manager import ConfigManager
from assistant.db.database import DatabaseManager
from assistant.db.services import ConversationService
from assistant.app.terminal.pipeline import ChatPipeline
from assistant.actions.executor import Executor
from assistant.analysis.report_builder import ReportBuilder
from assistant.ai.detector import detect_providers
from assistant.tools.detector import detect_tools

console = Console()

class InteractiveREPL:
    def __init__(self):
        self.db = DatabaseManager()
        self.config_mgr = ConfigManager()
        self.sys_info = discover_system()
        self.pending_plan = None
        
        # New layers
        self.conv_service = ConversationService(self.db.session)
        self.pipeline = ChatPipeline(self.db, self.config_mgr, self.sys_info)
        
        self.executor = Executor(self.db, self.pipeline.router, self.config_mgr.config)
        self.conversation = self.conv_service.get_or_create_conversation("Default Session")
        
    async def start(self):
        console.print("AI Assistant started. Type /help")
        
        while True:
            try:
                user_input = console.input("You: ").strip()
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "/exit"]:
                    console.print("Goodbye.")
                    break

                if user_input.startswith("/"):
                    if user_input == "/help":
                        self.show_help()
                        continue
                    if user_input == "/clear":
                        console.clear()
                        continue
                    if user_input.startswith("/compare"):
                        await self.run_comparison()
                        continue
                    if user_input.startswith("/mode"):
                        self.toggle_mode()
                        continue
                    if user_input.startswith("/context"):
                        self.handle_context_command(user_input)
                        continue
                    if user_input.startswith("/debug"):
                        self.handle_debug_command(user_input)
                        continue
                    if user_input.startswith("/status"):
                        self.show_status()
                        continue
                    if user_input.startswith("/history"):
                        self.show_history()
                        continue
                    if user_input.startswith("/memory"):
                        self.handle_memory_command(user_input)
                        continue
                    if user_input.startswith("/tools"):
                        self.show_tools()
                        continue
                    if user_input.startswith("/ai"):
                        self.show_ai()
                        continue
                    if user_input.startswith("/report"):
                        self.generate_report()
                        continue
                    if user_input.startswith("/test"):
                        self.handle_test_command(user_input)
                        continue

                await self.process_input(user_input)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        
        console.print("[yellow]Goodbye![/yellow]")

    def show_help(self):
        console.print("""
Available Commands:
/status  - Show environment and assistant status
/context - Manage session context (/context show, /context clear)
/memory  - Manage message history (/memory show, /memory clear)
/tools   - List detected tools and their versions
/ai      - List available AI providers and models
/report  - Generate a Markdown session report
/compare - Compare the last two scans for the current target
/mode    - Toggle between 'active' and 'learning' modes
/history - Show recent conversation history
/test    - Run health tests (/test brain, /test body)
/plan    - Show dry-run plan for a request (/plan scan 127.0.0.1)
/debug   - Show debug info (/debug intent, /debug plan, /debug prompt)
/clear   - Clear terminal screen
/help    - Show this help
/exit    - Quit the assistant
""")

    async def process_input(self, text: str):
        with console.status("[bold green]Thinking...[/bold green]"):
            response = await self.pipeline.process(text, self.conversation.id)
            
        # 1. Store last response for debug
        self.last_response = response

        # 2. Routing Logic (Action Runtime Layer)
        
        # Check if it's a direct chat or read-only action (already handled in pipeline for read-only)
        if not response.plan:
            console.print(f"\n[bold green]AI:[/bold green] {response.content}")
            return

        # Handle Intent Groups
        from assistant.tasks.task_types import NON_EXECUTABLE_INTENTS, READ_ONLY_INTENTS, CONFIRMATION_INTENTS, EXECUTABLE_INTENTS
        
        # If it was a read-only action, the pipeline already executed it and updated the plan content
        if response.action_request and response.action_request.action_type == "read_only_system_action":
             console.print(f"\n[bold green]AI:[/bold green] {response.content}")
             return

        if response.plan.intent in NON_EXECUTABLE_INTENTS:
            # Direct Chat Path: Just print
            console.print(f"\n[bold green]AI:[/bold green] {response.content}")
            return

        if response.plan.intent in CONFIRMATION_INTENTS:
            # Handle confirmation (e.g. "yes", "run it")
            await self.handle_confirmation()
            return

        # Executable Path: Check for approval
        if response.plan.requires_approval or response.plan.intent in EXECUTABLE_INTENTS:
            self.pending_plan = response.plan # Store for chat-based "yes"
            
            console.print(Panel(
                f"{response.plan.risk_summary}\n\n[bold]Risk Level:[/bold] {response.plan.risk_level}\n\n[dim](You can say 'yes' or 'run it' to execute)[/dim]", 
                title="Plan Approval Required", 
                subtitle=f"Intent: {response.plan.intent}"
            ))
            if click.confirm("Execute this plan now?"):
                self.pending_plan = None # Clear if handled here
                self.pipeline.planner.save_plan(response.plan) # Persist task
                await self.executor.execute_plan(response.plan, self.conversation.id)
            else:
                console.print("[yellow]Plan stored. You can confirm it later by saying 'yes'.[/yellow]")
        else:
            # Safe executable
            self.pending_plan = None
            self.pipeline.planner.save_plan(response.plan) # Persist task
            await self.executor.execute_plan(response.plan, self.conversation.id)

    async def handle_confirmation(self):
        """Execute the last pending plan if the user said 'yes' or 'run it'."""
        if not self.pending_plan:
            console.print("\n[bold red]AI:[/bold red] I'm sorry, I don't have a pending action to confirm. What would you like me to do?")
            return

        plan = self.pending_plan
        self.pending_plan = None # Clear it
        
        console.print(f"\n[bold green]AI:[/bold green] Proceeding with: [cyan]{plan.title}[/cyan]")
        self.pipeline.planner.save_plan(plan) # Persist task
        await self.executor.execute_plan(plan, self.conversation.id)

    def toggle_mode(self):
        current = self.config_mgr.config.execution.mode
        new_mode = "learning" if current == "active" else "active"
        self.config_mgr.config.execution.mode = new_mode
        self.config_mgr.save_config()
        console.print(f"[bold green]Execution mode switched to: {new_mode}[/bold green]")

    def handle_memory_command(self, cmd: str):
        parts = cmd.split()
        sub = parts[1] if len(parts) > 1 else "show"
        
        if sub == "show":
            self.show_history()
        elif sub == "clear":
            from assistant.db.models import Message
            self.db.session.query(Message).filter_by(conversation_id=self.conversation.id).delete()
            self.db.session.commit()
            console.print("[green]Conversation history cleared for this session.[/green]")

    def show_tools(self):
        tools = detect_tools()
        table = Table(title="Detected Tools")
        table.add_column("Tool")
        table.add_column("Status")
        table.add_column("Version")
        for tool in tools:
            status = "[green]OK[/green]" if tool.is_available else "[red]Missing[/red]"
            table.add_row(tool.name, status, tool.version or "-")
        console.print(table)

    def show_ai(self):
        providers = detect_providers()
        table = Table(title="AI Providers")
        table.add_column("Provider")
        table.add_column("Status")
        table.add_column("Models")
        for p in providers:
            status = "[green]Available[/green]" if p.is_available else "[red]Unavailable[/red]"
            table.add_row(p.name, status, ", ".join(p.models[:3]) + ("..." if len(p.models) > 3 else ""))
        console.print(table)

    def generate_report(self):
        report_builder = ReportBuilder(self.db)
        report = report_builder.generate_markdown_report(self.conversation.id)
        path = Path(f"session_report_{self.conversation.id}.md")
        report_builder.export_to_file(report, path)
        console.print(f"[bold green]Report generated:[/bold green] {path.absolute()}")

    def handle_context_command(self, cmd: str):
        parts = cmd.split()
        sub = parts[1] if len(parts) > 1 else "show"
        
        if sub == "show":
            entities = self.pipeline.entity_store.get_all()
            if not entities:
                console.print("[dim]Context is empty.[/dim]")
            else:
                table = Table(title="Current Context Entities")
                table.add_column("Entity")
                table.add_column("Value")
                for k, v in entities.items():
                    table.add_row(k, v)
                console.print(table)
        elif sub == "clear":
            self.pipeline.entity_store.clear()
            console.print("[green]Context entities cleared.[/green]")

    def handle_debug_command(self, cmd: str):
        parts = cmd.split()
        sub = parts[1] if len(parts) > 1 else ""
        
        if sub == "prompt":
            entities = self.pipeline.entity_store.get_all()
            prompt = self.pipeline.prompt_builder.build_system_prompt(entities, "DEBUG")
            console.print(Panel(prompt, title="System Prompt Debug"))
        elif sub == "intent":
            if hasattr(self, "last_response") and self.last_response.plan:
                console.print(f"[bold cyan]Last Intent:[/bold cyan] {self.last_response.plan.intent}")
            else:
                console.print("[yellow]No recent intent detected.[/yellow]")
        elif sub == "plan":
            if hasattr(self, "last_response") and self.last_response.plan:
                console.print(Panel(str(self.last_response.plan.model_dump_json(indent=2)), title="Last Plan Debug"))
            else:
                console.print("[yellow]No recent plan generated.[/yellow]")
        else:
            console.print("[dim]Available debug: /debug prompt, /debug intent, /debug plan[/dim]")

    def show_status(self):
        console.print(Panel(
            f"OS: {self.sys_info.os_detailed}\n"
            f"Shell: {self.sys_info.shell}\n"
            f"Local IP: {self.sys_info.local_ip}\n"
            f"Mode: {self.config_mgr.config.execution.mode}",
            title="Assistant Status"
        ))

    def show_history(self):
        msgs = self.conv_service.get_history(self.conversation.id)
        
        for m in msgs:
            role_style = "bold cyan" if m.role == "user" else "bold green"
            console.print(f"[{role_style}]{m.role.upper()}:[/{role_style}] {m.content}")

    def handle_test_command(self, cmd: str):
        # Forward to the CLI test commands logic
        from assistant.app.commands.test import run_test_body, run_test_brain
        parts = cmd.split()
        sub = parts[1] if len(parts) > 1 else "all"
        if sub == "body":
            run_test_body()
        elif sub == "brain":
            import asyncio
            asyncio.run(run_test_brain())
        else:
            run_test_body()
            import asyncio
            asyncio.run(run_test_brain())

    async def run_comparison(self):
        # Implementation of /compare from Phase 5
        entities = self.pipeline.entity_store.get_all()
        target = entities.get("last_target")
        if not target:
            console.print("[red]No target in context to compare.[/red]")
            return
        
        report_builder = ReportBuilder(self.db)
        diff_table = report_builder.build_diff_table(target)
        if diff_table:
            console.print(diff_table)
        else:
            console.print("[yellow]No previous scans found for this target to compare.[/yellow]")

def run_repl():
    repl = InteractiveREPL()
    asyncio.run(repl.start())
