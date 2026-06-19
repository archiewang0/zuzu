"""
使用 Playwright 爬取 Facebook 社團貼文。
需先執行 login.py 產生 session/auth.json。
"""

from __future__ import annotations

import asyncio
import logging
import re
from playwright.async_api import async_playwright, BrowserContext, Page
from config import AUTH_STATE_PATH
from scraper.parser import RentalPost

logger = logging.getLogger(__name__)

# 滾動頁面以載入更多貼文時的間隔
_SCROLL_PAUSE_MS = 2000
_MAX_SCROLLS = 5


async def _build_context(p) -> BrowserContext:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        storage_state=AUTH_STATE_PATH,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
        locale="zh-TW",
    )
    return context


async def _scroll_and_collect(page: Page, seen_ids: set[str]) -> list[dict]:
    """滾動頁面並收集貼文原始資料，直到遇到已見過的貼文或達到上限。"""
    posts = []
    collected_ids: set[str] = set()
    last_height = 0

    for _ in range(_MAX_SCROLLS):
        await page.wait_for_timeout(_SCROLL_PAUSE_MS)

        # !!!! 抓取所有貼文容器
        # 這裡是抓取 FB 最原始的位置
        articles = await page.query_selector_all("div[data-pagelet^='GroupFeed'] div[role='article']")
        if not articles:
            # fallback selector
            articles = await page.query_selector_all("div[role='article']")

        # logger.info("[articles] 共 %d 篇", len(articles))
        for i, article in enumerate(articles):
            preview = (await article.inner_text())[:80].replace("\n", " ")
            # logger.info("[article #%d] %s", i, preview)
            try:
                post_data = await _extract_article(page, article)
                if post_data:
                    pid = post_data["post_id"]
                    if pid not in seen_ids and pid not in collected_ids:
                        collected_ids.add(pid)
                        posts.append(post_data)
            except Exception as e:
                logger.debug("解析貼文失敗：%s", e)

        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    return posts


async def _find_post_id(article) -> tuple[str | None, str | None, str | None]:
    """從 article DOM 取出 (post_id, group_id, post_url)，三種格式依序嘗試。"""
    # 策略 1：/groups/.../posts/POST_ID/
    link_el = await article.query_selector("a[href*='/groups/'][href*='/posts/']")
    if link_el:
        href = (await link_el.get_attribute("href") or "").split("?")[0].rstrip("/")
        m = re.search(r"/posts/(\d+)", href)
        gm = re.search(r"/groups/(\d+)/", href)
        if m and gm:
            gid = gm.group(1)
            pid = m.group(1)
            return pid, gid, f"https://www.facebook.com/groups/{gid}/posts/{pid}/"

    # 策略 2：圖片相簿 set=pcb.POST_ID
    photo_el = await article.query_selector("a[href*='set=pcb.']")
    if photo_el:
        href = await photo_el.get_attribute("href") or ""
        m = re.search(r"set=pcb\.(\d+)", href)
        if m:
            return m.group(1), None, None

    # 策略 3：story_fbid
    story_el = await article.query_selector("a[href*='story_fbid']")
    if story_el:
        href = await story_el.get_attribute("href") or ""
        m = re.search(r"story_fbid[=:](\d+)", href)
        if m:
            return m.group(1), None, None

    return None, None, None


async def _resolve_url(article, post_id: str, group_id: str | None, post_url: str | None) -> str:
    """補全 group_id（若缺失），回傳最終貼文 URL。"""
    if not group_id:
        user_el = await article.query_selector("a[href*='/groups/'][href*='/user/']")
        if user_el:
            href = await user_el.get_attribute("href") or ""
            gm = re.search(r"/groups/(\d+)/", href)
            if gm:
                group_id = gm.group(1)

    if post_url:
        return post_url
    if group_id:
        return f"https://www.facebook.com/groups/{group_id}/posts/{post_id}/"
    return f"https://www.facebook.com/permalink.php?story_fbid={post_id}"


async def _expand_see_more(page: Page, article) -> None:
    """點擊「顯示更多」/「查看更多」展開完整內文。"""
    see_more = await article.query_selector(
        "div[role='button'][tabindex='0']:has-text('查看更多'), "
        "div[role='button'][tabindex='0']:has-text('顯示更多'), "
        "span:has-text('查看更多'), "
        "span:has-text('顯示更多')"
    )
    if see_more:
        try:
            await see_more.click()
            await page.wait_for_timeout(1500)
        except Exception:
            pass


async def _find_text_el(article):
    """找內文元素；找不到代表此 article 是留言而非貼文，回傳 None。"""
    text_el = await article.query_selector("div[data-ad-rendering-role='story_message']")
    if not text_el:
        text_el = await article.query_selector(
            "div[data-ad-comet-preview='message'], div[data-ad-preview='message']"
        )
    return text_el


async def _collect_images(article) -> list[str]:
    """收集貼文圖片 URL（排除 emoji / icon）。"""
    img_els = await article.query_selector_all("img[src*='fbcdn']")
    images = []
    for img in img_els:
        src = await img.get_attribute("src")
        if src and "emoji" not in src and "icon" not in src:
            images.append(src)
    return images


async def _extract_article(page: Page, article) -> dict | None:
    post_id, group_id, post_url = await _find_post_id(article)
    if not post_id:
        return None

    post_url = await _resolve_url(article, post_id, group_id, post_url)
    logger.info("[post_id] %s  url=%s", post_id, post_url)

    author_el = await article.query_selector("div[data-ad-rendering-role='profile_name'] h2 a")
    if not author_el:
        author_el = await article.query_selector("h2 a, h3 a")
    author = await author_el.inner_text() if author_el else "未知"

    time_el = await article.query_selector("abbr[title], time[datetime]")
    posted_at = ""
    if time_el:
        posted_at = await time_el.get_attribute("title") or await time_el.get_attribute("datetime") or ""

    await _expand_see_more(page, article)

    text_el = await _find_text_el(article)
    if not text_el:
        logger.debug("[skip] post_id=%s 無 story_message/comet_preview，疑似留言，略過", post_id)
        return None

    raw_text = await text_el.inner_text()
    logger.info("[raw_text] post_id=%s\n%s\n%s", post_id, "-" * 60, raw_text or "(空)")

    return {
        "post_id": post_id,
        "url": post_url,
        "author": author.strip(),
        "posted_at": posted_at.strip(),
        "raw_text": raw_text.strip(),
        "images": await _collect_images(article),
    }


async def scrape_group(group_url: str, seen_ids: set[str]) -> list[RentalPost]:
    """爬取指定社團，回傳尚未見過的新貼文清單。"""
    results = []

    async with async_playwright() as p:
        context = await _build_context(p)
        page = await context.new_page()

        try:
            logger.info("前往社團：%s", group_url)
            await page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            raw_posts = await _scroll_and_collect(page, seen_ids)

            for data in raw_posts:
                if data["post_id"] in seen_ids:
                    continue
                post = RentalPost(
                    post_id=data["post_id"],
                    url=data["url"],
                    author=data["author"],
                    posted_at=data["posted_at"],
                    raw_text=data["raw_text"],
                    images=data["images"],
                )
                results.append(post)

        except Exception as e:
            logger.error("爬取社團失敗 %s：%s", group_url, e)
        finally:
            await context.close()

    return results


async def scrape_all_groups(group_urls: list[str], seen_ids: set[str]) -> list[RentalPost]:
    tasks = [scrape_group(url, seen_ids) for url in group_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    posts = []
    for r in results:
        if isinstance(r, list):
            posts.extend(r)
        else:
            logger.error("社團爬取例外：%s", r)
    return posts
