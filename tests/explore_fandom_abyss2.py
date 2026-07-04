"""
explore_fandom_abyss2.py — Thử headers browser thật + fallback URLs
"""
import re
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
    "Referer": "https://genshin-impact.fandom.com/wiki/Spiral_Abyss",
}

urls = [
    "https://genshin-impact.fandom.com/wiki/Spiral_Abyss/Floors/2026-06-16",
    "https://genshin-impact.fandom.com/wiki/Spiral_Abyss",
]

for url in urls:
    print(f"\n→ GET {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  Status: {r.status_code}  |  Length: {len(r.text)}")
        if r.status_code == 200:
            headings = re.findall(r'<h[23][^>]*>\s*<span[^>]*>([^<]+)</span>', r.text)
            print(f"  Headings: {headings[:20]}")
            floors = sorted(set(re.findall(r'Floor\s+\d+', r.text)))
            print(f"  Floor mentions: {floors}")
            # Lưu
            fname = url.split("/")[-1] + ".html"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(r.text)
            print(f"  → Saved {fname}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nDONE.")