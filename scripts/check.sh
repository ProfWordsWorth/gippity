#!/usr/bin/env bash
set -euo pipefail

# Ensure we run from the repository root
cd "$(dirname "$0")/.."

# Unset provider environment variables to force offline mode
env_vars=(LLM_PROVIDER OPENAI_BASE_URL OPENAI_API_KEY REFLECTION_MODEL ART_MODEL HTML_MODEL)
for var in "${env_vars[@]}"; do
  unset "$var" || true
done

python -m ruff check .
python -m mypy src
python -m pytest -q
