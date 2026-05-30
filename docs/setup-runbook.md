# Setup Steps

## Updated Frontend Setup Checklist

1. `npm create vite@latest frontend -- --template vanilla-ts`
2. **`cd frontend`** *(Move into the folder first so all following commands work)*
3. `npm install`
4. `npm install socket.io-client`
5. Clean up boilerplate:

    * Open `frontend/src/main.ts`, select everything, and delete it so you have a blank canvas.
    * Delete `frontend/src/counter.ts` entirely.

6. `npm install --save-dev eslint prettier eslint-config-prettier`  

    * `--save-dev` specifies these are only dev dependencies
    * Look in package.json `"devDependencies": {`
    * When you deploy your frontend to a hosting provider (like Vercel, Netlify, or Render), the build platform will often run an optimized install command: `npm install --omit=dev`

7. Tool configs:
    
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

    * Create `frontend/.eslintrc.json`

    ```json
    {
    "env": {
        "browser": true,
        "es2022": true
    },
    "extends": [
        "eslint:recommended",
        "prettier"
    ],
    "parserOptions": {
        "ecmaVersion": "latest",
        "sourceType": "module"
    },
    "rules": {
        "no-unused-vars": "warn",
        "no-console": "off"
    }
    }
    ```

---

## ## backend

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
# backend/src/backend/main.py
import uvicorn
import socketio
from fastapi import FastAPI, Response

# 1. Create a standard FastAPI application instance
app = FastAPI()

# 2. Set up your Socket.io async server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# 3. Mount Socket.io onto the FastAPI app so they share port 8000
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)

# 4. Catch the pesky favicon request and kill it silently
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
    # Pass the shared asgi_app to uvicorn
    uvicorn.run(asgi_app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    main()

```

6. **Run the server locally to test:**

```bash
uv run python -m backend.main

```

or update pyproject.toml

```ini, toml
[project.scripts]
backend = "backend.main:main"

```

```bash
uv run backend

```

> Adding `reload=True` inside `main.py` means whenever you save changes to your Python files, the server will instantly refresh itself—just like Vite does on the frontend!

```bash
uv run uvicorn backend.main:asgi_app --reload

```


## tools

1. uv tool install pre-commit (from root)
2. tool configs

    -   Create `.pre-commit-config.yaml`

        ```yaml
        # .pre-commit-config.yaml (at the repository root)
        repos:
            # --- PYTHON BACKEND TOOLS ---
            - repo: https://github.com/astral-sh/ruff-pre-commit
                rev: v0.9.0
                hooks:
                - id: ruff         # Python Linter (Catches bugs)
                    files: ^backend/
                - id: ruff-format  # Python Formatter (Replaces Black)
                    files: ^backend/

            # --- TYPESCRIPT FRONTEND TOOLS ---
            - repo: https://github.com/pre-commit/mirrors-prettier
                rev: v3.1.0
                hooks:
                - id: prettier     # Frontend Formatter (HTML/CSS/TS)
                    files: ^frontend/
                    additional_dependencies: ['prettier@3.1.0']

            - repo: https://github.com/pre-commit/mirrors-eslint
                rev: v8.56.0
                hooks:
                - id: eslint       # Frontend Linter (Catches TS bugs)
                    # Bypasses strict leading anchors to ensure cross-platform matching
                    files: frontend/src/.*\.(ts|tsx)$
                    # Tells ESLint to look into the frontend folder for configuration context
                    args: [--config, frontend/.eslintrc.json, --prefix, frontend] 
                    additional_dependencies:
                    - eslint@8.56.0
                    - typescript@5.3.3
                    - "@typescript-eslint/parser@6.14.0"
                    - "@typescript-eslint/eslint-plugin@6.14.0"
                ```
    
    3. pre-commit install
    4. pre-commit run --all-files