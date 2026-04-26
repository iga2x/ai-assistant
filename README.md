# AI Assistant

A clean, installable terminal AI assistant that can help with PC tasks, coding, security scanning, and more. Built with a local-first philosophy and a powerful planning engine.

## Quick Start (Dev)

1. Clone the repo
2. Run install script: `./scripts/dev_install.sh`
3. Activate venv: `source .venv/bin/activate`
4. Start chat: `assistant chat`

## Core Commands

### System & AI
- `assistant status`: Show high-level environment summary.
- `assistant system info`: Detailed hardware and OS information.
- `assistant doctor`: Run a full health check of your installation.

### Security & Safety
- `assistant scope add <target>`: Add a target to the allowed scanning list.
- `assistant scope list`: View all targets in scope.
- `assistant scope check <target>`: Verify if a target is authorized.

### Automation & Chat
- `assistant chat`: Enter the interactive REPL.
- `assistant init`: Re-initialize configuration and plugins.

## Key Features
- **Local-First AI**: Optimized for Ollama and LM Studio. Works offline via a robust mock fallback.
- **Intelligent Planning**: Automatically breaks down complex requests (like "recon google.com") into actionable steps.
- **Safety First**: Mandatory scope validation and user approval for all risky shell commands.
- **Memory & Diffing**: Automatically parses `nmap` results and compares them with history to show changes.
- **Plugin System**: Easily extend the assistant by dropping Python scripts into `~/.assistant/plugins/`.

## User Data
The assistant stores data in `~/.assistant/`:
- `config.yaml`: Your settings.
- `assistant.db`: SQLite database for history, tasks, and scope.
- `logs/`: Application logs.
- `plugins/`: Custom extensions.

