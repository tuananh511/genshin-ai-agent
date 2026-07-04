"""
explore_yatta2.py — Xác nhận:
  1. Mùa Abyss hiện tại (openTime gần nhất <= now)
  2. Enemy name có rỗng hay không — và cách resolve
  3. Floor ID mapping (1096 → Floor 11, 1097 → Floor 12?)
  4. Blessing / LeyLine có data trong mùa hiện tại không

Chạy: python explore_yatta2.py
"""

import json
import time
import datetime
import requests

BASE = "https://gi.yatta.moe/api/v2/vi"
HEADERS = {"User-Agent": "genshin-ai-agent/3.0 explore-script"}


def fetch(endpoint: str) -> dict:
    url = f"{BASE}/{endpoint}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


data = fetch("tower")
abyss_data = data["data"]
monsters = abyss_data["monsterList"]
items = abyss_data["items"]

now = time.time()
print(f"Now (unix): {int(now)}  →  {datetime.datetime.fromtimestamp(now)}")

# ── 1. Tìm mùa hiện tại ──────────────────────────────────────────────────────
print("\n" + "═"*60)
print("1. TÌM MÙA HIỆN TẠI")
print("═"*60)

seasons = []
for sid, season in items.items():
    sched = season.get("schedule", {})
    open_ts = sched.get("openTime") or season.get("openTime")
    close_ts = sched.get("closeTime") or season.get("closeTime")
    seasons.append({
        "id": sid,
        "open_ts": open_ts,
        "close_ts": close_ts,
        "open_dt": datetime.datetime.fromtimestamp(open_ts) if open_ts else None,
        "close_dt": datetime.datetime.fromtimestamp(close_ts) if close_ts else None,
        "data": season,
    })
    print(f"  Mùa {sid}: open={datetime.datetime.fromtimestamp(open_ts) if open_ts else 'N/A'}"
          f"  close={datetime.datetime.fromtimestamp(close_ts) if close_ts else 'N/A'}")

# Mùa hiện tại = openTime <= now, gần nhất
current = max(
    (s for s in seasons if s["open_ts"] and s["open_ts"] <= now),
    key=lambda s: s["open_ts"],
    default=None,
)
if not current:
    current = max(seasons, key=lambda s: s["open_ts"] or 0)

print(f"\n  → Mùa được chọn: ID={current['id']}, open={current['open_dt']}")

# ── 2. Blessing và LeyLine trong mùa hiện tại ────────────────────────────────
print("\n" + "═"*60)
print("2. BLESSING & LEY LINE TRONG MÙA HIỆN TẠI")
print("═"*60)

sched = current["data"].get("schedule", {})
blessing_list = current["data"].get("blessing", [])
print(f"  blessing (raw): {json.dumps(blessing_list, ensure_ascii=False)[:200]}")

floor_list = sched.get("floorList", [])
print(f"\n  Tổng floors trong Spire: {len(floor_list)}")
for floor in floor_list:
    fid = floor.get("id")
    ley = floor.get("leyLineDisorder", [])
    print(f"\n  Floor raw_id={fid}")
    print(f"    leyLineDisorder: {json.dumps(ley, ensure_ascii=False)[:200]}")
    chambers = floor.get("chamberList", [])
    for ch in chambers:
        print(f"    Chamber {ch['id']}: lvl={ch.get('monsterLevel')} "
              f"| w1={ch.get('firstMonsterList')} "
              f"| w2={ch.get('secondMonsterList')}")

# ── 3. Enemy name resolution ──────────────────────────────────────────────────
print("\n" + "═"*60)
print("3. ENEMY NAME RESOLUTION")
print("═"*60)

print(f"  Tổng enemies trong monsterList: {len(monsters)}")

# Xem vài enemy
for i, (eid, ev) in enumerate(monsters.items()):
    if i >= 5:
        break
    print(f"  id={eid!r}  name={ev.get('name')!r}  icon={ev.get('icon','')[:60]!r}")

# Lấy tất cả enemy IDs từ mùa hiện tại và thử resolve tên
all_enemy_ids = set()
for floor in floor_list:
    for ch in floor.get("chamberList", []):
        all_enemy_ids.update(ch.get("firstMonsterList", []))
        all_enemy_ids.update(ch.get("secondMonsterList") or [])

print(f"\n  Enemy IDs trong mùa hiện tại: {sorted(all_enemy_ids)}")
print(f"\n  Resolve tên:")
resolved = 0
missing = 0
for eid in sorted(all_enemy_ids):
    entry = monsters.get(str(eid)) or monsters.get(eid)
    name = entry.get("name", "") if entry else ""
    if name:
        print(f"    {eid} → {name!r}  ✅")
        resolved += 1
    else:
        print(f"    {eid} → (rỗng/không có)  ❌")
        missing += 1

print(f"\n  Resolved: {resolved}/{resolved+missing}")

# ── 4. Floor ID mapping ───────────────────────────────────────────────────────
print("\n" + "═"*60)
print("4. FLOOR ID MAPPING")
print("═"*60)

# Abyss Corridor
entrance = current["data"].get("entrance", {})
corridor_floors = entrance.get("floorList", [])
print(f"  Abyss Corridor: {[f.get('id') for f in corridor_floors]}")
print(f"  Abyssal Moon Spire: {[f.get('id') for f in floor_list]}")
print(f"\n  → Spire floors theo thứ tự index = floor 9,10,11,12")
for i, floor in enumerate(floor_list, start=9):
    print(f"    index {i} = raw_id {floor.get('id')}")

# ── 5. Lưu mùa hiện tại ra file ──────────────────────────────────────────────
with open("explore_abyss_current.json", "w", encoding="utf-8") as f:
    json.dump(current["data"], f, ensure_ascii=False, indent=2)
print(f"\n  → Đã lưu mùa hiện tại ra explore_abyss_current.json")

print("\n" + "═"*60)
print("DONE.")
print("═"*60)