from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer

from catalog_cli.processor import inspect_item, prepare_run, resume_run, validate_input

app = typer.Typer(help="CLI utility for generating category catalogs via DeepSeek API")


@app.command()
def run(
    input_path: Path = typer.Argument(..., help="Path to the input Excel file"),
    concurrency: Optional[int] = typer.Option(None, help="Maximum number of concurrent requests"),
    rps: Optional[float] = typer.Option(None, help="Maximum requests per second"),
    no_tui: bool = typer.Option(False, help="Disable TUI visualization"),
) -> None:
    """Run processing for the provided Excel file."""
    asyncio.run(prepare_run(input_path, concurrency, rps, no_tui))


@app.command()
def resume(
    no_tui: bool = typer.Option(False, help="Disable TUI visualization"),
) -> None:
    """Resume processing from the last checkpoint."""
    asyncio.run(resume_run(no_tui))


@app.command()
def validate(
    input_path: Path = typer.Argument(..., help="Path to the input Excel file"),
) -> None:
    """Validate the input Excel file without sending requests."""
    count = asyncio.run(validate_input(input_path))
    typer.echo(f"Valid rows: {count}")


@app.command()
def inspect(
    item_id: str = typer.Option(..., "--item-id", help="Identifier of the item to inspect"),
) -> None:
    """Inspect a particular item from the processing state."""
    item = asyncio.run(inspect_item(item_id))
    if item:
        typer.echo(
            "\n".join(
                [
                    f"ID: {item.id}",
                    f"Sphere: {item.sphere}",
                    f"Subsphere: {item.subsphere}",
                    f"Status: {item.status}",
                    f"Retries: {item.retries}",
                    f"Last error: {item.last_error}",
                ]
            )
        )
    else:
        raise typer.Exit(code=1)
