"""Data models."""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class CommandMemo:
    action_id: int
    command_order: int
    command_text: str = ""
    memo_text: str = ""
    onenote_link: str = ""


@dataclass
class ActionBundle:
    id: Optional[int] = None
    part: str = ""
    bundle_name: str = ""
    command_text: str = ""
    description: str = ""
    keywords: str = ""
    expected_outcome: str = ""
    interpretation: str = ""
    updated_date: date = field(default_factory=date.today)
    todo: str = ""
    memos: List[CommandMemo] = field(default_factory=list)

