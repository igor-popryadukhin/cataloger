from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from catalog_cli.config import SETTINGS
from catalog_cli.io_excel.reader import ExcelFormatError, read_input_pairs
from catalog_cli.io_excel.writer import write_paths_excel
from catalog_cli.llm.client import (
    DeepSeekAuthError,
    DeepSeekClient,
    DeepSeekError,
    DeepSeekTransientError,
)
from catalog_cli.logging.setup import LOGGER
from catalog_cli.prompting.prompt_builder import build_prompt
from catalog_cli.prompting.parser import ParsedResponse, parse_response
from catalog_cli.state.database import Item, StateStore
from catalog_cli.tui.progress import ProgressDisplay


class RateLimiter:
    def __init__(self, rate_per_second: float) -> None:
        self.rate = max(rate_per_second, 0.01)
        self._lock = asyncio.Lock()
        self._next_time = time.monotonic()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if self._next_time > now:
                await asyncio.sleep(self._next_time - now)
            interval = 1.0 / self.rate
            self._next_time = max(now, self._next_time) + interval


@dataclass(slots=True)
class ProcessorConfig:
    concurrency: int
    rps: float
    max_attempts: int = 5
    min_valid_paths: int = 3


class CatalogProcessor:
    def __init__(self, store: StateStore, config: ProcessorConfig, no_tui: bool = False) -> None:
        self.store = store
        self.config = config
        self.rate_limiter = RateLimiter(config.rps)
        self.no_tui = no_tui

    async def prepare(self, pairs: Iterable[tuple[str, str]]) -> int:
        await self.store.reset_running()
        await self.store.upsert_items(pairs)
        stats = await self.store.stats()
        return sum(stats.values())

    async def run(self) -> None:
        await self.store.reset_running()
        total_stats = await self.store.stats()
        total = sum(total_stats.values())
        progress = ProgressDisplay(enabled=not self.no_tui)
        progress.set_total(total)
        async with progress:
            await progress.sync_stats(total_stats)
            async with DeepSeekClient() as client:
                workers = [
                    asyncio.create_task(self._worker(client, progress))
                    for _ in range(max(1, self.config.concurrency))
                ]
                await asyncio.gather(*workers)

    async def _worker(self, client: DeepSeekClient, progress: ProgressDisplay) -> None:
        while True:
            item = await self.store.fetch_next_pending()
            if item is None:
                break
            try:
                await self._process_item(item, client, progress)
            except DeepSeekAuthError as exc:
                LOGGER.error("Authentication error", extra={"error": str(exc)})
                await self.store.update_status(item.id, status="FAILED_GIVEUP", last_error=str(exc))
                await progress.advance("FAILED_GIVEUP")
                await progress.sync_stats(await self.store.stats())
                break
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.exception("Unexpected error", extra={"item_id": item.id, "error": str(exc)})
                await self.store.update_status(item.id, status="FAILED_GIVEUP", last_error=str(exc))
                await progress.advance("FAILED_GIVEUP")
                await progress.sync_stats(await self.store.stats())

    async def _process_item(
        self,
        item: Item,
        client: DeepSeekClient,
        progress: ProgressDisplay,
    ) -> None:
        sphere = item.sphere
        subsphere = item.subsphere
        prompt = build_prompt(sphere, subsphere)
        attempt = item.retries + 1
        LOGGER.info(
            "Processing item",
            extra={"item_id": item.id, "sphere": sphere, "subsphere": subsphere, "attempt": attempt},
        )
        try:
            await self.rate_limiter.acquire()
            response_text = await client.generate(prompt)
            parsed = parse_response(sphere, response_text)
            self._validate_paths(parsed)
            await self._write_outputs(sphere, subsphere, parsed)
        except DeepSeekAuthError:
            raise
        except DeepSeekTransientError as exc:
            await self._handle_retry(item, str(exc), progress)
            return
        except (DeepSeekError, ValueError) as exc:
            await self._handle_retry(item, str(exc), progress)
            return

        await self.store.update_status(item.id, status="DONE", retries=attempt, last_error=None)
        await progress.advance("DONE")
        await progress.sync_stats(await self.store.stats())
        LOGGER.info("Item completed", extra={"item_id": item.id})

    async def _write_outputs(self, sphere: str, subsphere: str, parsed: ParsedResponse) -> None:
        filename = self._build_filename(sphere, subsphere)
        excel_path = SETTINGS.output_dir / f"{filename}.xlsx"
        json_path = SETTINGS.artifacts_dir / f"{filename}.json"
        write_paths_excel(excel_path, parsed.normalized_paths)
        json_path.write_text(
            json.dumps(
                {
                    "sphere": sphere,
                    "subsphere": subsphere,
                    "raw_lines": parsed.raw_lines,
                    "paths": parsed.normalized_paths,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    async def _handle_retry(self, item: Item, message: str, progress: ProgressDisplay) -> None:
        new_attempt = item.retries + 1
        status = "FAILED_RETRYING" if new_attempt < self.config.max_attempts else "FAILED_GIVEUP"
        await self.store.update_status(item.id, status=status, retries=new_attempt, last_error=message)
        await progress.advance(status)
        await progress.sync_stats(await self.store.stats())
        LOGGER.warning(
            "Item failed",
            extra={
                "item_id": item.id,
                "attempt": new_attempt,
                "status": status,
                "error": message,
            },
        )

    def _validate_paths(self, parsed: ParsedResponse) -> None:
        if len(parsed.normalized_paths) < self.config.min_valid_paths:
            raise ValueError("Not enough valid paths returned by DeepSeek API")

    @staticmethod
    def _build_filename(sphere: str, subsphere: str) -> str:
        def sanitize(part: str) -> str:
            part = re.sub(r"[^\w]+", "_", part.strip())
            return part.strip("_") or "item"

        return f"{sanitize(sphere)}_{sanitize(subsphere)}"


async def prepare_run(input_path: Path, concurrency: Optional[int], rps: Optional[float], no_tui: bool) -> None:
    try:
        pairs = read_input_pairs(input_path)
    except FileNotFoundError as exc:
        LOGGER.error("Input file not found", extra={"path": str(input_path)})
        raise SystemExit(10) from exc
    except ExcelFormatError as exc:
        LOGGER.error("Excel format error", extra={"error": str(exc)})
        raise SystemExit(20) from exc

    store = StateStore()
    processor = CatalogProcessor(
        store,
        ProcessorConfig(
            concurrency=concurrency or SETTINGS.concurrency,
            rps=rps or SETTINGS.rps,
        ),
        no_tui=no_tui,
    )
    total = await processor.prepare(pairs)
    LOGGER.info("Starting run", extra={"total_items": total})
    try:
        await processor.run()
    except DeepSeekAuthError as exc:
        LOGGER.error("DeepSeek authentication failed", extra={"error": str(exc)})
        raise SystemExit(30) from exc
    except (OSError, IOError) as exc:
        LOGGER.error("Output write error", extra={"error": str(exc)})
        raise SystemExit(40) from exc


async def resume_run(no_tui: bool) -> None:
    store = StateStore()
    processor = CatalogProcessor(
        store,
        ProcessorConfig(
            concurrency=SETTINGS.concurrency,
            rps=SETTINGS.rps,
        ),
        no_tui=no_tui,
    )
    try:
        await processor.run()
    except DeepSeekAuthError as exc:
        LOGGER.error("DeepSeek authentication failed", extra={"error": str(exc)})
        raise SystemExit(30) from exc
    except (OSError, IOError) as exc:
        LOGGER.error("Output write error", extra={"error": str(exc)})
        raise SystemExit(40) from exc


async def validate_input(input_path: Path) -> int:
    try:
        pairs = read_input_pairs(input_path)
    except FileNotFoundError as exc:
        LOGGER.error("Input file not found", extra={"path": str(input_path)})
        raise SystemExit(10) from exc
    except ExcelFormatError as exc:
        LOGGER.error("Excel format error", extra={"error": str(exc)})
        raise SystemExit(20) from exc
    LOGGER.info("Validated input", extra={"rows": len(pairs)})
    return len(pairs)


async def inspect_item(item_id: str) -> Optional[Item]:
    store = StateStore()
    item = await store.get_item(item_id)
    if item is None:
        LOGGER.error("Item not found", extra={"item_id": item_id})
    else:
        LOGGER.info(
            "Item inspected",
            extra={
                "item_id": item.id,
                "sphere": item.sphere,
                "subsphere": item.subsphere,
                "status": item.status,
                "retries": item.retries,
                "last_error": item.last_error,
            },
        )
    return item
