# AI Assistant - Finalized MVP Roadmap

Goal: Build a personal AI terminal assistant with ethical hacking support that feels natural, fast, and safe.

## ✅ Phase 0: Clean Foundation

**Goal:** Create a **stable, clean, installable base** so development doesn’t become chaotic later.

### 0.1 Project Structure
- [x] Clean, scalable folder layout (app, config, db, tools, safety, etc.).
- [x] No user data inside repo.
- [x] Separation of CLI and core logic.

### 0.2 CLI Entrypoint
- [x] Single `assistant` command for everything.
- [x] Commands for `version`, `doctor`, `init`, `chat`, `config`.

### 0.3 User Data Directory
- [x] Automatic creation of `~/.assistant/` for config, db, logs, and workspaces.
- [x] Never writing into project folder during runtime.

### 0.4 Config System
- [x] Central loader with Pydantic validation.
- [x] Support for `config get`, `config set`, and `config reset`.

### 0.5 Logging System
- [x] Structured logging to console (Rich) and file (`~/.assistant/logs/`).
- [x] Separate `app.log` and `error.log`.

### 0.6 Database Setup (SQLite)
- [x] Persistent layer with SQLAlchemy.
- [x] Initial tables for conversations, messages, entities, and tasks.

### 0.7 System Paths Utility
- [x] Centralized path management in `assistant/utils/paths.py`.
- [x] No hardcoded paths in business logic.

### 0.8 Initialization Command
- [x] `assistant init` handles complete environment setup.

### 0.9 Doctor Command
- [x] `assistant doctor` provides one-click environment diagnostics.

### 0.10 Phase 0 Debug Checklist
- [x] `assistant` command works.
- [x] `assistant --version` prints version.
- [x] `assistant init` creates ~/.assistant/.
- [x] `assistant doctor` runs without crash.
- [x] config can be read and updated.
- [x] logs are written to file.
- [x] **0.11 Architecture Governance Rules**: No duplicate-purpose files, one responsibility per module, extend before create, backlog features disabled.
- [x] **0.12 Real Install Test**: Verified `pip install -e .`, `assistant init`, `assistant`, `assistant doctor`.

---

---
## ✅ Phase 1: System + AI + Tool Detection

**Goal:** Make the assistant aware of the machine it is running on.

### 1.1 System Detection
- [x] **OS/Version/Arch**: Deep detection (Ubuntu 24.04, etc.).
- [x] **Environment**: Shell (bash/zsh), Username, Hostname, Python version.
- [x] **Permissions**: Detect if running as root/admin.
- [x] **Implementation**: `assistant/system/discovery.py`, `os_detect.py`, `permissions.py`.

### 1.2 Hardware Detection
- [x] **Resources**: CPU count, RAM info, Disk free space.
- [x] **GPU**: Best-effort detection (NVIDIA/AMD).

### 1.3 Shell Detection
- [x] **Context**: Detect specific shell (bash, zsh, powershell) and terminal type.
- [x] **Path Awareness**: Real shell path detection.

### 1.4 Local Network Awareness
- [x] **Interfaces**: List local IPs and network interfaces (read-only).

### 1.5 AI Provider Detection
- [x] **Local**: Ollama/LM Studio reachability and model listing.
- [x] **Cloud**: Environment key presence (OpenAI, Anthropic, Gemini).
- [x] **Validation**: `assistant ai scan`, `assistant ai list`, `assistant ai test`.

### 1.6 Tool Detection & Classification
- [x] **Detection**: Version-aware detection for 15+ tools (nmap, git, nuclei, etc.).
- [x] **Classification**: Category mapping (recon, scanner, development) and risk levels.
- [x] **Stability**: Version command timeouts and error handling.

### 1.7 Status Dashboard
- [x] **Unified View**: `assistant status` provides a rich, truthful environment overview.

### 1.8 Testing Suite (Phase 1 Logic)
- [x] **Unit Tests**: `pytest` for discovery, AI, and tool logic.
- [x] **Integration Tests**: CLI behavior validation with `CliRunner`.
- [x] **Mocks**: Mocked provider responses and cross-platform behavior (Windows/Linux).
- [x] **1.9 Discovery Cache / Refresh Rules**: Startup uses cached profile, `assistant system refresh`, `assistant tools scan`, `assistant ai scan` implemented.
- [x] **1.10 Detection Error Policy**: Missing Ollama/broken tools do not crash, cloud API keys are never printed.

---

## ✅ Phase 1.5: CLI Interface + Brain/Body Verification

**Goal:** Make the assistant actually usable from terminal and verify the complete stack (Body + Brain).

### 1.5.1 Default CLI Behavior
- [x] **Direct Boot**: Running `assistant` without arguments must start the REPL immediately.
- [x] **No Help Default**: Do NOT show the help message if no command is provided.
- [x] **Launcher**: `run.sh` must behave exactly like the `assistant` command.

### 1.5.2 REPL Core Loop
- [x] **Location**: `assistant/app/terminal/repl.py`.
- [x] **Welcome Message**: "AI Assistant started. Type /help".
- [x] **Prompt**: "You: ".
- [x] **Exit condition**: "exit" or "/exit" prints "Goodbye." and closes.
- [x] **Command handling**: Support slash commands (e.g., `/help`).
- [x] **Chat Hook**: Basic `handle_chat` hook for future Phase 2 integration.

### 1.5.3 REPL Commands (Minimum)
- [x] `/help`: Show available commands.
- [x] `/status`: Show system + AI + tools status.
- [x] `/test`: Run quick health checks (Body + Brain).
- [x] `/context`: Show stored entities from the session.
- [x] `/exit`: Cleanly exit the session.

### 1.5.4 CLI Commands (Outside REPL)
- [x] `assistant status`: Unified environment overview.
- [x] `assistant doctor`: Deep diagnostics.
- [x] `assistant test [brain|body|all|features]`: Targeted verification.
- [x] `assistant system info`: Hardware and OS details.
- [x] `assistant ai list`: Detected providers and models.
- [x] `assistant tools list`: Available hacking and system tools.

### 1.5.5 Brain vs Body Verification
- [x] **Body Test**: Verify config, DB, logs, tools, and workspace connectivity.
- [x] **Brain Test**: Verify AI router, provider reachability, and basic prompt response.

### 1.5.6 Phase 1.5 Debug Checklist
- [x] `assistant` starts REPL directly
- [x] `run.sh` starts REPL
- [x] REPL accepts input
- [x] `/exit` works
- [x] `/help` works
- [x] `/status` works
- [x] `assistant test all` works
- [x] `brain test` works (or fallback)
- [x] `body test` works
- [x] CLI commands still work

### 1.5.7 Phase 1.5 Exit Criteria
Phase 1.5 is complete when:
1. Running `./run.sh` opens the assistant REPL immediately.
2. User can type a message and get a response (even if simulated).
3. `/exit` closes the session cleanly.

### ✅ 1.5.8 Default App Flow Test
- [x] **Verification**: `./run.sh`, `assistant`, and `assistant chat` all open the REPL.
- [x] **Clean Exit**: `/exit` command terminates the session gracefully.

---



## ✅ Phase 2: Chat + Memory + Context

**Goal:** Make the assistant feel natural, continuous, and aware of what the user means, even with messy input.

### ✅ 2.1 REPL / Terminal Chat Interface

```text
Goal: Clean interactive terminal chat, not a messy command dump.
```

Build:

```text
- `assistant` opens chat mode
- Clean scrolling messages
- User prompt clearly separated
- AI response formatting with Rich
- Slash commands supported
- Errors shown in friendly language
- Long outputs summarized by default
```

REPL commands:

```text
/help
/status
/context
/memory
/clear
/history
/tools
/ai
/report
/exit
```

Expected behavior:

```text
User: find my ip
AI: Your local IP is 192.168.1.20. I saved it as last_ip.

User: scan it
AI: I understand “it” as 192.168.1.20.
```

Debug commands:

```text
/context show       Show current context entities
/context clear      Clear current context
/memory last        Show last messages
/debug prompt       Show final prompt sent to AI
/debug intent       Show detected intent
```

---

### ✅ 2.2 Conversation Persistence

```text
Goal: Store chat history so the assistant does not forget immediately.
```

Build:

```text
- conversations table
- messages table
- active conversation ID
- save every user/assistant message
- load recent messages into prompt
```

Database:

```text
conversations:
- id
- title
- created_at
- updated_at
- workspace_id

messages:
- id
- conversation_id
- role
- content
- created_at
- metadata_json
```

Prompt memory limit:

```text
- Last 10-20 messages in prompt
- Important entities always injected
- Avoid sending huge history every time
```

Concerns:

```text
- Do not overfill prompt
- Do not store secrets blindly
- Add option to clear conversation
```

---

### ✅ 2.3 Context Entity Store

```text
Goal: Remember important things from conversation.
```

Track entities:

```text
last_ip
last_domain
last_url
last_file
last_target
last_workspace
last_tool
last_scan
last_command
last_report
```

Database:

```text
context_entities:
- id
- conversation_id
- workspace_id
- key
- value
- entity_type
- confidence
- source_message_id
- created_at
- updated_at
```

Example:

```text
User: find my ip
AI stores:
last_ip = 192.168.1.20
last_target = 192.168.1.20
```

Concerns:

```text
- Do not overwrite strong context with weak guesses
- Track confidence
- Track source message
- Prefer explicit user input over AI guess
```

Priority rule:

```text
explicit user value > tool result > AI inference > old memory
```

---

### ✅ 2.4 Context Resolver

```text
Goal: Understand “it”, “that”, “same”, “again”, “this file”, “that target”.
```

Resolver examples:

```text
"scan it" → last_target
"scan same again" → last_scan target
"check that domain" → last_domain
"open this file" → last_file
"compare it" → last_scan or last_target
```

Resolution rules:

```text
1. Look for explicit target in current input
2. If missing, check context entities
3. If one clear match exists, use it
4. If risky/ambiguous, ask confirmation
5. If no match, ask user for target
```

Example:

```text
User: scan it

AI:
I think “it” means 192.168.1.20 from earlier.
This is a scan action. Approve?
```

Bug concerns:

```text
- “it” may refer to IP, file, URL, or previous result
- Wrong resolution can cause wrong target execution
- Always confirm for risky actions
```

---

### ✅ 2.5 Input Normalization

```text
Goal: Handle typo-heavy and broken input before intent detection.
```

Examples:

```text
"sacn it" → "scan it"
"analize dis file" → "analyze this file"
"run same agin" → "run same again"
"find open ports are" → "find open ports"
```

Build:

```text
- lightweight spelling cleanup
- common command typo map
- normalize casing
- remove extra spaces
- keep original input for audit logs
```

Store both:

```text
original_input
normalized_input
```

Important:

```text
Do not silently change dangerous commands.
For risky actions, show interpreted meaning.
```

Example:

```text
AI: I interpreted “sacn it” as “scan it”.
Target: 192.168.1.20
Approve?
```

---

### ✅ 2.6 Intent Detection

```text
Goal: Understand what type of task user wants.
```

Intent categories:

```text
pc_task
system_info
coding_help
command_help
file_analysis
scan
compare
report
scope_management
tool_help
chat_only
unknown
```

Example mapping:

```text
"find my ip" → system_info
"scan it" → scan
"compare with last time" → compare
"make report" → report
"what is nmap" → tool_help
```

Output schema:

```json
{
  "intent": "scan",
  "target": "192.168.1.20",
  "needs_context": true,
  "risk_level": "medium",
  "confidence": 0.86
}
```

Concerns:

```text
- Low confidence should ask question
- Security intent must go through safety phase
- Do not execute from intent detection directly
```

---

### ✅ 2.7 Prompt Builder with Context Injection

```text
Goal: Give AI enough context without making it slow or confused.
```

Prompt should include:

```text
- Current OS/system summary
- Active workspace
- Available tools
- Recent conversation summary
- Important context entities
- Current user input
- Safety rules
```

Example injected context:

```text
System:
OS: Linux
Shell: bash
Available tools: nmap, curl, git

Context:
last_ip: 192.168.1.20
last_target: 192.168.1.20
last_scan: nmap scan from 2026-04-25

User input:
scan it
```

Concerns:

```text
- Too much context makes AI slower
- Old context can mislead AI
- Need freshness timestamps
```

---

### ✅ 2.8 Memory Privacy Controls

```text
Goal: Store useful memory without leaking sensitive data.
```

Sensitive patterns:

```text
api keys
passwords
tokens
cookies
private keys
authorization headers
client secrets
```

Rules:

```text
- Detect sensitive text before storing
- Redact in logs
- Do not send sensitive data to cloud AI
- Allow `/memory clear`
```

Commands:

```text
/memory show
/memory clear
/memory forget last_ip
/memory forget all
```

---

---

## ✅ Phase 2.5: Runtime Flow & Pipeline Integration

Goal: Connect REPL input to the full assistant pipeline.

Flow:
REPL
→ ChatPipeline
→ Save user message
→ Normalize input
→ Resolve context
→ Detect intent
→ Route chat/read-only/action
→ Planner if needed
→ Safety if needed
→ Approval if needed
→ Executor if approved
→ Save result
→ Return response

Rules:
- REPL only handles input/output.
- Pipeline routes processing.
- Planner never executes.
- Executor never runs without approval.
- chat_only must not create approval prompt.

---

## 🛠 Phase 2.9: Action Runtime Layer

**Goal:** Give the assistant a real body, not hardcoded replies.

### Core Flow
```text
User input
 ↓
Intent/router
 ↓
Decide response type:
   1. chat_response
   2. local_function_call
   3. tool_execution
   4. approval_required_action
 ↓
Run selected handler/tool
 ↓
Capture output
 ↓
Save context/result
 ↓
Return clean user answer
```

### Required Action Types
- `chat_response`: Normal AI interaction.
- `read_only_system_action`: Local system queries (date, IP, status).
- `safe_local_command`: Non-destructive shell commands.
- `risky_tool_action`: Security tools or destructive actions.
- `file_action`: Read/Write/Delete operations.
- `security_scan`: Nmap, nuclei, etc. (Requires approval).
- `report_action`: Building summaries or diffs.

### Architecture Structure
- `assistant/actions/router.py`: Decides action type.
- `assistant/actions/registry.py`: Maps actions to handlers.
- `assistant/actions/handlers.py`: Local read-only handlers.
- `assistant/actions/schemas.py`: ActionRequest / ActionResult.
- `assistant/actions/permissions.py`: Approval requirement logic.

---

---

## 🛠 Phase 2.7: Dynamic AI Provider + Model Runtime Routing

**Problem:**
Current config is static and doesn't account for what is actually running or installed on the system, leading to broken chat or fake offline fallbacks.

**Goal:**
Enable real-time detection and routing for AI models.

### Required Flow
1. **App Starts**: Initialize AI runtime.
2. **Detect Services**: Check Ollama, LM Studio, etc.
3. **Detect Models**: Query services for installed and *running* models.
4. **Resolve Model**:
   - Priority 1: Currently running model (if `prefer_running_model=true`).
   - Priority 2: User-configured default (if available).
   - Priority 3: First available local model.
5. **Route Chat**: Send request to the resolved live model.

### Correct Selection Priority (Ollama)
1. `ollama ps` → Currently running model.
2. `ollama tags` → Config default if installed.
3. First installed local model.
4. Fail with clear message if no model available (no silent mock fallback).

### Implementation Requirements
- **Config Update**: Add `auto_select_model`, `prefer_running_model`, and `allow_mock_fallback=false`.
- **Runtime State**: Create `RuntimeAIState` to track active provider/model/source.
- **Service Scanning**: Implement `/api/ps` check for Ollama.
- **Router Rule**: Block chat and warn user if no real AI is available.

### CLI Commands
```bash
assistant ai scan      # Manual service scan
assistant ai list      # Show all detected models
assistant ai active    # Show current routing state
assistant ai test      # Send test ping to active model
```

### Phase 2.7 Exit Criteria
- [x] Ollama running model is detected dynamically.
- [x] Active model is selected based on priority logic.
- [x] Chat routes through selected live model.
- [x] Mock fallback is disabled by default.
- [x] System reports "No AI Available" instead of faking responses.

---

## 🛠 Phase 2.8: AI Runtime Debug & Verification (Developer Only)

**Goal:**
Verify that the assistant is using the real AI brain, not fake fallback logic.

### Debug Flow
1. **Service Check**: Verify Ollama/Cloud service is reachable.
2. **Model Inventory**: Confirm models are detected via `/api/tags`.
3. **Selection Verification**: Ensure `RuntimeAIState` reflects the intended model.
4. **Prompt Test**: Send a real test prompt (e.g., "Return exactly: AI_RUNTIME_OK").
5. **Integration Audit**: Trace REPL → ChatPipeline → AI Router to ensure no silent fallbacks are active.

### Verification Checklist
- [x] Ollama service reachable.
- [x] AI router sends real request to the selected model.
- [x] Model returns structured JSON response.
- [x] REPL uses the live response, not the "offline mode" template.
- [x] Mock fallback remains disabled unless explicitly enabled for dev.

---

## ✅ Phase 3: AI-Led Planning — Full Detailed Plan

**Goal:**
Convert user input into the correct path:
```text
Normal conversation → direct AI response
Action request → structured plan
Risky action → approval before execution
```

Phase 3 must fix your current issue:
```text
User: hi
Assistant: Plan approval required ❌
```

Correct behavior:
```text
User: hi
Assistant: normal chat response ✅
```

---

### Chat vs Action Router

Non-executable:
- chat_only
- tool_help
- coding_help
- command_help

These go directly to AI response.

Read-only:
- system_info
- tools_list
- ai_list
- config_read

These do not need approval unless sensitive.

Executable:
- scan
- command_execute
- tool_run
- file_modify
- delete_action
- install_package

These require plan + safety + approval.

---

### 3.1 Input Routing Layer
**Goal:** Decide whether the message is normal chat or an action.

#### Intent Groups
- **Non-executable intents** (No approval): `chat_only`, `tool_help`, `coding_help`, `command_help`, `concept_explanation`, `general_question`.
- **Read-only intents** (Lightweight/No approval): `system_info`, `tool_list`, `config_read`, `history_read`, `workspace_list`.
- **Executable intents** (Plan + Approval): `scan`, `command_execute`, `tool_run`, `file_modify`, `install_package`, `delete_action`, `network_action`, `cloud_ai_send`.

---

### 3.2 Task Classification & Routing Logic
**Goal:** Correctly classify user intent and stop forcing normal messages through approval.

```python
NON_EXECUTABLE_INTENTS = {"chat_only", "tool_help", "coding_help", "command_help", "concept_explanation", "general_question"}
READ_ONLY_INTENTS = {"system_info", "tool_list", "config_read", "history_read", "workspace_list"}
EXECUTABLE_INTENTS = {"scan", "command_execute", "tool_run", "file_modify", "install_package", "delete_action", "network_action"}
```

#### Routing Flow:
1. **Direct Chat Path**: Normal conversation feels like AI chat. No plan, no approval.
2. **Read-Only Path**: Safe system queries (IP detection, tool listing) without annoying approval.
3. **Executable Path**: Create small, clear plans (Max 5 steps, linear, no branching) for risky actions.

---

### 3.3 Planning & Approval Rules
- **Constraints**: Max 5 steps, no branching/loops, no autonomous chains.
- **Strict Separation**: Planner must never execute commands or call tools.
- **Approval Message**: Must include Goal, Target, Tool, Risk Level, Reason, and Output Location.
- **Safety Hand-off**: Planner estimates risk; Safety engine reviews and has final authority to block or allow.

---

### 3.4 CLI / REPL Behavior & Mode
- **Learning Mode**: No execution, only explain what would be done.
- **Active Mode**: Plan → Safety → Approval → Execution.
- **Slash Commands**:
  - `/plan <request>`: Show dry-run plan only.
  - `/debug intent/plan`: Show last detected intent/plan.
  - `/mode learning/active`: Toggle execution mode.

---

### 3.5 Phase 3 Debug Checklist
- [x] "hi" gives normal response
- [x] "what is nmap" explains without approval
- [x] "find my ip" works without approval
- [x] "scan it" asks approval
- [x] chat_only does not create task in DB
- [x] planner never executes commands
- [x] BLOCKER: chat_only is incorrectly routed to approval system.

---

### 3.6 Phase 3 Exit Criteria
Phase 3 is complete when:
- Normal chat and Read-only requests work without approval.
- Executable actions create a plan.
- Risky actions require approval.
- Planner never executes anything.

---

## ✅ Phase 4: Safe Execution
- [x] **Tool Whitelist**: Strict restriction to authorized tools only.
- [x] **Timeout Protection**: Enforce execution limits on all subprocesses.
- [x] **Audit Logging**: Record every command and its output to the workspace.

## ✅ Phase 5: Result History + Comparison
- [x] **Structured Storage**: Save results (ports, protocols, states) as JSON/DB entities.
- [x] **Diff Engine**: Identify `new`, `removed`, or `unchanged` services.
- [x] **Compare Command**: Direct command to compare current vs last scan.

## ✅ Phase 6: Scope & Safety
- [x] **Scope Whitelist**: IP/Domain validation before execution.
- [x] **Execution Modes**: `learning` (explain) vs `active` (execute).

## ✅ Phase 7: Simple Reports
- [x] **Markdown Export**: Professional session summary.
- [x] **Instant Report**: `/report` command in REPL.

---

## 🚫 Backlog (Do Not Build Yet)
- Multi-agent orchestration
- Full-screen TUI dashboard
- RAG knowledge system
- Complex plugin system
- Project profiles
- Secure archiving
