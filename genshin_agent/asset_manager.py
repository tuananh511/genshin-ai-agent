import json
import requests
from datetime import datetime, timedelta
from genshin_agent.database import get_connection


ENKA_CHARACTERS_URL = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/characters.json"
ENKA_LOC_URL        = "https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/loc.json"
TEXTMAP_VI_URL      = "https://raw.githubusercontent.com/DimbreathBot/AnimeGameData/master/TextMap/TextMapVI.json"
TEXTMAP_EN_URL      = "https://raw.githubusercontent.com/DimbreathBot/AnimeGameData/master/TextMap/TextMapEN.json"
YATTA_WEAPON_URL    = "https://gi.yatta.moe/api/v2/vi/weapon"
YATTA_RELIQUARY_URL = "https://gi.yatta.moe/api/v2/vi/reliquary"
ENKA_ICON_BASE      = "https://enka.network/ui"
# Thêm 2 URL constant, cạnh YATTA_WEAPON_URL / YATTA_RELIQUARY_URL hiện có
YATTA_WEAPON_EN_URL    = "https://gi.yatta.moe/api/v2/en/weapon"
YATTA_RELIQUARY_EN_URL = "https://gi.yatta.moe/api/v2/en/reliquary"

USER_AGENT      = "genshin-ai-agent/3.0 (personal-project)"
CACHE_TTL_DAYS  = 7
SKILL_ORDER_LABELS = ["Đòn thường", "Kỹ năng nguyên tố", "Trảm nộ"]


def _cache_get(key: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT value, fetched_at FROM asset_cache WHERE key = ?", (key,)
    ).fetchone()
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
    Mọi module khác chỉ gọi qua instance `asset_manager` ở cuối file — không tự tải JSON riêng.

    Thứ tự tra tên vũ khí/artifact:
      1. TextMapVI (AnimeGameData) — đầy đủ nhất
      2. loc.json (Enka)
      3. TextMapEN
      4. gi.yatta.moe /vi/weapon hoặc /vi/reliquary — fallback cho ~11 hash không có trong TextMap
    """

    def __init__(self):
        self._characters:       dict | None = None
        self._loc_vi:           dict | None = None
        self._loc_en: dict | None = None
        self._textmap_vi:       dict | None = None
        self._textmap_en:       dict | None = None
        self._en_reverse:       dict | None = None
        self._yatta_weapons:    dict | None = None
        self._yatta_reliquaries: dict | None = None
        # Trong class AssetManager, thêm vào __init__:
        self._yatta_weapons_en:    dict | None = None
        self._yatta_reliquaries_en: dict | None = None
        self._weapon_en_reverse:   dict | None = None
        self._set_en_reverse:      dict | None = None

    # ── Enka / TextMap assets ────────────────────────────────────────────────

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
    def loc_en(self) -> dict:
        if self._loc_en is None:
            cached = _cache_get("enka_loc_en")
            if cached:
                print("  [cache] loc.json (en) từ cache")
                self._loc_en = cached
            else:
                print("  [fetch] Tải loc.json (en) từ Enka...")
                all_loc = _fetch_json(ENKA_LOC_URL)
                self._loc_en = all_loc.get("en", {})
                _cache_set("enka_loc_en", self._loc_en)
        return self._loc_en

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

    # ── Yatta fallback assets ────────────────────────────────────────────────

    @property
    def yatta_weapons(self) -> dict:
        """Weapon list từ gi.yatta.moe — key str(weaponId), value dict có 'name'."""
        if self._yatta_weapons is None:
            cached = _cache_get("yatta_weapons")
            if cached:
                print("  [cache] yatta weapons từ cache")
                self._yatta_weapons = cached
            else:
                print("  [fetch] Tải weapon list từ gi.yatta.moe...")
                try:
                    data = _fetch_json(YATTA_WEAPON_URL)
                    self._yatta_weapons = data.get("data", {}).get("items", {})
                    _cache_set("yatta_weapons", self._yatta_weapons)
                except Exception as e:
                    print(f"  [warn] Không tải được yatta weapons: {e}")
                    self._yatta_weapons = {}
        return self._yatta_weapons

    @property
    def yatta_reliquaries(self) -> dict:
        """Artifact set list từ gi.yatta.moe — key str(setId), value dict có 'name'."""
        if self._yatta_reliquaries is None:
            cached = _cache_get("yatta_reliquaries")
            if cached:
                print("  [cache] yatta reliquaries từ cache")
                self._yatta_reliquaries = cached
            else:
                print("  [fetch] Tải reliquary list từ gi.yatta.moe...")
                try:
                    data = _fetch_json(YATTA_RELIQUARY_URL)
                    self._yatta_reliquaries = data.get("data", {}).get("items", {})
                    _cache_set("yatta_reliquaries", self._yatta_reliquaries)
                except Exception as e:
                    print(f"  [warn] Không tải được yatta reliquaries: {e}")
                    self._yatta_reliquaries = {}
        return self._yatta_reliquaries

    # 2 property mới, đặt cạnh yatta_weapons / yatta_reliquaries hiện có
    @property
    def yatta_weapons_en(self) -> dict:
        """Weapon list bản EN từ gi.yatta.moe — dùng để tra 'EN name -> id' (guide nguồn ngoài luôn ghi tên EN)."""
        if self._yatta_weapons_en is None:
            cached = _cache_get("yatta_weapons_en")
            if cached:
                print("  [cache] yatta weapons (en) từ cache")
                self._yatta_weapons_en = cached
            else:
                print("  [fetch] Tải weapon list EN từ gi.yatta.moe...")
                try:
                    data = _fetch_json(YATTA_WEAPON_EN_URL)
                    self._yatta_weapons_en = data.get("data", {}).get("items", {})
                    _cache_set("yatta_weapons_en", self._yatta_weapons_en)
                except Exception as e:
                    print(f"  [warn] Không tải được yatta weapons EN: {e}")
                    self._yatta_weapons_en = {}
        return self._yatta_weapons_en

    @property
    def yatta_reliquaries_en(self) -> dict:
        """Reliquary set list bản EN từ gi.yatta.moe — dùng để tra 'EN name -> id'."""
        if self._yatta_reliquaries_en is None:
            cached = _cache_get("yatta_reliquaries_en")
            if cached:
                print("  [cache] yatta reliquaries (en) từ cache")
                self._yatta_reliquaries_en = cached
            else:
                print("  [fetch] Tải reliquary list EN từ gi.yatta.moe...")
                try:
                    data = _fetch_json(YATTA_RELIQUARY_EN_URL)
                    self._yatta_reliquaries_en = data.get("data", {}).get("items", {})
                    _cache_set("yatta_reliquaries_en", self._yatta_reliquaries_en)
                except Exception as e:
                    print(f"  [warn] Không tải được yatta reliquaries EN: {e}")
                    self._yatta_reliquaries_en = {}
        return self._yatta_reliquaries_en
    # ── Name resolution ──────────────────────────────────────────────────────

    def resolve_name(self, name_hash) -> str:
        """Tra tên theo TextMapVI → loc.json → TextMapEN.
        Trả '(chưa rõ tên)' nếu không nguồn nào có — không suy đoán."""
        h = str(name_hash)
        for source in (self.textmap_vi, self.loc_vi, self.textmap_en):
            if h in source:
                return source[h]
        return "(chưa rõ tên)"

    def get_weapon_name(self, weapon_id: int, name_hash=None) -> str:
        """Tra tên vũ khí theo thứ tự:
          1. resolve_name(hash) từ TextMap/loc.json  — nếu caller truyền hash
          2. gi.yatta.moe weapon list theo weaponId  — fallback
          3. '(chưa rõ tên #weapon_id)'              — không suy đoán
        """
        if name_hash is not None:
            name = self.resolve_name(name_hash)
            if not name.startswith("(chưa rõ"):
                return name

        entry = self.yatta_weapons.get(str(weapon_id))
        if entry and entry.get("name"):
            return entry["name"]

        return f"(chưa rõ tên #{weapon_id})"

    def get_reliquary_name(self, set_id: int, name_hash=None) -> str:
        """Tra tên artifact set theo thứ tự:
          1. resolve_name(hash) từ TextMap/loc.json  — nếu caller truyền hash
          2. gi.yatta.moe reliquary list theo setId  — fallback
          3. '(chưa rõ tên #set_id)'                 — không suy đoán
        """
        if name_hash is not None:
            name = self.resolve_name(name_hash)
            if not name.startswith("(chưa rõ"):
                return name

        entry = self.yatta_reliquaries.get(str(set_id))
        if entry and entry.get("name"):
            return entry["name"]

        return f"(chưa rõ tên #{set_id})"

    # ── Utilities ────────────────────────────────────────────────────────────

    @staticmethod
    def enka_icon_url(icon_name: str) -> str:
        return f"{ENKA_ICON_BASE}/{icon_name}.png" if icon_name else ""

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().replace("'", "'").split())

    # THAY THẾ translate_en_name + translate_set_label cũ (bỏ hẳn, không dùng TextMap cho việc này nữa)
    def translate_weapon_name_en(self, en_name: str) -> str:
        """Dịch tên vũ khí EN (từ guide nguồn ngoài) sang tiếng Việt, tra qua ID chung
        giữa bản /en/ và /vi/ của gi.yatta.moe — không dùng TextMap (TextMap không chứa tên vật phẩm)."""
        if self._weapon_en_reverse is None:
            self._weapon_en_reverse = {
                self._normalize(v["name"]): k for k, v in self.yatta_weapons_en.items()
            }
        weapon_id = self._weapon_en_reverse.get(self._normalize(en_name))
        if weapon_id is None:
            return en_name
        vi_entry = self.yatta_weapons.get(weapon_id)
        return vi_entry["name"] if vi_entry and vi_entry.get("name") else en_name

    def translate_set_label_en(self, label: str) -> str:
        """'Golden Troupe (4)' -> 'Đoàn Hát Hoàng Kim (4)' — giữ số mảnh, dịch tên set qua ID chung
        giữa bản /en/ và /vi/ của gi.yatta.moe."""
        if "(" in label:
            base, _, suffix = label.rpartition(" (")
            base = base.strip()
            suffix_full = f" ({suffix}"
        else:
            base, suffix_full = label.strip(), ""

        if self._set_en_reverse is None:
            self._set_en_reverse = {
                self._normalize(v["name"]): k for k, v in self.yatta_reliquaries_en.items()
            }
        set_id = self._set_en_reverse.get(self._normalize(base))
        if set_id is None:
            return label
        vi_entry = self.yatta_reliquaries.get(set_id)
        vi_name = vi_entry["name"] if vi_entry and vi_entry.get("name") else base
        return f"{vi_name}{suffix_full}"

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
        self._yatta_weapons = self._yatta_reliquaries = None
        conn = get_connection()
        for key in ("enka_characters", "enka_loc_vi", "textmap_vi", "textmap_en",
                    "yatta_weapons", "yatta_reliquaries","yatta_weapons_en", "yatta_reliquaries_en"):
            conn.execute("DELETE FROM asset_cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()
        _ = self.characters, self.loc_vi, self.textmap_vi, self.textmap_en
        # yatta lazy-load khi cần, không cần preload ở đây
        print("  [info] Đã cập nhật toàn bộ dữ liệu tĩnh")

    def resolve_name_en(self, name_hash) -> str:
        """Tra tên tiếng Anh riêng — dùng để build slug cho nguồn ngoài (genshin-builds.com)."""
        h = str(name_hash)
        for source in (self.textmap_en, self.loc_en):
            if h in source:
                return source[h]
        return ""

    def get_avatar_name_en(self, avatar_id: int) -> str:
        char_data = self.characters.get(str(avatar_id), {})
        name_hash = char_data.get("NameTextMapHash")
        return self.resolve_name_en(name_hash) if name_hash else ""


asset_manager = AssetManager()