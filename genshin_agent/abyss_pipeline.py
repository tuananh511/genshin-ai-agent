"""
abyss_pipeline.py — Entry point cho toàn bộ Abyss data flow.

Flow:
  1. get_current_period_title() → period_title
  2. Check cache (abyss_cache.py) theo period_title
     - HIT  → deserialize → trả về (period_title, floors) luôn, không gọi mạng/LLM
     - MISS → fetch wikitext → parse floors → dịch note_en → serialize → lưu cache
  3. Trả về (period_title, list[FloorData])

Cách dùng từ main.py hoặc module khác:
    from genshin_agent.abyss_pipeline import get_abyss_data
    period, floors = get_abyss_data(llm_call=safe_llm_call)
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date

from genshin_agent.abyss_cache import get as cache_get, put as cache_put
from genshin_agent.abyss_collector import (
    EnemyWave, ChamberData, FloorData,
    get_current_period_title, fetch_period_wikitext, parse_wikitext,
)
from genshin_agent.abyss_note_translator import translate_all_notes


# --- Serialize / Deserialize (dataclass <-> dict để lưu JSON) ---

def _floor_to_dict(floor: FloorData) -> dict:
    d = asdict(floor)
    # asdict không biết note_vi (set động), cần thêm thủ công
    d["chambers"] = []
    for ch in floor.chambers:
        ch_d = {
            "level": ch.level,
            "target": ch.target,
            "half1": {"waves": ch.half1.waves},
            "half2": {"waves": ch.half2.waves},
            "note_en": ch.note_en,
            "note_vi": getattr(ch, "note_vi", ""),
        }
        d["chambers"].append(ch_d)
    return d


def _dict_to_floor(d: dict) -> FloorData:
    chambers = []
    for ch_d in d["chambers"]:
        ch = ChamberData(
            level=ch_d["level"],
            target=ch_d["target"],
            half1=EnemyWave(waves=[list(map(tuple, w)) for w in ch_d["half1"]["waves"]]),
            half2=EnemyWave(waves=[list(map(tuple, w)) for w in ch_d["half2"]["waves"]]),
            note_en=ch_d["note_en"],
        )
        ch.note_vi = ch_d.get("note_vi", "")
        chambers.append(ch)
    return FloorData(
        floor_number=d["floor_number"],
        ley_line_disorder=d["ley_line_disorder"],
        chambers=chambers,
    )


def get_abyss_data(
    llm_call: callable,
    today: date | None = None,
    force_refresh: bool = False,
) -> tuple[str, list[FloorData]]:
    """
    Entry point. Trả về (period_title, list[FloorData]) với note_vi đã điền.

    llm_call: callable(prompt: str) -> str  (thường là safe_llm_call từ llm_client.py)
    force_refresh: bỏ qua cache, fetch lại từ đầu (dùng khi debug hoặc cần cập nhật).
    """
    period_title = get_current_period_title(today)

    # --- Check cache ---
    if not force_refresh:
        cached = cache_get(period_title)
        if cached:
            print(f"[Abyss] Dùng cache: {period_title}")
            floors = [_dict_to_floor(f) for f in cached["floors"]]
            return period_title, floors

    # --- Cache miss: fetch + parse + dịch ---
    print(f"[Abyss] Fetch mới: {period_title}")
    wikitext = fetch_period_wikitext(period_title)
    floors = parse_wikitext(wikitext)

    print(f"[Abyss] Dịch note spawn order...")
    floors = translate_all_notes(floors, llm_call)

    # --- Lưu cache ---
    payload = {"floors": [_floor_to_dict(f) for f in floors]}
    cache_put(period_title, payload)
    print(f"[Abyss] Đã lưu cache.")

    return period_title, floors
