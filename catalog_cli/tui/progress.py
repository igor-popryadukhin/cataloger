from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict

from rich.align import Align
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.table import Table


ROBOT_FRAMES = [
    r"[bold cyan] {^_^} ",
    r"[bold cyan] {^o^} ",
    r"[bold cyan] {^_^} ",
    r"[bold cyan] {^_^}/",
    r"[bold cyan] \{^_^} ",
]


@dataclass
class ProgressDisplay:
    enabled: bool = True
    total: int = 0
    stats: Dict[str, int] = field(default_factory=dict)
    progress: Progress | None = field(init=False, default=None)
    task_id: TaskID | None = field(init=False, default=None)
    live: Live | None = field(init=False, default=None)
    _frame: int = field(init=False, default=0)
    _animate_task: asyncio.Task | None = field(init=False, default=None)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    async def __aenter__(self) -> "ProgressDisplay":
        if not self.enabled:
            return self
        self.progress = Progress(transient=False)
        self.task_id = self.progress.add_task("Processing", total=self.total)
        self.live = Live(self._render(), refresh_per_second=4)
        self.live.__enter__()
        self._animate_task = asyncio.create_task(self._animate())
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if not self.enabled:
            return
        if self._animate_task:
            self._animate_task.cancel()
            try:
                await self._animate_task
            except asyncio.CancelledError:
                pass
        if self.live:
            self.live.__exit__(exc_type, exc, tb)

    def set_total(self, total: int) -> None:
        self.total = total
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, total=total)

    async def advance(self, status: str) -> None:
        if not self.enabled:
            return
        async with self._lock:
            self.stats[status] = self.stats.get(status, 0) + 1
            if self.progress and self.task_id is not None and status in {"DONE", "FAILED_GIVEUP"}:
                self.progress.advance(self.task_id)
            self._refresh()

    async def sync_stats(self, stats: Dict[str, int]) -> None:
        if not self.enabled:
            return
        async with self._lock:
            self.stats = stats
            completed = sum(stats.get(status, 0) for status in ("DONE", "FAILED_GIVEUP"))
            if self.progress and self.task_id is not None:
                self.progress.update(self.task_id, completed=completed)
            self._refresh()

    def _refresh(self) -> None:
        if self.live:
            self.live.update(self._render())

    async def _animate(self) -> None:
        while True:
            await asyncio.sleep(0.5)
            self._frame = (self._frame + 1) % len(ROBOT_FRAMES)
            self._refresh()

    def _render(self):
        if not self.progress:
            return ""
        table = Table.grid(expand=True)
        stats_table = Table.grid()
        for status, count in sorted(self.stats.items()):
            stats_table.add_row(f"[bold]{status}[/bold]", str(count))
        robot = ROBOT_FRAMES[self._frame]
        layout = Table.grid(padding=(0, 2))
        layout.add_row(Align.center(robot))
        layout.add_row(stats_table)
        layout.add_row(self.progress)
        return Panel(layout, title="DeepSeek Catalog Generator", border_style="cyan")
