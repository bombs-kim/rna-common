# Backend Server

A FastAPI-based backend server for interactive code debugging and generation using LLM.

## Features

- **Interactive Debugging**: Step-by-step code debugging via WebSocket
- **Code Generation**: Generate Python code from natural language requests using LLM
- **Code Editing**: Edit existing code with context-aware suggestions
- **Project Management**: Manage multiple code projects with persistent storage

## Requirements

- Python >= 3.12
- `uv` package manager
- OpenAI API key
- Cursor API key

## Installation

1. Install dependencies using `uv`:
```bash
uv sync --all-extras  # include dev depdencies
```

2. Create a `.env` file in the `backend` directory:
```env
DEBUG=False
OPENAI_API_KEY=your_openai_api_key
CURSOR_API_KEY=your_cursor_api_key
```

## Running the Server

### Using the run script (recommended):
```bash
../run_backend.sh
```

### Or manually:
```bash
cd backend
uv run python main.py
```

The server will start on `http://0.0.0.0:8000` by default.

## API Endpoints

### Projects

- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project details and code
- `GET /api/projects/{project_id}/code` - Get code for a project
- `POST /api/projects/{project_id}/code` - Generate and save new code
- `POST /api/projects/{project_id}/code/edit` - Edit existing code

### WebSocket Debugging

- `WS /ws/debug` - WebSocket endpoint for interactive debugging

#### WebSocket Message Types

- `start_session`: Start a new debugging session with code
- `step_over`: Step over the current line
- `step_into`: Step into the current line
- `step_out`: Step out of the current function
- `reset`: Reset the debugging session

## Project Structure

```
backend/
├── main.py                     # Entry point (uvicorn)
├── resource_based_modules/     # Domain modules: ORM models, CRUD, schemas per resource
├── server/                     # FastAPI app: http + ws
├── steps_project_engine/       # Steps project engine module
├── utils/                      # Utility functions
└── settings.py                 # Configuration management
```

## Development

### Adding Dependencies

```bash
# Add a production dependency
uv add package-name

# Add a development dependency
uv add --dev package-name
```
