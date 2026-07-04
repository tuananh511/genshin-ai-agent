"""
explore_yatta_en.py
Kiểm tra xem gi.yatta.moe có hỗ trợ bản /en/ cho weapon và reliquary không,
và xem cấu trúc dữ liệu trả về có field nào để tra chéo với bản /vi/ (ID chung?).
KHÔNG đoán cấu trúc — chỉ in ra để xem tận mắt trước khi viết parser thật.
"""
import requests

HEADERS = {"User-Agent": "genshin-ai-agent/3.0 (personal-project)"}

for kind in ("weapon", "reliquary"):
    url = f"https://gi.yatta.moe/api/v2/en/{kind}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    print(f"\n=== {url} ===")
    print("status:", resp.status_code)
    if resp.status_code != 200:
        print("body (rút gọn):", resp.text[:300])
        continue
    data = resp.json()
    items = data.get("data", {}).get("items", {})
    print("Tổng số item:", len(items))
    # In thử 1 item bất kỳ để xem cấu trúc field
    sample_id, sample_val = next(iter(items.items()))
    print("Sample ID:", sample_id)
    print("Sample value:", sample_val)

    # Thử tìm đúng "Iron Sting" / tương đương trong bản EN để xác nhận tồn tại
    if kind == "weapon":
        target = [v for v in items.values() if v.get("name") == "Iron Sting"]
        print("Tìm 'Iron Sting':", target)