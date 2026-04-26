#!/bin/bash
export PYTHONPATH=$PYTHONPATH:.
pytest tests/ "$@"
