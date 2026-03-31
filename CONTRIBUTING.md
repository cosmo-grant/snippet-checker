# CONTRIBUTING

All these commands assume you're at the project root.

Install requirements:

```
uv sync
```

Install the package (editable):

```
uv tool install -e .
```

Run checks:

```
just checks
```

Run the unit tests:

```
pytest test/unit
```

Run all tests (slow, and requires docker, an internet connection, docker hub, ...):

```
pytest
```

Check test coverage:

```
coverage run -m pytest
coverage report
```

Release a version:

```
uv build
git tag vX.Y.Z
git push --tags
uv publish --token "$TOKEN"
```
