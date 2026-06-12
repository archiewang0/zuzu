from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RentalPost:
    post_id: str
    url: str
    author: str
    posted_at: str
    raw_text: str
    images: list[str] = field(default_factory=list)

    # 【欄位】解析結果
    location: Optional[str] = None       # 地點
    landmark: Optional[str] = None       # 地標
    room_type: Optional[str] = None      # 房型
    floor: Optional[str] = None          # 樓層
    price: Optional[str] = None          # 租金
    deposit: Optional[str] = None        # 押金
    includes: Optional[str] = None       # 租金包含
    gas_type: Optional[str] = None       # 瓦斯類型
    utilities: Optional[str] = None      # 電/水/瓦斯
    electricity: Optional[str] = None    # 電費（獨立欄位）
    water: Optional[str] = None          # 水費（獨立欄位）
    facilities: Optional[str] = None     # 設備
    pets: Optional[str] = None           # 寵物
    min_period: Optional[str] = None     # 最短租期
    nearby: Optional[str] = None         # 附近有
    notes: Optional[str] = None          # 其他
    size: Optional[str] = None           # 坪數（regex fallback）


# 【欄位名稱】→ dataclass 屬性對應
_BRACKET_KEY_MAP = {
    "地點": "location",
    "地址": "location",
    "地標": "landmark",
    "房型": "room_type",
    "格局": "room_type",
    "樓層": "floor",
    "租金": "price",
    "月租": "price",
    "押金": "deposit",
    "租金包含": "includes",
    "費用包含": "includes",
    "包含": "includes",
    "瓦斯類型": "gas_type",
    "瓦斯": "gas_type",
    "電/水/瓦斯": "utilities",
    "水電費": "utilities",
    "電費": "electricity",
    "水費": "water",
    "設備": "facilities",
    "配備": "facilities",
    "寵物": "pets",
    "最短租期": "min_period",
    "租期": "min_period",
    "附近有": "nearby",
    "附近": "nearby",
    "其他": "notes",
    "備註": "notes",
}

_BRACKET_RE = re.compile(r'^【([^】]+)】(.*)$')
_SIZE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*坪')


def _parse_bracket_fields(text: str) -> dict[str, str]:
    """解析 【欄位名稱】內容 格式，支援下一行為內容的情況。"""
    result: dict[str, str] = {}
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    i = 0
    while i < len(lines):
        m = _BRACKET_RE.match(lines[i])
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()

            # 收集接續行（直到下一個 【...】 為止）
            j = i + 1
            extra: list[str] = []
            while j < len(lines) and not _BRACKET_RE.match(lines[j]):
                extra.append(lines[j])
                j += 1

            if not value and extra:
                value = '\n'.join(extra)
                i = j
            else:
                i += 1

            result[key] = value
        else:
            i += 1

    return result


def _extract_price_from_text(text: str) -> Optional[str]:
    """從租金欄位的內文提取金額，例如 'RoomD雅房 - $10800'"""
    m = re.search(r'[＄$NT]\s*(\d[\d,]+)', text)
    if m:
        return m.group(1)
    m = re.search(r'(\d[\d,]+)\s*[元/月]', text)
    if m:
        return m.group(1)
    return text if text else None


def parse_rental_info(post: RentalPost) -> RentalPost:
    text = post.raw_text
    bracket_data = _parse_bracket_fields(text)

    for bracket_key, attr in _BRACKET_KEY_MAP.items():
        if bracket_key in bracket_data:
            value = bracket_data[bracket_key].strip()
            if value:
                setattr(post, attr, value)

    # 租金欄位若為空（下一行是價格明細），嘗試提取數字
    if post.price and not re.search(r'\d', post.price):
        post.price = None
    if not post.price and '租金' in bracket_data:
        post.price = _extract_price_from_text(bracket_data['租金'])

    # 坪數 fallback（貼文中可能寫在內文任何地方）
    if not post.size:
        m = _SIZE_RE.search(text)
        if m:
            post.size = f"{m.group(1)} 坪"

    return post
