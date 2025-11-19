"""CSV file storage management."""

import csv
from pathlib import Path
from typing import Dict, List, Tuple

from .models import ActionBundle, CommandMemo, LinkEntry

MAIN_COLUMNS = [
    "ID",
    "Part",
    "Bundle Name",
    "Command",
    "Keywords",
]

MEMO_COLUMNS = ["ID", "Command ID", "Command Text", "Description", "Memo text", "onenote link"]
LINK_COLUMNS = ["ID", "Bundle ID", "Command ID", "URL", "Description", "Tags"]


def _safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def load_bundles(csv_path: Path) -> Dict[int, ActionBundle]:
    """지정된 CSV에서 번들 데이터 로드"""
    bundles: Dict[int, ActionBundle] = {}
    
    if not csv_path.exists():
        return bundles
    
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bundle_id = _safe_int(row.get("ID"))
            if bundle_id:
                bundle = ActionBundle(
                    id=bundle_id,
                    part=row.get("Part", ""),
                    bundle_name=row.get("Bundle Name", ""),
                    command_text=row.get("Command", ""),
                    keywords=row.get("Keywords", ""),
                )
                bundles[bundle_id] = bundle
    
    return bundles


def load_memos(csv_path: Path) -> Dict[int, List[CommandMemo]]:
    """CSV 파일에서 메모 데이터 로드"""
    memos_by_action: Dict[int, List[CommandMemo]] = {}
    
    if not csv_path.exists():
        return memos_by_action
    
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            action_id = _safe_int(row.get("ID"))
            if action_id:
                memo = CommandMemo(
                    action_id=action_id,
                    command_order=_safe_int(row.get("Command ID")),
                    command_text=row.get("Command Text", ""),
                    description=row.get("Description", ""),
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


def save_bundles(csv_path: Path, bundles: Dict[int, ActionBundle]) -> None:
    """번들 데이터를 CSV 파일에 저장"""
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
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
                    "Keywords": bundle.keywords,
                }
            )


def save_memos(csv_path: Path, memos_by_action: Dict[int, List[CommandMemo]]) -> None:
    """메모 데이터를 CSV 파일에 저장"""
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
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
                        "Description": memo.description,
                        "Memo text": memo.memo_text,
                        "onenote link": memo.onenote_link,
                    }
                )


def load_links(csv_path: Path) -> Dict[int, LinkEntry]:
    """URL 링크 데이터를 로드"""
    links: Dict[int, CommandMemo] = {}
    
    if not csv_path.exists():
        return links
    
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            link_id = _safe_int(row.get("ID"))
            if not link_id:
                continue
            entry = LinkEntry(
                id=link_id,
                bundle_id=_safe_int(row.get("Bundle ID")) or None,
                command_order=_safe_int(row.get("Command ID")) or None,
                url=row.get("URL", ""),
                description=row.get("Description", ""),
                tags=row.get("Tags", ""),
            )
            links[link_id] = entry
    
    return links


def save_links(csv_path: Path, links: Dict[int, LinkEntry]) -> None:
    """링크 데이터를 저장"""
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LINK_COLUMNS)
        writer.writeheader()
        for link_id in sorted(links.keys()):
            entry = links[link_id]
            writer.writerow(
                {
                    "ID": entry.id or "",
                    "Bundle ID": entry.bundle_id or "",
                    "Command ID": entry.command_order or "",
                    "URL": entry.url,
                    "Description": entry.description,
                    "Tags": entry.tags,
                }
            )


def get_all_data(main_path: Path, memo_path: Path, link_path: Path) -> tuple[
    Dict[int, ActionBundle], Dict[int, List[CommandMemo]], Dict[int, LinkEntry]
]:
    """지정된 경로 세트의 데이터 로드"""
    bundles = load_bundles(main_path)
    memos_by_action = load_memos(memo_path)
    links = load_links(link_path)
    
    # 번들에 메모 연결
    for bundle_id, bundle in bundles.items():
        bundle.memos = memos_by_action.get(bundle_id, [])
    
    return bundles, memos_by_action, links


def save_all_data(
    main_path: Path,
    memo_path: Path,
    link_path: Path,
    bundles: Dict[int, ActionBundle],
    memos_by_action: Dict[int, List[CommandMemo]],
    links: Dict[int, LinkEntry],
) -> None:
    """모든 데이터 저장 (번들 + 메모 + 링크)"""
    save_bundles(main_path, bundles)
    save_memos(memo_path, memos_by_action)
    save_links(link_path, links)
