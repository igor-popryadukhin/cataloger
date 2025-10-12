# Repository Guidelines

## Agent Instructions
- Всегда отвечай на русском языке, сохраняя профессиональный тон технического помощника.
- Контекст проекта: Catalog CLI — это инструмент командной строки на Python 3.11+, который по Excel-файлу с высокоуровневыми бизнес-сферами создаёт глубокие иерархические каталоги услуг и категорий, оптимизированные под SEO-ключевые слова, используя DeepSeek Chat Completions API. Инструмент устойчив к сбоям, поддерживает возобновляемую обработку и предлагает интерфейс на базе Rich с индикаторами прогресса и анимацией робота.

## Project Structure & Module Organization
- `catalog_cli/` houses the Typer CLI in `cli/app.py`, the async orchestrator in `processor.py`, and domain subpackages `io_excel`, `llm`, `prompting`, `state`, `tui`, and `logging`.
- `tests/` holds the pytest suite; runtime directories (`input/`, `out/`, `artifacts/`, `logs/`, `state/`) are git-ignored yet created automatically when the CLI runs.
- `pyproject.toml` defines entry points and dependencies; `.env` carries DeepSeek settings; `Dockerfile` mirrors the local layout for containerized execution.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` then `pip install -e .` expose the editable `catalog-cli` entry point.
- `catalog-cli run input/source.xlsx --concurrency 3 --rps 2` executes a batch (`--no-tui` suits CI); `catalog-cli resume` and `catalog-cli validate input/source.xlsx` cover restarts and dry runs.
- `pytest -q` runs the suite; `pytest -k parser -vv` narrows scope; `docker build -t catalog-cli:latest .` plus a `docker run` mounting `input`, `out`, `artifacts`, `state`, `logs` isolates execution.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and snake_case names; constants stay UPPER_SNAKE_CASE.
- Maintain type hints and dataclasses as in `catalog_cli/processor.py`; keep orchestration async-friendly and side-effectful code near CLI boundaries.
- Use `catalog_cli.logging.setup.LOGGER` with structured `extra` payloads instead of ad-hoc prints.

## Testing Guidelines
- Name tests `test_<behavior>` like `tests/test_parser.py`; prioritize realistic DeepSeek payloads and normalization logic.
- Mock external clients so `pytest -q` stays offline; assert on state transitions, retries, and generated artifacts.
- Keep fixtures UTF-8 aware to mirror Cyrillic-heavy examples and ensure idempotent filesystem writes.

## Commit & Pull Request Guidelines
- Adopt Conventional Commit prefixes (`feat:`, `fix:`, `refactor:`) matching the existing `refactor: gitignore update` history.
- Scope each commit to a single concern and note configuration or schema changes in the body.
- PRs should include run commands (`pytest -q`, sample `catalog-cli run`), linked issues, and screenshots only when TUI output changes.

## Security & Configuration Tips
- Store DeepSeek secrets in `.env` or runtime environment variables; never commit populated `.env` files or generated artifacts.
- Tune throttling flags (`--rps`, `--concurrency`) conservatively to respect API quotas; when containerized, mount only the required directories with minimal permissions.
