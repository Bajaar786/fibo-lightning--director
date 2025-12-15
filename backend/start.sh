#!/bin/bash
# Render startup script
echo "Starting FIBO Lightning Director API..."
uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1