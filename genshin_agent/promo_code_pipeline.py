"""promo_code_pipeline.py — Lấy danh sách Promotional Code (gift code) đang active
cho Genshin Impact từ Fandom Wiki, qua MediaWiki API (giống cơ chế abyss_collector.py
đã dùng, để né bot-detection khi fetch trực tiếp trang /wiki/).

Nguồn: https://genshin-impact.fandom.com/wiki/Promotional_Code
Cơ chế: parse template {{Code Row|code|server|reward|discovery|expiry|notes}}
trong wikitext -- cấu trúc này lấy từ wikitext thật (session 2026-07-02), không đoán.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from datetime import date

import requests

HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
API_BASE   = "https://genshin-impact.fandom.com/api.php"
PAGE_TITLE = "Promotional_Code"

SERVER_LABELS = {
    "G":   "Toàn server (trừ CN)",
    "A":   "Tất cả server",
    "SEA": "Server Đông Nam Á",
    "CN":  "Server Trung Quốc",
    "NA":  "Server Bắc Mỹ",
    "EU":  "Server Châu Âu",
    "SAR": "Server TW/HK/Macao",
}

_CODE_ROW_RE      = re.compile(r"\{\{Code Row\|(.*?)\}\}", re.DOTALL)
_HTML_COMMENT_RE  = re.compile(r"<!--.*?-->", re.DOTALL)
_REF_TAG_RE       = re.compile(r"<ref>.*?</ref>", re.DOTALL)


class PromoCodeError(Exception):
    """Raise khi không lấy được dữ liệu thật -- không bao giờ tự suy đoán thay thế."""


@dataclass
class PromoCode:
    code: str
    server_label: str
    rewards: list[tuple[str, int]] = field(default_factory=list)
    discovery_date: str = ""
    expiry_label: str = ""   # "hết hạn YYYY-MM-DD" / "chưa rõ ngày hết hạn" / "vô thời hạn"
    notes: str = ""


def fetch_wikitext() -> str:
    resp = requests.get(
        API_BASE,
        params={"action": "parse", "page": PAGE_TITLE, "prop": "wikitext", "format": "json"},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise PromoCodeError(f"Fandom API lỗi khi fetch trang '{PAGE_TITLE}': {data['error']}")
    return data["parse"]["wikitext"]["*"]


def _parse_reward_str(reward_str: str) -> list[tuple[str, int]]:
    rewards = []
    for token in reward_str.split(";"):
        token = token.strip()
        if not token:
            continue
        if "*" in token:
            name, _, count = token.rpartition("*")
            try:
                rewards.append((name.strip(), int(count.strip())))
            except ValueError:
                rewards.append((token, 1))
        else:
            rewards.append((token, 1))
    return rewards


def _parse_expiry_label(expiry_raw: str) -> str:
    expiry_raw = expiry_raw.strip()
    if expiry_raw == "unknown":
        return "chưa rõ ngày hết hạn"
    if expiry_raw == "indef":
        return "vô thời hạn"
    return f"hết hạn {expiry_raw}"


def _is_expired(expiry_raw: str) -> bool:
    """Lọc phòng hờ trường hợp trang wiki cập nhật trễ, code đã hết hạn thật nhưng
    vẫn còn nằm trong khu ==Active Codes==. Không parse được ngày -> KHÔNG tự suy
    đoán là hết hạn (an toàn hơn là giữ lại, để người dùng tự kiểm tra)."""
    expiry_raw = expiry_raw.strip()
    if expiry_raw in ("unknown", "indef"):
        return False
    try:
        y, m, d = (int(p) for p in expiry_raw.split("-"))
        return date(y, m, d) < date.today()
    except ValueError:
        return False


def parse_active_codes(wikitext: str) -> list[PromoCode]:
    text = _HTML_COMMENT_RE.sub("", wikitext)
    text = _REF_TAG_RE.sub("", text)

    # Chỉ lấy phần trong section "Active Codes" -- phòng hờ khi hàm này được tái
    # sử dụng cho case fetch nguyên trang (có cả section History phía dưới).
    section_match = re.search(r"==\s*Active Codes\s*==(.*?)(?:\n==|\Z)", text, re.DOTALL)
    section_text = section_match.group(1) if section_match else text

    results: list[PromoCode] = []
    for m in _CODE_ROW_RE.finditer(section_text):
        parts = [p.strip() for p in m.group(1).split("|")]
        positional = [p for p in parts if "=" not in p]  # bỏ named param (notacode=, ref=...)
        if len(positional) < 5:
            continue  # dữ liệu không đủ field -- bỏ qua, không đoán field thiếu
        code, server, reward_str, discovery, expiry = positional[:5]
        notes = positional[5] if len(positional) > 5 else ""

        if _is_expired(expiry):
            continue

        results.append(PromoCode(
            code=code,
            server_label=SERVER_LABELS.get(server, server),
            rewards=_parse_reward_str(reward_str),
            discovery_date=discovery,
            expiry_label=_parse_expiry_label(expiry),
            notes=notes,
        ))
    return results


def get_active_promo_codes() -> list[PromoCode]:
    wikitext = fetch_wikitext()
    return parse_active_codes(wikitext)