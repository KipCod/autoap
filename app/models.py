"""Data models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CommandMemo:
    action_id: int
    command_order: int
    command_text: str = ""
    description: str = ""
    memo_text: str = ""
    onenote_link: str = ""


@dataclass
class ActionBundle:
    id: Optional[int] = None
    part: str = ""
    bundle_name: str = ""
    command_text: str = ""
    keywords: str = ""
    memos: List[CommandMemo] = field(default_factory=list)


@dataclass
class LinkEntry:
    id: Optional[int] = None
    bundle_id: Optional[int] = None
    command_order: Optional[int] = None
    url: str = ""
    description: str = ""
    tags: str = ""


@dataclass
class DatasetState:
    bundles: Dict[int, ActionBundle] = field(default_factory=dict)
    memos_by_action: Dict[int, List[CommandMemo]] = field(default_factory=dict)
    links: Dict[int, LinkEntry] = field(default_factory=dict)
    tagged_database: List[Dict[str, str]] = field(default_factory=list)
