"""
theater_pipeline.py — Entry point cho toàn bộ Theater (Nhà Hát) data flow.

Khác abyss_pipeline.py: KHÔNG có bước dịch note bằng LLM (theater_collector.py
không có note_en/note_vi) — không cần llm_call. Cache riêng qua theater_cache.py
(xem docstring file đó — lý do phải tách khỏi abyss_cache.py).

Flow:
  1. get_current_period_title() → period_title
  2. Check cache theo period_title
     - HIT  → deserialize → trả về (period_title, acts)
     - MISS → get_current_theater_data() (fetch + parse, raise TheaterDataError
       nếu mùa hiện tại chưa có Battles trên wiki) → serialize → lưu cache
  3. Trả về (period_title, list[ActData])
"""
from __future__ import annotations

from datetime import date

from genshin_agent.theater_cache import get as cache_get, put as cache_put
from genshin_agent.theater_collector import (
    ActData, BattleData, BattleVariant, EnemyWave, EnemyEntry,
    get_current_period_title, get_current_theater_data, TheaterDataError,
)


# --- Serialize / Deserialize (dataclass <-> dict để lưu JSON) ---

def _entry_to_dict(e: EnemyEntry) -> dict:
    return {"name": e.name, "count": e.count, "aura": e.aura, "is_bounty_target": e.is_bounty_target}


def _dict_to_entry(d: dict) -> EnemyEntry:
    return EnemyEntry(name=d["name"], count=d["count"], aura=d["aura"], is_bounty_target=d["is_bounty_target"])


def _variant_to_dict(v: BattleVariant) -> dict:
    return {
        "target": v.target,
        "level_raw": v.level_raw,
        "advantage": v.advantage,
        "enemies": {"waves": [[_entry_to_dict(e) for e in wave] for wave in v.enemies.waves]},
    }


def _dict_to_variant(d: dict) -> BattleVariant:
    return BattleVariant(
        target=d["target"],
        level_raw=d["level_raw"],
        advantage=d["advantage"],
        enemies=EnemyWave(waves=[[_dict_to_entry(e) for e in wave] for wave in d["enemies"]["waves"]]),
    )


def _battle_to_dict(b: BattleData) -> dict:
    return {
        "battle_name": b.battle_name,
        "stage_effects": b.stage_effects,
        "variants": [_variant_to_dict(v) for v in b.variants],
    }


def _dict_to_battle(d: dict) -> BattleData:
    return BattleData(
        battle_name=d["battle_name"],
        stage_effects=d["stage_effects"],
        variants=[_dict_to_variant(v) for v in d["variants"]],
    )


def _act_to_dict(act: ActData) -> dict:
    return {
        "act_name": act.act_name,
        "description": act.description,
        "battles": [_battle_to_dict(b) for b in act.battles],
    }


def _dict_to_act(d: dict) -> ActData:
    return ActData(
        act_name=d["act_name"],
        description=d["description"],
        battles=[_dict_to_battle(b) for b in d["battles"]],
    )


def get_theater_data(
    today: date | None = None,
    force_refresh: bool = False,
) -> tuple[str, list[ActData]]:
    """
    Entry point. Trả về (period_title, list[ActData]).

    force_refresh: bỏ qua cache, fetch lại từ đầu.
    Raise TheaterDataError nếu mùa hiện tại chưa có dữ liệu Battles trên wiki
    (KHÔNG fallback mùa cũ — đúng quyết định đã chốt, xem theater_collector.py).
    """
    period_title = get_current_period_title(today)

    if not force_refresh:
        cached = cache_get(period_title)
        if cached:
            print(f"[Theater] Dùng cache: {period_title}")
            acts = [_dict_to_act(a) for a in cached["acts"]]
            return period_title, acts

    print(f"[Theater] Fetch mới: {period_title}")
    period_title, acts = get_current_theater_data(today)  # tự fetch + parse + raise nếu rỗng

    cache_put(period_title, {"acts": [_act_to_dict(a) for a in acts]})
    print(f"[Theater] Đã lưu cache.")

    return period_title, acts