#!/bin/bash
# Developer installation script

echo "Starting Developer Install for AI Assistant..."

# 1. Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# 2. Upgrade pip
echo "Upgrading pip..."
./.venv/bin/pip install --upgrade pip

# 3. Install in editable mode with dev dependencies
echo "Installing assistant in editable mode..."
./.venv/bin/pip install -e ".[dev]"

# 4. Initialize assistant
echo "Initializing assistant configuration..."
./.venv/bin/python -m assistant.main init

# 5. Run health check
echo "Running doctor check..."
./.venv/bin/python -m assistant.main doctor

echo "----------------------------------------"
echo "Installation complete!"
echo "Run 'source .venv/bin/activate' to start."
echo "Then use 'assistant' to begin."
