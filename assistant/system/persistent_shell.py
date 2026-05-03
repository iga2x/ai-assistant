import os
import subprocess
import shlex
from typing import Dict, Any, Optional, List


class PersistentShell:
    """
    A subprocess-based shell executor for clean, isolated command execution.

    Unlike PTY-based approaches, this uses subprocess with pipes to ensure:
    - No prompt artifacts in output
    - Correct exit code capture
    - Complete output isolation per command
    - No stale buffer mixing between executions

    Each command runs in a fresh shell process with clean I/O boundaries.
    """

    def __init__(self, shell: str = "/bin/bash"):
        """
        Initialize the shell executor.

        Args:
            shell: Path to shell executable (default: /bin/bash)
        """
        self.shell = shell

    def _execute_command(self, command: str, timeout: int, cwd: Optional[str] = None,
                         env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute a single command in a subprocess with clean I/O isolation.

        Args:
            command: Command string to execute
            timeout: Maximum execution time in seconds
            cwd: Working directory (default: None = current directory)
            env: Environment variables (default: None = inherit from parent)

        Returns:
            Dict with 'success', 'stdout', 'stderr', 'returncode'
        """
        try:
            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            # Start subprocess with clean pipe boundaries
            process = subprocess.Popen(
                [self.shell, '-c', command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                cwd=cwd,
                env=process_env,
                text=False  # Use bytes for consistent encoding
            )

            # Wait with timeout
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout_bytes, stderr_bytes = process.communicate()
                return {
                    "success": False,
                    "stdout": stdout_bytes.decode('utf-8', errors='replace'),
                    "stderr": f"Command timed out after {timeout}s",
                    "returncode": -1
                }

            # Decode output
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')

            # Clean up: remove trailing newlines but preserve internal structure
            stdout = self._clean_output(stdout)
            stderr = self._clean_output(stderr)

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode
            }

        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command execution failed: {str(e)}",
                "returncode": -1
            }

    def _clean_output(self, output: str) -> str:
        """
        Clean command output by removing trailing whitespace and normalizing line endings.

        Args:
            output: Raw output string

        Returns:
            Cleaned output string
        """
        # Normalize line endings
        output = output.replace('\r\n', '\n').replace('\r', '\n')

        # Remove trailing newlines/whitespace
        output = output.rstrip()

        return output

    def execute(self, command: str, timeout: int = 60, cwd: Optional[str] = None,
                env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute a command with clean, isolated output.

        This is the main interface - executes a command in a subprocess
        and returns its output with proper exit code.

        Args:
            command: Command string to execute
            timeout: Maximum execution time in seconds (default: 60)
            cwd: Working directory (default: None = current directory)
            env: Environment variables (default: None = inherit from parent)

        Returns:
            Dict with keys:
            - success: bool (True if exit code == 0)
            - stdout: str (command's standard output, cleaned)
            - stderr: str (command's standard error, cleaned)
            - returncode: int (process exit code, -1 on error)
        """
        return self._execute_command(command, timeout, cwd, env)

    def close(self):
        """
        Close the shell executor.

        No-op for subprocess-based implementation since each command
        runs in a fresh process.
        """
        pass
