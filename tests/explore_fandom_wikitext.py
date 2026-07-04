"""
explore_fandom_wikitext.py — In full wikitext để xem cấu trúc enemy list
"""
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
BASE = "https://genshin-impact.fandom.com/api.php"

r = requests.get(BASE, params={
    "action": "parse", "page": "Spiral_Abyss/Floors/2026-06-16",
    "prop": "wikitext", "format": "json",
}, headers=HEADERS, timeout=15)

wikitext = r.json()["parse"]["wikitext"]["*"]
print(wikitext)