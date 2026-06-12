"""
執行一次來手動登入 Facebook，並儲存 session。
之後主程式會自動使用這個 session。

用法：python login.py
"""

import asyncio
from playwright.async_api import async_playwright
from config import AUTH_STATE_PATH
import os


async def manual_login():
    os.makedirs(os.path.dirname(AUTH_STATE_PATH), exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.facebook.com/login")
        print("請在瀏覽器中手動登入 Facebook...")
        print("登入完成後，請按 Enter 繼續...")
        input()

        await context.storage_state(path=AUTH_STATE_PATH)
        print(f"Session 已儲存至 {AUTH_STATE_PATH}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(manual_login())
