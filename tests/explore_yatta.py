"""
explore_yatta.py — Chạy script này trên máy của bạn để xác nhận:
  1. gi.yatta.moe/api/v2/vi/weapon  → fallback tên vũ khí cho AssetManager
  2. gi.yatta.moe/api/v2/vi/reliquary → fallback tên Thánh Di Vật
  3. gi.yatta.moe/api/v2/vi/tower    → dữ liệu Spiral Abyss cho Planner

Chạy: python explore_yatta.py
Không cần cài thêm thư viện (chỉ dùng requests đã có trong project).
"""

import json
import requests

BASE = "https://gi.yatta.moe/api/v2/vi"
HEADERS = {"User-Agent": "genshin-ai-agent/3.0 explore-script"}

# ─── Các hash bị thiếu trong TextMap — dùng để test fallback ──────────────────
# Đây là weaponId thật lấy từ Enka mà AssetManager hiện trả "(chưa rõ tên)"
# Thay bằng hash thật từ account của bạn nếu muốn test cụ thể hơn
KNOWN_MISSING_WEAPON_IDS = [
    11416,  # Engulfing Lightning (đã biết bị thiếu)
]


def fetch(endpoint: str) -> dict:
    url = f"{BASE}/{endpoint}"
    print(f"\n→ GET {url}")
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"  Status: {r.status_code}")
    r.raise_for_status()
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
# 1. WEAPON FALLBACK
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("1. WEAPON — gi.yatta.moe/api/v2/vi/weapon")
print("═" * 60)

data = fetch("weapon")

print(f"  retcode   : {data.get('response')}")
items = data.get("data", {}).get("items", {})
print(f"  Tổng vũ khí: {len(items)}")

# Xem cấu trúc 1 item
first_key, first_val = next(iter(items.items()))
print(f"\n  Ví dụ 1 item:")
print(f"    key (str)  : {first_key!r}")
print(f"    id (int)   : {first_val.get('id')}")
print(f"    name       : {first_val.get('name')!r}")
print(f"    fields có  : {list(first_val.keys())}")

# Test tra hash bị thiếu
print(f"\n  Test tra hash bị thiếu:")
for wid in KNOWN_MISSING_WEAPON_IDS:
    # key có thể là string hoặc int — thử cả hai
    val = items.get(str(wid)) or items.get(wid)
    if val:
        print(f"    ID {wid} → name={val.get('name')!r}  ✅ tìm thấy!")
    else:
        print(f"    ID {wid} → ❌ không tìm thấy trong list")

# Lưu sample để xem
with open("explore_weapon_sample.json", "w", encoding="utf-8") as f:
    sample = dict(list(items.items())[:5])
    json.dump(sample, f, ensure_ascii=False, indent=2)
print("\n  → Đã lưu 5 item mẫu ra explore_weapon_sample.json")


# ══════════════════════════════════════════════════════════════════════════════
# 2. RELIQUARY (Thánh Di Vật) FALLBACK
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("2. RELIQUARY — gi.yatta.moe/api/v2/vi/reliquary")
print("═" * 60)

data = fetch("reliquary")

print(f"  retcode     : {data.get('response')}")
items_r = data.get("data", {}).get("items", {})
print(f"  Tổng artifact set: {len(items_r)}")

first_key, first_val = next(iter(items_r.items()))
print(f"\n  Ví dụ 1 item:")
print(f"    key        : {first_key!r}")
print(f"    id         : {first_val.get('id')}")
print(f"    name       : {first_val.get('name')!r}")
print(f"    fields có  : {list(first_val.keys())}")

with open("explore_reliquary_sample.json", "w", encoding="utf-8") as f:
    sample = dict(list(items_r.items())[:5])
    json.dump(sample, f, ensure_ascii=False, indent=2)
print("\n  → Đã lưu 5 item mẫu ra explore_reliquary_sample.json")


# ══════════════════════════════════════════════════════════════════════════════
# 3. SPIRAL ABYSS (TOWER)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("3. ABYSS — gi.yatta.moe/api/v2/vi/tower")
print("═" * 60)

data = fetch("tower")

print(f"  retcode     : {data.get('response')}")
abyss_data = data.get("data", {})
print(f"  Top-level keys: {list(abyss_data.keys())}")

# monsterList
monsters = abyss_data.get("monsterList", {})
print(f"\n  monsterList: {len(monsters)} enemies")
if monsters:
    eid, eval_ = next(iter(monsters.items()))
    print(f"    Ví dụ enemy: id={eid!r}, name={eval_.get('name')!r}, fields={list(eval_.keys())}")

# items (các mùa Abyss)
abyss_items = abyss_data.get("items", {})
print(f"\n  items (mùa Abyss): {len(abyss_items)} mùa")

for season_id, season in abyss_items.items():
    sched = season.get("schedule", {})
    open_ts = sched.get("openTime")
    close_ts = sched.get("closeTime")
    print(f"\n  Mùa ID={season_id}")
    print(f"    openTime  : {open_ts}")
    print(f"    closeTime : {close_ts}")

    # Blessing
    blessing = season.get("blessing", [])
    if blessing:
        print(f"    blessing  : {blessing[0].get('description', '')[:80]!r}")

    # Floors trong Abyssal Moon Spire (schedule)
    floor_list = sched.get("floorList", [])
    print(f"    floors (Spire): {len(floor_list)}")
    for floor in floor_list:
        fid = floor.get("id")
        chambers = floor.get("chamberList", [])
        ley = floor.get("leyLineDisorder", [])
        ley_desc = ley[0].get("description", "")[:60] if ley else "(none)"
        print(f"      Floor {fid}: {len(chambers)} chambers | ley={ley_desc!r}")

        for ch in chambers:
            cid = ch.get("id")
            w1 = ch.get("firstMonsterList", [])
            w2 = ch.get("secondMonsterList", [])
            print(f"        Chamber {cid}: half1={w1}, half2={w2}")

# Lưu full response
with open("explore_abyss_full.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("\n  → Đã lưu full response ra explore_abyss_full.json")

print("\n" + "═" * 60)
print("DONE. Gửi output này lại để xác nhận trước khi code module chính.")
print("═" * 60)