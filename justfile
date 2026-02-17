checks:
  uv run ruff check --fix src
  uv run ruff format src
  uv run mypy src
