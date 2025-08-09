# gippity

## Quickstart

Run the static checks and test suite:

```
ruff .
mypy src
pytest -q
```

## Package layout

```
src/lectio_plus/
    __init__.py
    app.py
    scrape.py
    parse.py
    prompts.py
    curator.py
    html_build.py
    cache.py
```

Additional tests live in `tests/` and sample HTML fixtures are in
`fixtures/`.
