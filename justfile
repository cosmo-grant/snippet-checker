checks:
  uv run ruff check --exclude test/e2e/snippets --fix src test
  uv run ruff format --exclude test/e2e/snippets src test
  uv run ty check --exclude test/e2e/snippets src test

formatter-images:
  ls images/formatters | parallel 'cd images/formatters/{} && docker image build -t snip-{} . && cd -'

runner-images:
  ls images/runners | parallel 'cd images/runners/{} && docker image build -t snip-{} . && cd -'

