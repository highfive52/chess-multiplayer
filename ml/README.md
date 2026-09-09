# ML environment setup

Use `uv` to create and manage the local Python environment for the eventual ML inference model and the notebooks.

1. Pin the project to Python 3.12 so everyone uses the same interpreter:

```bash
cd ml
uv python pin 3.12
uv init
```

2. Sync the environment from the project config so `uv` creates the virtual environment and installs the project dependencies:

```bash
uv sync
uv add ipykernel
```

3. Register the environment as a Jupyter kernel so the notebooks can use it directly:

```bash
uv run python -m ipykernel install --user \
    --name chess-ml \
    --display-name "Chess ML"
```

After this, open the notebooks and select the `Chess ML` kernel.

## Running the tests

Run the ML test suite from the `ml` directory with `uv`:

```bash
cd ml
uv run pytest
```

To run a specific test file, pass the path directly:

```bash
uv run pytest tests/test_dataset.py
```

You can also run a focused subset with a test name filter:

```bash
uv run pytest -k training_data
```
