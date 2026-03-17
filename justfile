checks:
  uv run ruff check --exclude test/e2e/snippets --fix src test
  uv run ruff format --exclude test/e2e/snippets src test
  uv run mypy --exclude test/e2e/snippets src
