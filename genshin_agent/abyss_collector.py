"""
abyss_collector.py — Lấy dữ liệu Spiral Abyss (Floor/Chamber/Enemy/Ley Line Disorder)
từ genshin-impact.fandom.com, qua MediaWiki Action API (wikitext thô).

Nguồn xác nhận qua explore script (xem PROJECT_MEMORY.md mục 14):
- Danh sách kỳ: Category:Spiral Abyss Floors (category members), KHÔNG dùng DPL/index page
  vì DPL chỉ resolve khi render HTML, không có trong wikitext thô.
- Trang theo kỳ: Spiral_Abyss/Floors/YYYY-MM-DD, chứa block {{Domain Enemies}} cho từng floor.

Nguyên tắc: không suy đoán. Nếu category API lỗi hoặc không có kỳ nào start_date <= hôm nay,
hàm raise lỗi rõ ràng thay vì fallback tính theo công thức ngày 16.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
API_BASE = "https://genshin-impact.fandom.com/api.php"
CATEGORY = "Category:Spiral Abyss Floors"

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


class AbyssDataError(Exception):
    """Raise khi không lấy được dữ liệu thật — không bao giờ tự suy đoán thay thế."""


@dataclass
class EnemyWave:
    # mỗi phần tử trong list là 1 wave; mỗi wave là list (tên quái, số lượng)
    waves: list[list[tuple[str, int]]] = field(default_factory=list)


@dataclass
class ChamberData:
    level: str | None
    target: str | None
    half1: EnemyWave
    half2: EnemyWave
    note_en: str | None  # mô tả spawn order gốc tiếng Anh, None nếu không có


@dataclass
class FloorData:
    floor_number: int
    ley_line_disorder: list[str]  # rỗng nếu không có (hoặc bị comment trong wikitext)
    chambers: list[ChamberData]


def get_current_period_title(today: date | None = None) -> str:
    """
    Lấy title trang đúng kỳ Abyss hiện tại, vd 'Spiral Abyss/Floors/2026-06-16'.
    Logic: liệt kê category members (sort giảm dần theo tên = giảm dần theo ngày),
    loại các kỳ có start_date > hôm nay (trang tương lai, wiki tạo sẵn trước),
    lấy kỳ có start_date gần nhất <= hôm nay.
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
        raise AbyssDataError(f"Fandom API lỗi khi lấy category members: {data['error']}")

    members = data.get("query", {}).get("categorymembers", [])
    if not members:
        raise AbyssDataError("Category 'Spiral Abyss Floors' rỗng hoặc không tồn tại — kiểm tra lại tên category.")

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
        raise AbyssDataError(
            f"Không tìm thấy kỳ Abyss nào có ngày bắt đầu <= hôm nay ({today}) "
            f"trong {len(members)} trang lấy được — có thể cần tăng cmlimit."
        )

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def fetch_period_wikitext(period_title: str) -> str:
    """Fetch wikitext thô của trang theo kỳ (vd 'Spiral Abyss/Floors/2026-06-16')."""
    resp = requests.get(
        API_BASE,
        params={"action": "parse", "page": period_title, "prop": "wikitext", "format": "json"},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise AbyssDataError(f"Fandom API lỗi khi fetch trang '{period_title}': {data['error']}")
    return data["parse"]["wikitext"]["*"]


def _strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _parse_template_params(block: str) -> dict[str, str]:
    """
    Parse nội dung bên trong {{Domain Enemies | k = v | k2 = v2 ... }} thành dict.
    Tách theo '|' ở cấp ngoài cùng (không cắt nhầm '|' bên trong giá trị vì
    các field này không chứa template lồng nhau theo dữ liệu đã quan sát).
    """
    params: dict[str, str] = {}
    parts = block.split("|")
    for part in parts[1:]:  # parts[0] là tên template "Domain Enemies"
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        params[key.strip()] = value.strip()
    return params


def _parse_enemy_field(raw: str) -> EnemyWave:
    """
    ';' = nhiều loại quái cùng 1 wave. '//' = nhiều wave nối tiếp.
    '*N' sau tên = số lượng.
    """
    ew = EnemyWave()
    if not raw:
        return ew
    for wave_str in raw.split("//"):
        wave_str = wave_str.strip()
        if not wave_str:
            continue
        wave: list[tuple[str, int]] = []
        for enemy_str in wave_str.split(";"):
            enemy_str = enemy_str.strip()
            if not enemy_str:
                continue
            m = re.match(r"^(.*?)\*(\d+)$", enemy_str)
            if m:
                name, count = m.group(1).strip(), int(m.group(2))
            else:
                name, count = enemy_str, 1
            wave.append((name, count))
        if wave:
            ew.waves.append(wave)
    return ew


def _parse_floor_section(floor_number: int, section_text: str) -> FloorData:
    clean = _strip_html_comments(section_text)

    # Ley Line Disorder: nằm trong block '''Ley Line Disorder''' ... ** dòng bullet
    ley_line_disorder: list[str] = []
    lld_match = re.search(r"'''Ley Line Disorder'''(.*?)(?=\{\{Domain Enemies|\Z)", clean, re.DOTALL)
    if lld_match:
        for line in lld_match.group(1).splitlines():
            line = line.strip()
            if line.startswith("**"):
                ley_line_disorder.append(line.lstrip("*").strip())

    # Tìm tất cả block {{Domain Enemies ... }} trong section (thường 1, nhưng để vòng lặp cho chắc)
    chambers: list[ChamberData] = []
    for dm in re.finditer(r"\{\{Domain Enemies(.*?)\n\}\}", clean, re.DOTALL):
        params = _parse_template_params(dm.group(1))
        n = 1
        while f"level{n}" in params or f"enemies{n}_1" in params:
            note = params.get(f"note{n}", "").strip() or None
            chambers.append(
                ChamberData(
                    level=params.get(f"level{n}") or None,
                    target=params.get(f"target{n}") or None,
                    half1=_parse_enemy_field(params.get(f"enemies{n}_1", "")),
                    half2=_parse_enemy_field(params.get(f"enemies{n}_2", "")),
                    note_en=note,
                )
            )
            n += 1

    return FloorData(floor_number=floor_number, ley_line_disorder=ley_line_disorder, chambers=chambers)


def parse_wikitext(wikitext: str) -> list[FloorData]:
    """
    Tách wikitext thành từng section '===Floor N===' rồi parse riêng từng floor.
    Chỉ lấy floor nào thực sự có block {{Domain Enemies}} — không giả định Floor 9-12
    luôn có mặt (theo đúng nguyên tắc không suy đoán cấu trúc).
    """
    floors: list[FloorData] = []
    matches = list(re.finditer(r"===Floor (\d+)===", wikitext))
    for i, m in enumerate(matches):
        floor_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(wikitext)
        section = wikitext[start:end]
        floor_data = _parse_floor_section(floor_num, section)
        if floor_data.chambers:  # chỉ giữ floor có dữ liệu enemy thật
            floors.append(floor_data)
    return floors


def get_current_abyss_data(today: date | None = None) -> tuple[str, list[FloorData]]:
    """Entry point: trả về (period_title, list[FloorData]) của kỳ Abyss hiện tại."""
    period_title = get_current_period_title(today)
    wikitext = fetch_period_wikitext(period_title)
    floors = parse_wikitext(wikitext)
    if not floors:
        raise AbyssDataError(
            f"Fetch trang '{period_title}' thành công nhưng không parse ra floor nào — "
            f"có thể cấu trúc wikitext đã đổi, cần kiểm tra lại bằng tay."
        )
    return period_title, floors


if __name__ == "__main__":
    title, floors = get_current_abyss_data()
    print(f"Kỳ hiện tại: {title}\n")
    for f in floors:
        print(f"=== Floor {f.floor_number} ===")
        if f.ley_line_disorder:
            print("Ley Line Disorder:")
            for line in f.ley_line_disorder:
                print(f"  - {line}")
        for idx, ch in enumerate(f.chambers, start=1):
            print(f"  Chamber {idx}: level={ch.level} target={ch.target}")
            print(f"    Half 1: {ch.half1.waves}")
            print(f"    Half 2: {ch.half2.waves}")
            if ch.note_en:
                print(f"    Note (EN): {ch.note_en}")
        print()