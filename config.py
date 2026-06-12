import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

FB_GROUP_URLS = [
    url.strip()
    for url in os.getenv("FB_GROUP_URLS", "").split(",")
    if url.strip()
]

INTERVAL_MINUTES = int(os.getenv("INTERVAL_MINUTES", "15"))
AUTH_STATE_PATH = os.getenv("AUTH_STATE_PATH", "session/auth.json")
SEEN_POSTS_PATH = "storage/seen_posts.json"
