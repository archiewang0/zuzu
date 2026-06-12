# zuzu — Facebook 租屋社團爬蟲 → Telegram 通知

## 功能

- 使用 Playwright 爬取 Facebook 租屋社團貼文
- 自動解析：租金、坪數、樓層、類型、建物、對外窗、管理室、代收垃圾、電費、水費
- 只通知上次爬取後的**新貼文**，避免重複
- 定時排程（預設每 15 分鐘）
- 發送至 Telegram 個人/群組

## 安裝

**建立並啟動虛擬環境**

```bash
python -m venv .venv
source .venv/bin/activate
```

**安裝套件**

```bash
pip install -r requirements.txt
playwright install chromium
```

> 之後每次使用前都需要先執行 `source .venv/bin/activate`，退出環境用 `deactivate`。

## 設定

```bash
cp .env.example .env
# 編輯 .env，填入 Telegram Bot Token、Chat ID、社團 URL
```

取得 Telegram Chat ID：對 `@userinfobot` 發訊息即可。

## 使用

### 1. 第一次登入（只需執行一次）

```bash
python login.py
```

瀏覽器會開啟，手動登入 Facebook 後按 Enter，session 會儲存至 `session/auth.json`。

### 2. 啟動排程

```bash
python main.py
```

## 專案結構

```
zuzu/
├── main.py              # 主程式 / 排程
├── login.py             # 手動登入，儲存 session
├── config.py            # 讀取 .env 設定
├── scraper/
│   ├── facebook.py      # Playwright 爬蟲
│   └── parser.py        # 租屋資訊解析（regex）
├── notifier/
│   └── telegram.py      # Telegram 發送
├── storage/
│   └── seen_posts.py    # 已讀貼文追蹤
└── session/             # auth.json（gitignored）
```
