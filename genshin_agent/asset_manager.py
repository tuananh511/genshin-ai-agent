import json
import requests
from datetime import datetime, timedelta
from genshin_agent.database import get_connection

ENKA_CHARACTERS_URL = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/characters.json"
ENKA_LOC_URL = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/loc.json"
TEXTMAP_VI_URL = "https://raw.githubusercontent.com/DimbreathBot/AnimeGameData/master/TextMap/TextMapVI.json"
TEXTMAP_EN_URL = "https://raw.githubusercontent.com/DimbreathBot/AnimeGameData/master/TextMap/TextMapEN.json"
ENKA_ICON_BASE = "https://enka.network/ui"

USER_AGENT = "genshin-ai-agent/0.1 (personal-project)"
CACHE_TTL_DAYS = 7
SKILL_ORDER_LABELS = ["Đòn thường", "Kỹ năng nguyên tố", "Trảm nộ"]


def _cache_get(key: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT value, fetched_at FROM asset_cache WHERE key = ?", (key,)).fetchone()
    conn.close()
    if not row:
        return None
    fetched_at = datetime.fromisoformat(row["fetched_at"])
    if datetime.now() - fetched_at > timedelta(days=CACHE_TTL_DAYS):
        return None
    return json.loads(row["value"])


def _cache_set(key: str, value: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO asset_cache (key, value, fetched_at) VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, fetched_at=excluded.fetched_at""",
        (key, json.dumps(value, ensure_ascii=False), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def _fetch_json(url: str) -> dict:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    return resp.json()


class AssetManager:
    """Quản lý tập trung mọi dữ liệu tĩnh (tên nhân vật/vũ khí/artifact, element, skill).
    Mọi module khác chỉ gọi qua instance `asset_manager` ở cuối file — không tự tải JSON riêng."""

    def __init__(self):
        self._characters: dict | None = None
        self._loc_vi: dict | None = None
        self._textmap_vi: dict | None = None
        self._textmap_en: dict | None = None
        self._en_reverse: dict | None = None

    @property
    def characters(self) -> dict:
        if self._characters is None:
            cached = _cache_get("enka_characters")
            if cached:
                print("  [cache] characters.json từ cache")
                self._characters = cached
            else:
                print("  [fetch] Tải characters.json từ Enka...")
                self._characters = _fetch_json(ENKA_CHARACTERS_URL)
                _cache_set("enka_characters", self._characters)
        return self._characters

    @property
    def loc_vi(self) -> dict:
        if self._loc_vi is None:
            cached = _cache_get("enka_loc_vi")
            if cached:
                print("  [cache] loc.json (vi) từ cache")
                self._loc_vi = cached
            else:
                print("  [fetch] Tải loc.json từ Enka...")
                all_loc = _fetch_json(ENKA_LOC_URL)
                self._loc_vi = all_loc.get("vi", all_loc.get("en", {}))
                _cache_set("enka_loc_vi", self._loc_vi)
        return self._loc_vi

    @property
    def textmap_vi(self) -> dict:
        if self._textmap_vi is None:
            cached = _cache_get("textmap_vi")
            if cached:
                print("  [cache] TextMapVI từ cache")
                self._textmap_vi = cached
            else:
                print("  [fetch] Tải TextMapVI (file nặng, có thể mất 10-30s)...")
                self._textmap_vi = _fetch_json(TEXTMAP_VI_URL)
                _cache_set("textmap_vi", self._textmap_vi)
        return self._textmap_vi

    @property
    def textmap_en(self) -> dict:
        if self._textmap_en is None:
            cached = _cache_get("textmap_en")
            if cached:
                print("  [cache] TextMapEN từ cache")
                self._textmap_en = cached
            else:
                print("  [fetch] Tải TextMapEN...")
                self._textmap_en = _fetch_json(TEXTMAP_EN_URL)
                _cache_set("textmap_en", self._textmap_en)
        return self._textmap_en

    def resolve_name(self, name_hash) -> str:
        """Tra tên theo thứ tự: TextMapVI (đầy đủ, đã xác nhận) -> loc.json Enka -> TextMapEN.
        Trả về '(chưa rõ tên)' nếu không nguồn nào có — không suy đoán."""
        h = str(name_hash)
        for source in (self.textmap_vi, self.loc_vi, self.textmap_en):
            if h in source:
                return source[h]
        return "(chưa rõ tên)"
    
    @staticmethod
    def enka_icon_url(icon_name: str) -> str:
        return f"{ENKA_ICON_BASE}/{icon_name}.png" if icon_name else ""
    
    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().replace("'", "'").split())

    def translate_en_name(self, en_name: str) -> str:
        """Dịch tên riêng (vũ khí, set artifact) từ tiếng Anh sang tiếng Việt
        bằng cách tra ngược qua TextMap — không dùng LLM, để khớp đúng tên chính thức.
        So khớp đã chuẩn hoá (chữ thường, khoảng trắng) để khoan dung hơn với khác biệt định dạng."""
        if self._en_reverse is None:
            self._en_reverse = {self._normalize(v): k for k, v in self.textmap_en.items()}
        h = self._en_reverse.get(self._normalize(en_name))
        if h is None:
            return en_name
        return self.textmap_vi.get(h, en_name)
    
    def translate_set_label(self, label: str) -> str:
        """'Golden Troupe (4)' -> 'Đoàn Hát Hoàng Kim (4)' — giữ số mảnh, chỉ dịch tên."""
        if "(" in label:
            base, _, suffix = label.rpartition(" (")
            return f"{self.translate_en_name(base.strip())} ({suffix}"
        return self.translate_en_name(label)

    def get_avatar_name(self, avatar_id: int) -> str:
        char_data = self.characters.get(str(avatar_id), {})
        name_hash = char_data.get("NameTextMapHash")
        return self.resolve_name(name_hash) if name_hash else f"Unknown({avatar_id})"

    def get_avatar_element(self, avatar_id: int) -> str:
        return self.characters.get(str(avatar_id), {}).get("Element", "Unknown")

    def get_skill_name(self, avatar_id: int, skill_id) -> str:
        skill_order = self.characters.get(str(avatar_id), {}).get("SkillOrder", [])
        try:
            index = skill_order.index(int(skill_id))
            return SKILL_ORDER_LABELS[index] if index < len(SKILL_ORDER_LABELS) else f"Kỹ năng khác ({skill_id})"
        except (ValueError, IndexError):
            return f"Talent {skill_id}"

    def refresh_all(self):
        """Tải lại toàn bộ, bỏ qua cache — gọi khi người dùng chọn cập nhật database."""
        self._characters = self._loc_vi = self._textmap_vi = self._textmap_en = None
        conn = get_connection()
        for key in ("enka_characters", "enka_loc_vi", "textmap_vi", "textmap_en"):
            conn.execute("DELETE FROM asset_cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        _ = self.characters, self.loc_vi, self.textmap_vi, self.textmap_en
        print("  [info] Đã cập nhật toàn bộ dữ liệu tĩnh")


asset_manager = AssetManager()