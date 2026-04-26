# Module Ownership Rules

To maintain architecture integrity, all developers (and AI assistants) must follow these rules.

## Core Principles
1.  **One Purpose = One Owner File**: Do not split the same logic across multiple files in different layers.
2.  **CLI is Interface Only**: The `app/` layer must not contain business logic, tool execution, or model routing.
3.  **Action Runtime Separation**: The AI **describes** the intent; the Action Runtime **executes** it.

## Ownership Map

| Layer | Responsibility | Rule |
| :--- | :--- | :--- |
| `app/` | CLI/REPL Interface | Must not access `subprocess` or `sqlite3` directly. |
| `ai/` | Model Connectivity | Handles provider detection and raw chat completion. |
| `brain/` | Reasoning & Prompts | Converts system state into instructions for the AI. |
| `context/` | Information Recall | Manages entities and resolves ambiguous references. |
| `actions/` | Execution Bridge | The ONLY layer allowed to call the `Executor`. |
| `tasks/` | Plan Management | Defines schemas for multi-step operations. Never executes. |
| `tools/` | Subprocess Wrapper | Clean interface to OS binaries. |
| `safety/` | Policy Enforcement | Validates scope and permission. Cannot be bypassed. |
| `db/` | Persistence | Handles ORM and session state. |

## Strict Prohibitions
*   **No Direct Execution**: The `Planner` must never call `subprocess`. It only describes what *should* be run.
*   **No Raw Reasoning to User**: Internal reasoning tags (`<thought>`, JSON reasoning) must be filtered out before reaching the REPL.
*   **No Approval for Read-Only**: System queries (date, IP, version) must execute immediately through handlers, bypassing the plan approval prompt.
*   **One Runner**: All shell commands must go through `tools/runner.py` to ensure consistent logging and safety checks.
*   **Workspace Hygiene**: Never write user data or logs into the project repository. Use `~/.assistant/` as defined in `utils/paths.py`.
