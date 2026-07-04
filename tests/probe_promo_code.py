# probe_promo_code.py — chạy 1 lần để xem wikitext thật của trang Promotional Code
import requests
import json

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
API_BASE = "https://genshin-impact.fandom.com/api.php"

resp = requests.get(
    API_BASE,
    params={"action": "parse", "page": "Promotional_Code", "prop": "wikitext", "format": "json"},
    headers=HEADERS,
    timeout=15,
)
resp.raise_for_status()
data = resp.json()
wikitext = data["parse"]["wikitext"]["*"]

with open("promo_code_wikitext.txt", "w", encoding="utf-8") as f:
    f.write(wikitext)

print(f"Đã lưu {len(wikitext)} ký tự vào promo_code_wikitext.txt")
# In thử đoạn có chữ "Active" để xem nhanh cấu trúc
idx = wikitext.find("Active")
print(wikitext[idx:idx+1500] if idx != -1 else "(không thấy chữ 'Active')")