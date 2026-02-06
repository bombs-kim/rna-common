#!/bin/bash

echo "Starting backend server with auto-reload..."
cd backend
uv run uvicorn main:app --reload
