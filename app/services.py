"""Domain services for command handling and CSV sync."""

from collections import Counter
from typing import Dict, List

from .models import ActionBundle, CommandMemo, LinkEntry


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
        (memo.command_order, memo.command_text): (
            memo.description,
            memo.memo_text,
            memo.onenote_link,
        )
        for memo in existing
    }
    
    # 새로운 메모 리스트 생성
    new_memos: List[CommandMemo] = []
    for idx, command in enumerate(commands, start=1):
        # 기존 메모 데이터가 있으면 사용, 없으면 빈 값
        description, memo_text, onenote_link = memo_data.get((idx, command), ("", "", ""))
        memo = CommandMemo(
            action_id=bundle.id or 0,
            command_order=idx,
            command_text=command,
            description=description,
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


def get_next_link_id(links: Dict[int, LinkEntry]) -> int:
    """다음 링크 ID"""
    if not links:
        return 1
    return max(links.keys()) + 1


def keyword_candidates(bundles: Dict[int, ActionBundle], limit: int = 15) -> List[str]:
    """번들 키워드를 빈도순으로 정리"""
    keywords: List[str] = []
    for bundle in bundles.values():
        if not bundle.keywords:
            continue
        parts = [token.strip().lower() for token in bundle.keywords.replace(";", ",").split(",")]
        keywords.extend([token for token in parts if token])

    counter = Counter(keywords)
    return [keyword for keyword, _ in counter.most_common(limit)]
