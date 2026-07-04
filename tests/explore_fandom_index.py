"""
explore_fandom_index.py — In wikitext trang index Spiral_Abyss
Mục đích: xác nhận cấu trúc list các kỳ (để biết cách lấy kỳ mới nhất)
"""
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://genshin-impact.fandom.com/api.php"

r = requests.get(BASE, params={
    "action": "parse", "page": "Spiral_Abyss",
    "prop": "wikitext", "format": "json",
}, headers=HEADERS, timeout=15)

print("status:", r.status_code)
wikitext = r.json()["parse"]["wikitext"]["*"]
print("length:", len(wikitext))
print(wikitext)