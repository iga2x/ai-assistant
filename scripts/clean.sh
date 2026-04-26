#!/bin/bash
# Clean script for AI Assistant

echo "Cleaning AI Assistant environment..."

# Remove virtual environment
if [ -d ".venv" ]; then
    echo "Removing .venv..."
    rm -rf .venv
fi

# Remove build artifacts
echo "Removing build artifacts..."
rm -rf build/ dist/ *.egg-info/

# Remove local user data (optional, but good for total reset)
if [ -d ".assistant" ]; then
    echo "Removing local user data (.assistant)..."
    rm -rf .assistant
fi

# Reset system-wide user data
# rm -rf ~/.assistant

echo "Clean complete."
