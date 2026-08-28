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

Build runner images:

```
just runner-images
```

Build formatter images:

```
just formatter-images
```

Run all tests (slow, and requires images, docker, an internet connection, docker hub, ...):

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
# update version in pyproject.toml
uv sync
# commit changes
uv build --clear
git tag vX.Y.Z
git push --tags
uv publish --token "$TOKEN"
```
