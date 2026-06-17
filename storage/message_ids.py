"""
追蹤 Bot 已發送訊息的 message_id，供後續刪除使用。
"""

from __future__ import annotations

import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "message_ids.json")
_MAX = 2000  # 最多保留幾筆


def load_message_ids() -> list[int]:
    if not os.path.exists(_PATH):
        return []
    with open(_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_message_ids(ids: list[int]) -> None:
    with open(_PATH, "w", encoding="utf-8") as f:
        json.dump(ids[-_MAX:], f)


def append_message_id(mid: int) -> None:
    ids = load_message_ids()
    ids.append(mid)
    save_message_ids(ids)


def clear_message_ids() -> None:
    save_message_ids([])
