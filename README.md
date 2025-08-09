# gippity

## Quickstart

1. Install dependencies: `pip install -r requirements.txt`
2. Run the linters: `ruff check .`
3. Run the type checker: `mypy src`
4. Run the tests: `pytest -q`

## Package layout

```
src/
└── lectio_plus/
    ├── __init__.py
    ├── app.py
    ├── cache.py
    ├── curator.py
    ├── html_build.py
    ├── parse.py
    ├── prompts.py
    └── scrape.py
```
