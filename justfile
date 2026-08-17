checks:
  uv run ruff check --exclude test/e2e/snippets --fix src test
  uv run ruff format --exclude test/e2e/snippets src test
  uv run ty check --exclude test/e2e/snippets src test

images:
  ls Dockerfiles/formatters | parallel 'cd Dockerfiles/formatters/{} && docker image build -t test-{} . && cd -'
