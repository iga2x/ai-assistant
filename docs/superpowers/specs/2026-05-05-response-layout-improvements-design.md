# Response Layout and Execution Output Improvements Design

**Date:** 2026-05-05
**Author:** Claude Sonnet 4.6

## Problem Statement

Current AI assistant responses are messy and hard to understand:

1. **Chat answers are too verbose** - Long lists of methods, excessive details, unclear structure
2. **Task execution output is cluttered** - Reasoning, plans, execution, summaries mixed together
3. **Failure handling is broken** - After errors, assistant stops responding or freezes

## Goal

Improve response clarity across all output types with a 3-part incremental implementation:

1. **Part 1:** Simple, structured chat answers
2. **Part 2:** Clean task execution output with Main View + Execution Monitor
3. **Part 3:** Robust failure recovery system

## Part 1: Structured Chat Answers

### Structure

All AI responses use a consistent 4-field structure:

```
Answer: [1-2 sentences, direct answer]

Command / Example: [optional - command, code block, or simple example]

Details: [optional - expanded explanation, alternatives, edge cases]

Next step: [optional - suggested next action or approval note]
```

### Field Rules

**Answer:**
- Always shown
- Short and direct (1-2 sentences)
- No internal reasoning
- No latency display
- No planner text
- No raw debug logs

**Command / Example:**
- Show only when useful
- Use code block for shell commands
- Prefer one best command first
- Avoid listing too many alternatives unless user asks

**Details:**
- Show only when needed
- Use for alternatives, warnings, edge cases, or "why" explanation
- Keep it short by default

**Next step:**
- Show only when action is possible or approval may be needed
- For chat/how-to questions: suggest what command the user can run
- For semi/full execution mode: say what can be executed, not hidden planner details

### Examples

**Example 1: Direct IP query**
```
Answer: Your local IP is 192.168.10.108.

Command / Example:
hostname -I

Details: This shows the IP addresses assigned to your machine.
```

**Example 2: How-to question**
```
Answer: Use hostname -I for a quick local IP check.

Command / Example:
hostname -I

Details: For more detail, use ip addr show and look for the inet value under your active interface.
```

**Example 3: Security check**
```
Answer: You can check local listening ports with ss.

Command / Example:
ss -tulnp

Details: This is local-only and read-only. Scanning other hosts should require approval.
```

### Implementation Responsibilities

**Prompt Builder:**
- Ask model to output structured answer fields
- Define clear structure in system prompt

**AI Response Parser:**
- Parse Answer / Command / Details / Next step fields
- Handle missing optional fields gracefully

**Result Synthesizer:**
- Convert execution results into same structure
- Ensure consistency between chat and task answers

**REPL / Renderer (repl.py):**
- Only render already-clean structured fields
- Use Rich formatting (bold, colors, code blocks)
- Do not parse or interpret content

## Part 2: Clean Task Execution Output

### Architecture: Main View + Execution Monitor

**Main View:**
- Clean user interaction
- Assistant clean answers (Part 1 structure)
- Optional Plan Panel
- Result Panel
- Approval prompts

**Execution Monitor:**
- Real-time command output
- Full execution logs
- Tool stdout/stderr
- Errors and tracebacks
- Status updates
- Optional debug metadata

**Controls:**
- Press `v` to toggle Execution Monitor
- `/view` opens or focuses Execution Monitor
- `/logs` shows recent execution logs
- `/debug` enables reasoning/latency/internal diagnostics

### Panel Definitions

**Plan Panel:**
- Optional
- Shows user-facing planned actions
- Used for multi-step, risky, approval-based, or user-requested planning

**Result Panel:**
- Always shown after task execution
- Uses Part 1 structure (Answer, Command/Example, Details, Next step)
- Synthesizes command output, never dumps raw logs

### Visibility Rules

**Main View:**
- Never shows raw execution logs by default
- Shows Result Panel after every completed task
- Shows Plan Panel only for:
  - Multi-step tasks
  - Medium/high risk tasks
  - Tasks needing approval
  - User explicitly asked what will happen
- Simple safe tasks show only Result Panel

**Execution Monitor:**
- Receives command output in real time
- Stores stdout, stderr, command status, duration, and errors
- Internal reasoning and latency hidden unless debug mode enabled
- Failed tasks show full traceback/output here

### Rules

1. Hide internal reasoning, latency, planner JSON, route decisions, debug logs, and workspace paths from normal output
2. Do not show Plan Panel for simple one-command safe tasks unless user asks
3. Always show Result Panel after execution
4. Result Panel must synthesize command output instead of dumping raw output
5. Command output may appear in Execution Monitor, not Result Panel
6. Failed commands must show clean error in Result Panel and raw error in Execution Monitor only if useful
7. Approval tasks should show Plan Panel before execution
8. Debug mode may show extra panels/logs, but normal mode must stay clean

### Examples

**Example 1: Simple local query (Main View only)**
```
╭────────────────────────────────── Result ────────────────────────────────────╮
│ Answer: Your local IP is 192.168.10.108.                                     │
│                                                                              │
│ Command / Example:                                                           │
│ hostname -I                                                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Example 2: Network scan task (Main View + Execution Monitor)**

Main View:
```
╭──────────────────────────────────── Plan ────────────────────────────────────╮
│ Scan 192.168.10.108 for common open ports.                                   │
│ This is a local network scan and may require approval in Semi mode.           │
╰──────────────────────────────────────────────────────────────────────────────╯

╭────────────────────────────────── Result ────────────────────────────────────╮
│ Answer: No open ports were found in the scanned range.                       │
│                                                                              │
│ Command / Example:                                                           │
│ nmap -sT -p 1-1000 192.168.10.108                                            │
│                                                                              │
│ Details: Scanned ports 1-1000 only. Full logs are available with /view.       │
│ Next step: Run a local listening-port check with ss -tulnp.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

Execution Monitor:
```
[12:41:03] Starting task: Scan common ports
[12:41:03] Command: nmap -sT -p 1-1000 192.168.10.108
[12:41:04] stdout:
Starting Nmap...
All 1000 scanned ports on 192.168.10.108 are closed
[12:41:04] Exit code: 0
[12:41:04] Duration: 1.2s
```

## Part 3: Failure Recovery System

### Problem

After command failure, assistant:
- Stops responding
- Freezes input loop
- Dumps raw tracebacks
- Returns None or empty result

### Solution

Every failure produces a structured Result Panel + recoverable next action.

### Failure Result Structure

**Answer:**
- What failed
- Why it likely failed
- Human-readable, short

**Command / Example:**
- Suggested fix command
- Retry command
- Alternative command
- Only shown when useful

**Details:**
- Short error summary
- No raw traceback in main view
- Mention that full logs are available in Execution Monitor when relevant

**Next step:**
- Ask whether to retry
- Offer safer alternative
- Offer to continue without that step

### Auto-Retry Policy

**Safe auto-retry allowed:**
- Timeout with smaller scope
- Temporary command formatting issue
- Missing optional flag
- Tool not found when there is a known fallback command
- Empty output when an alternative read-only command exists

**Ask before retry:**
- sudo required
- Permission denied
- Network scan
- Exploit/pentest tool
- Destructive command
- Package install
- Command changes system state

**Never auto-retry:**
- rm, delete, wipe, overwrite
- Credential/token operations
- Exploit execution
- Brute force
- Unknown generated command

### Rules

1. Never freeze after failure
2. Never return None or empty result
3. Always return a structured Result Panel
4. Main View shows clean error explanation only
5. Full stderr, traceback, and raw output go to Execution Monitor
6. Suggest a fix or alternative when obvious
7. Keep conversation going with a clear Next step
8. Do not auto-run sudo or privilege escalation
9. Do not auto-retry destructive, risky, external-network, or high-cost commands
10. Auto-retry only safe read-only cases with bounded limits
11. Failed command must not break REPL loop
12. Reset processing state in finally block

### Failure Categories

1. `permission_denied` - sudo required, insufficient permissions
2. `command_not_found` - tool not installed
3. `timeout` - command exceeded time limit
4. `network_unreachable` - host down, network issues
5. `invalid_target` - wrong IP, malformed input
6. `empty_output` - command succeeded but returned nothing useful
7. `parse_error` - output couldn't be parsed
8. `unsafe_blocked` - command blocked by safety gate
9. `unknown_error` - catch-all for unexpected failures

### Examples

**Example 1: Permission error**
```
╭────────────────────────────────── Result ────────────────────────────────────╮
│ Answer: The command failed because it needs higher permissions.              │
│                                                                              │
│ Command / Example:                                                           │
│ sudo arp-scan -l                                                             │
│                                                                              │
│ Details: arp-scan needs raw packet access, usually CAP_NET_RAW/root.          │
│ Full error is available in Execution Monitor with /view.                     │
│                                                                              │
│ Next step: Retry with sudo? [y/n]                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Example 2: Network down**
```
╭────────────────────────────────── Result ────────────────────────────────────╮
│ Answer: The target appears unreachable.                                      │
│                                                                              │
│ Details: The scan reported that the host seems down. This can happen if the   │
│ host is offline, blocking probes, or the IP is wrong.                         │
│                                                                              │
│ Next step: Check basic connectivity first? [y/n]                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

**Example 3: Timeout**
```
╭────────────────────────────────── Result ────────────────────────────────────╮
│ Answer: The command timed out before it finished.                            │
│                                                                              │
│ Command / Example:                                                           │
│ nmap --max-retries 2 -p 1-1000 192.168.10.108                                │
│                                                                              │
│ Details: The scan may be too broad or the target may be slow to respond.      │
│ Full output is available in Execution Monitor with /view.                    │
│                                                                              │
│ Next step: Retry with a quicker scan? [y/n]                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Implementation Plan

### Part 1: Structured Chat Answers

1. **Modify Prompt Builder** (`assistant/brain/prompt_builder.py`)
   - Add structured response format to system prompt
   - Define Answer, Command/Example, Details, Next step fields

2. **Create Response Parser** (`assistant/ai/response_parser.py` - new file)
   - Parse structured fields from AI responses
   - Handle missing optional fields
   - Return validated structured object

3. **Update Result Synthesizer** (`assistant/analysis/synthesizer.py`)
   - Output same 4-field structure
   - Ensure execution results match chat response format

4. **Update REPL Renderer** (`assistant/app/terminal/repl.py`)
   - Render structured fields with Rich formatting
   - Remove any parsing/interpretation logic
   - Keep as pure renderer

### Part 2: Main View + Execution Monitor

1. **Create Execution Monitor** (`assistant/app/terminal/execution_monitor.py` - new file)
   - Real-time log display
   - Command stdout/stderr capture
   - Status updates and timestamps
   - Toggle visibility support

2. **Update Executor** (`assistant/actions/executor.py`)
   - Send output to Execution Monitor
   - Store full logs
   - Track execution state

3. **Update REPL** (`assistant/app/terminal/repl.py`)
   - Add Plan Panel rendering
   - Add Result Panel rendering (Part 1 structure)
   - Remove raw execution output from main view
   - Add `/view`, `/logs`, `/debug` commands
   - Add `v` key handler for monitor toggle

4. **Update Pipeline** (`assistant/app/terminal/pipeline.py`)
   - Separate plan, execution, result phases
   - Return structured result to REPL

### Part 3: Failure Recovery

1. **Update Result Synthesizer** (`assistant/analysis/synthesizer.py`)
   - Add failure category detection
   - Generate structured error results
   - Add Next step suggestions for each failure type
   - Never return None or empty result

2. **Update Executor** (`assistant/actions/executor.py`)
   - Catch all exceptions
   - Return ExecutionResult with failure details
   - Store full error in Execution Monitor
   - Apply auto-retry policy

3. **Update REPL** (`assistant/app/terminal/repl.py`)
   - Handle Next step prompts for failures
   - Reset processing state in finally block
   - Ensure failed tasks don't break input loop

4. **Update Safety Gate** (`assistant/safety/gate.py`)
   - Return structured failure when blocking
   - Include reason and alternative suggestions

## Success Criteria

1. Chat answers are simple and directly address user questions
2. Task execution output is clean with optional detailed views
3. Failures always produce helpful, recoverable responses
4. Assistant never freezes or stops responding after errors
5. Main view remains uncluttered while logs are accessible

## Testing Plan

1. **Part 1 Testing:**
   - Test various question types (direct IP, how-to, security)
   - Verify structured format is always produced
   - Check optional fields appear/disappear correctly

2. **Part 2 Testing:**
   - Test simple tasks (show only Result)
   - Test complex tasks (show Plan + Result)
   - Test Execution Monitor toggle and log viewing
   - Verify no raw output leaks to main view

3. **Part 3 Testing:**
   - Test each failure category
   - Verify auto-retry behavior
   - Verify permission retry requires confirmation
   - Ensure REPL continues after all failure types
