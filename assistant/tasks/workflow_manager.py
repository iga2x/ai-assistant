import asyncio
import subprocess
import shlex
from typing import Dict, Optional, Any, List
from pathlib import Path
from rich.console import Console
from dataclasses import dataclass, field
from assistant.safety.gate import SafetyGate

console = Console()


@dataclass
class ToolSession:
    """Running interactive tool session."""
    id: str
    tool_name: str
    process: Any
    started_at: float
    output_buffer: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """Active workflow state."""
    name: str
    target: str
    current_step: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)
    completed_steps: List[str] = field(default_factory=list)


class WorkflowManager:
    """Manages interactive tool sessions and multi-step workflows."""

    def __init__(self):
        self.active_sessions: Dict[str, ToolSession] = {}
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.session_counter = 0
        self.workflows_dir = Path(__file__).parent / "workflows"
        self.safety_gate = SafetyGate()

    def create_session(self, tool_name: str, command: str = None) -> ToolSession:
        """Start interactive tool session (wifite, msfconsole, metasploit)."""
        session_id = f"session_{self.session_counter}"
        self.session_counter += 1

        cmd = command or self._get_tool_command(tool_name)

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )

            session = ToolSession(
                id=session_id,
                tool_name=tool_name,
                process=process,
                started_at=asyncio.get_event_loop().time(),
                metadata={"command": cmd}
            )

            self.active_sessions[session_id] = session
            console.print(f"[green]Started session:[/green] {session_id} ({tool_name})")
            console.print(f"[dim]Use '/session send {session_id} <command>' to interact[/dim]")

            return session

        except Exception as e:
            console.print(f"[red]Failed to start {tool_name}:[/red] {e}")
            raise

    def send_to_session(self, session_id: str, command: str) -> str:
        """Send command to running tool session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        session = self.active_sessions[session_id]

        if session.process.poll() is not None:
            console.print(f"[yellow]Session {session_id} has ended[/yellow]")
            self.end_session(session_id)
            return "Session ended"

        try:
            session.process.stdin.write(command + "\n")
            session.process.stdin.flush()

            session.output_buffer.append(f"> {command}")
            console.print(f"[cyan]{session_id}:[/cyan] > {command}")

            return f"Sent to {session_id}"

        except Exception as e:
            console.print(f"[red]Error sending to session:[/red] {e}")
            raise

    def read_session_output(self, session_id: str, timeout: float = 1.0) -> str:
        """Read output from tool session."""
        if session_id not in self.active_sessions:
            return ""

        session = self.active_sessions[session_id]

        if session.process.poll() is not None:
            return ""

        try:
            import select
            if select.select([session.process.stdout], [], [], timeout)[0]:
                output = session.process.stdout.read(4096)
                session.output_buffer.append(output)
                return output
            return ""
        except Exception:
            return ""

    def end_session(self, session_id: str):
        """End a tool session."""
        if session_id not in self.active_sessions:
            return

        session = self.active_sessions[session_id]

        if session.process.poll() is None:
            session.process.terminate()
            try:
                session.process.wait(timeout=5)
            except:
                session.process.kill()

        del self.active_sessions[session_id]
        console.print(f"[yellow]Ended session:[/yellow] {session_id}")

    def run_workflow(self, workflow_name: str, target: str, variables: Dict[str, Any] = None) -> WorkflowState:
        """Execute predefined workflow with user confirmation for each step."""
        workflow = self._load_workflow(workflow_name)

        if not workflow:
            console.print(f"[red]Workflow '{workflow_name}' not found[/red]")
            raise ValueError(f"Workflow not found: {workflow_name}")

        state = WorkflowState(
            name=workflow_name,
            target=target,
            variables=variables or {}
        )

        self.active_workflows[workflow_name] = state

        console.print(f"\n[bold cyan]Starting workflow:[/bold cyan] {workflow_name}")
        console.print(f"[dim]Target:[/dim] {target}")

        for i, step in enumerate(workflow["steps"]):
            state.current_step = i
            console.print(f"\n[bold yellow]Step {i+1}/{len(workflow['steps'])}:[/bold yellow] {step.get('description', '')}")

            from rich.prompt import Confirm
            if not Confirm.ask("Continue to this step?"):
                console.print("[yellow]Workflow paused[/yellow]")
                return state

            result = self._execute_workflow_step(step, state)

            if result.get("success"):
                state.completed_steps.append(step.get("name", f"step_{i}"))
                if "output_var" in step:
                    state.variables[step["output_var"]] = result.get("output", "")
                console.print("[green]Step completed[/green]")
            else:
                console.print(f"[red]Step failed:[/red] {result.get('error', 'Unknown error')}")
                break

        console.print(f"\n[bold green]Workflow '{workflow_name}' finished[/bold green]")
        console.print(f"[dim]Completed steps:[/dim] {len(state.completed_steps)}/{len(workflow['steps'])}")

        return state

    def continue_workflow(self, workflow_name: str):
        """Continue paused workflow from current step."""
        if workflow_name not in self.active_workflows:
            console.print(f"[red]No active workflow: {workflow_name}[/red]")
            return

        state = self.active_workflows[workflow_name]
        workflow = self._load_workflow(workflow_name)

        if state.current_step >= len(workflow["steps"]):
            console.print("[green]Workflow already complete[/green]")
            return

        step = workflow["steps"][state.current_step]

        result = self._execute_workflow_step(step, state)

        if result.get("success"):
            state.completed_steps.append(step.get("name", f"step_{state.current_step}"))
            if "output_var" in step:
                state.variables[step["output_var"]] = result.get("output", "")
            state.current_step += 1
            console.print("[green]Step completed[/green]")

        if state.current_step >= len(workflow["steps"]):
            console.print(f"\n[bold green]Workflow '{workflow_name}' finished[/bold green]")
            del self.active_workflows[workflow_name]

    def list_sessions(self) -> List[ToolSession]:
        """List all active sessions."""
        return list(self.active_sessions.values())

    def list_workflows(self) -> List[str]:
        """List available workflow templates."""
        workflows_file = self.workflows_dir / "default_workflows.yaml"

        if not workflows_file.exists():
            return []

        import yaml
        with open(workflows_file) as f:
            workflows = yaml.safe_load(f)
            return list(workflows.get("workflows", {}).keys())

    def _load_workflow(self, name: str) -> Optional[Dict]:
        """Load workflow template from YAML."""
        workflows_file = self.workflows_dir / "default_workflows.yaml"

        if not workflows_file.exists():
            return None

        import yaml
        with open(workflows_file) as f:
            workflows = yaml.safe_load(f)
            return workflows.get("workflows", {}).get(name)

    def _execute_workflow_step(self, step: Dict, state: WorkflowState) -> Dict[str, Any]:
        """Execute single workflow step with safety checks."""
        tool = step.get("tool", "shell")
        command = step.get("command", "")

        # Format command with variables (safe formatting)
        try:
            command = command.format(
                target=shlex.quote(str(state.target)) if state.target else "",
                **{k: shlex.quote(str(v)) for k, v in state.variables.items()}
            )
        except Exception as e:
            return {"success": False, "error": f"Command formatting error: {e}"}

        console.print(f"[dim]Executing:[/dim] {command}")

        # Safety check before execution
        safety_check = self.safety_gate.check_command(command)
        if safety_check.decision.value == "block":
            return {
                "success": False,
                "error": f"Safety block: {safety_check.reason}",
                "output": f"Command blocked by safety gate: {safety_check.reason}"
            }

            # Use ToolRegistry for execution (unifies with PersistentShell)
            from assistant.tools.registry import get_global_registry
            registry = get_global_registry()
            
            tool_res = registry.run_tool(tool, command)
            
            return {
                "success": tool_res.get("success", False),
                "output": tool_res.get("stdout", ""),
                "error": tool_res.get("stderr") if not tool_res.get("success") else None
            }


        elif tool in ["nmap", "wifi"]:
            from assistant.tools.runner import ToolRunner
            runner = ToolRunner()

            tool_result = runner.run_tool(tool, command)
            return {
                "success": tool_result.get("success", False),
                "output": tool_result.get("stdout", ""),
                "error": tool_result.get("stderr") if not tool_result.get("success") else None
            }

        elif tool in ["nuclei", "subfinder"]:
            import shutil
            if not shutil.which(tool):
                console.print(f"[yellow]Tool '{tool}' not installed. Skipping step.[/yellow]")
                return {
                    "success": True,
                    "output": f"Skipped: {tool} not available",
                    "error": None
                }

            from assistant.tools.runner import ToolRunner
            runner = ToolRunner()

            tool_result = runner.run_tool(tool, command)
            return {
                "success": tool_result.get("success", False),
                "output": tool_result.get("stdout", ""),
                "error": tool_result.get("stderr") if not tool_result.get("success") else None
            }

        else:
            return {"success": False, "error": f"Unknown tool: {tool}"}

    def _get_tool_command(self, tool_name: str) -> str:
        """Get startup command for interactive tool."""
        tool_commands = {
            "wifite": "wifite --monitor",
            "msfconsole": "msfconsole",
            "metasploit": "msfconsole",
            "burpsuite": "burpsuite",
            "aircrack": "aircrack-ng",
        }

        return tool_commands.get(tool_name.lower(), tool_name)
