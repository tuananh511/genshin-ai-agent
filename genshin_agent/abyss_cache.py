"""
abyss_cache.py — Cache JSON cho Spiral Abyss data (đã dịch).

Tách biệt hoàn toàn khỏi database.py của Enka pipeline (đúng Constraint).
Cache theo period_title (vd "Spiral Abyss/Floors/2026-06-16").
Kỳ mới = cache tự expire (key không khớp → miss → fetch lại).
Không có TTL thời gian — kỳ Abyss reset ~1 tháng, period_title thay đổi
là tín hiệu duy nhất cần thiết để invalidate.
"""
from __future__ import annotations

import json
from pathlib import Path

CACHE_FILE = Path("abyss_cache.json")


def _load() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save(data: dict) -> None:
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get(period_title: str) -> dict | None:
    """Trả về cached data (dict) nếu có, None nếu miss."""
    return _load().get(period_title)


def put(period_title: str, payload: dict) -> None:
    """Lưu payload vào cache theo period_title."""
    data = _load()
    # Chỉ giữ kỳ hiện tại — xoá các kỳ cũ để cache không phình mãi
    data = {period_title: payload}
    _save(data)
