"""
主程式：定時爬取 Facebook 租屋社團，並將新貼文發送至 Telegram。

啟動方式：python main.py
第一次使用請先執行：python login.py
"""

import asyncio
import logging
import os
import sys
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import FB_GROUP_URLS, INTERVAL_MINUTES, AUTH_STATE_PATH
from scraper.facebook import scrape_all_groups
from scraper.parser import parse_rental_info
from notifier.telegram import send_posts
from storage.seen_posts import load_seen_ids, mark_seen

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_scrape_job() -> None:
    logger.info("開始爬取，共 %d 個社團", len(FB_GROUP_URLS))

    seen_ids = load_seen_ids()
    new_posts = await scrape_all_groups(FB_GROUP_URLS, seen_ids)

    if not new_posts:
        logger.info("沒有新貼文")
        return

    logger.info("發現 %d 則新貼文，開始解析", len(new_posts))
    parsed = [parse_rental_info(post) for post in new_posts]

    await send_posts(parsed)
    mark_seen([p.post_id for p in parsed])
    logger.info("已發送 %d 則通知", len(parsed))


def _check_prerequisites() -> bool:
    ok = True
    if not os.path.exists(AUTH_STATE_PATH):
        print(f"[錯誤] 找不到 session 檔案：{AUTH_STATE_PATH}")
        print("請先執行：python login.py")
        ok = False
    if not FB_GROUP_URLS:
        print("[錯誤] 請在 .env 設定 FB_GROUP_URLS")
        ok = False
    return ok


async def main() -> None:
    if not _check_prerequisites():
        sys.exit(1)

    logger.info("排程啟動，每 %d 分鐘執行一次", INTERVAL_MINUTES)

    # 啟動時立即執行一次
    await run_scrape_job()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scrape_job,
        trigger=IntervalTrigger(minutes=INTERVAL_MINUTES),
        id="scrape_job",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("程式結束")
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
