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
from dataclasses import dataclass, field
from typing import List as TypingList


@dataclass
class StepResult:
    description: str
    command: str
    stdout: str
    stderr: str
    exit_code: int
    status: str  # completed | failed | skipped | blocked


@dataclass
class ExecutionResult:
    success: bool
    plan_title: str
    steps: TypingList[StepResult] = field(default_factory=list)
    combined_output: str = ""
    failed_steps: TypingList[str] = field(default_factory=list)
    skipped_steps: TypingList[str] = field(default_factory=list)

console = Console()

class Executor:
    def __init__(self, db: DatabaseManager, router: Any, config: Any = None):
        self.db = db
        self.router = router
        self.config = config
        self.runner = ToolRunner()
        self.ws_mgr = WorkspaceManager()
        from assistant.context.entities import EntityStore
        from assistant.context.resolver import ContextResolver

        if db:
            self.entity_store = EntityStore(db)
            self.context_resolver = ContextResolver(self.entity_store)
        else:
            from assistant.context.entities import EntityStore as DummyStore
            self.entity_store = None
            self.context_resolver = None

    async def execute_plan(self, plan: Plan, conversation_id: int) -> ExecutionResult:
        from assistant.tasks.task_types import ActionType, TargetClass

        if plan.intent in ["chat", "chat_response", "tool_help"]:
            if plan.steps:
                console.print(f"\n[bold green]AI:[/bold green] {plan.steps[0].description}")
            return ExecutionResult(success=True, plan_title=plan.title)

        console.print(f"\n[bold yellow]Executing Plan: {plan.title}[/bold yellow]")
        sm = ScopeManager(self.db) if self.db else None
        
        result_steps: TypingList[StepResult] = []
        combined_parts: TypingList[str] = []
        failed_steps: TypingList[str] = []
        skipped_steps: TypingList[str] = []

        main_target = "general"
        for step in plan.steps:
            target = self.extract_target(step.command)
            if target != "127.0.0.1":
                main_target = target
                break

        session_dir = self.ws_mgr.create_session_dir(main_target)

        for step in plan.steps:
            if step.status == "completed":
                continue

            if step.tool == "assistant":
                console.print(f"\n[bold green]AI:[/bold green] {step.description}")
                step.status = "completed"
                result_steps.append(StepResult(
                    description=step.description, command="",
                    stdout=step.description, stderr="", exit_code=0, status="completed"
                ))
                continue

            console.print(f"[bold cyan]Step:[/bold cyan] {step.description}")

            step.command = self.substitute_context(step.command)

            target = self.extract_target(step.command)
            target_class = self.classify_target(target)

            if sm and (plan.intent == "network_scan" or "scan" in step.command.lower()):
                if target_class in [TargetClass.PUBLIC_IP, TargetClass.PUBLIC_DOMAIN]:
                    if not sm.is_in_scope(target):
                        console.print(f"[bold red]Safety Block:[/bold red] Target '{target}' is PUBLIC and OUT OF SCOPE. Skipping.")
                        step.status = "blocked"
                        skipped_steps.append(step.description)
                        continue

                if target_class == TargetClass.LOCAL_PRIVATE_SUBNET and not plan.requires_approval:
                    if not Confirm.ask(f"[bold yellow]Warning:[/bold yellow] This is a local subnet scan ({target}). Proceed?"):
                        console.print("[yellow]Scan aborted by user.[/yellow]")
                        step.status = "skipped"
                        skipped_steps.append(step.description)
                        continue

            step_needs_approval = step.requires_approval and not plan.requires_approval
            if step_needs_approval:
                if not Confirm.ask(f"Do you approve running: [bold green]{step.command}[/bold green]?"):
                    console.print("[yellow]Step skipped by user.[/yellow]")
                    step.status = "skipped"
                    skipped_steps.append(step.description)
                    continue

            if self.config and hasattr(self.config, 'execution') and self.config.execution.mode == "learning":
                console.print(f"[bold yellow]Learning Mode:[/bold yellow] Would execute: [dim]{step.command}[/dim]")
                result = {"success": True, "stdout": "Simulated output", "stderr": "", "returncode": 0}
            else:
                result = self.runner.run_tool(step.tool, step.command, cwd=str(session_dir))

            # Write per-step log only if workspace capture is explicitly enabled
            if self.config and getattr(getattr(self.config, 'execution', None), 'save_all_outputs', False):
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
                stdout = result["stdout"]
                if self.db:
                    self.db.log_audit(step.command, "success", result["returncode"])

                from assistant.analysis.parsers import parse_arp_scan, parse_ip_neighbor, parse_security_findings
                
                if "nmap" in step.command.lower():
                    await self.handle_nmap_analysis(step, stdout)
                elif "arp-scan" in step.command.lower():
                    hosts = parse_arp_scan(stdout)
                    if hosts:
                        from rich.table import Table
                        table = Table(title="ARP Discovery Results")
                        table.add_column("IP Address", style="cyan")
                        table.add_column("MAC Vendor / Latency", style="dim")
                        for h in hosts:
                            table.add_row(h.ip, h.latency)
                        console.print(table)
                elif "ip neighbor" in step.command.lower() or "ip neigh" in step.command.lower():
                    hosts = parse_ip_neighbor(stdout)
                    if hosts:
                        from rich.table import Table
                        table = Table(title="Known Network Neighbors (ARP Cache)")
                        table.add_column("IP Address", style="cyan")
                        table.add_column("Status", style="magenta")
                        for h in hosts:
                            table.add_row(h.ip, h.status)
                        console.print(table)
                elif any(tool in step.command.lower() for tool in ["subfinder", "assetfinder", "amass"]):
                    from assistant.analysis.parsers import parse_subdomains
                    domains = parse_subdomains(stdout)
                    if domains:
                        from rich.table import Table
                        table = Table(title=f"Subdomains Discovered ({len(domains)})")
                        table.add_column("Domain", style="cyan")
                        for d in sorted(domains):
                            table.add_row(d)
                        console.print(table)
                else:
                    findings = parse_security_findings(stdout)
                    if findings:
                        from rich.table import Table
                        table = Table(title="Security Findings Detected")
                        table.add_column("Severity", style="bold red")
                        table.add_column("Finding", style="white")
                        table.add_column("Target", style="cyan")
                        
                        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
                        sorted_findings = sorted(findings, key=lambda x: sev_order.get(x.severity, 99))
                        
                        for f in sorted_findings:
                            color = "red" if f.severity in ["critical", "high"] else "yellow" if f.severity == "medium" else "blue"
                            table.add_row(f"[{color}]{f.severity.upper()}[/{color}]", f.title, f.target)
                        console.print(table)
                
                if stdout:
                    self.extract_entities(stdout)
                    console.print(f"[dim]{stdout}[/dim]")

                result_steps.append(StepResult(
                    description=step.description, command=step.command,
                    stdout=stdout, stderr=result["stderr"],
                    exit_code=result["returncode"], status="completed"
                ))
                # Always append to combined_parts to preserve all step outputs
                combined_parts.append(stdout)

            else:
                stderr = result["stderr"]
                console.print(f"[bold red]Step failed:[/bold red] {stderr}")
                step.status = "failed"
                failed_steps.append(step.description)
                result_steps.append(StepResult(
                    description=step.description, command=step.command,
                    stdout=result["stdout"], stderr=stderr,
                    exit_code=result["returncode"], status="failed"
                ))
                if self.db:
                    self.db.log_audit(step.command, "failed", result["returncode"])
                break

        console.print("[bold green]Plan execution finished.[/bold green]\n")
        overall_success = len(failed_steps) == 0
        return ExecutionResult(
            success=overall_success,
            plan_title=plan.title,
            steps=result_steps,
            combined_output="\n".join(combined_parts),
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
        )

    def substitute_context(self, command: str) -> str:
        if not self.entity_store:
            return command

        resolved = command

        entities = self.entity_store.get_all()

        last_ip = entities.get("last_ip")
        last_target = entities.get("last_target")
        last_domain = entities.get("last_domain")

        substitutions = {
            "<ip>": last_ip or last_target or "127.0.0.1",
            "<target>": last_target or last_ip or "127.0.0.1",
            "it": last_target or last_ip or "127.0.0.1",
            "my ip": last_ip or "127.0.0.1",
            "that ip": last_ip or last_target or "127.0.0.1",
            "the same target": last_target or last_ip or "127.0.0.1",
        }

        import re
        for placeholder, value in substitutions.items():
            if value:
                pattern = r'\b' + re.escape(placeholder) + r'\b'
                resolved = re.sub(pattern, value, resolved, flags=re.IGNORECASE)

        return resolved

    def classify_target(self, target: str) -> str:
        from assistant.tasks.task_types import TargetClass
        import ipaddress
        
        if target in ["127.0.0.1", "localhost"]:
            return TargetClass.LOCAL_MACHINE
            
        try:
            ip = ipaddress.ip_address(target)
            if ip.is_private:
                return TargetClass.LOCAL_PRIVATE_IP
            return TargetClass.PUBLIC_IP
        except ValueError:
            if "/" in target:
                return TargetClass.LOCAL_PRIVATE_SUBNET # Simplification
            if "." in target:
                return TargetClass.PUBLIC_DOMAIN
        
        return TargetClass.UNKNOWN

    def extract_target(self, command: str) -> str:
        for word in command.split():
            if "." in word or "localhost" in word:
                return word.strip(".,?!")
        return "127.0.0.1"

    def extract_entities(self, text: str):
        if self.context_resolver:
            self.context_resolver.extract_entities(text) 


    async def handle_nmap_analysis(self, step: PlanStep, output: str):
        if not self.db:
            return

        results = parse_nmap_output(output)
        services = results.get("services", [])
        hosts = results.get("hosts", [])

        if not services and not hosts:
            console.print("[yellow]No hosts or services found in nmap output.[/yellow]")
            return

        target = self.extract_target(step.command)

        # Show discovery results if no services but hosts found
        if not services and hosts:
            from rich.table import Table
            table = Table(title=f"Host Discovery: {target}")
            table.add_column("IP/Hostname", style="cyan")
            table.add_column("Status", style="green")
            for h in hosts:
                table.add_row(h.ip, h.status)
            console.print(table)
            return

        with self.db.get_session() as session:
            # ... existing service persistence logic ...

            prev_snapshot = session.query(ScanSnapshot).filter_by(
                target=target, tool_name="nmap"
            ).order_by(ScanSnapshot.created_at.desc()).first()

            new_snapshot = ScanSnapshot(tool_name="nmap", target=target, raw_output=output)
            session.add(new_snapshot)
            session.flush()

            for s in services:
                db_service = Service(
                    snapshot_id=new_snapshot.id,
                    port=s.port,
                    protocol=s.protocol,
                    service_name=s.service_name,
                    state=s.state
                )
                session.add(db_service)
            
            # Commit handled by context manager
            
            if prev_snapshot:
                # Need to detached prev_snapshot services before session closes if we use them later
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

