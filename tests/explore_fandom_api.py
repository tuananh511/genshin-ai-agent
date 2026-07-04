"""
explore_fandom_api.py — Thử MediaWiki API thay vì crawl HTML
"""
import re
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

BASE = "https://genshin-impact.fandom.com/api.php"

# Thử 3 cách gọi API khác nhau
tests = [
    # 1. Parse wikitext của trang Floors/2026-06-16
    {
        "label": "parse page Floors/2026-06-16",
        "params": {
            "action": "parse", "page": "Spiral_Abyss/Floors/2026-06-16",
            "prop": "wikitext", "format": "json",
        }
    },
    # 2. Query revisions (raw wikitext)
    {
        "label": "query revisions Floors/2026-06-16",
        "params": {
            "action": "query", "titles": "Spiral_Abyss/Floors/2026-06-16",
            "prop": "revisions", "rvprop": "content", "rvslots": "main",
            "format": "json",
        }
    },
    # 3. Parse trang Spiral_Abyss chính
    {
        "label": "parse Spiral_Abyss main",
        "params": {
            "action": "parse", "page": "Spiral_Abyss",
            "prop": "sections", "format": "json",
        }
    },
]

for test in tests:
    print(f"\n→ {test['label']}")
    try:
        r = requests.get(BASE, params=test["params"], headers=HEADERS, timeout=15)
        print(f"  Status: {r.status_code}  |  Length: {len(r.text)}")
        if r.status_code == 200:
            data = r.json()
            # Kiểm tra có error không
            if "error" in data:
                print(f"  API error: {data['error']}")
                continue
            # In sample
            text = json.dumps(data, ensure_ascii=False)
            print(f"  Response sample (500 chars): {text[:500]}")
            # Lưu
            fname = f"explore_fandom_{test['label'].replace(' ', '_')[:30]}.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  → Saved {fname}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nDONE.")