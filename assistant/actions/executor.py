import asyncio
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Confirm

from assistant.db.database import DatabaseManager
from assistant.tools.runner import ToolRunner
from assistant.tasks.task_types import Plan, PlanStep
from assistant.analysis.parsers import parse_nmap_output, ParsedService
from assistant.analysis.diff_engine import DiffEngine
from assistant.analysis.report_builder import ReportBuilder
from assistant.db.models import ScanSnapshot, Service
from assistant.safety.scope import ScopeManager
from assistant.workspace.manager import WorkspaceManager
import json

console = Console()

class Executor:
    def __init__(self, db: DatabaseManager, router: Any, config: Any = None):
        self.db = db
        self.router = router
        self.config = config
        self.runner = ToolRunner()
        self.ws_mgr = WorkspaceManager()

    async def execute_plan(self, plan: Plan, conversation_id: int):
        # 1. If it's a non-executable chat plan, just print and return
        if plan.intent in ["chat_only", "tool_help", "coding_help"]:
            if plan.steps:
                console.print(f"\n[bold green]AI:[/bold green] {plan.steps[0].description}")
            return

        console.print(f"\n[bold yellow]Executing Plan: {plan.title}[/bold yellow]")
        sm = ScopeManager(self.db)
        
        # Determine main target for workspace
        main_target = "general"
        for step in plan.steps:
            target = self.extract_target(step.command)
            if target != "127.0.0.1":
                main_target = target
                break
        
        session_dir = self.ws_mgr.create_session_dir(main_target)
        console.print(f"[dim]Workspace: {session_dir}[/dim]\n")
        
        for step in plan.steps:
            if step.status == "completed":
                continue

            # Special case for assistant tool (chatting inside a plan)
            if step.tool == "assistant":
                console.print(f"\n[bold green]AI:[/bold green] {step.description}")
                step.status = "completed"
                continue

            console.print(f"[bold cyan]Step:[/bold cyan] {step.description}")
            
            # Scope Check for security/recon tools
            target = self.extract_target(step.command)
            if any(tool in step.command.lower() for tool in ["nmap", "whois", "dig", "curl"]):
                if not sm.is_in_scope(target):
                    console.print(f"[bold red]Safety Block:[/bold red] Target '{target}' is OUT OF SCOPE. Skipping step.")
                    step.status = "blocked"
                    self.db.log_audit(step.command, "blocked")
                    continue

            if step.requires_approval:
                if not Confirm.ask(f"Do you approve running: [bold green]{step.command}[/bold green]?"):
                    console.print("[yellow]Step skipped by user.[/yellow]")
                    step.status = "skipped"
                    self.db.log_audit(step.command, "skipped")
                    continue

            # Execute the tool
            if self.config and hasattr(self.config, 'execution') and self.config.execution.mode == "learning":
                console.print(f"[bold yellow]Learning Mode:[/bold yellow] Would execute: [dim]{step.command}[/dim]")
                await asyncio.sleep(0.5) 
                result = {"success": True, "stdout": f"Learning mode simulated output for: {step.command}", "stderr": "", "returncode": 0}
            else:
                result = self.runner.run_tool(step.tool, step.command, cwd=str(session_dir))
            
            # Save raw output to file
            output_file = session_dir / f"step_{step.order}_{step.tool}.log"
            with open(output_file, "w") as f:
                f.write(f"Command: {step.command}\n")
                f.write(f"Exit Code: {result['returncode']}\n")
                f.write("-" * 20 + "\n")
                f.write(result["stdout"])
                f.write(result["stderr"])

            if result["success"]:
                console.print("[bold green]Step completed successfully.[/bold green]")
                step.status = "completed"
                self.db.log_audit(step.command, "success", result["returncode"])
                
                # Post-execution analysis for nmap
                if "nmap" in step.command.lower():
                    await self.handle_nmap_analysis(step, result["stdout"])
                elif result["stdout"]:
                    console.print(f"[dim]{result['stdout']}[/dim]")
            else:
                console.print(f"[bold red]Step failed:[/bold red] {result['stderr']}")
                step.status = "failed"
                self.db.log_audit(step.command, "failed", result["returncode"])
                break
        
        console.print("[bold green]Plan execution finished.[/bold green]\n")

    def extract_target(self, command: str) -> str:
        """Extract target from command string."""
        for word in command.split():
            if "." in word or "localhost" in word:
                return word.strip(".,?!")
        return "127.0.0.1" 

    async def handle_nmap_analysis(self, step: PlanStep, output: str):
        """Parse nmap output, compare with history, and show report."""
        services = parse_nmap_output(output)
        if not services:
            console.print("[yellow]No services found in nmap output.[/yellow]")
            return

        target = self.extract_target(step.command)

        prev_snapshot = self.db.session.query(ScanSnapshot).filter_by(
            target=target, tool_name="nmap"
        ).order_by(ScanSnapshot.created_at.desc()).first()

        new_snapshot = ScanSnapshot(tool_name="nmap", target=target, raw_output=output)
        self.db.session.add(new_snapshot)
        self.db.session.commit()
        
        for s in services:
            db_service = Service(
                snapshot_id=new_snapshot.id,
                port=s.port,
                protocol=s.protocol,
                service_name=s.service_name,
                state=s.state
            )
            self.db.session.add(db_service)
        self.db.session.commit()

        if prev_snapshot:
            prev_services = [ParsedService(
                port=s.port, protocol=s.protocol, service_name=s.service_name, state=s.state
            ) for s in prev_snapshot.services]
            
            diff_engine = DiffEngine()
            diff = diff_engine.compare_services(prev_services, services)
            
            report_builder = ReportBuilder(self.db)
            table = report_builder.build_diff_table(diff)
            console.print(table)
        else:
            console.print(f"[bold green]First scan for {target} recorded. {len(services)} services found.[/bold green]")
