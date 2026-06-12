#!/bin/bash
set -e

cd "$(dirname "$0")"

# ── 首次設定 ──────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "🔧 首次設定：建立虛擬環境..."
    python3 -m venv .venv
    source .venv/bin/activate

    echo "📦 安裝套件..."
    pip install -r requirements.txt

    echo "🌐 安裝 Playwright Chromium..."
    playwright install chromium
else
    source .venv/bin/activate
fi

# ── 確認 .env ─────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  .env 已建立，請填入以下設定後重新執行 run.sh："
    echo "   TELEGRAM_BOT_TOKEN=..."
    echo "   TELEGRAM_CHAT_ID=..."
    echo "   FB_GROUP_URLS=..."
    echo ""
    exit 0
fi

# 檢查是否還是預設占位符
if grep -q "your_bot_token_here" .env; then
    echo ""
    echo "⚠️  請先編輯 .env 填入真實的 Token 與社團 URL，再重新執行 run.sh"
    echo ""
    exit 0
fi

# ── Facebook Session ──────────────────────────────────────
if [ ! -f "session/auth.json" ]; then
    echo "🔑 尚未登入 Facebook，開啟瀏覽器進行登入..."
    python login.py
fi

# ── 啟動排程 ──────────────────────────────────────────────
echo "🚀 啟動爬蟲排程..."
python main.py
