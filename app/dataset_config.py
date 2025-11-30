"""Dataset configuration loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

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
    image_paths: Optional[List[str]] = None
    default_image_width: int = 500
    default_image_height: int = 400


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
                "image_paths": [],
                "default_image_width": 500,
                "default_image_height": 400,
            },
            {
                "id": "set_b",
                "label": "세트 B",
                "main_csv": "set_b_main.csv",
                "memo_csv": "set_b_memos.csv",
                "link_csv": "set_b_links.csv",
                "image_paths": [],
                "default_image_width": 500,
                "default_image_height": 400,
            },
        ]
    }

    CONFIG_PATH.write_text(json.dumps(default_payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _resolve_path(path_str: str) -> Path:
    """경로 문자열을 Path 객체로 변환.
    
    - 절대 경로인 경우: 그대로 사용
    - 상대 경로인 경우: DATA_DIR 기준으로 해석
    - 파일명만 있는 경우: DATA_DIR과 결합
    """
    path = Path(path_str)
    if path.is_absolute():
        return path
    # 상대 경로인 경우 DATA_DIR 기준으로 해석
    return (DATA_DIR / path).resolve()


def _normalize_image_path(image_path: str) -> str:
    """이미지 경로를 정규화.
    
    - 절대 경로인 경우: 그대로 반환 (절대 경로로 직접 사용)
    - /static/으로 시작하면 제거
    - 그 외: 그대로 반환 (static 폴더 기준 상대 경로로 가정)
    """
    if not image_path:
        return ""
    
    # /static/으로 시작하면 제거
    if image_path.startswith("/static/"):
        return image_path[8:]  # "/static/" 길이만큼 제거
    
    # 절대 경로는 그대로 반환 (절대 경로로 직접 사용)
    path = Path(image_path)
    if path.is_absolute():
        return image_path
    
    # 상대 경로는 그대로 반환 (static 폴더 기준)
    return image_path


def _normalize_image_paths(image_paths: Optional[List[str]]) -> List[str]:
    """이미지 경로 배열을 정규화."""
    if not image_paths:
        return []
    return [_normalize_image_path(path) for path in image_paths if path]


def load_dataset_definitions() -> List[DatasetDefinition]:
    """Return dataset definitions with resolved CSV paths."""
    _ensure_default_file()
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    datasets: List[DatasetDefinition] = []

    for item in raw.get("datasets", []):
        main_csv = _resolve_path(item["main_csv"])
        memo_csv = _resolve_path(item["memo_csv"])
        link_csv = _resolve_path(item["link_csv"])
        
        # image_paths 배열 처리 (하위 호환성을 위해 image_path도 지원)
        image_paths = item.get("image_paths", [])
        if not image_paths and "image_path" in item:
            # 기존 image_path가 있으면 배열로 변환
            old_path = item.get("image_path", "")
            image_paths = [old_path] if old_path else []
        
        image_paths = _normalize_image_paths(image_paths)
        default_image_width = item.get("default_image_width", 500)
        default_image_height = item.get("default_image_height", 400)

        datasets.append(
            DatasetDefinition(
                id=item["id"],
                label=item.get("label", item["id"]),
                main_csv=main_csv,
                memo_csv=memo_csv,
                link_csv=link_csv,
                image_paths=image_paths or None,
                default_image_width=default_image_width,
                default_image_height=default_image_height,
            )
        )

    if not datasets:
        raise ValueError("datasets.json에는 최소 1개의 세트가 필요합니다.")

    return datasets

