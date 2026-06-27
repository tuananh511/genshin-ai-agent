import requests
import json
from datetime import datetime, timedelta
from genshin_agent.database import get_connection

ENKA_CHARACTERS_URL = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/characters.json"
ENKA_LOC_URL = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/loc.json"

CACHE_TTL_HOURS = 24  # tải lại sau 24 giờ


def _cache_get(key: str) -> dict | None:
    """Đọc từ cache, trả về None nếu không có hoặc đã hết hạn."""
    conn = get_connection()
    row = conn.execute(
        "SELECT value, fetched_at FROM asset_cache WHERE key = ?", (key,)
    ).fetchone()
    conn.close()

    if not row:
        return None

    fetched_at = datetime.fromisoformat(row["fetched_at"])
    if datetime.now() - fetched_at > timedelta(hours=CACHE_TTL_HOURS):
        return None  # hết hạn

    return json.loads(row["value"])


def _cache_set(key: str, value: dict):
    """Lưu vào cache với timestamp hiện tại."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO asset_cache (key, value, fetched_at)
           VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, fetched_at=excluded.fetched_at""",
        (key, json.dumps(value, ensure_ascii=False), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_characters_data() -> dict:
    """
    Trả về dict: avatarId (str) -> {Element, SkillOrder, Skills, NameTextMapHash, ...}
    Cache 24h, chỉ fetch lại khi hết hạn.
    """
    cached = _cache_get("enka_characters")
    if cached:
        print("  [cache] Dùng characters data từ cache")
        return cached

    print("  [fetch] Tải characters.json từ Enka...")
    response = requests.get(ENKA_CHARACTERS_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    _cache_set("enka_characters", data)
    return data


def get_loc_data(lang: str = "en") -> dict:
    """
    Trả về dict: hash (str) -> tên nhân vật/vũ khí/...
    Cache 24h.
    """
    cache_key = f"enka_loc_{lang}"
    cached = _cache_get(cache_key)
    if cached:
        print(f"  [cache] Dùng loc data ({lang}) từ cache")
        return cached

    print(f"  [fetch] Tải loc.json ({lang}) từ Enka...")
    response = requests.get(ENKA_LOC_URL, timeout=15)
    response.raise_for_status()
    all_loc = response.json()
    lang_data = all_loc.get(lang, {})
    _cache_set(cache_key, lang_data)
    return lang_data


def resolve_name(name_hash: str | int, loc: dict) -> str:
    """Tra tên từ hash. Trả về hash gốc nếu không tìm thấy."""
    return loc.get(str(name_hash), str(name_hash))


def get_avatar_name(avatar_id: int, characters: dict, loc: dict) -> str:
    """Tra tên nhân vật từ avatarId."""
    char_data = characters.get(str(avatar_id), {})
    name_hash = char_data.get("NameTextMapHash")
    if not name_hash:
        return f"Unknown({avatar_id})"
    return resolve_name(name_hash, loc)


def get_avatar_element(avatar_id: int, characters: dict) -> str:
    """Tra element của nhân vật từ avatarId."""
    char_data = characters.get(str(avatar_id), {})
    return char_data.get("Element", "Unknown")

SKILL_ORDER_LABELS = ["Đòn thường", "Kỹ năng nguyên tố", "Trảm nộ"]

def get_skill_name(avatar_id: int, skill_id: str, characters: dict) -> str:
    """Map skill_id -> tên dễ đọc, dựa vào vị trí của nó trong SkillOrder."""
    char_data = characters.get(str(avatar_id), {})
    skill_order = char_data.get("SkillOrder", [])
    try:
        index = skill_order.index(int(skill_id))
        return SKILL_ORDER_LABELS[index] if index < len(SKILL_ORDER_LABELS) else f"Kỹ năng khác ({skill_id})"
    except (ValueError, IndexError):
        return f"Talent {skill_id}"