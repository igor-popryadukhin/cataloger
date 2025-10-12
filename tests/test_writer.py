from __future__ import annotations

from pathlib import Path

import pandas as pd

from catalog_cli.io_excel.writer import format_generated_paths, write_paths_excel


def test_write_paths_excel(tmp_path: Path) -> None:
    output = tmp_path / "test.xlsx"
    sphere = "Сфера"
    subsphere = "Подсфера"
    paths = [
        "Сфера/Подсфера/A/B",
        "Сфера/Подсфера/C/D",
    ]

    write_paths_excel(output, sphere, subsphere, paths)

    df = pd.read_excel(output, dtype=str)
    assert list(df.columns) == ["Sphere", "Subsphere", "Generated Path"]
    assert df.shape[0] == 2
    assert df.iloc[0]["Sphere"] == sphere
    assert df.iloc[0]["Subsphere"] == subsphere
    expected = format_generated_paths(sphere, subsphere, paths)
    assert df.iloc[0]["Generated Path"] == expected[0]
