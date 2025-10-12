from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(key)
    if value is not None:
        return value
    return default


@dataclass(slots=True)
class Settings:
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    timeout: float = 60.0
    rps: float = 1.0
    concurrency: int = 1
    output_dir: Path = Path("out")
    artifacts_dir: Path = Path("artifacts/json")
    state_db: Path = Path("state/catalog_state.db")
    log_dir: Path = Path("logs")

    @classmethod
    def load(cls) -> "Settings":
        defaults = cls()
        deepseek_base_url = _env("DEEPSEEK_BASE_URL", defaults.deepseek_base_url)
        deepseek_api_key = _env("DEEPSEEK_API_KEY", defaults.deepseek_api_key)
        deepseek_model = _env("DEEPSEEK_MODEL", defaults.deepseek_model)
        timeout = float(_env("TIMEOUT", str(defaults.timeout)))
        rps = float(_env("RPS", str(defaults.rps)))
        concurrency = int(_env("CONCURRENCY", str(defaults.concurrency)))
        output_dir = Path(_env("OUTPUT_DIR", str(defaults.output_dir)))
        artifacts_dir = Path(_env("ARTIFACTS_DIR", str(defaults.artifacts_dir)))
        state_db = Path(_env("STATE_DB", str(defaults.state_db)))
        log_dir = Path(_env("LOG_DIR", str(defaults.log_dir)))

        settings = cls(
            deepseek_base_url=deepseek_base_url,
            deepseek_api_key=deepseek_api_key,
            deepseek_model=deepseek_model,
            timeout=timeout,
            rps=rps,
            concurrency=concurrency,
            output_dir=output_dir,
            artifacts_dir=artifacts_dir,
            state_db=state_db,
            log_dir=log_dir,
        )
        settings.ensure_directories()
        return settings

    def ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.state_db.parent.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


SETTINGS = Settings.load()
