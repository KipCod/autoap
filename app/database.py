"""CSV file storage management."""

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List

from .models import ActionBundle, CommandMemo

# CSV 파일 경로
DATA_DIR = Path(__file__).resolve().parent
MAIN_CSV_PATH = DATA_DIR / "action_bundles.csv"
MEMO_CSV_PATH = DATA_DIR / "command_memos.csv"

MAIN_COLUMNS = [
    "ID",
    "Part",
    "Bundle Name",
    "Command",
    "Description",
    "Keywords",
    "Expected Outcome",
    "Interpretation",
    "Updated Date",
    "Todo",
]

MEMO_COLUMNS = ["ID", "Command ID", "Command Text", "Memo text", "onenote link"]


def _parse_date(value: str) -> date:
    """날짜 문자열을 date 객체로 변환"""
    if not value:
        return date.today()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(value)
    except ValueError:
        return date.today()


def load_bundles() -> Dict[int, ActionBundle]:
    """CSV 파일에서 번들 데이터 로드"""
    bundles: Dict[int, ActionBundle] = {}
    
    if not MAIN_CSV_PATH.exists():
        return bundles
    
    with open(MAIN_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bundle_id = int(row.get("ID", 0))
            if bundle_id:
                bundle = ActionBundle(
                    id=bundle_id,
                    part=row.get("Part", ""),
                    bundle_name=row.get("Bundle Name", ""),
                    command_text=row.get("Command", ""),
                    description=row.get("Description", ""),
                    keywords=row.get("Keywords", ""),
                    expected_outcome=row.get("Expected Outcome", ""),
                    interpretation=row.get("Interpretation", ""),
                    updated_date=_parse_date(row.get("Updated Date", "")),
                    todo=row.get("Todo", ""),
                )
                bundles[bundle_id] = bundle
    
    return bundles


def load_memos() -> Dict[int, List[CommandMemo]]:
    """CSV 파일에서 메모 데이터 로드"""
    memos_by_action: Dict[int, List[CommandMemo]] = {}
    
    if not MEMO_CSV_PATH.exists():
        return memos_by_action
    
    with open(MEMO_CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            action_id = int(row.get("ID", 0))
            if action_id:
                memo = CommandMemo(
                    action_id=action_id,
                    command_order=int(row.get("Command ID", 0)),
                    command_text=row.get("Command Text", ""),
                    memo_text=row.get("Memo text", ""),
                    onenote_link=row.get("onenote link", ""),
                )
                if action_id not in memos_by_action:
                    memos_by_action[action_id] = []
                memos_by_action[action_id].append(memo)
    
    # 각 액션의 메모를 command_order로 정렬
    for action_id in memos_by_action:
        memos_by_action[action_id].sort(key=lambda m: m.command_order)
    
    return memos_by_action


def save_bundles(bundles: Dict[int, ActionBundle]) -> None:
    """번들 데이터를 CSV 파일에 저장"""
    with open(MAIN_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MAIN_COLUMNS)
        writer.writeheader()
        
        for bundle_id in sorted(bundles.keys()):
            bundle = bundles[bundle_id]
            writer.writerow(
                {
                    "ID": bundle.id or "",
                    "Part": bundle.part,
                    "Bundle Name": bundle.bundle_name,
                    "Command": bundle.command_text,
                    "Description": bundle.description,
                    "Keywords": bundle.keywords,
                    "Expected Outcome": bundle.expected_outcome,
                    "Interpretation": bundle.interpretation,
                    "Updated Date": (
                        bundle.updated_date.isoformat()
                        if isinstance(bundle.updated_date, date)
                        else str(bundle.updated_date)
                        if bundle.updated_date
                        else ""
                    ),
                    "Todo": bundle.todo,
                }
            )


def save_memos(memos_by_action: Dict[int, List[CommandMemo]]) -> None:
    """메모 데이터를 CSV 파일에 저장"""
    with open(MEMO_CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MEMO_COLUMNS)
        writer.writeheader()
        
        for action_id in sorted(memos_by_action.keys()):
            memos = sorted(memos_by_action[action_id], key=lambda m: m.command_order)
            for memo in memos:
                writer.writerow(
                    {
                        "ID": memo.action_id,
                        "Command ID": memo.command_order,
                        "Command Text": memo.command_text,
                        "Memo text": memo.memo_text,
                        "onenote link": memo.onenote_link,
                    }
                )


def get_all_data() -> tuple[Dict[int, ActionBundle], Dict[int, List[CommandMemo]]]:
    """모든 데이터 로드 (번들 + 메모)"""
    bundles = load_bundles()
    memos_by_action = load_memos()
    
    # 번들에 메모 연결
    for bundle_id, bundle in bundles.items():
        bundle.memos = memos_by_action.get(bundle_id, [])
    
    return bundles, memos_by_action


def save_all_data(bundles: Dict[int, ActionBundle], memos_by_action: Dict[int, List[CommandMemo]]) -> None:
    """모든 데이터 저장 (번들 + 메모)"""
    save_bundles(bundles)
    save_memos(memos_by_action)
