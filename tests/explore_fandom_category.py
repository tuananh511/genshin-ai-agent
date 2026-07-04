"""
explore_fandom_category.py — Lấy danh sách trang trong Category:Spiral Abyss Floors
Mục đích: xác nhận có thể lấy "kỳ mới nhất" trực tiếp qua category members,
không cần parse DPL.
"""
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://genshin-impact.fandom.com/api.php"

r = requests.get(BASE, params={
    "action": "query",
    "list": "categorymembers",
    "cmtitle": "Category:Spiral Abyss Floors",
    "cmsort": "sortkey",
    "cmdir": "descending",
    "cmlimit": "10",
    "format": "json",
}, headers=HEADERS, timeout=15)

print("status:", r.status_code)
data = r.json()
print(data)