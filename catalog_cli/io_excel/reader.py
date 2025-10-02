from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd


class ExcelFormatError(Exception):
    """Raised when the input Excel file does not conform to the expected format."""


def read_input_pairs(path: Path) -> List[Tuple[str, str]]:
    try:
        df = pd.read_excel(path, dtype=str)
    except FileNotFoundError as exc:
        raise FileNotFoundError("Input Excel file not found") from exc
    except Exception as exc:  # pragma: no cover - handled generically
        raise ExcelFormatError(f"Failed to read Excel file: {exc}") from exc

    if df.shape[1] < 2:
        raise ExcelFormatError("Excel file must contain at least two columns")

    df = df.fillna("")

    first_col = df.columns[0]
    second_col = df.columns[1]

    pairs: List[Tuple[str, str]] = []
    for _, row in df.iterrows():
        sphere = str(row[first_col]).strip()
        subsphere = str(row[second_col]).strip()
        if not sphere or not subsphere:
            continue
        pairs.append((sphere, subsphere))

    if not pairs:
        raise ExcelFormatError("No valid sphere/subsphere pairs found in Excel file")

    return pairs
