import subprocess
from typing import Dict, Any
from rich.console import Console
from assistant.tools.nmap_tool import NmapTool


console = Console()

TOOL_WHITELIST = [
    "nmap", "git", "python3", "curl", "wget", "dig", "whois", 
    "grep", "sed", "awk", "ls", "cat", "ip", "ping", "whoami", "tail", "head"
]


class ToolRunner:
    def __init__(self):
        self.registry = {
            "nmap": NmapTool()
        }

    def is_safe_command(self, command: str) -> bool:
        """Check for unsafe characters that could lead to command injection."""
        unsafe_chars = [";", "&&", "||", ">", "<", "`", "$(", "${"]
        # Allow simple pipes if both sides are whitelisted? 
        # For Phase 4, we'll be strict: no pipes or redirects unless we explicitly allow them.
        for char in unsafe_chars:
            if char in command:
                return False
        
        # Check if the primary tool is whitelisted
        parts = command.split()
        if not parts:
            return False
            
        tool = parts[0]
        # Handle cases like '/usr/bin/nmap' or './script.py' (not allowed for now)
        if "/" in tool or tool.startswith("."):
            return False
            
        return tool in TOOL_WHITELIST

    def run_shell(self, command: str, cwd: str = None) -> Dict[str, Any]:
        """Execute a shell command with strict whitelist and timeout."""
        try:
            if not self.is_safe_command(command):
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Error: Command '{command}' failed safety check (blocked tool or unsafe characters).",
                    "returncode": -1
                }

            console.print(f"[dim]Executing: {command} (in {cwd or '.'})[/dim]")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=60 # Default 1 minute timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Error: Command timed out after 60 seconds.",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def run_tool(self, tool_name: str, args: str, cwd: str = None) -> Dict[str, Any]:
        """Run a tool by name, either from registry or as shell."""
        if tool_name not in TOOL_WHITELIST:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Error: Tool '{tool_name}' is not whitelisted.",
                "returncode": -1
            }

        tool = self.registry.get(tool_name)
        if tool:
            # For registered tools, args is the command part after tool name
            # We need to strip the tool name from args if it's already there
            # e.g. "nmap -F 127.0.0.1" -> "-F 127.0.0.1"
            clean_args = args.replace(f"{tool_name} ", "", 1) if args.startswith(tool_name) else args
            return tool.execute(clean_args, cwd=cwd)
        
        # Default to shell execution
        return self.run_shell(args, cwd=cwd)


