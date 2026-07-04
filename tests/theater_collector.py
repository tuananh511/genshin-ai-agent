"""
theater_collector.py — Lấy dữ liệu Imaginarium Theater (Nhà Hát) từ
genshin-impact.fandom.com, qua MediaWiki Action API (wikitext thô).

Mirror convention của abyss_collector.py. Khác biệt THẬT đã xác nhận qua
probe wikitext trực tiếp (xem PROJECT_MEMORY.md — không suy đoán):

1. Category riêng: 'Category:Imaginarium Theater Seasons' (khác Abyss),
   nhưng cùng cơ chế categorymembers + lọc start_date <= hôm nay như Abyss.
2. Trang theo mùa: Imaginarium_Theater/Seasons/YYYY-MM-01 (luôn ngày 1,
   vì mùa Nhà Hát tính theo tháng — đã xác nhận qua nhiều mùa liên tiếp
   05, 06, 07/2026 đều rơi đúng ngày 1).
3. Mùa MỚI BẮT ĐẦU có thể CHƯA có section 'Battles' trên wiki (cộng đồng
   cập nhật trễ vài ngày) — hàm parse_wikitext() trả về list rỗng trong
   trường hợp này, và get_current_theater_data() raise TheaterDataError
   rõ ràng, KHÔNG fallback dữ liệu mùa cũ (quyết định đã chốt với người dùng).
4. Cấu trúc {{Domain Enemies}} khác Abyss:
   - Field advantage{N} (hệ có lợi thế) — Abyss không có.
   - level{N} có thể chứa nhiều mức độ khó gộp trong 1 chuỗi
     ('Easy Mode: 75<br>Normal Mode: 80<br>Hard/Visionary Mode: 85')
     thay vì 1 số cố định như Abyss.
   - enemies{N} là 1 wave field duy nhất (không tách half1/half2 như Abyss).
   - Nhiều N song song (N=1,2,3...) trong 1 block = nhiều BIẾN THỂ enemy
     ngẫu nhiên độc lập có thể rơi vào (đã xác nhận qua Act 5: target1 vs
     target2 có điều kiện thắng và bộ quái hoàn toàn khác nhau) — KHÔNG
     phải tuần tự, phải hiển thị tất cả kèm ghi chú "1 trong các biến thể".
   - target{N}/enemies{N} có thể chứa template lồng nhau kèm dấu '|'
     (vd {{Color|help|"Star Challenge"}}) → cần tách '|' biết đếm độ sâu,
     KHÔNG dùng split("|") phẳng như abyss_collector.py.
5. Có thêm {{Description|text|name}} ở đầu Act cho Arcana Challenge và
   Act Boss (không có ở Act thường) — mô tả cơ chế/gợi ý hệ khắc chế.
   Template này cũng chứa nested {{Color|...}} nên cần trích bằng đếm
   độ sâu dấu ngoặc, không dùng regex non-greedy đơn giản.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
API_BASE = "https://genshin-impact.fandom.com/api.php"
CATEGORY = "Category:Imaginarium Theater Seasons"

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
BATTLE_HEADER_RE = re.compile(r";Battle\{\{[Cc]olon\}\}\s*(.*?)\n")
ACT_HEADER_RE = re.compile(r"===\s*((?:Act \d+)|(?:Arcana Challenge [IVX]+))\s*===")


class TheaterDataError(Exception):
    """Raise khi không lấy được dữ liệu thật — không bao giờ tự suy đoán thay thế."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EnemyEntry:
    name: str
    count: int               # -1 nghĩa là '*-' trong wikitext (quái liên tục / không giới hạn)
    aura: str | None = None  # từ hậu tố '/{{Aura|...}}' gắn sau tên quái, None nếu không có


@dataclass
class EnemyWave:
    # mỗi phần tử trong list là 1 wave (list[EnemyEntry])
    waves: list[list[EnemyEntry]] = field(default_factory=list)


@dataclass
class BattleVariant:
    # 1 biến thể trong số N=1,2,3... của cùng 1 {{Domain Enemies}} — mỗi
    # biến thể là 1 khả năng enemy/target ngẫu nhiên ĐỘC LẬP, không tuần tự.
    target: str | None
    level_raw: str | None       # nguyên chuỗi gốc, có thể chứa nhiều mode (xem docstring)
    advantage: str | None       # hệ có lợi thế, None nếu field không tồn tại
    enemies: EnemyWave


@dataclass
class BattleData:
    battle_name: str | None       # 'Normal', 'Elite Assault'... None nếu Act không có sub-battle
    stage_effects: list[str]      # rỗng nếu không có
    variants: list[BattleVariant]


@dataclass
class ActData:
    act_name: str                  # 'Act 1', 'Arcana Challenge I', 'Act 10'...
    description: str | None        # từ {{Description|text|name}}, None nếu không có
    battles: list[BattleData]


# ---------------------------------------------------------------------------
# Fetch — mirror abyss_collector.py
# ---------------------------------------------------------------------------

def get_current_period_title(today: date | None = None) -> str:
    """
    Lấy title trang đúng mùa Nhà Hát hiện tại, vd 'Imaginarium Theater/Seasons/2026-07-01'.
    Cùng logic get_current_period_title() của abyss_collector.py: liệt kê category
    members, loại trang tương lai, lấy mùa gần nhất có start_date <= hôm nay.
    """
    today = today or date.today()
    resp = requests.get(
        API_BASE,
        params={
            "action": "query",
            "list": "categorymembers",
            "cmtitle": CATEGORY,
            "cmsort": "sortkey",
            "cmdir": "descending",
            "cmlimit": "10",
            "format": "json",
        },
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise TheaterDataError(f"Fandom API lỗi khi lấy category members: {data['error']}")

    members = data.get("query", {}).get("categorymembers", [])
    if not members:
        raise TheaterDataError(
            f"Category '{CATEGORY}' rỗng hoặc không tồn tại — kiểm tra lại tên category."
        )

    candidates: list[tuple[date, str]] = []
    for m in members:
        title = m["title"]
        match = DATE_RE.search(title)
        if not match:
            continue
        try:
            d = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if d <= today:
            candidates.append((d, title))

    if not candidates:
        raise TheaterDataError(
            f"Không tìm thấy mùa Nhà Hát nào có ngày bắt đầu <= hôm nay ({today}) "
            f"trong {len(members)} trang lấy được — có thể cần tăng cmlimit."
        )

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def fetch_period_wikitext(period_title: str) -> str:
    """Fetch wikitext thô của trang theo mùa (vd 'Imaginarium Theater/Seasons/2026-07-01')."""
    resp = requests.get(
        API_BASE,
        params={"action": "parse", "page": period_title, "prop": "wikitext", "format": "json"},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise TheaterDataError(f"Fandom API lỗi khi fetch trang '{period_title}': {data['error']}")
    return data["parse"]["wikitext"]["*"]


def _strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Parsing helpers — khác abyss_collector.py: cần đếm độ sâu {{ }} vì field
# target/enemies/Description của Nhà Hát chứa template lồng nhau có dấu '|'.
# ---------------------------------------------------------------------------

def _extract_template_block(text: str, start_idx: int) -> str:
    """
    text[start_idx:] bắt đầu bằng '{{'. Trả về nội dung bên trong (không gồm
    '{{' '}}' ngoài cùng), xử lý đúng template lồng nhau bằng đếm độ sâu.
    Dùng cho {{Description|...}} vì có thể chứa {{Color|...}} lồng bên trong
    trên CÙNG 1 dòng (không thể dùng trick '\\n}}' như Domain Enemies).
    """
    assert text[start_idx:start_idx + 2] == "{{"
    depth = 0
    i = start_idx
    while i < len(text):
        if text[i:i + 2] == "{{":
            depth += 1
            i += 2
            continue
        if text[i:i + 2] == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return text[start_idx + 2:i - 2]
            continue
        i += 1
    raise ValueError(f"Không tìm thấy '}}' đóng khớp cho template tại vị trí {start_idx}")


def _split_top_level_pipes(s: str) -> list[str]:
    """
    Tách chuỗi theo '|' ở cấp ngoài cùng, KHÔNG tách '|' bên trong {{...}}
    lồng nhau (vd {{Color|help|"Star Challenge"}} phải giữ nguyên làm 1 phần).
    Đây là điểm khác abyss_collector.py._parse_template_params — bắt buộc vì
    dữ liệu Nhà Hát có template lồng chứa '|', khác giả định của Abyss.
    """
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    i = 0
    while i < len(s):
        if s[i:i + 2] == "{{":
            depth += 1
            current.append("{{")
            i += 2
            continue
        if s[i:i + 2] == "}}":
            depth -= 1
            current.append("}}")
            i += 2
            continue
        if s[i] == "|" and depth == 0:
            parts.append("".join(current))
            current = []
            i += 1
            continue
        current.append(s[i])
        i += 1
    parts.append("".join(current))
    return parts


def _parse_template_params(block: str) -> dict[str, str]:
    """Parse nội dung bên trong {{Domain Enemies | k = v | ... }} thành dict."""
    params: dict[str, str] = {}
    parts = _split_top_level_pipes(block)
    for part in parts[1:]:  # parts[0] là tên template "Domain Enemies"
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        params[key.strip()] = value.strip()
    return params


AURA_SUFFIX_RE = re.compile(r"/\{\{Aura\|(.*?)\}\}$")


def _extract_aura_suffix(s: str) -> tuple[str, str | None]:
    """
    Tách hậu tố '/{{Aura|Tên Aura}}' gắn sau 1 enemy (vd quái đó luôn có sẵn
    1 buff/aura đặc biệt khi xuất hiện) — đã xác nhận qua dữ liệu thật
    (Act 1 Normal: 'Thunderhelm Lawachurl*1/{{Aura|Engulfing Storm}}').
    Trả về (chuỗi đã bỏ hậu tố, tên aura hoặc None).
    """
    m = AURA_SUFFIX_RE.search(s)
    if m:
        return s[:m.start()].strip(), m.group(1).strip()
    return s, None


def _parse_enemy_field(raw: str) -> EnemyWave:
    """
    ';' = nhiều loại quái cùng 1 wave. '//' = nhiều wave nối tiếp.
    '*N' sau tên = số lượng. '*-' = không giới hạn/liên tục -> lưu count=-1.
    '/{{Aura|...}}' sau '*N' = quái đó có sẵn aura đặc biệt -> tách riêng field aura.
    """
    ew = EnemyWave()
    if not raw:
        return ew
    for wave_str in raw.split("//"):
        wave_str = wave_str.strip()
        if not wave_str:
            continue
        wave: list[EnemyEntry] = []
        for enemy_str in wave_str.split(";"):
            enemy_str = enemy_str.strip()
            if not enemy_str:
                continue
            enemy_str, aura = _extract_aura_suffix(enemy_str)
            m = re.match(r"^(.*?)\*(-|\d+)$", enemy_str)
            if m:
                name = m.group(1).strip()
                count = -1 if m.group(2) == "-" else int(m.group(2))
            else:
                name, count = enemy_str, 1
            wave.append(EnemyEntry(name=name, count=count, aura=aura))
        if wave:
            ew.waves.append(wave)
    return ew


def _parse_description(section: str) -> str | None:
    idx = section.find("{{Description")
    if idx == -1:
        return None
    inner = _extract_template_block(section, idx)
    parts = _split_top_level_pipes(inner)
    if len(parts) < 2:
        return None
    return parts[1].strip()


def _parse_stage_effects(block: str) -> list[str]:
    """Tìm '''Stage Effects''': rồi lấy các dòng bullet '**' phía dưới, dừng khi gặp {{Domain Enemies."""
    effects: list[str] = []
    m = re.search(r"'''Stage Effects'''(.*?)(?=\{\{Domain Enemies|\Z)", block, re.DOTALL)
    if not m:
        return effects
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("**"):
            effects.append(line.lstrip("*").strip())
    return effects


def _parse_domain_enemies_variants(block: str) -> list[BattleVariant]:
    """Tìm block {{Domain Enemies ... }} (đóng bằng '\\n}}' — không có nested
    template nào của Nhà Hát tự đóng theo đúng pattern này) rồi tách N biến thể."""
    variants: list[BattleVariant] = []
    dm = re.search(r"\{\{Domain Enemies(.*?)\n\}\}", block, re.DOTALL)
    if not dm:
        return variants
    params = _parse_template_params(dm.group(1))
    n = 1
    while any(params.get(f"{key}{n}") for key in ("target", "level", "advantage", "enemies")):
        variants.append(
            BattleVariant(
                target=params.get(f"target{n}") or None,
                level_raw=params.get(f"level{n}") or None,
                advantage=params.get(f"advantage{n}") or None,
                enemies=_parse_enemy_field(params.get(f"enemies{n}", "")),
            )
        )
        n += 1
    return variants


def _parse_act_section(act_name: str, section_text: str) -> ActData:
    clean = _strip_html_comments(section_text)
    description = _parse_description(clean)

    battle_matches = list(BATTLE_HEADER_RE.finditer(clean))
    battles: list[BattleData] = []

    if not battle_matches:
        # Act không có sub-battle riêng (Arcana Challenge, Act Boss) —
        # toàn bộ section là 1 battle ngầm định.
        stage_effects = _parse_stage_effects(clean)
        variants = _parse_domain_enemies_variants(clean)
        if variants:
            battles.append(BattleData(battle_name=None, stage_effects=stage_effects, variants=variants))
    else:
        for i, bm in enumerate(battle_matches):
            battle_name = bm.group(1).strip()
            start = bm.end()
            end = battle_matches[i + 1].start() if i + 1 < len(battle_matches) else len(clean)
            battle_block = clean[start:end]
            stage_effects = _parse_stage_effects(battle_block)
            variants = _parse_domain_enemies_variants(battle_block)
            if variants:
                battles.append(BattleData(battle_name=battle_name, stage_effects=stage_effects, variants=variants))

    return ActData(act_name=act_name, description=description, battles=battles)


def parse_wikitext(wikitext: str) -> list[ActData]:
    """
    Tách wikitext thành từng section '===Act N===' / '===Arcana Challenge I==='
    rồi parse riêng. Chỉ giữ Act thực sự có battle với dữ liệu enemy thật —
    nếu mùa hiện tại chưa có phần Battles trên wiki, trả về list RỖNG
    (không suy đoán/không fallback — xử lý ở get_current_theater_data()).
    """
    acts: list[ActData] = []
    matches = list(ACT_HEADER_RE.finditer(wikitext))
    for i, m in enumerate(matches):
        act_name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(wikitext)
        section = wikitext[start:end]
        act_data = _parse_act_section(act_name, section)
        if act_data.battles:  # chỉ giữ Act có dữ liệu enemy thật
            acts.append(act_data)
    return acts


def get_current_theater_data(today: date | None = None) -> tuple[str, list[ActData]]:
    """
    Entry point: trả về (period_title, list[ActData]) của mùa Nhà Hát hiện tại.

    Raise TheaterDataError rõ ràng (KHÔNG fallback mùa cũ) nếu mùa hiện tại
    chưa có section Battles trên wiki — theo đúng quyết định đã chốt: báo
    "chưa có dữ liệu mùa này" cho người dùng thay vì hiển thị dữ liệu cũ.
    """
    period_title = get_current_period_title(today)
    wikitext = fetch_period_wikitext(period_title)
    acts = parse_wikitext(wikitext)
    if not acts:
        raise TheaterDataError(
            f"Mùa '{period_title}' chưa có dữ liệu Battles trên wiki (thường do "
            f"cộng đồng wiki cập nhật trễ vài ngày đầu mùa) — không có gì để hiển thị."
        )
    return period_title, acts


if __name__ == "__main__":
    title, acts = get_current_theater_data()
    print(f"Mùa hiện tại: {title}\n")
    for a in acts:
        print(f"=== {a.act_name} ===")
        if a.description:
            print(f"  Description: {a.description}")
        for b in a.battles:
            label = b.battle_name or "(mặc định)"
            print(f"  Battle: {label}")
            if b.stage_effects:
                print("    Stage Effects:")
                for e in b.stage_effects:
                    print(f"      - {e}")
            for idx, v in enumerate(b.variants, start=1):
                print(f"    Variant {idx}: level={v.level_raw!r} advantage={v.advantage!r} target={v.target!r}")
                print(f"      Enemies: {v.enemies.waves}")
        print()