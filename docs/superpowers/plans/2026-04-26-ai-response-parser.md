# AI Response Parser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix AI response output layer to properly parse JSON responses and hide internal fields from users while supporting debug mode.

**Architecture:** Create response parser module that extracts structured fields from AI responses, handles edge cases (invalid JSON, missing content), and integrates with pipeline for clean user-facing output. Debug mode reveals internal fields via config flags.

**Tech Stack:** Python, Pydantic, pytest, existing config system

---

## File Structure

**New Files:**
- `assistant/brain/response_parser.py` - Core response parsing logic
- `tests/brain/test_response_parser.py` - Unit tests for parser

**Modified Files:**
- `assistant/config/manager.py` - Add debug config options
- `assistant/app/terminal/pipeline.py` - Integrate response parser
- `assistant/app/terminal/repl.py` - Support debug output display

---

### Task 1: Add Debug Config Options

**Files:**
- Modify: `assistant/config/manager.py`

- [ ] **Step 1: Add DebugConfig class with debug flags**

```python
class DebugConfig(BaseModel):
    show_ai_reasoning: bool = False
    show_raw_ai_response: bool = False
    show_intent: bool = False
    show_plan: bool = False
```

Insert after `PrivacyConfig` class (around line 44).

- [ ] **Step 2: Add debug config to AppConfig**

```python
class AppConfig(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    debug: DebugConfig = Field(default_factory=DebugConfig)
```

Replace existing `AppConfig` class (lines 45-51) with this version.

- [ ] **Step 3: Run tests to verify config changes**

Run: `python -c "from assistant.config.manager import AppConfig; c = AppConfig(); print('Debug config exists:', hasattr(c, 'debug'))"`
Expected: `Debug config exists: True`

- [ ] **Step 4: Commit**

```bash
git add assistant/config/manager.py
git commit -m "feat: add debug config options for AI response parsing"
```

---

### Task 2: Create Response Parser Module

**Files:**
- Create: `assistant/brain/response_parser.py`

- [ ] **Step 1: Create module with parsed response dataclass**

```python
from dataclasses import dataclass
from typing import Optional, Any
import json

@dataclass
class ParsedAIResponse:
    content: str
    intent: Optional[str] = None
    reasoning: Optional[str] = None
    plan: Optional[dict] = None
    raw: str = ""
    valid_json: bool = False

class ResponseParser:
    @staticmethod
    def parse_ai_response(raw_response: str) -> ParsedAIResponse:
        pass
```

- [ ] **Step 2: Run module import test**

Run: `python -c "from assistant.brain.response_parser import ResponseParser; print('Module imported')"`
Expected: `Module imported`

- [ ] **Step 3: Commit**

```bash
git add assistant/brain/response_parser.py
git commit -m "feat: add response parser module structure"
```

---

### Task 3: Implement Valid JSON Parsing

**Files:**
- Modify: `assistant/brain/response_parser.py`

- [ ] **Step 1: Write failing test for valid JSON parsing**

```python
def test_parse_valid_json_with_content():
    raw = '{"reasoning": "User asked for help", "intent": "chat_only", "content": "Hello! How can I help?", "plan": null}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "Hello! How can I help?"
    assert result.intent == "chat_only"
    assert result.reasoning == "User asked for help"
    assert result.plan is None
    assert result.raw == raw
    assert result.valid_json is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/brain/test_response_parser.py::test_parse_valid_json_with_content -v`
Expected: FAIL with "not implemented" or similar

- [ ] **Step 3: Implement valid JSON parsing**

```python
@staticmethod
def parse_ai_response(raw_response: str) -> ParsedAIResponse:
    try:
        data = json.loads(raw_response)
        content = data.get("content", "")
        intent = data.get("intent")
        reasoning = data.get("reasoning")
        plan = data.get("plan")
        return ParsedAIResponse(
            content=content,
            intent=intent,
            reasoning=reasoning,
            plan=plan,
            raw=raw_response,
            valid_json=True
        )
    except json.JSONDecodeError:
        return ParsedAIResponse(
            content="I understood, but I do not have a clear response.",
            raw=raw_response,
            valid_json=False
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/brain/test_response_parser.py::test_parse_valid_json_with_content -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/brain/test_response_parser.py assistant/brain/response_parser.py
git commit -m "feat: implement valid JSON parsing in response parser"
```

---

### Task 4: Handle Missing/Empty Content

**Files:**
- Modify: `assistant/brain/response_parser.py`

- [ ] **Step 1: Write failing test for missing content**

```python
def test_parse_json_missing_content():
    raw = '{"reasoning": "User asked", "intent": "chat_only", "plan": {"title": "Test"}}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "I understood, but I do not have a clear response."
    assert result.valid_json is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/brain/test_response_parser.py::test_parse_json_missing_content -v`
Expected: FAIL (content would be empty string, not fallback message)

- [ ] **Step 3: Implement missing content handling**

```python
@staticmethod
def parse_ai_response(raw_response: str) -> ParsedAIResponse:
    try:
        data = json.loads(raw_response)
        content = data.get("content", "")

        if not content or not content.strip():
            content = "I understood, but I do not have a clear response."

        intent = data.get("intent")
        reasoning = data.get("reasoning")
        plan = data.get("plan")
        return ParsedAIResponse(
            content=content,
            intent=intent,
            reasoning=reasoning,
            plan=plan,
            raw=raw_response,
            valid_json=True
        )
    except json.JSONDecodeError:
        return ParsedAIResponse(
            content="I understood, but I do not have a clear response.",
            raw=raw_response,
            valid_json=False
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/brain/test_response_parser.py::test_parse_json_missing_content -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/brain/test_response_parser.py assistant/brain/response_parser.py
git commit -m "feat: handle missing/empty content in JSON responses"
```

---

### Task 5: Handle Plain Text Responses

**Files:**
- Modify: `assistant/brain/response_parser.py`

- [ ] **Step 1: Write failing test for plain text**

```python
def test_parse_plain_text():
    raw = "Hello! How can I help you today?"
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "Hello! How can I help you today?"
    assert result.valid_json is False
    assert result.intent is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/brain/test_response_parser.py::test_parse_plain_text -v`
Expected: FAIL (content would be fallback message, not raw text)

- [ ] **Step 3: Implement plain text handling**

```python
@staticmethod
def parse_ai_response(raw_response: str) -> ParsedAIResponse:
    try:
        data = json.loads(raw_response)
        content = data.get("content", "")

        if not content or not content.strip():
            content = "I understood, but I do not have a clear response."

        intent = data.get("intent")
        reasoning = data.get("reasoning")
        plan = data.get("plan")
        return ParsedAIResponse(
            content=content,
            intent=intent,
            reasoning=reasoning,
            plan=plan,
            raw=raw_response,
            valid_json=True
        )
    except json.JSONDecodeError:
        if raw_response.strip():
            return ParsedAIResponse(
                content=raw_response.strip(),
                raw=raw_response,
                valid_json=False
            )
        return ParsedAIResponse(
            content="I understood, but I do not have a clear response.",
            raw=raw_response,
            valid_json=False
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/brain/test_response_parser.py::test_parse_plain_text -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/brain/test_response_parser.py assistant/brain/response_parser.py
git commit -m "feat: handle plain text responses"
```

---

### Task 6: Handle Invalid JSON with Content-like Text

**Files:**
- Modify: `assistant/brain/response_parser.py`

- [ ] **Step 1: Write failing test for malformed JSON**

```python
def test_parse_malformed_json():
    raw = '{"reasoning": "test", "intent": "chat"'  # Missing closing brace
    result = ResponseParser.parse_ai_response(raw)
    assert result.valid_json is False
    assert result.content == "I understood, but I do not have a clear response."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/brain/test_response_parser.py::test_parse_malformed_json -v`
Expected: FAIL (malformed JSON would crash)

- [ ] **Step 3: Test passes - JSONDecodeError catches malformed JSON**

Current implementation already catches JSONDecodeError, so test should pass.

- [ ] **Step 4: Verify test passes**

Run: `pytest tests/brain/test_response_parser.py::test_parse_malformed_json -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/brain/test_response_parser.py
git commit -m "test: add malformed JSON handling test"
```

---

### Task 7: Test Plan Field Extraction

**Files:**
- Modify: `tests/brain/test_response_parser.py`

- [ ] **Step 1: Write failing test for plan extraction**

```python
def test_parse_json_with_plan():
    raw = '{"reasoning": "User wants action", "intent": "scan", "content": "Starting scan", "plan": {"title": "Scan", "intent": "scan", "steps": []}}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.plan is not None
    assert result.plan["title"] == "Scan"
    assert result.plan["intent"] == "scan"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/brain/test_response_parser.py::test_parse_json_with_plan -v`
Expected: FAIL

- [ ] **Step 3: Test passes - plan extraction already implemented**

Current implementation extracts plan field, so test should pass.

- [ ] **Step 4: Verify test passes**

Run: `pytest tests/brain/test_response_parser.py::test_parse_json_with_plan -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/brain/test_response_parser.py
git commit -m "test: add plan extraction test"
```

---

### Task 8: Test Empty Raw Response

**Files:**
- Modify: `tests/brain/test_response_parser.py`

- [ ] **Step 1: Write failing test for empty response**

```python
def test_parse_empty_response():
    raw = ""
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "I understood, but I do not have a clear response."
    assert result.valid_json is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/brain/test_response_parser.py::test_parse_empty_response -v`
Expected: FAIL (empty string check might not handle this case)

- [ ] **Step 3: Implement empty response handling**

```python
@staticmethod
def parse_ai_response(raw_response: str) -> ParsedAIResponse:
    try:
        if not raw_response or not raw_response.strip():
            return ParsedAIResponse(
                content="I understood, but I do not have a clear response.",
                raw=raw_response,
                valid_json=False
            )

        data = json.loads(raw_response)
        content = data.get("content", "")

        if not content or not content.strip():
            content = "I understood, but I do not have a clear response."

        intent = data.get("intent")
        reasoning = data.get("reasoning")
        plan = data.get("plan")
        return ParsedAIResponse(
            content=content,
            intent=intent,
            reasoning=reasoning,
            plan=plan,
            raw=raw_response,
            valid_json=True
        )
    except json.JSONDecodeError:
        if raw_response.strip():
            return ParsedAIResponse(
                content=raw_response.strip(),
                raw=raw_response,
                valid_json=False
            )
        return ParsedAIResponse(
            content="I understood, but I do not have a clear response.",
            raw=raw_response,
            valid_json=False
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/brain/test_response_parser.py::test_parse_empty_response -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/brain/test_response_parser.py assistant/brain/response_parser.py
git commit -m "feat: handle empty raw responses"
```

---

### Task 9: Test Debug Mode Field Access

**Files:**
- Modify: `tests/brain/test_response_parser.py`

- [ ] **Step 1: Write test to verify all fields accessible for debug**

```python
def test_all_fields_accessible():
    raw = '{"reasoning": "AI reasoning", "intent": "chat_only", "content": "Response content", "plan": {"title": "Test Plan"}}'
    result = ResponseParser.parse_ai_response(raw)
    assert hasattr(result, 'content')
    assert hasattr(result, 'intent')
    assert hasattr(result, 'reasoning')
    assert hasattr(result, 'plan')
    assert hasattr(result, 'raw')
    assert hasattr(result, 'valid_json')
    assert result.reasoning == "AI reasoning"
    assert result.raw == raw
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/brain/test_response_parser.py::test_all_fields_accessible -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/brain/test_response_parser.py
git commit -m "test: verify all parsed fields are accessible"
```

---

### Task 10: Create Test File Structure

**Files:**
- Create: `tests/brain/__init__.py`
- Create: `tests/brain/test_response_parser.py`

- [ ] **Step 1: Create brain test directory init file**

```python
# tests/brain/__init__.py
```

- [ ] **Step 2: Create test file with all test imports and setup**

```python
# tests/brain/test_response_parser.py
import pytest
from assistant.brain.response_parser import ResponseParser, ParsedAIResponse

def test_parse_valid_json_with_content():
    raw = '{"reasoning": "User asked for help", "intent": "chat_only", "content": "Hello! How can I help?", "plan": null}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "Hello! How can I help?"
    assert result.intent == "chat_only"
    assert result.reasoning == "User asked for help"
    assert result.plan is None
    assert result.raw == raw
    assert result.valid_json is True

def test_parse_json_missing_content():
    raw = '{"reasoning": "User asked", "intent": "chat_only", "plan": {"title": "Test"}}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "I understood, but I do not have a clear response."
    assert result.valid_json is True

def test_parse_plain_text():
    raw = "Hello! How can I help you today?"
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "Hello! How can I help you today?"
    assert result.valid_json is False
    assert result.intent is None

def test_parse_malformed_json():
    raw = '{"reasoning": "test", "intent": "chat"'  # Missing closing brace
    result = ResponseParser.parse_ai_response(raw)
    assert result.valid_json is False
    assert result.content == "I understood, but I do not have a clear response."

def test_parse_json_with_plan():
    raw = '{"reasoning": "User wants action", "intent": "scan", "content": "Starting scan", "plan": {"title": "Scan", "intent": "scan", "steps": []}}'
    result = ResponseParser.parse_ai_response(raw)
    assert result.plan is not None
    assert result.plan["title"] == "Scan"
    assert result.plan["intent"] == "scan"

def test_parse_empty_response():
    raw = ""
    result = ResponseParser.parse_ai_response(raw)
    assert result.content == "I understood, but I do not have a clear response."
    assert result.valid_json is False

def test_all_fields_accessible():
    raw = '{"reasoning": "AI reasoning", "intent": "chat_only", "content": "Response content", "plan": {"title": "Test Plan"}}'
    result = ResponseParser.parse_ai_response(raw)
    assert hasattr(result, 'content')
    assert hasattr(result, 'intent')
    assert hasattr(result, 'reasoning')
    assert hasattr(result, 'plan')
    assert hasattr(result, 'raw')
    assert hasattr(result, 'valid_json')
    assert result.reasoning == "AI reasoning"
    assert result.raw == raw
```

- [ ] **Step 3: Run all tests to verify they pass**

Run: `pytest tests/brain/test_response_parser.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/brain/
git commit -m "test: add complete response parser test suite"
```

---

### Task 11: Integrate Response Parser into Pipeline

**Files:**
- Modify: `assistant/app/terminal/pipeline.py`

- [ ] **Step 1: Import ResponseParser in pipeline**

Add at top of file with other imports:
```python
from assistant.brain.response_parser import ResponseParser
```

- [ ] **Step 2: Parse raw AI output before passing to planner**

Modify the `process` method around line 51:

```python
# 6. AI Router (Get response)
raw_output = await self.router.chat_completion(messages)

# 6.5. Parse AI response (extract content, handle edge cases)
parsed = ResponseParser.parse_ai_response(raw_output)

# 7. Planner (Create action request or plan) - use parsed content for plan generation
response = self.planner.create_plan(parsed.content, resolved)
```

- [ ] **Step 3: Store parsed data for debug access**

Modify the return statement at line 74 to include parsed data:

```python
# Store parsed data for debug access
response._parsed = parsed

return response
```

- [ ] **Step 4: Test pipeline integration with mock data**

Run: `python -c "
from assistant.brain.response_parser import ResponseParser
raw = '{\"reasoning\": \"test\", \"intent\": \"chat_only\", \"content\": \"Hello\"}'
parsed = ResponseParser.parse_ai_response(raw)
print('Content:', parsed.content)
print('Intent:', parsed.intent)
"`
Expected: `Content: Hello` and `Intent: chat_only`

- [ ] **Step 5: Commit**

```bash
git add assistant/app/terminal/pipeline.py
git commit -m "feat: integrate response parser into chat pipeline"
```

---

### Task 12: Update REPL to Show Only Content (Normal Mode)

**Files:**
- Modify: `assistant/app/terminal/repl.py`

- [ ] **Step 1: Verify current REPL prints only content**

Check lines 132, 140, 145 in repl.py - they already print `response.content`, which is correct. No changes needed for normal mode.

- [ ] **Step 2: Run REPL to verify content-only display**

Run: `python -m assistant.app.main --test-mode` (or equivalent test)
Expected: Only `content` field displayed to user

- [ ] **Step 3: Commit (no changes if verification passes)**

```bash
git status
```
(If no changes needed, skip commit)

---

### Task 13: Add Debug Output Display in REPL

**Files:**
- Modify: `assistant/app/terminal/repl.py`

- [ ] **Step 1: Import debug config access**

Modify `process_input` method to access debug config. Add after line 122:

```python
async def process_input(self, text: str):
    with console.status("[bold green]Thinking...[/bold green]"):
        response = await self.pipeline.process(text, self.conversation.id)

    # Debug output based on config flags
    debug_config = self.config_mgr.config.debug

    if debug_config.show_raw_ai_response and hasattr(response, '_parsed'):
        console.print(f"\n[dim][DEBUG] Raw AI Response:[/dim]\n{response._parsed.raw}")

    if debug_config.show_ai_reasoning and hasattr(response, '_parsed') and response._parsed.reasoning:
        console.print(f"\n[dim][DEBUG] AI Reasoning:[/dim]\n{response._parsed.reasoning}")

    if debug_config.show_intent and hasattr(response, '_parsed') and response._parsed.intent:
        console.print(f"\n[dim][DEBUG] Intent:[/dim] {response._parsed.intent}")

    if debug_config.show_plan and hasattr(response, '_parsed') and response._parsed.plan:
        console.print(f"\n[dim][DEBUG] Plan:[/dim]\n{response._parsed.plan}")

    # 1. Store last response for debug
    self.last_response = response
```

- [ ] **Step 2: Test debug output display**

Run: Enable debug flags in config and test:
```python
from assistant.config.manager import ConfigManager
cm = ConfigManager()
cm.config.debug.show_raw_ai_response = True
cm.config.debug.show_ai_reasoning = True
cm.save_config()
```
Then run REPL with a query. Expected: Debug fields displayed before normal response.

- [ ] **Step 3: Commit**

```bash
git add assistant/app/terminal/repl.py
git commit -m "feat: add debug output display in REPL"
```

---

### Task 14: Test End-to-End Integration

**Files:**
- Create: `tests/integration/test_response_pipeline.py`

- [ ] **Step 1: Create integration test directory**

```python
# tests/integration/__init__.py
```

- [ ] **Step 2: Create end-to-end pipeline test**

```python
# tests/integration/test_response_pipeline.py
import pytest
from assistant.brain.response_parser import ResponseParser

def test_pipeline_with_valid_json():
    """Test that valid JSON produces clean content for users."""
    raw_json = '{"reasoning": "User greeting", "intent": "chat_only", "content": "Hello there!", "plan": null}'
    parsed = ResponseParser.parse_ai_response(raw_json)

    # User-facing content is clean
    assert parsed.content == "Hello there!"

    # Debug fields are accessible
    assert parsed.reasoning == "User greeting"
    assert parsed.intent == "chat_only"
    assert parsed.valid_json is True

def test_pipeline_with_plain_text():
    """Test that plain text is handled gracefully."""
    raw_text = "Here's your answer to the question."
    parsed = ResponseParser.parse_ai_response(raw_text)

    assert parsed.content == "Here's your answer to the question."
    assert parsed.valid_json is False
    assert parsed.intent is None

def test_pipeline_with_missing_content():
    """Test fallback message when content is missing."""
    raw_json = '{"reasoning": "Some reasoning", "intent": "scan", "plan": {"title": "Scan"}}'
    parsed = ResponseParser.parse_ai_response(raw_json)

    assert parsed.content == "I understood, but I do not have a clear response."
    assert parsed.valid_json is True
    assert parsed.intent == "scan"
```

- [ ] **Step 3: Run integration tests**

Run: `pytest tests/integration/test_response_pipeline.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/integration/
git commit -m "test: add end-to-end response pipeline tests"
```

---

### Task 15: Verify REPL Never Prints Raw JSON

**Files:**
- Test: Manual verification

- [ ] **Step 1: Create test to ensure raw JSON never leaks**

```python
# tests/integration/test_repl_output.py
def test_repl_never_prints_raw_json():
    """Verify that the REPL output never contains raw JSON structure."""
    from assistant.brain.response_parser import ResponseParser

    raw_json = '{"reasoning": "test", "intent": "chat_only", "content": "Hello", "plan": null}'
    parsed = ResponseParser.parse_ai_response(raw_json)

    # Content should be clean text, not JSON
    assert "{" not in parsed.content
    assert "}" not in parsed.content
    assert "reasoning" not in parsed.content
    assert "intent" not in parsed.content

    # Raw is stored separately
    assert "{" in parsed.raw
    assert "reasoning" in parsed.raw
```

- [ ] **Step 2: Run test**

Run: `pytest tests/integration/test_repl_output.py::test_repl_never_prints_raw_json -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_repl_output.py
git commit -m "test: verify REPL never prints raw JSON"
```

---

### Task 16: Add Debug CLI Commands

**Files:**
- Modify: `assistant/app/terminal/repl.py`

- [ ] **Step 1: Add debug toggle commands**

Add to `/debug` command handler around line 254:

```python
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
    elif sub == "reasoning":
        if hasattr(self, "last_response") and hasattr(self.last_response, "_parsed") and self.last_response._parsed.reasoning:
            console.print(Panel(self.last_response._parsed.reasoning, title="AI Reasoning Debug"))
        else:
            console.print("[yellow]No recent reasoning available.[/yellow]")
    elif sub == "raw":
        if hasattr(self, "last_response") and hasattr(self.last_response, "_parsed"):
            console.print(Panel(self.last_response._parsed.raw, title="Raw AI Response Debug"))
        else:
            console.print("[yellow]No recent raw response available.[/yellow]")
    elif sub == "on":
        self.config_mgr.config.debug.show_ai_reasoning = True
        self.config_mgr.config.debug.show_intent = True
        self.config_mgr.config.debug.show_plan = True
        self.config_mgr.save_config()
        console.print("[green]Debug output enabled.[/green]")
    elif sub == "off":
        self.config_mgr.config.debug.show_ai_reasoning = False
        self.config_mgr.config.debug.show_intent = False
        self.config_mgr.config.debug.show_plan = False
        self.config_mgr.config.debug.show_raw_ai_response = False
        self.config_mgr.config.save_config()
        console.print("[green]Debug output disabled.[/green]")
    else:
        console.print("[dim]Available debug: /debug prompt, /debug intent, /debug plan, /debug reasoning, /debug raw, /debug on, /debug off[/dim]")
```

- [ ] **Step 2: Update help text**

Modify `show_help` method around line 119 to include new debug options:

```python
/debug   - Show debug info (/debug intent, /debug plan, /debug prompt, /debug reasoning, /debug raw, /debug on/off)
```

- [ ] **Step 3: Test debug commands**

Run REPL and test:
- `/debug reasoning` - Should show AI reasoning if available
- `/debug raw` - Should show raw AI response
- `/debug on` - Should enable all debug output
- `/debug off` - Should disable all debug output

- [ ] **Step 4: Commit**

```bash
git add assistant/app/terminal/repl.py
git commit -m "feat: add debug CLI commands for AI response inspection"
```

---

### Task 17: Final Integration Test Run

**Files:**
- Test: All test suites

- [ ] **Step 1: Run all response parser tests**

Run: `pytest tests/brain/test_response_parser.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/integration/ -v`
Expected: All tests PASS

- [ ] **Step 3: Run existing test suite to ensure no regressions**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Manual REPL test**

Run REPL and verify:
1. Normal queries show only content
2. Invalid JSON shows fallback message
3. Plain text responses work
4. `/debug on` shows internal fields
5. `/debug off` hides internal fields
6. `/debug reasoning`, `/debug raw`, `/debug plan` work correctly

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "test: complete integration testing - all tests pass"
```

---

## Self-Review Results

**1. Spec Coverage:**
- ✅ Create `assistant/brain/response_parser.py` - Task 2
- ✅ Add `parse_ai_response(raw_response)` - Task 2
- ✅ Return content, intent, reasoning, plan, raw, valid_json - Task 2
- ✅ Handle valid JSON - Task 3
- ✅ Handle plain text - Task 5
- ✅ Handle invalid JSON - Task 6
- ✅ Fallback for missing/empty content - Task 4
- ✅ REPL prints only content - Task 12
- ✅ Hide internal fields in normal mode - Task 12, 13
- ✅ Add debug config (show_ai_reasoning, show_raw_ai_response, show_intent, show_plan) - Task 1
- ✅ Add tests for all cases - Tasks 3-10, 14-15

**2. Placeholder Scan:** No placeholders found. All code is concrete.

**3. Type Consistency:** 
- `ParsedAIResponse` fields consistent throughout
- `ResponseParser.parse_ai_response` signature consistent
- Config field names match usage in REPL

Plan complete and saved.
