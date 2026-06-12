"""
以 JSON 檔案追蹤已發送的貼文 ID，避免重複通知。
"""

from __future__ import annotations

import json
import os
from config import SEEN_POSTS_PATH


def load_seen_ids() -> set[str]:
    if not os.path.exists(SEEN_POSTS_PATH):
        return set()
    with open(SEEN_POSTS_PATH, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_seen_ids(ids: set[str]) -> None:
    os.makedirs(os.path.dirname(SEEN_POSTS_PATH), exist_ok=True)
    with open(SEEN_POSTS_PATH, "w", encoding="utf-8") as f:
        json.dump(list(ids), f, ensure_ascii=False)


def mark_seen(new_ids: list[str]) -> None:
    seen = load_seen_ids()
    seen.update(new_ids)
    # 只保留最近 5000 筆，避免檔案無限增長
    if len(seen) > 5000:
        seen = set(list(seen)[-5000:])
    save_seen_ids(seen)
