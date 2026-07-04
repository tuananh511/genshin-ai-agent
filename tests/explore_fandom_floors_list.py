"""
explore_fandom_floors_list.py — In wikitext trang Spiral_Abyss/Floors
Mục đích: xác nhận cấu trúc danh sách các kỳ (để biết cách lấy URL kỳ mới nhất)
"""
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://genshin-impact.fandom.com/api.php"

r = requests.get(BASE, params={
    "action": "parse", "page": "Spiral_Abyss/Floors",
    "prop": "wikitext", "format": "json",
}, headers=HEADERS, timeout=15)

print("status:", r.status_code)
data = r.json()
if "error" in data:
    print("ERROR:", data["error"])
else:
    wikitext = data["parse"]["wikitext"]["*"]
    print("length:", len(wikitext))
    print(wikitext)