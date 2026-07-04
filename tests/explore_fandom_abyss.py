"""
explore_fandom_abyss.py — Xác nhận cấu trúc HTML trang Fandom Abyss
Chạy: python explore_fandom_abyss.py
"""
import re
import requests
from datetime import datetime, date

USER_AGENT = "genshin-ai-agent/3.0 (personal-project)"

def get_current_season_date() -> str:
    """Tính ngày bắt đầu mùa Abyss hiện tại (ngày 1 hoặc 16 gần nhất)."""
    today = date.today()
    if today.day >= 16:
        start = date(today.year, today.month, 16)
    else:
        start = date(today.year, today.month, 1)
    return start.strftime("%Y-%m-%d")

season_date = get_current_season_date()
url = f"https://genshin-impact.fandom.com/wiki/Spiral_Abyss/Floors/{season_date}"
print(f"Season date: {season_date}")
print(f"URL: {url}")

resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
print(f"Status: {resp.status_code}")

html = resp.text
print(f"HTML length: {len(html)}")

# Xem các heading h2/h3 để hiểu cấu trúc trang
headings = re.findall(r'<h[23][^>]*>\s*<span[^>]*>([^<]+)</span>', html)
print(f"\nHeadings (h2/h3): {headings[:30]}")

# Tìm các table hoặc div có chứa "Floor"
floor_sections = re.findall(r'Floor\s+\d+', html)
print(f"\nFloor mentions (unique): {sorted(set(floor_sections))}")

# Tìm enemy names — thường trong các span/td
# Fandom dùng class "wikitable" cho bảng
tables = re.findall(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)
print(f"\nWikitables found: {len(tables)}")
for i, t in enumerate(tables[:2]):
    # Strip tags để xem text
    text = re.sub(r'<[^>]+>', ' ', t)
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"\nTable {i+1} (first 500 chars):\n{text[:500]}")

# Lưu HTML để xem thêm
with open("explore_fandom_abyss.html", "w", encoding="utf-8") as f:
    f.write(html)
print(f"\n→ Đã lưu HTML ra explore_fandom_abyss.html")
print("DONE.")