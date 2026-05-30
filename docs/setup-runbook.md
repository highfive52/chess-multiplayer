# Setup Steps

## Updated Frontend Setup Checklist

1. `npm create vite@latest frontend -- --template vanilla-ts`
2. **`cd frontend`** *(Move into the folder first so all following commands work)*
3. `npm install`
4. `npm install socket.io-client`
5. Clean up boilerplate:
* Open `frontend/src/main.ts`, select everything, and delete it so you have a blank canvas.
* Delete `frontend/src/counter.ts` entirely.


6. `npm install --save-dev eslint prettier eslint-config-prettier typescript-eslint @eslint/js`
* `--save-dev` specifies these are only dev dependencies.
* `typescript-eslint` and `@eslint/js` are required for the new ESLint Flat Config engine.


7. Update `frontend/package.json` to include the explicit lint execution script:
```json
"scripts": {
  "dev": "vite",
  "build": "tsc && vite build",
  "lint": "eslint .",
  "preview": "vite preview"
}

```


8. Tool configs:
* Create `frontend/.prettierrc`


```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2
}

```


* Create `frontend/eslint.config.js` *(Note the new file extension and modular layout)*


```javascript
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        browser: true,
      },
    },
    rules: {
      "no-unused-vars": "warn",
      "no-console": "off",
      "@typescript-eslint/no-unused-vars": ["warn"],
    },
  },
);

```



---

## Backend Setup Checklist

1. **Navigate to the backend directory:**
```bash
# From your repository root:
mkdir backend
cd backend

```


2. **Initialize the Python project using `uv`:**
```bash
uv init --app --package --python 3.12

```


> This automatically generates a modern `pyproject.toml`, a virtual environment, and a boilerplate script.


3. **Add the backend dependencies:**
```bash
uv add fastapi uvicorn python-socketio

```


> This instantly downloads and installs the server components and updates your `pyproject.toml`.


4. **Add the testing dependencies (as development packages):**
```bash
uv add --dev pytest httpx

```


> `httpx` allows `pytest` to make asynchronous testing requests to your FastAPI application.


5. **Overwrite `backend/main.py` with your server code:**
```python
import uvicorn
import socketio
from fastapi import FastAPI, Response

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

def main():
    uvicorn.run(asgi_app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()

```

6. **Create a backend smoke test file:**
* Create a file at `backend/tests/test_smoke.py`:

```python
def test_backend_health():
    """Sanity check to verify the testing orchestrator executes cleanly."""
    assert True

```

> Keeping an explicit smoke test guarantees your CI test environment won't exit with error code 5 due to an empty test suite.

7. **Run the server locally to test:**
```bash
uv run python -m backend.main

```

Or update `pyproject.toml`:
```toml
[project.scripts]
backend = "backend.main:main"

```


```bash
uv run backend

```

To enable hot-reloading during development:
```bash
uv run uvicorn backend.main:asgi_app --reload

```

---

## Local Pre-commit Tools Setup

1. `uv tool install pre-commit` (from repo root)
2. Create `.pre-commit-config.yaml` at the repository root:
```yaml
repos:
  # --- PYTHON BACKEND TOOLS ---
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff         # Python Linter
        files: ^backend/
      - id: ruff-format  # Python Formatter
        files: ^backend/

  # --- TYPESCRIPT FRONTEND TOOLS ---
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier     # Frontend Formatter
        files: ^frontend/
        additional_dependencies: ['prettier@3.1.0']

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v10.4.1
    hooks:
      - id: eslint       # Frontend Flat-Config Linter
        files: ^frontend/
        # Point directly to the new flat config file and context prefix
        args: [--config, frontend/eslint.config.js, --prefix, frontend]
        additional_dependencies:
          - eslint@10.4.1
          - typescript@6.0.2
          - typescript-eslint@8.24.0
          - "@eslint/js@10.4.1"

```

3. `pre-commit install`
4. `pre-commit run --all-files`

---

## Root Orchestration Setup (Unified Dev Environment)

To run both the FastAPI backend and the Vite frontend simultaneously with a single terminal command, install and configure `concurrently` at the repository root.

1. **Navigate to your repository root:**
```bash
cd /path/to/chess-multiplayer

```

2. **Initialize a root `package.json` (if you haven't already):**
```bash
npm init -y

```

3. **Install `concurrently` as a root development dependency:**
```bash
npm install --save-dev concurrently

```

4. **Configure the unified execution scripts:**
Open your root **`package.json`** file and modify the `"scripts"` section to map the dual-stack development commands:
```json
{
  "name": "chess-multiplayer",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "dev": "concurrently \"uv run --directory backend uvicorn backend.main:asgi_app --reload\" \"npm run dev --prefix frontend\"",
    "lint": "concurrently \"uv run --directory backend ruff check backend/\" \"npm run lint --prefix frontend\"",
    "format:check": "concurrently \"uv run --directory backend ruff format --check backend/\" \"npm run --prefix frontend npx prettier --check .\""
  },
  "devDependencies": {
    "concurrently": "^10.0.1"
  }
}

```

5. **Launch the entire local application:**
From the repository root, run the following command to spin up the hot-reloading backend server and the Vite frontend dev server at the exact same time:
```bash
npm run dev

```

> `concurrently` will spin up both processes in a single terminal session, prefixing the console logs with different colors so you can easily trace frontend asset compiling and backend WebSocket traffic simultaneously. Splitting the session or shutting down the terminal will cleanly terminate both servers at once.

> **Tip:** You can also run `npm run lint` from the root to run your Python and TypeScript linters side-by-side locally before pushing your code to GitHub. Typing `Ctrl + C` in your terminal will cleanly terminate both the frontend and backend servers together.

