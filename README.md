# gippity

## Quickstart

1. Install dependencies: `pip install -r requirements.txt`
2. Run the linters: `ruff check .`
3. Run the type checker: `mypy src`
4. Run the tests: `pytest -q`
5. Start the web server: `python -m lectio_plus.app --serve`

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

## LLM providers

Offline (default):

```
LLM_PROVIDER not set → FakeLLM
```

Ollama:

```
export LLM_PROVIDER=ollama
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama
export REFLECTION_MODEL=deepseek-r1:14b
export ART_MODEL=mistral:latest
export HTML_MODEL=mistral:latest

python -m lectio_plus.app --serve
```

Tests run entirely offline and do not require network access.  The
`LLM_PROVIDER`, `OPENAI_BASE_URL` and `OPENAI_API_KEY` variables are optional
and only needed when experimenting with Ollama.
