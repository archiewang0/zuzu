"""
Telegram Bot 指令處理：刪除訊息。

/deleteall          — 刪除所有 Bot 已發送的訊息
/deletelast <n>     — 刪除最後 n 則訊息（預設 1）
/help               — 顯示可用指令
"""

from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import TELEGRAM_CHAT_ID
from storage.message_ids import (
    load_message_ids,
    save_message_ids,
    clear_message_ids,
)

logger = logging.getLogger(__name__)

_ALLOWED_CHAT = int(TELEGRAM_CHAT_ID)


def _is_authorized(update: Update) -> bool:
    return update.effective_chat is not None and update.effective_chat.id == _ALLOWED_CHAT


async def handle_deleteall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    ids = load_message_ids()
    if not ids:
        await update.message.reply_text("沒有可刪除的訊息記錄。")
        return

    deleted = 0
    failed = 0
    for mid in ids:
        try:
            await context.bot.delete_message(chat_id=_ALLOWED_CHAT, message_id=mid)
            deleted += 1
        except Exception:
            failed += 1

    clear_message_ids()
    reply = f"✅ 已刪除 {deleted} 則訊息。"
    if failed:
        reply += f"（{failed} 則已過期或無法刪除）"
    # 嘗試刪除指令本身
    try:
        await update.message.delete()
    except Exception:
        await update.message.reply_text(reply)
    logger.info("deleteall：刪除 %d 則，失敗 %d 則", deleted, failed)


async def handle_deletelast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return

    # 解析數量參數
    n = 1
    if context.args:
        try:
            n = max(1, int(context.args[0]))
        except ValueError:
            await update.message.reply_text("用法：/deletelast <數量>，例如 /deletelast 5")
            return

    ids = load_message_ids()
    if not ids:
        await update.message.reply_text("沒有可刪除的訊息記錄。")
        return

    to_delete = ids[-n:]
    remaining = ids[:-n] if n < len(ids) else []

    deleted = 0
    failed = 0
    for mid in to_delete:
        try:
            await context.bot.delete_message(chat_id=_ALLOWED_CHAT, message_id=mid)
            deleted += 1
        except Exception:
            failed += 1

    save_message_ids(remaining)
    reply = f"✅ 已刪除最後 {deleted} 則訊息。"
    if failed:
        reply += f"（{failed} 則已過期或無法刪除）"
    try:
        await update.message.delete()
    except Exception:
        await update.message.reply_text(reply)
    logger.info("deletelast %d：刪除 %d 則，失敗 %d 則", n, deleted, failed)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        return
    text = (
        "📋 可用指令：\n"
        "/deleteall — 刪除所有 Bot 發過的訊息\n"
        "/deletelast <n> — 刪除最後 n 則（預設 1）\n"
        "/help — 顯示此說明"
    )
    await update.message.reply_text(text)
