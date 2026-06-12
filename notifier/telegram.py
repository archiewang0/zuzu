"""
透過 Telegram Bot API 發送租屋貼文通知。
"""

from __future__ import annotations

import logging
import asyncio
import telegram
from telegram.constants import ParseMode
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scraper.parser import RentalPost

logger = logging.getLogger(__name__)

_bot: telegram.Bot | None = None


def _get_bot() -> telegram.Bot:
    global _bot
    if _bot is None:
        _bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    return _bot


def _format_message(post: RentalPost) -> str:
    lines = []

    # 標題行
    lines.append(f"🏠 *新租屋貼文*")
    lines.append(f"👤 {_esc(post.author)}　🕐 {_esc(post.posted_at)}")
    lines.append("")

    # 結構化欄位
    fields = [
        ("📍 地點", post.location),
        ("🗺 地標", post.landmark),
        ("🛏 房型", post.room_type),
        ("🏢 樓層", post.floor),
        ("📐 坪數", post.size),
        ("💰 租金", post.price),
        ("🔑 押金", post.deposit),
        ("📦 租金含", post.includes),
        ("🔥 瓦斯", post.gas_type),
        ("💡 水電費", post.utilities),
        ("⚡ 電費", post.electricity),
        ("💧 水費", post.water),
        ("🛋 設備", post.facilities),
        ("🐾 寵物", post.pets),
        ("📅 最短租期", post.min_period),
        ("🏪 附近", post.nearby),
        ("📌 其他", post.notes),
    ]
    for label, value in fields:
        if value:
            lines.append(f"{label}：{_esc(value)}")

    # 內文摘要（前 200 字）
    if post.raw_text:
        lines.append("")
        preview = post.raw_text[:200].replace("\n", " ")
        if len(post.raw_text) > 200:
            preview += "…"
        lines.append(f"📝 {_esc(preview)}")

    # 連結
    lines.append("")
    lines.append(f"[🔗 查看原始貼文]({post.url})")

    return "\n".join(lines)


def _esc(text: str) -> str:
    """Escape MarkdownV2 特殊字元。"""
    special = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


async def _send_post(post: RentalPost) -> None:
    bot = _get_bot()
    message = _format_message(post)

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=False,
    )

    # 如果有圖片，發送第一張
    if post.images:
        try:
            await bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=post.images[0],
                caption=f"📷 {post.author} 的貼文圖片",
            )
        except Exception as e:
            logger.debug("圖片發送失敗：%s", e)


async def send_posts(posts: list[RentalPost]) -> None:
    for post in posts:
        try:
            await _send_post(post)
            # 避免觸發 Telegram rate limit
            await asyncio.sleep(1)
        except Exception as e:
            logger.error("Telegram 發送失敗 (post_id=%s)：%s", post.post_id, e)
