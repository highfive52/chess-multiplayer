# Setup Steps

## Updated Frontend Setup Checklist

1. `npm create vite@latest frontend -- --template vanilla-ts`
2. **`cd frontend`** *(Move into the folder first so all following commands work)*
3. `npm install`
4. `npm install socket.io-client`
5. Clean up boilerplate (optional):
   - Open `frontend/src/main.ts` and replace with your application boot code.
   - Remove unused example files such as `frontend/src/counter.ts` if present.

6. Install frontend dev tools:

```bash
npm install --save-dev eslint prettier eslint-config-prettier typescript-eslint @eslint/js typescript
```

7. Update `frontend/package.json` to run lint only against your source directory:

```json
"scripts": {
  "dev": "vite",
  "build": "tsc && vite build",
  "lint": "eslint src",
  "preview": "vite preview"
}
```

8. Tool configs:
- Create `frontend/.prettierrc` with your formatting preferences:

```json
{
  "semi": true,
  "singleQuote": false,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2
}
```

- Use an ESLint flat config file. Create `frontend/eslint.config.cjs` and include an `ignores` entry to prevent linting built assets (`.eslintignore` is deprecated):

```javascript
module.exports = {
  ignores: ['dist/**', '.cache/**', 'node_modules/**'],
  languageOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    globals: { browser: true },
  },
  // example ruleset (adjust to taste)
  rules: {
    'no-unused-vars': 'warn',
    'no-console': 'off',
  },
};
```

Notes:
- We limit ESLint to `src` in `package.json` to avoid scanning `dist` files produced by the build.
- If you previously used a `.eslintignore`, prefer moving those patterns to the `ignores` array in `eslint.config.cjs`.

---

## Backend Setup Checklist

1. **Create and activate a venv (recommended):**

```powershell
# From repository root
python -m venv backend\.venv
.\backend\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

2. **If you scaffolded with `uv`, you may already have a pyproject and venv.**
   - `uv` is a helpful toolchain, but `concurrently` (npm) does not activate venvs automatically.

3. **Install backend dependencies (if not already present):**

```powershell
pip install fastapi uvicorn python-socketio
```

4. **Run the backend for development:**

- With the venv activated:

```powershell
python -m uvicorn backend.main:asgi_app --reload --port 8000
```

- Or call the venv Python explicitly (useful when orchestrating from the repo root):

```powershell
backend\.venv\Scripts\python -m uvicorn backend.main:asgi_app --reload --port 8000
```

Notes:
- Calling the venv's python (explicit path) in scripts allows `concurrently` to run the backend without activating the venv first.
- You can also use `uv` if you prefer and have it on PATH, but be aware `concurrently` won't activate a venv for you.

---

## Local Pre-commit Tools Setup

1. Ensure `pre-commit` is available (we use the `pre-commit` toolchain). If you used `uv`'s tooling, it may provide helpers; otherwise install pre-commit normally:

```bash
pip install pre-commit
```

2. Create `.pre-commit-config.yaml` at the repository root (examples already in repo). After creating or updating it:

```bash
pre-commit install
pre-commit run --all-files
```

Notes:
- The repo's pre-commit configuration runs Python checks (ruff) and frontend formatters (prettier) and lints. We intentionally configure the frontend lint to point only at `frontend/src` to avoid linting compiled assets.

---

## Root Orchestration Setup (Unified Dev Environment)

To run Redis, the FastAPI backend and the Vite frontend together you can use `concurrently` at the repository root. The dev script in this repo explicitly calls the backend venv Python so the backend runs with the correct environment even when `concurrently` spawns the process.

Example root `package.json` `dev` script used in this project:

```json
"dev": "concurrently --kill-others -n \"redis,backend,frontend\" -c \"bgRed,bgBlue,bgGreen\" \"docker run --rm --name chess-redis -p 6379:6379 redis:alpine\" \"backend\\.venv\\Scripts\\python -m uvicorn backend.main:asgi_app --reload --port 8000\" \"npm run dev --prefix frontend\""
```

Notes and tips:
- If a previous `chess-redis` container exists you must remove it before running the script:

```powershell
docker rm -f chess-redis
```

- Alternatively you can run the three pieces in separate terminals while developing:
  - Terminal A (backend): activate venv and run `python -m uvicorn ...`
  - Terminal B (redis): `docker run --rm --name chess-redis -p 6379:6379 redis:alpine`
  - Terminal C (frontend): `npm --prefix frontend run dev`

- `concurrently` will prefix console logs and terminate all child processes on Ctrl+C.

---

If you'd like, I can also:
- Commit the updated runbook, or
- Add a short example `Makefile` or PowerShell script to standardize dev startup on Windows/macOS.
