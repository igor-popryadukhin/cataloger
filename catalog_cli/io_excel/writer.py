from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def write_paths_excel(path: Path, paths: Iterable[str]) -> None:
    df = pd.DataFrame({"Path": list(paths)})
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Paths", index=False)
