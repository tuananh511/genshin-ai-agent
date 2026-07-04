"""
crimsonwitch_collector.py
Nguồn: crimsonwitch.com — "Stat Recommendations" theo nhân vật (có thể nhiều build/role
khác nhau, VD Durin có 4 build: Pyro Sub DPS, Vape/Melt Sub DPS, Transformative Reaction DPS,
Pyro Main DPS).

Cơ chế: Next.js App Router (App Router SPA yêu cầu JS để render UI), nhưng toàn bộ dữ liệu
build của TẤT CẢ nhân vật (213 entries đã xác nhận) được server nhúng sẵn trong RSC flight
data (script `self.__next_f.push([1, "..."])`) ngay ở lần fetch đầu tiên — không cần Playwright,
không cần loop qua URL từng nhân vật. Đã research + verify bằng probe thật trước khi viết file
này (xem PROJECT_MEMORY.md mục 4/6 — Nhóm B3).
"""
import re
import json
import requests

BASE_URL = "https://www.crimsonwitch.com/"
HEADERS = {"User-Agent": "genshin-ai-agent/3.0 (personal-project)"}


def _fetch_html() -> str:
    resp = requests.get(BASE_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def _extract_builds_json(html: str) -> list[dict]:
    """Tìm chunk RSC chứa 'initialBuilds', unescape (chunk là 1 JS string literal lồng),
    rồi cắt đúng mảng JSON bằng cách đếm độ sâu ngoặc [ ] — không dùng regex đoán ranh giới,
    vì nội dung bên trong có thể chứa dấu ']' trong chuỗi (VD tên set/vũ khí)."""
    raw_chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.DOTALL)

    target_raw = next((c for c in raw_chunks if "initialBuilds" in c), None)
    if target_raw is None:
        raise ValueError(
            "Không tìm thấy chunk RSC chứa 'initialBuilds' — "
            "cấu trúc trang crimsonwitch.com có thể đã đổi, cần probe lại."
        )

    unescaped = json.loads('"' + target_raw + '"')

    marker = '"initialBuilds":'
    start = unescaped.index(marker) + len(marker)
    depth = 0
    end = None
    for i in range(start, len(unescaped)):
        ch = unescaped[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise ValueError("Không tìm được điểm kết thúc mảng 'initialBuilds' — dữ liệu có thể bị cắt giữa chừng.")

    return json.loads(unescaped[start:end])


def get_all_builds() -> dict[str, list[dict]]:
    """Trả về {character_name (tên tiếng Anh theo crimsonwitch): [build, ...]}.
    Mỗi list đã sort theo build_priority tăng dần (build #1 = ưu tiên cao nhất).
    Fetch 1 LẦN DUY NHẤT cho TẤT CẢ nhân vật — không loop theo URL từng nhân vật."""
    html = _fetch_html()
    builds = _extract_builds_json(html)

    grouped: dict[str, list[dict]] = {}
    for b in builds:
        grouped.setdefault(b["character_name"], []).append(b)

    for name in grouped:
        grouped[name].sort(key=lambda b: b["build_priority"])

    return grouped


def get_character_builds(character_name_en: str, all_builds: dict[str, list[dict]] | None = None) -> list[dict]:
    """Lấy build của 1 nhân vật theo tên tiếng Anh.
    ⚠️ CHƯA XÁC MINH tên này khớp 100% với AssetManager.get_avatar_name_en() — cần test
    thật với vài nhân vật trước khi wiring vào report (VD Traveler theo hệ, tên có dấu nối...).

    Truyền sẵn `all_builds` nếu đã gọi get_all_builds() từ trước trong cùng lần chạy,
    tránh fetch lại (chỉ nên fetch 1 lần cho cả account, không phải 1 lần/nhân vật)."""
    if all_builds is None:
        all_builds = get_all_builds()
    return all_builds.get(character_name_en, [])
