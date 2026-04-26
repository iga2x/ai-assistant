# Architecture Rules

## No Duplicate Purpose Files
Do not create a new file/module if an existing file already owns that responsibility. Always verify if the logic belongs in an existing module before creating a new one.

## One Responsibility Owner
Each responsibility must have exactly one owner module.
- CLI commands → `assistant/app/commands/`
- Interactive terminal → `assistant/app/terminal/`
- AI provider logic → `assistant/ai/`
- Prompt building → `assistant/brain/`
- Memory/context → `assistant/context/`
- Planning/execution → `assistant/tasks/`
- Safety/scope/privacy → `assistant/safety/`
- Tool detection/running → `assistant/tools/`
- Reports/diffs/parsing → `assistant/analysis/`
- Workspaces/files → `assistant/workspace/`
- System discovery → `assistant/system/`
- Database models/session → `assistant/db/`

## CLI Is Interface Only
The CLI layer (`app/commands/`) is responsible for argument parsing and output formatting. It calls services from other modules. It must **not** contain business logic.

## MVP First
Backlog features must not be active in the main execution flow. Keep the core application lean and focused on the MVP roadmap.

## Extend Before Create
Prefer extending existing files over creating new parallel files. If a file exists for a general responsibility, update it rather than creating a specific version of it.

## Developer Checklist
Before adding a file:
- [ ] List existing related files.
- [ ] Select the correct owner module from the ownership map.
- [ ] Explain why a new file is needed if an existing one exists.
- [ ] Ensure no duplication of CLI/REPL/UI logic.
- [ ] Update imports instead of creating parallel logic.
- [ ] Update tests for changed behavior.
