checks:
  uv run ruff check --fix src test
  uv run ruff format src test
  uv run mypy src
