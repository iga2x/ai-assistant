# AI Assistant Runtime Flow

This document describes the various execution paths within the AI Assistant.

## 1. Normal Chat Flow
*Used for general conversation and help.*

1.  **REPL**: Captures user input.
2.  **ChatPipeline**: Orchestrates the turn.
3.  **InputNormalizer**: Cleans text (lowercase, trimming).
4.  **ContextResolver**: Resolves pronouns (it, that) using the `EntityStore`.
5.  **PromptBuilder**: Assembles the system prompt with current state and entities.
6.  **AIRouter**: Sends the prompt to the selected AI model (e.g., Ollama/Qwen).
7.  **Planner**: Parses the JSON response and classifies the intent.
8.  **ActionRouter**: Detects `chat_response` and returns content directly.
9.  **REPL**: Displays the AI response.

## 2. Read-Only Action Flow
*Used for "what is today", "find my ip", "list tools".*

1.  **REPL** → **ChatPipeline** → **AI Router** (same as chat).
2.  **Planner**: Classifies intent as `read_only_system_action`.
3.  **ActionRouter**: Identifies the handler (e.g., `get_local_ip`).
4.  **Handler**: Executes a local Python function to retrieve system data.
5.  **ActionResult**: Returns the output string.
6.  **ChatPipeline**: Updates the response content with the handler result.
7.  **REPL**: Prints the system information directly.

## 3. Risky Action Flow
*Used for "scan it", "run nmap", "delete file".*

1.  **REPL** → **ChatPipeline** → **AI Router**.
2.  **Planner**: Classifies intent as `security_scan` or `risky_tool_action`.
3.  **Planner**: Generates a multi-step `Plan` object.
4.  **ActionRouter**: Returns `needs_pipeline=True`.
5.  **REPL**: Detects an executable plan in the response.
6.  **SafetyPolicy**: Checks if commands are in scope.
7.  **ApprovalPrompt**: Asks the user "Execute this plan? [y/N]".
8.  **Executor**: Runs the plan steps if approved.
9.  **ToolRunner**: Executes subprocess commands.
10. **OutputCapture**: Saves logs to the session workspace.
11. **REPL**: Shows progress and final summary.

## 4. AI Runtime Flow
*Used for model detection and connectivity.*

1.  **AIRuntime.refresh()**: Called before every chat turn.
2.  **Detector**: Scans local ports (11434 for Ollama) and env vars for cloud keys.
3.  **Resolver**: Selects the best model based on priority rules (Running > Default > First Found).
4.  **State**: Updates `available` status and active provider.

## 5. Tool Execution Flow
*Used by the Executor.*

1.  **WorkspaceManager**: Creates a unique session directory.
2.  **ScopeManager**: Validates IP/Domain targets against the allowed list.
3.  **ToolRunner**: Uses `subprocess.run` with time-outs and output capture.
4.  **AuditLog**: Records the command, result code, and timestamp in DB.
