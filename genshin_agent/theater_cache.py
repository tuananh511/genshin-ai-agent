"""
theater_cache.py — Cache JSON cho Imaginarium Theater data.

Mirror abyss_cache.py 100% logic, chỉ đổi CACHE_FILE — bắt buộc phải tách
file riêng vì put() ở đây (giống Abyss) luôn xoá hết key cũ, chỉ giữ 1 kỳ
hiện tại. Nếu dùng chung file với Abyss, chạy 2 event trong 1 lần main.py
sẽ làm event chạy sau xoá mất cache của event chạy trước.
"""
from __future__ import annotations

import json
from genshin_agent.paths import app_base_dir

CACHE_FILE = app_base_dir() / "theater_cache.json"


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
    data = {period_title: payload}
    _save(data)