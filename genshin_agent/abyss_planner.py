"""
abyss_planner.py — Sinh cảnh báo counter/tránh element cho từng chamber Abyss.
Logic: code thuần, tra lookup table cố định (không dùng AI).
Enemy không có trong table → báo "chưa có dữ liệu" thay vì đoán.
"""
from __future__ import annotations
from dataclasses import dataclass
from genshin_agent.abyss_collector import FloorData


# ---------------------------------------------------------------------------
# Lookup table: tên enemy → dict gợi ý
# "use"  : element nên dùng để phá khiên / hiệu quả nhất
# "avoid": element nên tránh (bị hấp thụ / heal cho quái)
# "note" : ghi chú thêm (optional)
# Chỉ hardcode những enemy đã xác nhận chắc chắn.
# ---------------------------------------------------------------------------
ENEMY_DATA: dict[str, dict] = {

    # --- Theater-specific: Hilichurl/Mitachurl shield theo màu (đã xác nhận qua Fandom) ---
    "Rock Shieldwall Mitachurl": {
        "use": ["Geo"], "avoid": [],
        "note": "Khiên Geo — vũ khí nặng (Claymore) hoặc phản ứng Overload (Pyro+Electro) cũng phá hiệu quả. Nhắm mặt sau khi phá khiên."
    },
    "Rock Shield Hilichurl Guard": {
        "use": ["Geo"], "avoid": [],
        "note": "Khiên Geo cùng họ với Rock Shieldwall Mitachurl — vũ khí nặng hoặc Geo để phá."
    },

    # --- Nobushi / Kairagi (Inazuma) — KHÔNG có khiên nguyên tố, chỉ tự chuyển
    # tạm sang sát thương nguyên tố khi tấn công (đã xác nhận qua Fandom) ---
    "Nobushi: Kikouban": {"use": [], "avoid": [], "note": "Không có khiên nguyên tố — DPS tự do, chỉ né đòn."},
    "Nobushi: Hitsukeban": {"use": [], "avoid": [], "note": "Không có khiên nguyên tố — DPS tự do, chỉ né đòn."},
    "Nobushi: Jintouban": {"use": [], "avoid": [], "note": "Không có khiên nguyên tố — DPS tự do, chỉ né đòn."},
    "Kairagi: Dancing Thunder": {
        "use": [], "avoid": [],
        "note": "Không có khiên. Đi theo cặp: nếu 1 con chết trước, con còn lại vào trạng thái cuồng nộ (hồi máu + miễn Đóng Băng/hoá đá) — nên hạ cả 2 gần cùng lúc."
    },
    "Kairagi: Fiery Might": {
        "use": [], "avoid": [],
        "note": "Không có khiên. Đi theo cặp: nếu 1 con chết trước, con còn lại vào trạng thái cuồng nộ (hồi máu + miễn Đóng Băng/hoá đá) — nên hạ cả 2 gần cùng lúc."
    },

    # --- Treasure Hoarders — ném thuốc nguyên tố tầm xa, không có khiên (Fandom xác nhận) ---
    "Treasure Hoarders: Crusher": {"use": [], "avoid": [], "note": "Không có khiên — lính cận chiến thường, DPS tự do."},
    "Treasure Hoarders: Pyro Potioneer": {"use": [], "avoid": [], "note": "Không có khiên — chỉ ném thuốc Pyro tầm xa, né đòn là chính."},
    "Treasure Hoarders: Cryo Potioneer": {"use": [], "avoid": [], "note": "Không có khiên — chỉ ném thuốc Cryo tầm xa, né đòn là chính."},
    "Treasure Hoarders: Hydro Potioneer": {"use": [], "avoid": [], "note": "Không có khiên — chỉ ném thuốc Hydro tầm xa, né đòn là chính."},
    "Treasure Hoarders: Electro Potioneer": {"use": [], "avoid": [], "note": "Không có khiên — chỉ ném thuốc Electro tầm xa, né đòn là chính."},

    # --- Eremite elite (Sumeru desert) — không có khiên, có "Infused Form" tự buff
    # tạm thời, đánh liên tục để ngắt (Fandom xác nhận) ---
    "Eremite Stone Enchanter": {"use": [], "avoid": [], "note": "Không có khiên — có 'Infused Form' Geo tự buff tạm thời, đánh liên tục để ngắt sẽ làm nó yếu đi."},
    "Eremite Desert Clearwater": {"use": [], "avoid": [], "note": "Không có khiên — có 'Infused Form' Hydro tự buff tạm thời, đánh liên tục để ngắt sẽ làm nó yếu đi."},
    "Eremite Scorching Loremaster": {"use": [], "avoid": [], "note": "Không có khiên — có 'Infused Form' Pyro tự buff tạm thời, đánh liên tục để ngắt sẽ làm nó yếu đi."},
    "Eremite Daythunder": {"use": [], "avoid": [], "note": "Không có khiên — có 'Infused Form' Electro tự buff tạm thời, đánh liên tục để ngắt sẽ làm nó yếu đi."},

    # --- Ruin-series còn thiếu (mirror Ruin Guard/Grader đã có — cùng họ máy, không có shield) ---
    "Ruin Destroyer": {"use": [], "avoid": [], "note": "Không có shield element — DPS tự do (cùng họ máy Ruin)."},
    "Ruin Scout":      {"use": [], "avoid": [], "note": "Không có shield element — DPS tự do (cùng họ máy Ruin)."},
    "Ruin Defender":   {"use": [], "avoid": [], "note": "Không có shield element — DPS tự do (cùng họ máy Ruin)."},
    "Ruin Cruiser":    {"use": [], "avoid": [], "note": "Không có shield element — DPS tự do (cùng họ máy Ruin)."},

    # --- Primal Construct (Sumeru desert automaton) — chủ yếu Vật Lý, không có khiên ---
    "Primal Construct: Repulsor":  {"use": [], "avoid": [], "note": "Chủ yếu gây sát thương Vật Lý, không có khiên nguyên tố — DPS tự do."},
    "Primal Construct: Reshaper":  {"use": [], "avoid": [], "note": "Chủ yếu gây sát thương Vật Lý, không có khiên nguyên tố — DPS tự do."},
    "Primal Construct: Prospector":{"use": [], "avoid": [], "note": "Chủ yếu gây sát thương Vật Lý, không có khiên nguyên tố — DPS tự do."},

    # --- Natlan Saurian (thú Natlan) — không có khiên, tự đánh bằng nguyên tố riêng của loài.
    # Chỉ 3 loài xác nhận được nguyên tố cụ thể qua Fandom, còn lại xác nhận được
    # "không có khiên" (đặc điểm chung cả nhóm) nhưng CHƯA xác nhận nguyên tố chính xác. ---
    "Tatankasaurus": {"use": [], "avoid": [], "note": "Không có khiên — tự gây sát thương Electro tầm gần khi húc/lao, né đòn là chính."},
    "Tatankasaurus Warrior: Skybreaker":        {"use": [], "avoid": [], "note": "Cùng họ Tatankasaurus — không có khiên, né đòn là chính."},
    "Tatankasaurus Warrior: Spiritlight Chaser":{"use": [], "avoid": [], "note": "Cùng họ Tatankasaurus — không có khiên, né đòn là chính."},
    "Qucusaurus": {"use": [], "avoid": [], "note": "Không có khiên — tự gây sát thương Pyro tầm xa/gần khi bay, né đòn là chính."},
    "Qucusaurus Warrior: Heartstar Hammer": {"use": [], "avoid": [], "note": "Cùng họ Qucusaurus — không có khiên, né đòn là chính."},
    "Qucusaurus Warrior: Blazing Sky":      {"use": [], "avoid": [], "note": "Cùng họ Qucusaurus — không có khiên, né đòn là chính."},
    "Qucusaurus Chick": {"use": [], "avoid": [], "note": "Bản non của Qucusaurus — không có khiên, HP thấp hơn."},
    "Iktomisaurus": {"use": [], "avoid": [], "note": "Không có khiên — tự gây sát thương Cryo tầm xa, né đòn là chính."},
    "Iktomisaurus Chick": {"use": [], "avoid": [], "note": "Bản non của Iktomisaurus — không có khiên, HP thấp hơn."},
    "Yumkasaur Whelp":  {"use": [], "avoid": [], "note": "Thú non Natlan — không có khiên nguyên tố (nguyên tố tấn công cụ thể chưa xác minh được)."},
    "Tepetlisaur Whelp":{"use": [], "avoid": [], "note": "Thú non Natlan — không có khiên nguyên tố (nguyên tố tấn công cụ thể chưa xác minh được)."},

    # --- Black Serpents (Chasm/Khaenri'ah) — KHÔNG dùng Shield khi đánh nhóm này,
    # đòn trúng nhân vật có Shield sẽ cho chúng buff (Fandom xác nhận rõ) ---
    "Black Serpent Knight: Rockbreaker Ax": {
        "use": [], "avoid": [],
        "note": "⚠️ TRÁNH dùng Shield khi giao tranh — đòn trúng nhân vật có Shield sẽ cho chúng buff (tự trừ %HP để buff). Không có khiên nguyên tố cần phá."
    },
    "Shadowy Husk: Standard Bearer": {
        "use": [], "avoid": [],
        "note": "⚠️ TRÁNH dùng Shield khi giao tranh — đòn trúng nhân vật có Shield sẽ cho chúng buff. Bản thân nó tạo khiên Pyro cho đồng minh gần đó khi đánh trúng người có Shield."
    },
    "Shadowy Husk: Line Breaker": {
        "use": [], "avoid": [],
        "note": "⚠️ TRÁNH dùng Shield khi giao tranh — đòn trúng nhân vật có Shield sẽ cho chúng buff (hồi máu đồng minh gần đó)."
    },
    "Shadowy Husk: Defender": {
        "use": [], "avoid": [],
        "note": "⚠️ TRÁNH dùng Shield khi giao tranh — đòn trúng nhân vật có Shield sẽ cho chúng buff. Bản thân nó có khiên chắn phía trước, đánh vòng sau/bên hông."
    },

    # --- Xuanwen Beast — dùng element nào cũng như nhau (Fandom + GameWith xác nhận) ---
    "Xuanwen Beast": {"use": [], "avoid": [], "note": "Không có khiên/né nguyên tố — dùng element nào cũng hiệu quả như nhau, dù bản thân nó đánh bằng Anemo."},

    # --- Hydro Phantasm bản thường — cùng họ Veteran đã có, mirror cùng cơ chế ---
    "Tainted Water-Spouting Phantasm": {
        "use": ["Pyro", "Electro"], "avoid": ["Hydro"],
        "note": "Hydro phantom — không thể Freeze. Luôn nhận Vaporize nếu bị Pyro. (Cùng cơ chế Veteran Tainted Water-Splitting Phantasm, chỉ khác rank.)"
    },
    "Tainted Water-Splitting Phantasm": {
        "use": ["Pyro", "Electro"], "avoid": ["Hydro"],
        "note": "Hydro phantom — không thể Freeze. Luôn nhận Vaporize nếu bị Pyro. (Cùng cơ chế Veteran Tainted Water-Splitting Phantasm, chỉ khác rank.)"
    },

    # --- Whopperflower — nổ diện rộng theo nguyên tố bản thân, không có khiên ---
    "Cryo Whopperflower":   {"use": [], "avoid": [], "note": "Không có khiên — nổ diện rộng gây Cryo khi hết trụ, né ra xa. DPS tự do."},
    "Electro Whopperflower":{"use": [], "avoid": [], "note": "Không có khiên — nổ diện rộng gây Electro khi hết trụ, né ra xa. DPS tự do."},

    # --- Boss theo Act, cơ chế lấy trực tiếp từ act.description (đã scrape) —
    # thêm entry để badge enemy không hiện "chưa có dữ liệu" dù thật ra có mô tả rồi ---
    "Jadeplume Terrorshroom": {
        "use": ["Electro"], "avoid": [],
        "note": "Electro đẩy nhanh vào trạng thái Activated/kiệt sức. Pyro sẽ đốt Burning khiến nó sinh nấm con để chạy trốn — không nên spam Pyro liên tục. Xem mô tả Act phía trên để rõ cơ chế đầy đủ."
    },
    "Aeonblight Drake": {
        "use": [], "avoid": [],
        "note": "Không có khiên cố định — tấn công các lõi (core) lộ ra theo chu kỳ để làm tê liệt và xoá kháng nguyên tố tích luỹ. Xem mô tả Act phía trên."
    },
    "Super-Heavy Landrover: Mechanized Fortress": {
        "use": ["Pyro"], "avoid": [],
        "note": "Pyro làm nó tích nhiệt vào Overheating; nếu tiếp tục sẽ tự kích Cryo Ward hạ nhiệt — ngắt quá trình hạ nhiệt gây rối loạn hoạt động. Xem mô tả Act phía trên."
    },


    # --- Domain Keeper (v6.5, Automaton Asmoday) ---
    # Cơ chế đặc biệt: track số lần nhận Pyro/Hydro/Electro/Cryo → chuyển hình
    # dùng 1 element duy nhất để không kích hoạt biến hình không mong muốn
    "Domain Keeper": {
        "use": [], "avoid": [],
        "note": "Cơ chế biến hình: đánh 3 lần bằng cùng 1 element (Pyro/Hydro/Electro/Cryo) → quái chuyển sang hình element đó và tăng RES element đó. Chọn 1 element làm chủ và bám theo, tránh trộn lẫn."
    },

    # --- Construction Specialist Mek - Pneuma (Fontaine Automaton) ---
    "Construction Specialist Mek - Pneuma": {
        "use": [], "avoid": [],
        "note": "Không có elemental shield — DPS tự do. Cơ chế Pneuma/Ousia không ảnh hưởng đến weakness."
    },

    # --- Thundering Wayob Manifestation (Natlan) ---
    # Khiên non-elemental ban đầu → phá bằng multi-hit. Nếu không phá kịp → sinh elemental shield Electro
    "Thundering Wayob Manifestation": {
        "use": ["Cryo"],
        "avoid": [],
        "note": "Phá khiên ban đầu bằng skill/burst đánh nhiều lần (khiên non-elemental). Nếu không phá kịp sẽ sinh khiên Electro → dùng Cryo để phá. Cẩn thận: Arena hút energy liên tục."
    },

    # --- Veteran Tainted Water-Splitting Phantasm (Hydro, Fontaine) ---
    "Veteran Tainted Water-Splitting Phantasm": {
        "use": ["Pyro", "Electro"],
        "avoid": ["Hydro"],
        "note": "Hydro phantom — không thể Freeze. Luôn nhận Vaporize nếu bị Pyro."
    },

    # --- Secret Source Automaton: Hunter-Seeker (Natlan) ---
    "Secret Source Automaton: Hunter-Seeker": {
        "use": [], "avoid": [],
        "note": "Không có elemental shield. Nightsoul hoặc elemental attack đều hiệu quả."
    },

    # --- Secret Source Automaton: Configuration Device (Natlan boss) ---
    "Secret Source Automaton: Configuration Device": {
        "use": [], "avoid": [],
        "note": "Boss Natlan — không có elemental shield cố định. Nightsoul application hoặc high DPS team."
    },

    # --- Solitary Suanni (Liyue boss, Hydro + Anemo) ---
    "Solitary Suanni": {
        "use": ["Cryo", "Electro"],
        "avoid": ["Hydro"],
        "note": "Khi tụ Hydro-aligned adeptal energy: Freeze để stun, rồi Shatter/Melt phá băng → quái bất động. Cơ chế này quan trọng để DPS tự do."
    },

    # --- The Open-Eyed / Watcher: Fallen Vigil (v6.x boss) ---
    # Cơ chế: track Pyro/Hydro/Electro/Cryo instances, sinh add cùng element đó
    # Bản clone: khiên chỉ phá được bằng Pyro/Electro-infused Swirl (phải dùng Anemo swirl)
    "The Open-Eyed": {
        "use": ["Anemo"],
        "avoid": [],
        "note": "Cơ chế: dùng ít nhất 2 element phản ứng với nhau để boss 'ghi lại'. Bản clone có khiên chỉ phá được bằng Anemo Swirl mang Pyro hoặc Electro — Pyro/Electro attack thường KHÔNG phá được khiên clone."
    },

    # --- Wayward Hermetic Spiritspeaker (Natlan boss, Cryo clones) ---
    "Wayward Hermetic Spiritspeaker": {
        "use": ["Pyro"],
        "avoid": [],
        "note": "Phase bất khả xâm phạm: triệu hồi clone Cryo — dùng Pyro phá clone nhanh nhất để stun boss. Masters of Night-Wind characters (Citlali, Ororon) có thể dừng clone bằng charged attack."
    },
    
    # --- Abyss Mage ---
    "Pyro Abyss Mage":   {"use": ["Hydro", "Cryo", "Electro"], "avoid": ["Pyro"], "note": "Hydro phá khiên nhanh nhất"},
    "Cryo Abyss Mage":   {"use": ["Pyro", "Electro"],           "avoid": ["Cryo", "Hydro"], "note": "Pyro phá khiên nhanh nhất"},
    "Hydro Abyss Mage":  {"use": ["Cryo", "Electro"],           "avoid": ["Hydro", "Pyro"], "note": "Cryo phá khiên nhanh nhất"},
    "Electro Abyss Mage":{"use": ["Cryo", "Pyro"],              "avoid": ["Electro"],        "note": "Cryo phá khiên nhanh nhất"},

    # --- Abyss Lector / Herald ---
    "Abyss Lector: Violet Lightning": {"use": ["Cryo"],  "avoid": ["Electro"], "note": "Khiên Electro — Cryo để phá, chịu đựng cho đến khi hết khiên"},
    "Abyss Lector: Fathomless Flames":{"use": ["Hydro"], "avoid": ["Pyro"],    "note": "Khiên Pyro — Hydro để phá"},
    "Abyss Herald: Wicked Torrents":  {"use": ["Cryo"],  "avoid": ["Hydro"],   "note": "Khiên Hydro — Cryo để phá"},
    "Abyss Herald: Frost Fall":       {"use": ["Pyro"],  "avoid": ["Cryo"],    "note": "Khiên Cryo — Pyro để phá"},

    # --- Slime ---
    "Pyro Slime":         {"use": ["Hydro", "Cryo"], "avoid": ["Pyro"]},
    "Large Pyro Slime":   {"use": ["Hydro", "Cryo"], "avoid": ["Pyro"]},
    "Cryo Slime":         {"use": ["Pyro"],           "avoid": ["Cryo", "Hydro"]},
    "Large Cryo Slime":   {"use": ["Pyro"],           "avoid": ["Cryo", "Hydro"]},
    "Hydro Slime":        {"use": ["Cryo", "Electro"],"avoid": ["Hydro"]},
    "Large Hydro Slime":  {"use": ["Cryo", "Electro"],"avoid": ["Hydro"]},
    "Electro Slime":      {"use": ["Cryo"],           "avoid": ["Electro"]},
    "Large Electro Slime":{"use": ["Cryo"],           "avoid": ["Electro"]},
    "Mutant Electro Slime":{"use": ["Cryo"],          "avoid": ["Electro"], "note": "Không nên dùng Pyro — sẽ hóa Overloaded gây choáng team"},
    "Geo Slime":          {"use": ["Geo"],             "avoid": [],          "note": "Vũ khí nặng hoặc Geo để phá khiên Geo"},
    "Dendro Slime":       {"use": ["Pyro"],            "avoid": []},

    # --- Lawachurl ---
    "Cryo Lawachurl":     {"use": ["Pyro"],       "avoid": ["Cryo", "Hydro"]},
    "Frostarm Lawachurl": {"use": ["Pyro"],       "avoid": ["Cryo", "Hydro"], "note": "Giống Cryo Lawachurl — Pyro để phá giáp băng"},
    "Geo Lawachurl":      {"use": ["Geo"],         "avoid": [], "note": "Vũ khí nặng hoặc Geo để phá giáp Geo"},
    "Ignited Lawachurl":  {"use": ["Hydro"],       "avoid": ["Pyro"]},

    # --- Fatui Skirmisher ---
    "Fatui Skirmisher - Pyro Agent":       {"use": ["Hydro"],      "avoid": ["Pyro"]},
    "Fatui Skirmisher - Cryogunner Legionnaire": {"use": ["Pyro"], "avoid": ["Cryo", "Hydro"]},
    "Fatui Skirmisher - Electrohammer Vanguard":  {"use": ["Cryo"], "avoid": ["Electro"]},
    "Fatui Skirmisher - Geochanter Bracer":        {"use": ["Geo"],  "avoid": [], "note": "Vũ khí nặng hoặc Geo để phá"},
    "Fatui Skirmisher - Hydrogunner Legionnaire":  {"use": ["Cryo", "Electro"], "avoid": ["Hydro"]},
    "Fatui Skirmisher - Anemoboxer Vanguard":      {"use": [],        "avoid": [], "note": "Có thể hút Anemo shield — dùng element bất kỳ sau khi khiên tan"},

    # --- Specter ---
    "Pyro Specter":    {"use": ["Hydro", "Cryo"], "avoid": ["Pyro"], "note": "Nổ khi chết — đứng xa"},
    "Cryo Specter":    {"use": ["Pyro"],           "avoid": ["Cryo"],"note": "Nổ khi chết — đứng xa"},
    "Hydro Specter":   {"use": ["Cryo", "Electro"],"avoid": ["Hydro"],"note": "Nổ khi chết — đứng xa"},
    "Electro Specter": {"use": ["Cryo"],           "avoid": ["Electro"],"note": "Nổ khi chết — đứng xa"},
    "Geo Specter":     {"use": ["Geo"],            "avoid": [], "note": "Nổ khi chết — đứng xa"},
    "Anemo Specter":   {"use": [],                 "avoid": [], "note": "Nổ khi chết — đứng xa"},

    # --- Primo Geovishap ---
    "Primo Geovishap (Pyro)":   {"use": ["Hydro"],   "avoid": ["Pyro"],    "note": "Khiên Pyro giai đoạn cuối — Hydro để phá"},
    "Primo Geovishap (Cryo)":   {"use": ["Pyro"],    "avoid": ["Cryo"],    "note": "Khiên Cryo giai đoạn cuối"},
    "Primo Geovishap (Hydro)":  {"use": ["Cryo"],    "avoid": ["Hydro"],   "note": "Khiên Hydro giai đoạn cuối"},
    "Primo Geovishap (Electro)":{"use": ["Cryo"],    "avoid": ["Electro"], "note": "Khiên Electro giai đoạn cuối"},

    # --- Mirror Maiden ---
    "Mirror Maiden": {"use": ["Cryo", "Electro"], "avoid": ["Hydro"], "note": "Khiên Hydro khi bị giam — Cryo/Electro để thoát"},

    # --- Ruin series (không có shield, ghi note hữu ích) ---
    "Ruin Guard":             {"use": [], "avoid": [], "note": "Nhắm vào mắt (điểm yếu) — không có shield element"},
    "Ruin Grader":            {"use": [], "avoid": [], "note": "Nhắm vào mắt ở chân — không có shield element"},
    "Ruin Drake: Earthguard": {"use": [], "avoid": [], "note": "Không có shield element — DPS tự do"},
    "Ruin Drake: Skywatch":   {"use": [], "avoid": [], "note": "Không có shield element — DPS tự do"},
    "Ruin Hunter":            {"use": [], "avoid": [], "note": "Kéo vào trạng thái bay để tấn công điểm yếu"},

    # --- Hilichurl ---
    "Hydro Hilichurl Rogue":  {"use": ["Cryo", "Electro"], "avoid": ["Hydro"]},
}

# ---------------------------------------------------------------------------

@dataclass
class EnemyWarning:
    enemy_name: str
    count: int
    use: list[str]      # element nên dùng
    avoid: list[str]    # element nên tránh
    note: str           # ghi chú thêm
    unknown: bool       # True nếu không có trong lookup


@dataclass
class HalfWarning:
    half: int           # 1 hoặc 2
    enemies: list[EnemyWarning]


@dataclass
class ChamberWarning:
    chamber_index: int  # 1-based
    level: str | None
    target: str | None
    halves: list[HalfWarning]


@dataclass
class FloorWarning:
    floor_number: int
    ley_line_disorder: list[str]
    chambers: list[ChamberWarning]


def _warn_enemy(name: str, count: int) -> EnemyWarning:
    data = ENEMY_DATA.get(name)
    if data is None:
        return EnemyWarning(
            enemy_name=name, count=count,
            use=[], avoid=[], note="", unknown=True,
        )
    return EnemyWarning(
        enemy_name=name, count=count,
        use=data.get("use", []),
        avoid=data.get("avoid", []),
        note=data.get("note", ""),
        unknown=False,
    )


def _warn_half(half_index: int, wave_list) -> HalfWarning:
    seen: dict[str, int] = {}
    for wave in wave_list.waves:
        for name, count in wave:
            seen[name] = seen.get(name, 0) + count
    return HalfWarning(
        half=half_index,
        enemies=[_warn_enemy(name, count) for name, count in seen.items()],
    )


def generate_warnings(floors: list[FloorData]) -> list[FloorWarning]:
    """Entry point: nhận list[FloorData] từ abyss_pipeline, trả về list[FloorWarning]."""
    result = []
    for floor in floors:
        chamber_warnings = []
        for idx, ch in enumerate(floor.chambers, start=1):
            chamber_warnings.append(ChamberWarning(
                chamber_index=idx,
                level=ch.level,
                target=ch.target,
                halves=[
                    _warn_half(1, ch.half1),
                    _warn_half(2, ch.half2),
                ],
            ))
        result.append(FloorWarning(
            floor_number=floor.floor_number,
            ley_line_disorder=floor.ley_line_disorder,
            chambers=chamber_warnings,
        ))
    return result


def format_warnings(floor_warnings: list[FloorWarning]) -> str:
    """Render text thuần để in ra terminal hoặc đưa vào report."""
    lines = []
    for fw in floor_warnings:
        lines.append(f"=== Floor {fw.floor_number} ===")
        if fw.ley_line_disorder:
            lines.append("Ley Line Disorder:")
            for lld in fw.ley_line_disorder:
                lines.append(f"  • {lld}")
        for cw in fw.chambers:
            lines.append(f"\n  Chamber {cw.chamber_index} (Lv.{cw.level}) — {cw.target}")
            for hw in cw.halves:
                lines.append(f"    Nửa {'đầu' if hw.half == 1 else 'sau'}:")
                for ew in hw.enemies:
                    prefix = f"      [{ew.enemy_name} ×{ew.count}]"
                    if ew.unknown:
                        lines.append(f"{prefix} — chưa có dữ liệu về quái tên \"{ew.enemy_name}\"")
                    else:
                        parts = []
                        if ew.use:
                            parts.append(f"dùng {'/'.join(ew.use)}")
                        if ew.avoid:
                            parts.append(f"tránh {'/'.join(ew.avoid)}")
                        if ew.note:
                            parts.append(ew.note)
                        lines.append(f"{prefix} — {' | '.join(parts) if parts else 'không có cảnh báo đặc biệt'}")
        lines.append("")
    return "\n".join(lines)