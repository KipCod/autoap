"""Dataset configuration loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

DATA_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DATA_DIR / "datasets.json"


@dataclass(frozen=True)
class DatasetDefinition:
    """Dataset definition with CSV filenames."""

    id: str
    label: str
    main_csv: Path
    memo_csv: Path
    link_csv: Path
    image_path: str = ""


def _ensure_default_file() -> None:
    """Create default datasets config when missing."""
    if CONFIG_PATH.exists():
        return

    default_payload = {
        "datasets": [
            {
                "id": "set_a",
                "label": "세트 A",
                "main_csv": "set_a_main.csv",
                "memo_csv": "set_a_memos.csv",
                "link_csv": "set_a_links.csv",
                "image_path": "",
            },
            {
                "id": "set_b",
                "label": "세트 B",
                "main_csv": "set_b_main.csv",
                "memo_csv": "set_b_memos.csv",
                "link_csv": "set_b_links.csv",
                "image_path": "",
            },
        ]
    }

    CONFIG_PATH.write_text(json.dumps(default_payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_dataset_definitions() -> List[DatasetDefinition]:
    """Return dataset definitions with resolved CSV paths."""
    _ensure_default_file()
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    datasets: List[DatasetDefinition] = []

    for item in raw.get("datasets", []):
        main_csv = DATA_DIR / item["main_csv"]
        memo_csv = DATA_DIR / item["memo_csv"]
        link_csv = DATA_DIR / item["link_csv"]

        datasets.append(
            DatasetDefinition(
                id=item["id"],
                label=item.get("label", item["id"]),
                main_csv=main_csv,
                memo_csv=memo_csv,
                link_csv=link_csv,
                image_path=item.get("image_path", ""),
            )
        )

    if not datasets:
        raise ValueError("datasets.json에는 최소 1개의 세트가 필요합니다.")

    return datasets

