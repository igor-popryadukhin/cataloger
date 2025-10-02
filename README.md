# Catalog CLI

Catalog CLI is a Python 3.11+ command-line tool that generates deep hierarchical catalogs of services and categories by querying the DeepSeek Chat Completions API. It accepts an Excel workbook with high-level business spheres/sub-spheres and produces detailed tree-like taxonomies optimised for SEO keywords. The tool is resilient to failures, supports resumable processing, and provides a Rich-based terminal UI with progress indicators and a robot animation.

## Features

- 📁 Reads input rows from Excel (columns **A** = sphere, **B** = sub-sphere).
- 🤖 Builds prompts and queries the DeepSeek `/v1/chat/completions` endpoint with retries and rate limiting.
- 🗂️ Normalises and validates hierarchical `A/B/C/...` paths, writes per-row Excel outputs and JSON artifacts.
- 💾 Persists processing state in SQLite so executions can be resumed after interruptions.
- 🧭 Structured logging with JSON events written to disk.
- 🖥️ Interactive TUI progress display (can be disabled with `--no-tui`).
- 🐳 First-class Docker support for isolated execution.

## Requirements

- Python 3.11+
- Access to the DeepSeek API and a valid API key.
- The dependencies listed in [`requirements.txt`](requirements.txt).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Alternatively, install the project in editable mode:

```bash
pip install -e .
```

## Configuration

Runtime configuration is controlled through environment variables. Create an `.env` file or export the variables directly:

| Variable | Description | Default |
| --- | --- | --- |
| `DEEPSEEK_BASE_URL` | DeepSeek API base URL | `https://api.deepseek.com/v1` |
| `DEEPSEEK_API_KEY` | DeepSeek API key | **required** |
| `DEEPSEEK_MODEL` | Model name passed to API | `deepseek-chat` |
| `TIMEOUT` | HTTP request timeout (seconds) | `60` |
| `RPS` | Requests per second throttle | `1` |
| `CONCURRENCY` | Max concurrent DeepSeek calls | `1` |
| `OUTPUT_DIR` | Directory for generated Excel files | `./out` |
| `ARTIFACTS_DIR` | Directory for JSON artifacts | `./artifacts` |
| `STATE_DB` | Path to SQLite state database | `./state/catalog.db` |
| `LOG_DIR` | Directory for structured log files | `./logs` |

Ensure all output directories exist or allow the CLI to create them at runtime.

## Usage

After installation and configuration, run the CLI via the `catalog-cli` entry point.

### Run a new batch

```bash
catalog-cli run input/source.xlsx --concurrency 3 --rps 2
```

- Reads the input workbook, queues each `<A>:<B>` row, and starts processing.
- Generates Excel files in `OUTPUT_DIR` and JSON artifacts in `ARTIFACTS_DIR`.
- Displays a Rich TUI with progress, live logs, and robot animation (omit `--no-tui` to disable).

### Resume an interrupted batch

```bash
catalog-cli resume
```

- Continues unfinished items tracked in the SQLite state database.
- Automatically resets stale `RUNNING` jobs back to `PENDING` before resuming.

### Validate an input workbook

```bash
catalog-cli validate input/source.xlsx
```

- Checks that the Excel file contains the expected schema and prepares rows without invoking the API.

### Inspect an item

```bash
catalog-cli inspect --item-id <uuid>
```

- Displays stored metadata, retries, and artifacts for a particular queue item.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success (even with recorded failures) |
| `10` | Missing input file |
| `20` | Invalid Excel format |
| `30` | DeepSeek API error (auth, etc.) |
| `40` | Output write failure |

## Output Artifacts

- `out/<A>_<B>.xlsx` — Excel workbook containing a `Paths` sheet with validated `A/...` entries starting at row 2.
- `artifacts/json/<A>_<B>.json` — JSON document containing raw and normalised model responses.
- `logs/app.log` — JSON structured logs of processing events.

## Testing

Run the unit and integration tests with:

```bash
pytest -q
```

## Docker Usage

Build the Docker image:

```bash
docker build -t catalog-cli:latest .
```

Execute the CLI inside a container with appropriate volumes and environment variables:

```bash
docker run --rm \
  -e DEEPSEEK_BASE_URL=https://api.deepseek.com/v1 \
  -e DEEPSEEK_API_KEY="sk-***" \
  -e DEEPSEEK_MODEL=deepseek-chat \
  -v "$(pwd)/input":/app/input:ro \
  -v "$(pwd)/out":/app/out \
  -v "$(pwd)/artifacts":/app/artifacts \
  -v "$(pwd)/state":/app/state \
  -v "$(pwd)/logs":/app/logs \
  catalog-cli:latest run /app/input/source.xlsx --concurrency 3 --rps 2
```

## Troubleshooting

- Ensure your DeepSeek API key is valid and has sufficient quota. 429 or 5xx responses trigger automatic retries (up to 5 attempts).
- If processing stops unexpectedly, rerun `catalog-cli resume` to continue from the last checkpoint.
- Use `catalog-cli inspect --item-id <uuid>` to examine failures and raw responses for debugging.

## License

This project is licensed under the [MIT License](LICENSE).
