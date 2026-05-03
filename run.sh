#!/bin/bash
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
export PYTHONPATH=$PYTHONPATH:.
python3 -m assistant.main "$@"
