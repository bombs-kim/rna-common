# Steps Version 0.2

Interactive code generation and debugging tool with LLM integration.

## Quick Start

1. Start the backend:
   ```bash
   ./run_backend.sh
   ```

2. Start the frontend:
   ```bash
   ./run_frontend.sh
   ```

3. Open `http://localhost:5173` in your browser.

## Requirements

- Python >= 3.12
- `uv` package manager
- OpenAI API key and Cursor API key (configure in `backend/.env`)

See `backend/README.md` for detailed setup instructions.

### Pre-commit hooks

Config is at `.pre-commit-config.yaml`. From the repo root run `pre-commit install` to install the hook.
