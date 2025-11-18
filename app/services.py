"""Domain services for command handling and CSV sync."""

from datetime import date, datetime
from typing import Dict, List

from .models import ActionBundle, CommandMemo


def normalize_commands(command_text: str) -> List[str]:
    """Split command text into individual commands."""
    if not command_text:
        return []
    raw_lines = [line.strip() for line in command_text.replace("\r", "").split("\n")]
    return [line for line in raw_lines if line]


def sync_memos(bundle: ActionBundle, command_text: str) -> None:
    """Ensure CommandMemo rows mirror the provided command text."""
    commands = normalize_commands(command_text)
    existing = sorted(bundle.memos, key=lambda memo: memo.command_order)
    
    # 기존 메모의 텍스트와 링크를 보존하기 위한 딕셔너리
    memo_data = {
        (memo.command_order, memo.command_text): (memo.memo_text, memo.onenote_link)
        for memo in existing
    }
    
    # 새로운 메모 리스트 생성
    new_memos: List[CommandMemo] = []
    for idx, command in enumerate(commands, start=1):
        # 기존 메모 데이터가 있으면 사용, 없으면 빈 값
        memo_text, onenote_link = memo_data.get((idx, command), ("", ""))
        memo = CommandMemo(
            action_id=bundle.id or 0,
            command_order=idx,
            command_text=command,
            memo_text=memo_text,
            onenote_link=onenote_link,
        )
        new_memos.append(memo)
    
    bundle.memos = new_memos


def get_next_bundle_id(bundles: Dict[int, ActionBundle]) -> int:
    """다음 사용 가능한 번들 ID 반환"""
    if not bundles:
        return 1
    return max(bundles.keys()) + 1


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
