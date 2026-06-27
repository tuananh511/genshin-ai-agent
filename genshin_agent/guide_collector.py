import json
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from genshin_agent.database import get_connection

BASE_URL = "https://keqingmains.com"
USER_AGENT = "genshin-ai-agent/0.1 (personal-project)"
CACHE_TTL_DAYS = 7


def _candidate_slugs(display_name: str) -> list[str]:
    """Sinh các khả năng slug từ tên hiển thị.
    'Sangonomiya Kokomi' -> ['sangonomiya-kokomi', 'sangonomiyakokomi', 'kokomi', 'sangonomiya']
    """
    words = re.findall(r"[a-zA-Z]+", display_name.lower())
    candidates = ["-".join(words), "".join(words)]
    for w in reversed(words):  # thử từ CUỐI trước (đa số tên gọi tắt là từ sau: Kokomi, Kazuha)
        if w not in candidates and len(w) > 2:
            candidates.append(w)
    return candidates


def _try_fetch(slug: str):
    url = f"{BASE_URL}/{slug}/"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    except requests.RequestException:
        return None
    return resp if resp.status_code == 200 else None


def _resolve_and_fetch(display_name: str):
    """Thử từng slug khả năng, trả về (slug đúng, response) đầu tiên thành công."""
    for slug in _candidate_slugs(display_name):
        resp = _try_fetch(slug)
        if resp:
            return slug, resp
    return None




MAX_SECTION_CHARS = 1200  # giới hạn độ dài, tránh tốn token khi đưa vào prompt LLM


def _extract_section(soup: BeautifulSoup, heading_keywords: list[str]) -> str:
    """Tìm heading có chứa 1 trong các từ khoá (không phân biệt hoa thường),
    lấy toàn bộ text các sibling cho tới khi gặp heading CÙNG cấp hoặc CAO hơn tiếp theo."""
    heading = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3", "h4"]
        and any(kw.lower() in tag.get_text().lower() for kw in heading_keywords)
    )
    if not heading:
        return ""

    level = int(heading.name[1])
    texts = []
    current = heading
    for _ in range(15):
        current = current.find_next_sibling()
        if current is None:
            break
        if current.name and current.name.startswith("h") and current.name[1].isdigit():
            if int(current.name[1]) <= level:
                break
        text = current.get_text(separator=" ", strip=True)
        if text:
            texts.append(text)

    full_text = "\n".join(texts)
    return full_text[:MAX_SECTION_CHARS]


def _parse_guide_html(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    return {
        "artifact_section": _extract_section(soup, ["Artifact Stats", "Artifacts", "Best Artifacts", "Artifact Sets"]),
        "weapon_section": _extract_section(soup, ["Weapons", "Best Weapons"]),
    }


def _cache_get(avatar_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM character_guides WHERE avatar_id = ?", (avatar_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    fetched_at = datetime.fromisoformat(row["fetched_at"])
    if datetime.now() - fetched_at > timedelta(days=CACHE_TTL_DAYS):
        return None
    return {
        "slug": row["slug"],
        "artifact_section": row["artifact_section"],
        "weapon_section": row["weapon_section"],
    }


def _cache_set(avatar_id: int, slug, data: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO character_guides (avatar_id, slug, artifact_section, weapon_section, fetched_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(avatar_id) DO UPDATE SET
               slug=excluded.slug,
               artifact_section=excluded.artifact_section,
               weapon_section=excluded.weapon_section,
               fetched_at=excluded.fetched_at""",
        (avatar_id, slug, data["artifact_section"], data["weapon_section"], datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_character_guide(avatar_id: int, display_name: str) -> dict:
    cached = _cache_get(avatar_id)
    if cached:
        print(f"  [cache] Guide '{display_name}' (slug={cached['slug']}) từ cache")
        return cached

    print(f"  [fetch] Đang dò URL guide cho '{display_name}'...")
    found = _resolve_and_fetch(display_name)

    if not found:
        print(f"  [warn] Không tìm thấy guide cho '{display_name}' trên KeqingMains")
        empty = {"slug": None, "artifact_section": "", "weapon_section": ""}
        _cache_set(avatar_id, None, empty)
        return empty

    slug, response = found
    print(f"  [fetch] -> dùng slug '{slug}'")
    data = _parse_guide_html(response.text)
    _cache_set(avatar_id, slug, data)
    data["slug"] = slug
    return data