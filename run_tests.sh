#!/bin/bash

# Run tests for the Aegis Guardrail service

echo "Running Aegis Guardrail tests..."

# Set environment variables for testing
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export REDIS_HOST=localhost
export REDIS_PORT=6379
export LOG_LEVEL=WARNING

# Run unit tests
echo "Running unit tests..."
python -m pytest tests/test_policy_engine.py -v

# Run API tests
echo "Running API tests..."
python -m pytest tests/test_api.py -v

echo "Tests completed!"
