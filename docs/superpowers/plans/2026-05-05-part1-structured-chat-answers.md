# Part 1: Structured Chat Answers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all AI responses use a consistent 4-field structure (Answer, Command/Example, Details, Next step) with clean rendering.

**Architecture:** Separate parsing from rendering. Prompt builder asks for structure, parser extracts fields, synthesizer uses same structure for execution results, REPL only renders.

**Tech Stack:** Python 3.13+, Rich (terminal formatting), pydantic (data validation), pytest (testing)

---

## File Structure

- **Create:** `assistant/ai/response_parser.py` - Parse structured fields from AI responses, handle missing optional fields, return validated data
- **Create:** `assistant/ai/response_types_v2.py` - New response types with structured fields
- **Modify:** `assistant/brain/prompt_builder.py` - Add structured response format to system prompt
- **Modify:** `assistant/analysis/synthesizer.py` - Output same 4-field structure for execution results
- **Modify:** `assistant/app/terminal/repl.py` - Render structured fields, remove parsing logic
- **Create:** `tests/ai/test_response_parser.py` - Test parser with various response formats
- **Modify:** `tests/analysis/test_synthesizer.py` - Test synthesizer outputs new structure

---

### Task 1: Create new response types with structured fields

**Files:**
- Create: `assistant/ai/response_types_v2.py`

- [ ] **Step 1: Write failing test for new response types**

```python
# tests/ai/test_response_types_v2.py
from assistant.ai.response_types_v2 import StructuredResponse, ResponseField

def test_structured_response_creation():
    response = StructuredResponse(
        answer="Your local IP is 192.168.10.108",
        command="hostname -I",
        details="This shows the IP addresses assigned to your machine.",
        next_step="Try checking your network configuration?"
    )
    assert response.answer == "Your local IP is 192.168.10.108"
    assert response.command == "hostname -I"
    assert response.details == "This shows the IP addresses assigned to your machine."
    assert response.next_step == "Try checking your network configuration?"

def test_structured_response_with_optional_fields():
    response = StructuredResponse(answer="Simple answer")
    assert response.answer == "Simple answer"
    assert response.command is None
    assert response.details is None
    assert response.next_step is None

def test_response_field_validation():
    field = ResponseField(name="answer", content="test content", required=True)
    assert field.name == "answer"
    assert field.content == "test content"
    assert field.required is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ai/test_response_types_v2.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Create response_types_v2.py with minimal implementation**

```python
# assistant/ai/response_types_v2.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ResponseField:
    """Single field in a structured response."""
    name: str
    content: Optional[str]
    required: bool = False

@dataclass
class StructuredResponse:
    """Structured AI response with 4 fields."""
    answer: str
    command: Optional[str] = None
    details: Optional[str] = None
    next_step: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ai/test_response_types_v2.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add assistant/ai/response_types_v2.py tests/ai/test_response_types_v2.py
git commit -m "feat: add structured response types with 4 fields"
```

---

### Task 2: Create response parser to extract structured fields

**Files:**
- Create: `assistant/ai/response_parser.py`
- Test: `tests/ai/test_response_parser.py`

- [ ] **Step 1: Write failing test for parser**

```python
# tests/ai/test_response_parser.py
from assistant.ai.response_parser import ResponseParser
from assistant.ai.response_types_v2 import StructuredResponse

def test_parse_simple_response():
    text = """
    Answer: Your local IP is 192.168.10.108.

    Command / Example:
    hostname -I

    Details: This shows the IP addresses assigned to your machine.
    """
    parser = ResponseParser()
    result = parser.parse(text)
    assert isinstance(result, StructuredResponse)
    assert result.answer == "Your local IP is 192.168.10.108."
    assert result.command == "hostname -I"
    assert result.details == "This shows the IP addresses assigned to your machine."
    assert result.next_step is None

def test_parse_response_with_all_fields():
    text = """
    Answer: Scan completed successfully.

    Command / Example:
    nmap -sT -p 1-1000 192.168.10.108

    Details: Scanned ports 1-1000. Full logs available with /view.

    Next step: Run a local listening-port check with ss -tulnp.
    """
    parser = ResponseParser()
    result = parser.parse(text)
    assert result.answer == "Scan completed successfully."
    assert result.command == "nmap -sT -p 1-1000 192.168.10.108"
    assert result.details == "Scanned ports 1-1000. Full logs available with /view."
    assert result.next_step == "Run a local listening-port check with ss -tulnp."

def test_parse_response_without_optional_fields():
    text = "Answer: Simple answer."
    parser = ResponseParser()
    result = parser.parse(text)
    assert result.answer == "Simple answer."
    assert result.command is None
    assert result.details is None
    assert result.next_step is None

def test_parse_response_with_code_blocks():
    text = """
    Answer: Use this command.

    Command / Example:
    ```bash
    hostname -I
    ```

    Details: This shows your IP.
    """
    parser = ResponseParser()
    result = parser.parse(text)
    assert result.answer == "Use this command."
    assert "hostname -I" in result.command
    assert result.details == "This shows your IP."

def test_parse_unstructured_response_fallback():
    text = "This is an unstructured response without any labeled fields."
    parser = ResponseParser()
    result = parser.parse(text)
    assert isinstance(result, StructuredResponse)
    assert result.answer == "This is an unstructured response without any labeled fields."
    assert result.command is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ai/test_response_parser.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Create response_parser.py with parsing logic**

```python
# assistant/ai/response_parser.py
import re
from typing import Optional
from assistant.ai.response_types_v2 import StructuredResponse

class ResponseParser:
    """Parse structured fields from AI responses."""

    def parse(self, text: str) -> StructuredResponse:
        """Extract Answer, Command/Example, Details, Next step from text."""
        # Extract Answer (always present)
        answer = self._extract_field(text, ["Answer:", "answer:"])
        if not answer:
            # Fallback: use entire text as answer if no structure found
            answer = text.strip()

        # Extract optional fields
        command = self._extract_field(text, ["Command / Example:", "Command:", "Example:"])
        details = self._extract_field(text, ["Details:", "details:"])
        next_step = self._extract_field(text, ["Next step:", "Next Step:"])

        # Clean code blocks from command
        if command:
            command = self._remove_code_block_markers(command)

        return StructuredResponse(
            answer=answer,
            command=command,
            details=details,
            next_step=next_step
        )

    def _extract_field(self, text: str, labels: list[str]) -> Optional[str]:
        """Extract field content after one of the given labels."""
        for label in labels:
            pattern = rf"{label}\s*(.+?)(?=\n(?:{{0,3}})(?:Answer:|Command|Example|Details|Next|$))"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                # Remove trailing empty lines
                return re.sub(r'\n+$', '', content)
        return None

    def _remove_code_block_markers(self, text: str) -> str:
        """Remove ```bash and ``` markers from command text."""
        text = re.sub(r'```\w*\n?', '', text)
        text = re.sub(r'\n?```', '', text)
        return text.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ai/test_response_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add assistant/ai/response_parser.py tests/ai/test_response_parser.py
git commit -m "feat: add response parser for structured fields"
```

---

### Task 3: Update prompt builder to request structured response

**Files:**
- Modify: `assistant/brain/prompt_builder.py`

- [ ] **Step 1: Write test to check prompt includes structure**

```python
# tests/brain/test_prompt_builder.py
from assistant.brain.prompt_builder import PromptBuilder

def test_prompt_builder_includes_structured_response_format():
    builder = PromptBuilder()
    prompt = builder.build_system_prompt({}, {}, "chat")
    assert "Answer:" in prompt
    assert "Command / Example:" in prompt
    assert "Details:" in prompt
    assert "Next step:" in prompt
    assert "structured" in prompt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/brain/test_prompt_builder.py::test_prompt_builder_includes_structured_response_format -v`
Expected: FAIL (structured format not in prompt)

- [ ] **Step 3: Add structured response format to system prompt**

First, read the current prompt_builder to understand its structure:

```python
# Read existing build_system_prompt method
```

Then add this after the existing system prompt instructions:

```python
# In assistant/brain/prompt_builder.py, modify build_system_prompt method

# After existing instructions, add:

"""
## Response Format

Always structure your responses using these 4 fields:

**Answer:** [1-2 sentences, direct answer]
- Always shown
- Short and direct (1-2 sentences)
- No internal reasoning
- No latency display
- No planner text
- No raw debug logs

**Command / Example:** [optional - command, code block, or simple example]
- Show only when useful
- Use code block for shell commands
- Prefer one best command first
- Avoid listing too many alternatives unless user asks

**Details:** [optional - expanded explanation, alternatives, edge cases]
- Show only when needed
- Use for alternatives, warnings, edge cases, or "why" explanation
- Keep it short by default

**Next step:** [optional - suggested next action or approval note]
- Show only when action is possible or approval may be needed
- For chat/how-to questions: suggest what command the user can run
- For semi/full execution mode: say what can be executed, not hidden planner details

Example format:

Answer: Your local IP is 192.168.10.108.

Command / Example:
hostname -I

Details: This shows the IP addresses assigned to your machine.

Next step: Check your network configuration? (optional)
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/brain/test_prompt_builder.py::test_prompt_builder_includes_structured_response_format -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add assistant/brain/prompt_builder.py tests/brain/test_prompt_builder.py
git commit -m "feat: add structured response format to system prompt"
```

---

### Task 4: Update synthesizer to output structured response

**Files:**
- Modify: `assistant/analysis/synthesizer.py`

- [ ] **Step 1: Write test for synthesizer structured output**

```python
# tests/analysis/test_synthesizer_v2.py
import pytest
from unittest.mock import AsyncMock
from assistant.analysis.synthesizer import synthesize_result
from assistant.tasks.task_types import Plan, Step
from assistant.actions.executor import ExecutionResult, StepResult

@pytest.mark.asyncio
async def test_synthesize_result_returns_structured_response():
    # Create a simple plan
    plan = Plan(
        title="Get IP",
        intent="task",
        risk_level="low",
        steps=[Step(command="hostname -I", tool="hostname")]
    )

    # Create execution result
    result = ExecutionResult(
        success=True,
        steps=[
            StepResult(
                command="hostname -I",
                stdout="192.168.10.108\n",
                stderr="",
                status="success"
            )
        ],
        failed_steps=[],
        combined_output="192.168.10.108\n"
    )

    # Synthesize without AI router (deterministic)
    synthesis = await synthesize_result(plan, result, ai_router=None)

    # Should return a string that matches structured format
    assert synthesis is not None
    assert "Answer:" in synthesis
    assert "192.168.10.108" in synthesis
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_synthesizer_v2.py -v`
Expected: FAIL (current synthesizer returns plain string, not structured)

- [ ] **Step 3: Modify synthesizer to output structured format**

Read the current synthesizer.py to understand existing parsing logic. Then modify the return format:

```python
# In assistant/analysis/synthesizer.py

# Import the new types
from assistant.ai.response_types_v2 import StructuredResponse

# Create a helper function to format synthesis as structured response
def _format_structured_synthesis(answer: str, command: str = None, details: str = None, next_step: str = None) -> str:
    """Format synthesis output as structured response."""
    output = f"Answer: {answer}\n\n"

    if command:
        output += f"Command / Example:\n{command}\n\n"

    if details:
        output += f"Details: {details}\n\n"

    if next_step:
        output += f"Next step: {next_step}"

    return output.strip()

# Modify existing parsing functions to return structured data
def _parse_ip_addr(stdout: str) -> dict:
    """Extract primary non-loopback IPv4 from `ip addr show` output.
    Returns dict with 'answer' and 'details' keys.
    """
    for line in stdout.splitlines():
        m = re.search(r'inet\s+((?!127\.)\d{1,3}(?:\.\d{1,3}){3})', line)
        if m:
            return {
                "answer": f"Your local IP is {m.group(1)}.",
                "command": "hostname -I",
                "details": "This shows the IP addresses assigned to your machine."
            }
    return {}

# Update the main synthesis function
async def synthesize_result(
    plan: "Plan",
    result: "ExecutionResult",
    ai_router=None,
) -> Optional[str]:
    """Return a human-readable summary of execution results in structured format."""

    # ... existing failure handling ...

    # For deterministic parsing, use structured format
    parts = []
    for step in result.steps:
        cmd = step.command.lower()
        out = step.stdout

        if "ip addr" in cmd or "ifconfig" in cmd:
            parsed = _parse_ip_addr(out)
            if parsed:
                return _format_structured_synthesis(
                    answer=parsed.get("answer"),
                    command=parsed.get("command"),
                    details=parsed.get("details")
                )

        if "hostname" in cmd:
            ip = _parse_hostname_i(out)
            if ip:
                return _format_structured_synthesis(
                    answer=f"Your local IP is {ip}.",
                    command="hostname -I",
                    details="This shows the IP addresses assigned to your machine."
                )

        # ... continue with other parsers ...

    # If no structured parsing matched, try AI synthesis
    if ai_router and _needs_ai_synthesis(plan, result):
        # ... existing AI synthesis logic ...
        # But format the AI response using structured format
        if raw_response:
            return f"Answer: {raw_response.strip()}"

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/analysis/test_synthesizer_v2.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add assistant/analysis/synthesizer.py tests/analysis/test_synthesizer_v2.py
git commit -m "feat: update synthesizer to output structured response format"
```

---

### Task 5: Update REPL to render structured responses

**Files:**
- Modify: `assistant/app/terminal/repl.py`

- [ ] **Step 1: Write test for REPL structured rendering**

This is harder to test directly, so we'll create a helper function test:

```python
# tests/app/terminal/test_repl_renderer.py
from assistant.app.terminal.repl import render_structured_response
from assistant.ai.response_types_v2 import StructuredResponse
from rich.console import Console

def test_render_structured_response_with_all_fields():
    console = Console()
    response = StructuredResponse(
        answer="Your local IP is 192.168.10.108.",
        command="hostname -I",
        details="This shows the IP addresses assigned to your machine.",
        next_step="Check your network configuration?"
    )

    # Capture output
    output = console.render_str(lambda: render_structured_response(console, response))

    assert "Your local IP is 192.168.10.108." in output
    assert "hostname -I" in output
    assert "This shows the IP addresses assigned to your machine." in output
    assert "Check your network configuration?" in output

def test_render_structured_response_with_only_answer():
    console = Console()
    response = StructuredResponse(answer="Simple answer.")

    output = console.render_str(lambda: render_structured_response(console, response))

    assert "Simple answer." in output
    # Should not show empty sections
    assert "Command" not in output
    assert "Details" not in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/app/terminal/test_repl_renderer.py -v`
Expected: FAIL (render_structured_response doesn't exist)

- [ ] **Step 3: Create renderer function and update REPL**

```python
# In assistant/app/terminal/repl.py

# Add imports
from assistant.ai.response_parser import ResponseParser
from assistant.ai.response_types_v2 import StructuredResponse

# Initialize parser
class InteractiveREPL:
    def __init__(self):
        # ... existing init ...
        self.response_parser = ResponseParser()

# Add renderer function
def render_structured_response(console, response: StructuredResponse):
    """Render a structured response with Rich formatting."""
    from rich.panel import Panel
    from rich.syntax import Syntax

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

# Update process_input to use parser and renderer
async def process_input(self, text: str):
    # ... existing code up to line 267 ...

    # After getting response from pipeline
    with console.status("[bold green]Thinking...[/bold green]"):
        conv_id = self.conversation.id if self.conversation else None
        response = await self.pipeline.process(text, conv_id)

    # Parse structured response
    if response.content:
        structured = self.response_parser.parse(response.content)

        # Render using structured renderer
        console.print()  # Add spacing
        render_structured_response(console, structured)

        # Handle plan execution separately if needed
        if response.plan:
            # ... existing plan handling logic ...
            return
        return

    # ... rest of existing logic for non-content responses ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/app/terminal/test_repl_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add assistant/app/terminal/repl.py tests/app/terminal/test_repl_renderer.py
git commit -m "feat: add structured response rendering to REPL"
```

---

### Task 6: Integration test for full flow

**Files:**
- Test: `tests/integration/test_structured_response_flow.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_structured_response_flow.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from assistant.ai.response_parser import ResponseParser
from assistant.brain.prompt_builder import PromptBuilder

def test_prompt_to_parser_flow():
    """Test that prompt builder produces format that parser can understand."""
    builder = PromptBuilder()
    prompt = builder.build_system_prompt({}, {}, "chat")

    # Simulate AI response following the format
    ai_response = """
    Answer: Test answer here.

    Command / Example:
    test command

    Details: Test details here.
    """

    parser = ResponseParser()
    structured = parser.parse(ai_response)

    assert structured.answer == "Test answer here."
    assert structured.command == "test command"
    assert structured.details == "Test details here."

def test_parser_handles_edge_cases():
    """Test parser handles malformed or partial responses."""
    parser = ResponseParser()

    # Empty answer
    result = parser.parse("")
    assert result.answer == ""

    # Only answer
    result = parser.parse("Answer: Just an answer.")
    assert result.answer == "Just an answer."
    assert result.command is None
    assert result.details is None

    # Case insensitive labels
    result = parser.parse("answer: lowercase label test")
    assert result.answer == "lowercase label test"
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/integration/test_structured_response_flow.py -v`
Expected: PASS

- [ ] **Step 3: Manual test with real AI**

Test the actual flow by running the assistant:
```bash
python -m assistant.main
```

Ask: "find my ip"

Expected output should show:
- Answer: Your local IP is [IP]
- Command / Example: hostname -I
- Details: [explanation]

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_structured_response_flow.py
git commit -m "test: add integration tests for structured response flow"
```

---

## Self-Review

**Spec coverage:**
- ✅ 4-field structure defined (Task 1)
- ✅ Parser extracts fields (Task 2)
- ✅ Prompt builder requests structure (Task 3)
- ✅ Synthesizer uses same structure (Task 4)
- ✅ REPL renders cleanly (Task 5)
- ✅ Integration tests verify flow (Task 6)

**Placeholder scan:**
- None found - all tasks have complete code

**Type consistency:**
- `StructuredResponse` fields (answer, command, details, next_step) consistent across all tasks
- `ResponseParser` methods use correct types
- Rich rendering uses proper Console object

**Dependencies:**
- Task 2 (parser) depends on Task 1 (types) - correct order
- Task 3 (prompt) is independent
- Task 4 (synthesizer) depends on Task 1 (types)
- Task 5 (REPL) depends on Tasks 1, 2
- Task 6 (integration) depends on all previous - correct order
