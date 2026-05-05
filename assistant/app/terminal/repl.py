import asyncio
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.prompt import Confirm
from rich.syntax import Syntax

from assistant.utils.paths import get_log_file
from assistant.system.discovery import discover_system
from assistant.ai.detector import detect_providers
from assistant.ai.response_parser import ResponseParser
from assistant.ai.response_types_v2 import StructuredResponse
from assistant.tools.manager import ToolManager
from assistant.config.manager import ConfigManager
from assistant.db.database import DatabaseManager
from assistant.db.services import ConversationService
from assistant.app.terminal.pipeline import ChatPipeline
from assistant.tasks.workflow_manager import WorkflowManager
from assistant.actions.executor import Executor
from assistant.analysis.synthesizer import synthesize_result
from assistant.analysis.report_builder import ReportBuilder


console = Console()

class InteractiveREPL:
    def __init__(self):
        try:
            self.db = DatabaseManager()
            self.conv_service = ConversationService(self.db.session)
        except Exception:
            self.db = None
            self.conv_service = None
            
        self.config_mgr = ConfigManager()
        self.sys_info = discover_system()
        self.pending_plan = None

        # New layers
        self.pipeline = ChatPipeline(self.db, self.config_mgr, self.sys_info)
        self.workflow_mgr = WorkflowManager()

        self.executor = Executor(self.db, self.pipeline.router, self.config_mgr.config if self.config_mgr else None)

        # Debug mode flag
        self.debug_enabled = False

        # Response parser for structured responses
        self.response_parser = ResponseParser()

        # Initialize session state
        self.conversation = None
        if self.conv_service:
            try:
                self.conversation = self.conv_service.get_or_create_conversation("Default Session")
            except Exception:
                pass
            
        self.last_response = None
        self.last_intent = None

    async def start(self):
        console.print("AI Assistant started. Type /help")
        self._auto_discover_identity()
        
        # Setup tab completion for files/directories
        import readline
        import glob
        import os

        def completer(text, state):
            # First, try to complete commands starting with /
            if text.startswith('/'):
                commands = ['/status', '/context', '/memory', '/remember', '/forget', '/tools', '/ai', '/report', '/compare', '/mode', '/history', '/test', '/plan', '/debug', '/clear', '/help', '/exit']
                matches = [c for c in commands if c.startswith(text)]
                return matches[state] if state < len(matches) else None

            # Otherwise, complete files and directories
            # We use glob to expand the path
            try:
                # Handle home directory expansion
                expanded_text = os.path.expanduser(text)
                
                # Use glob to find matches
                matches = glob.glob(expanded_text + '*')
                
                # Append / to directories
                matches = [m + '/' if os.path.isdir(m) else m for m in matches]
                
                # If original text used ~, return with ~
                if text.startswith('~'):
                    home = os.path.expanduser('~')
                    matches = [m.replace(home, '~', 1) for m in matches]
                
                return matches[state] if state < len(matches) else None
            except Exception:
                return None

        readline.set_completer(completer)
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind("tab: complete")

        while True:
            try:
                # Use standard input() for readline support, but print prompt with rich
                console.print("[bold cyan]You:[/bold cyan] ", end="")
                user_input = input().strip()
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
                        if not user_input.startswith("/debug "):  # If just /debug, toggle mode
                            self.debug_enabled = not self.debug_enabled
                            console.print(f"[bold green]Debug mode: {'enabled' if self.debug_enabled else 'disabled'}[/bold green]")
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
                    if user_input.startswith("/remember"):
                        await self.handle_remember_command(user_input)
                        continue
                    if user_input.startswith("/forget"):
                        self.handle_forget_command(user_input)
                        continue
                    if user_input.startswith("/test"):
                        await self.handle_test_command(user_input)
                        continue
                    if user_input.startswith("/setup"):
                        self.handle_setup_command()
                        continue
                    if user_input.startswith("/session"):
                        self.handle_session_command(user_input)
                        continue
                    if user_input.startswith("/workflow"):
                        self.handle_workflow_command(user_input)
                        continue

                await self.process_input(user_input)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                console.print(f"[red]Error: {e}[/red]")
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
        
        console.print("[yellow]Goodbye![/yellow]")

    def show_help(self):
        console.print("""
Available Commands:
/status  - Show environment and assistant status
/context - Manage session context (/context show, /context clear)
/memory  - Manage memory (/memory show, /memory cleanup, /memory export, /memory clear)
/remember - Store a fact (/remember name = value)
/forget  - Remove a fact (/forget name)
/tools   - List detected tools and their versions
/ai      - List available AI providers and models
/report  - Generate a Markdown session report
/compare - Compare the last two scans for the current target
/mode    - Toggle between 'chat', 'semi', and 'full' modes
/debug   - Show debug info (/debug to toggle, /debug intent, /debug plan, /debug prompt)
/history - Show recent conversation history
/test    - Run health tests (/test brain, /test body)
/plan    - Show dry-run plan for a request (/plan scan 127.0.0.1)
/debug   - Show debug info (/debug intent, /debug plan, /debug prompt)
/clear   - Clear terminal screen
/help    - Show this help
/setup   - Interactive configuration wizard
/exit    - Quit the assistant
""")

    def _auto_discover_identity(self):
        """Silently discover and remember the user's local identity."""
        try:
            local_ip = self.sys_info.local_ip
            if local_ip and local_ip != "127.0.0.1":
                self.pipeline.memory.entities.set("my_local_ip", local_ip, "ip")
                # Also store in short-term context
                self.pipeline.entity_store.set("my_local_ip", local_ip)
            
            hostname = self.sys_info.hostname
            if hostname:
                self.pipeline.memory.entities.set("my_hostname", hostname, "hostname")
                self.pipeline.entity_store.set("my_hostname", hostname)
        except Exception:
            pass

    async def _handle_suggestions(self):
        """Ask user about suggested memories with context, avoiding 'self' duplicates."""
        while self.pipeline.memory.suggested_memories:
            suggestion = self.pipeline.memory.suggested_memories.pop(0)
            val = suggestion["value"]
            typ = suggestion["type"]
            
            # SILENT AUTO-BIND: If this is my own IP, just save it and move on
            if typ == "ip" and val == self.sys_info.local_ip:
                self.pipeline.memory.entities.set("my_local_ip", val, "ip")
                continue

            from rich.prompt import Prompt
            
            console.print(f"\n[bold yellow]Memory Suggestion:[/bold yellow] Found {typ} [white]'{val}'[/white].")
            
            if typ == "ip":
                is_mine = Confirm.ask("Is this your device (local machine)?")
                if is_mine:
                    name = "my_local_ip"
                else:
                    name = Prompt.ask(f"What is this IP? (e.g. gateway, target-pc, home-router)", default=f"device_{val.split('.')[-1]}")
            else:
                default_name = val.replace("/", "_").replace(".", "_").replace("~", "home").strip("_")
                if len(default_name) > 20: default_name = f"entry_{typ}_{hash(val)%1000}"
                name = Prompt.ask(f"How should I remember this {typ}?", default=default_name)

            if name:
                self.pipeline.memory.entities.set(name, val, typ)
                console.print(f"[green]✔[/green] Saved as [cyan]{name}[/cyan] in long-term memory.")



    async def process_input(self, text: str):
        # 0. Check for explicit confirmation first to avoid AI loop
        confirm_keywords = ["yes", "ok", "yes plz", "run it", "do it", "confirm", "y"]
        if text.lower() in confirm_keywords:
            if self.pending_plan:
                await self.handle_confirmation()
                return
            else:
                console.print("\n[bold red]AI:[/bold red] There is nothing waiting for confirmation.")
                return

        with console.status("[bold green]Thinking...[/bold green]"):
            conv_id = self.conversation.id if self.conversation else None
            response = await self.pipeline.process(text, conv_id)
            
        # 1. Store last response for debug
        self.last_response = response

        # 2. Routing Logic (Action Runtime Layer)
        
        # Display Reasoning to user so they see the "expert thinking"
        if response.reasoning:
            console.print(f"\n[bold blue]Reasoning:[/bold blue] [italic]{response.reasoning}[/italic]")
        
        # Display Latency for debug/perf monitoring
        if hasattr(response, 'latency'):
            console.print(f"[dim]Latency: {response.latency:.2f}s[/dim]")

        # Show context filter metadata
        if self.debug_enabled and hasattr(response, 'debug'):
            context_filter = response.debug.get("context_filter")
            if context_filter and context_filter.get("filtered"):
                console.print(
                    f"[dim][CTX] system_context_allowed={context_filter['allowed']} "
                    f"filtered={context_filter['filtered']} "
                    f"reason={context_filter['reason']}[/dim]"
                )


        # Check if it's a direct chat or read-only action (already handled in pipeline for read-only)
        if not response.plan:
            # Parse structured response
            if response.content:
                structured = self.response_parser.parse(response.content)

                # Render using structured renderer
                console.print()  # Add spacing
                render_structured_response(console, structured)
            return

        # Handle Intent Groups
        from assistant.tasks.task_types import NON_EXECUTABLE_INTENTS, READ_ONLY_INTENTS, CONFIRMATION_INTENTS, EXECUTABLE_INTENTS

        if response.plan.intent in NON_EXECUTABLE_INTENTS:
            # Direct Chat Path: Just print
            # Parse structured response
            if response.content:
                structured = self.response_parser.parse(response.content)

                # Render using structured renderer
                console.print()  # Add spacing
                render_structured_response(console, structured)
            return

        if response.plan.intent in CONFIRMATION_INTENTS:
            # Handle confirmation (e.g. "yes", "run it")
            await self.handle_confirmation()
            return

        # Centralized Execution Decision based on Modes
        mode = getattr(self.config_mgr.config.execution, 'mode', 'semi')
        
        # If mode == chat, NEVER execute
        if mode == "chat":
            if response.plan and (response.plan.intent in EXECUTABLE_INTENTS or response.plan.intent in READ_ONLY_INTENTS or hasattr(response.plan, 'steps') and response.plan.steps):
                cmds = [s.command for s in response.plan.steps if hasattr(s, 'command') and s.command]
                if cmds:
                    explanation = f"To accomplish '{response.plan.title}', you can run:\n" + "\n".join([f"  {cmd}" for cmd in cmds])
                    console.print(f"\n[bold green]AI:[/bold green] {explanation}")
                    return
            # Parse structured response
            if response.content:
                structured = self.response_parser.parse(response.content)

                # Render using structured renderer
                console.print()  # Add spacing
                render_structured_response(console, structured)
            return
            
        # Parse structured response
        if response.content:
            structured = self.response_parser.parse(response.content)

            # Render using structured renderer
            console.print()  # Add spacing
            render_structured_response(console, structured)

            # Add mode-specific prefix if needed
            if response.plan and response.plan.intent not in NON_EXECUTABLE_INTENTS:
                if mode == "semi":
                    console.print("[dim]I have prepared a plan (see approval below)[/dim]")
                elif mode == "full":
                    if response.plan.requires_approval:
                        console.print("[dim]I have prepared a plan (see approval below)[/dim]")
                    else:
                        console.print("[dim]Executing plan[/dim]")

        exec_result = None
        if mode == "semi":
            # ALWAYS ask approval
            self.pending_plan = response.plan
            console.print(Panel(
                f"{response.plan.risk_summary}\n\n[bold]Risk Level:[/bold] {response.plan.risk_level}\n\n[dim](You can say 'yes' or 'run it' to execute)[/dim]", 
                title="Plan Approval Required (Semi Mode)", 
                subtitle=f"Intent: {response.plan.intent}"
            ))
            if Confirm.ask("[bold yellow]Execute this plan now?[/bold yellow]"):
                self.pending_plan = None
                if self.db:
                    self.pipeline.planner.save_plan(response.plan)
                exec_result = await self.executor.execute_plan(response.plan, self.conversation.id if self.conversation else None)
            else:
                console.print("[yellow]Plan stored. You can confirm it later by saying 'yes'.[/yellow]")
                
        elif mode == "full":
            if response.plan.requires_approval:
                self.pending_plan = response.plan
                console.print(Panel(
                    f"{response.plan.risk_summary}\n\n[bold]Risk Level:[/bold] {response.plan.risk_level}\n\n[dim](You can say 'yes' or 'run it' to execute)[/dim]", 
                    title="Plan Approval Required", 
                    subtitle=f"Intent: {response.plan.intent}"
                ))
                if Confirm.ask("[bold yellow]Execute this plan now?[/bold yellow]"):
                    self.pending_plan = None
                    if self.db:
                        self.pipeline.planner.save_plan(response.plan)
                    exec_result = await self.executor.execute_plan(response.plan, self.conversation.id if self.conversation else None)
                else:
                    console.print("[yellow]Plan stored. You can confirm it later by saying 'yes'.[/yellow]")
            else:
                # Execute immediately
                self.pending_plan = None
                if self.db:
                    self.pipeline.planner.save_plan(response.plan)
                exec_result = await self.executor.execute_plan(response.plan, self.conversation.id if self.conversation else None)
        
        # 3. Optional post-execution synthesis — deterministic first, AI only if needed
        if exec_result is not None:
            synthesis = await synthesize_result(
                plan=response.plan,
                result=exec_result,
                ai_router=self.pipeline.router if _needs_ai_synthesis_check(response.plan, exec_result) else None,
            )
            if synthesis:
                console.print(f"\n[bold green]Summary:[/bold green] {synthesis}")
            
            # Only suggest memories if execution succeeded
            if exec_result.success:
                await self._handle_suggestions()

    async def handle_confirmation(self):
        """Execute the last pending plan if the user said 'yes' or 'run it'."""
        if not self.pending_plan:
            console.print("\n[bold red]AI:[/bold red] There is nothing waiting for confirmation.")
            return

        plan = self.pending_plan
        self.pending_plan = None  # Clear it
        
        console.print(f"\n[bold green]AI:[/bold green] Proceeding with: [cyan]{plan.title}[/cyan]")
        if self.db:
            self.pipeline.planner.save_plan(plan)  # Persist task
        exec_result = await self.executor.execute_plan(plan, self.conversation.id if self.conversation else None)
        
        # Post-execution synthesis
        if exec_result is not None:
            synthesis = await synthesize_result(
                plan=plan,
                result=exec_result,
                ai_router=self.pipeline.router if _needs_ai_synthesis_check(plan, exec_result) else None,
            )
            if synthesis:
                console.print(f"\n[bold green]Summary:[/bold green] {synthesis}")
            
            # Only suggest memories if execution succeeded
            if exec_result.success:
                await self._handle_suggestions()

    def toggle_mode(self):
        modes = ["chat", "semi", "full"]
        current = getattr(self.config_mgr.config.execution, 'mode', 'semi')
        if current not in modes:
            current = 'semi'
        new_mode = modes[(modes.index(current) + 1) % len(modes)]
        self.config_mgr.config.execution.mode = new_mode
        self.config_mgr.save_config()
        console.print(f"[bold green]Execution mode switched to: {new_mode}[/bold green]")

    def handle_memory_command(self, cmd: str):
        parts = cmd.split()
        if len(parts) < 2:
            self._show_memory_list()
            return
            
        sub = parts[1]
        
        if sub == "show":
            category = parts[2] if len(parts) > 2 else None
            self._show_memory_list(category)
        elif sub == "cleanup":
            self.pipeline.memory.cleanup()
            console.print("[green]Memory cleanup completed. Purged old/low-confidence entries.[/green]")
        elif sub == "export":
            path = Path("memory_backup.db")
            msg = self.pipeline.memory.export(path)
            console.print(f"[bold green]{msg}[/bold green]")
        elif sub == "clear":
            from assistant.db.models import Message
            self.db.session.query(Message).filter_by(conversation_id=self.conversation.id).delete()
            self.db.session.commit()
            console.print("[green]Conversation history cleared for this session.[/green]")

    def _show_memory_list(self, category: str = None):
        entities = self.pipeline.memory.entities.list_all(category)
        if not entities:
            console.print(f"[dim]No memory entries found{f' for category {category}' if category else ''}.[/dim]")
            return
            
        table = Table(title=f"Long-term Memory {'('+category+')' if category else ''}")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Value", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Last Used", style="dim")
        
        for e in entities:
            table.add_row(
                e["name"], 
                e["type"], 
                e["value"], 
                f"{e['confidence']:.2f}", 
                e["last_used"][:10] if e["last_used"] else "-"
            )
        console.print(table)

    async def handle_remember_command(self, cmd: str):
        # /remember name = value
        if "=" not in cmd:
            console.print("[red]Usage: /remember <name> = <value>[/red]")
            return
            
        try:
            line = cmd.replace("/remember", "").strip()
            name, value = [p.strip() for p in line.split("=", 1)]
            self.pipeline.memory.entities.set(name, value, "manual_entry")
            console.print(f"[bold green]Fact remembered:[/bold green] {name} = {value}")
        except Exception as e:
            console.print(f"[red]Error saving fact: {e}[/red]")

    def handle_forget_command(self, cmd: str):
        # /forget name
        parts = cmd.split()
        if len(parts) < 2:
            console.print("[red]Usage: /forget <name>[/red]")
            return
            
        name = parts[1]
        self.pipeline.memory.entities.delete(name)
        console.print(f"[yellow]Fact forgotten:[/yellow] {name}")

    def show_tools(self):
        manager = ToolManager()
        tools = manager.detect()
        table = Table(title="Detected Tools")
        table.add_column("Tool")
        table.add_column("Status")
        table.add_column("Version")
        for tool in tools:
            status = "[green]OK[/green]" if tool.is_available() else "[red]Missing[/red]"
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
            prompt = self.pipeline.prompt_builder.build_system_prompt(entities, {}, "DEBUG")
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
            console.print("[dim]Available debug: /debug (toggle), /debug prompt, /debug intent, /debug plan[/dim]")

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

    async def handle_test_command(self, cmd: str):
        # Forward to the CLI test commands logic
        from assistant.app.commands.test import run_test_body, run_test_brain
        parts = cmd.split()
        sub = parts[1] if len(parts) > 1 else "all"
        if sub == "body":
            run_test_body()
        elif sub == "brain":
            await run_test_brain()
        else:
            run_test_body()
            await run_test_brain()

    def handle_setup_command(self):
        from assistant.app.commands.setup import setup
        from click.testing import CliRunner
        runner = CliRunner()
        from assistant.app.commands.setup import setup as setup_cmd
        setup.callback()

    def handle_session_command(self, cmd: str):
        parts = cmd.split()
        if len(parts) < 2:
            console.print("[yellow]Usage: /session [start|list|send|end] <args>[/yellow]")
            return

        action = parts[1]

        if action == "start" and len(parts) >= 3:
            tool = parts[2]
            command = " ".join(parts[3:]) if len(parts) > 3 else None
            try:
                self.workflow_mgr.create_session(tool, command)
            except Exception as e:
                console.print(f"[red]Error starting session:[/red] {e}")

        elif action == "list":
            sessions = self.workflow_mgr.list_sessions()
            if not sessions:
                console.print("[dim]No active sessions[/dim]")
            else:
                table = Table(title="Active Sessions")
                table.add_column("ID")
                table.add_column("Tool")
                table.add_column("Started")
                for s in sessions:
                    import datetime
                    started = datetime.datetime.fromtimestamp(s.started_at).strftime("%H:%M:%S")
                    table.add_row(s.id, s.tool_name, started)
                console.print(table)

        elif action == "send" and len(parts) >= 4:
            session_id = parts[2]
            command = " ".join(parts[3:])
            try:
                self.workflow_mgr.send_to_session(session_id, command)
            except Exception as e:
                console.print(f"[red]Error sending command:[/red] {e}")

        elif action == "end" and len(parts) >= 3:
            session_id = parts[2]
            self.workflow_mgr.end_session(session_id)

    def handle_workflow_command(self, cmd: str):
        parts = cmd.split()
        if len(parts) < 2:
            console.print("[yellow]Usage: /workflow [list|run|continue] <args>[/yellow]")
            return

        action = parts[1]

        if action == "list":
            workflows = self.workflow_mgr.list_workflows()
            if not workflows:
                console.print("[dim]No workflows available[/dim]")
            else:
                console.print("\n[bold cyan]Available Workflows:[/bold cyan]")
                for wf in workflows:
                    console.print(f"  • {wf}")

        elif action == "run" and len(parts) >= 4:
            workflow_name = parts[2]
            target = parts[3]
            try:
                self.workflow_mgr.run_workflow(workflow_name, target)
            except Exception as e:
                console.print(f"[red]Error running workflow:[/red] {e}")

        elif action == "continue" and len(parts) >= 3:
            workflow_name = parts[2]
            self.workflow_mgr.continue_workflow(workflow_name)

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


def render_structured_response(console, response: StructuredResponse):
    """Render a structured response with Rich formatting."""
    # Always render Answer
    console.print(f"[bold green]Answer:[/bold green] {response.answer}")

    # Render Command/Example if present
    if response.command:
        console.print(f"[bold cyan]Command / Example:[/bold cyan]")
        # Use code block if it looks like a command
        if response.command.strip().startswith(("hostname", "ip", "nmap", "ss", "ping")):
            console.print(Syntax(response.command.strip(), "bash", theme="monokai", line_numbers=False))
        else:
            console.print(response.command.strip())

    # Render Details if present
    if response.details:
        console.print(f"[bold yellow]Details:[/bold yellow] {response.details}")

    # Render Next step if present
    if response.next_step:
        console.print(f"[bold magenta]Next step:[/bold magenta] {response.next_step}")


def _needs_ai_synthesis_check(plan, result) -> bool:
    """Module-level helper so both process_input and handle_confirmation can call it."""
    from assistant.analysis.synthesizer import _needs_ai_synthesis
    return _needs_ai_synthesis(plan, result)


def run_repl():
    repl = InteractiveREPL()
    asyncio.run(repl.start())
