import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from genshin_agent.database import get_connection

BASE_URL = "https://genshin-impact-helper-team.github.io/genshin-builds/en"
USER_AGENT = "genshin-ai-agent/0.1 (personal-project)"
INDEX_CACHE_KEY = "genshin_builds_index"
INDEX_CACHE_TTL_DAYS = 7

def _clean_text(text: str) -> str:
    """Bỏ icon ghi chú (ⓘ) và chuẩn hoá khoảng trắng bị dính do parse HTML lồng nhau."""
    text = text.replace("ⓘ", "")
    return " ".join(text.split())

def _fetch(url: str) -> str | None:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    except requests.RequestException:
        return None
    return resp.text if resp.status_code == 200 else None


def _get_character_index() -> list[dict]:
    """[{'name': 'Furina ★5 Sword...', 'slug': 'furina'}, ...] — cache 7 ngày trong asset_cache."""
    conn = get_connection()
    row = conn.execute("SELECT value, fetched_at FROM asset_cache WHERE key = ?", (INDEX_CACHE_KEY,)).fetchone()
    if row:
        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if datetime.now() - fetched_at < timedelta(days=INDEX_CACHE_TTL_DAYS):
            conn.close()
            return json.loads(row["value"])
    conn.close()

    html = _fetch(BASE_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    excluded = {"weapons", "artifacts", "faq", "credits", "changelog", "en"}
    entries = []
    for a in soup.select("a[href*='/genshin-builds/en/']"):
        classes = a.get("class") or []
        if "nav-link" in classes or "dropdown-link" in classes:
            continue
        slug = a.get("href", "").rstrip("/").split("/")[-1]
        if slug in excluded:
            continue
        text = a.get_text(separator=" ", strip=True)
        if text:
            entries.append({"name": text, "slug": slug})

    conn = get_connection()
    conn.execute(
        """INSERT INTO asset_cache (key, value, fetched_at) VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, fetched_at=excluded.fetched_at""",
        (INDEX_CACHE_KEY, json.dumps(entries, ensure_ascii=False), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return entries


def _resolve_slug(display_name: str, index: list[dict]) -> str | None:
    for entry in index:
        if display_name.lower() in entry["name"].lower():
            return entry["slug"]
    return None


def _popover_info(tag) -> dict | None:
    """Tên + URL ảnh thật nằm trong attribute này, mã hoá entity — parse lại 1 lần nữa."""
    inner = BeautifulSoup(tag.get("data-info-popover-html", ""), "html.parser")
    name_tag = inner.select_one(".info-popover-name")
    if not name_tag:
        return None
    img_tag = inner.select_one("img")
    img_src = img_tag.get("src", "") if img_tag else ""
    image_url = f"https://genshin-impact-helper-team.github.io{img_src}" if img_src else ""
    return {"name": name_tag.get_text(strip=True), "image_url": image_url}


def _section_after(soup: BeautifulSoup, heading_text: str):
    heading = soup.find(lambda t: t.name in ["h1", "h2", "h3"] and heading_text in t.get_text())
    return heading.find_next_sibling() if heading else None


def _parse_weapons(section) -> list[dict]:
    if not section:
        return []
    results = []
    for p in section.select(".weapon-popover"):
        info = _popover_info(p)
        if info:
            results.append(info)
    return results


def _parse_artifact_sets(section) -> list[dict]:
    if not section:
        return []
    results = []
    for row in section.select(".rank-row"):
        popover = row.select_one(".artifact-popover")
        if not popover:
            continue
        info = _popover_info(popover)
        if not info:
            continue
        suffix = row.select_one(".artifact-piece-suffix")
        piece = _clean_text(suffix.get_text(separator=" ", strip=True)) if suffix else ""
        results.append({"name": info["name"], "image_url": info["image_url"], "pieces": piece})
    return results


def _parse_artifact_stats(section) -> dict:
    result = {"main_stats": {}, "substats": []}
    if not section:
        return result
    for sub in section.select(".recommendation-section"):
        h3 = sub.find("h3")
        if not h3:
            continue
        if "Main Stat" in h3.get_text():
            for row in sub.select(".stat-row"):
                strong = row.find("strong")
                if strong:
                    labels = [_clean_text(l.get_text(separator=" ", strip=True)) for l in row.select(".inline-note-label")]
                    result["main_stats"][strong.get_text(strip=True)] = " / ".join(labels)
        elif "Substat" in h3.get_text():
            result["substats"] = [_clean_text(l.get_text(separator=" ", strip=True)) for l in sub.select(".inline-note-label")]
    return result


def _parse_talents(section) -> list[str]:
    if not section:
        return []
    return [_clean_text(l.get_text(separator=" ", strip=True)) for l in section.select(".inline-note-label")]


def fetch_character_guide(display_name: str) -> dict | None:
    """Lấy guide đầy đủ cho 1 nhân vật. None nếu không tìm thấy trên genshin-builds."""
    index = _get_character_index()
    slug = _resolve_slug(display_name, index)
    if not slug:
        print(f"  [warn] Không tìm thấy '{display_name}' trong danh sách genshin-builds")
        return None

    html = _fetch(f"{BASE_URL}/{slug}")
    if not html:
        print(f"  [warn] Không fetch được trang '{display_name}' (slug={slug})")
        return None

    soup = BeautifulSoup(html, "html.parser")
    return {
        "slug": slug,
        "weapons": _parse_weapons(_section_after(soup, "Weapons")),
        "artifact_sets": _parse_artifact_sets(_section_after(soup, "Artifact Sets")),
        "artifact_stats": _parse_artifact_stats(_section_after(soup, "Artifact Stats")),
        "talents": _parse_talents(_section_after(soup, "Talents")),
    }

def _cache_get(avatar_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM character_guides WHERE avatar_id = ?", (avatar_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "slug": row["slug"],
        "weapons": json.loads(row["weapons_json"]),
        "artifact_sets": json.loads(row["artifact_sets_json"]),
        "artifact_stats": json.loads(row["artifact_stats_json"]),
        "talents": json.loads(row["talents_json"]),
    }


def _cache_set(avatar_id: int, guide: dict):
    conn = get_connection()
    conn.execute(
        """INSERT INTO character_guides (avatar_id, slug, weapons_json, artifact_sets_json, artifact_stats_json, talents_json, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(avatar_id) DO UPDATE SET
               slug=excluded.slug, weapons_json=excluded.weapons_json,
               artifact_sets_json=excluded.artifact_sets_json, artifact_stats_json=excluded.artifact_stats_json,
               talents_json=excluded.talents_json, fetched_at=excluded.fetched_at""",
        (
            avatar_id, guide["slug"],
            json.dumps(guide["weapons"], ensure_ascii=False),
            json.dumps(guide["artifact_sets"], ensure_ascii=False),
            json.dumps(guide["artifact_stats"], ensure_ascii=False),
            json.dumps(guide["talents"], ensure_ascii=False),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def get_character_guide(avatar_id: int, display_name: str, force_refresh: bool = False) -> dict | None:
    """force_refresh=False: chỉ đọc cache, không gọi mạng (dùng khi người dùng chọn N).
    force_refresh=True: crawl lại thật, ghi đè cache (dùng khi chọn Y)."""
    if not force_refresh:
        cached = _cache_get(avatar_id)
        if cached:
            print(f"  [cache] Guide '{display_name}' từ cache")
        else:
            print(f"  [info] Chưa có cache cho '{display_name}' (chọn Y update database để lấy lần đầu)")
        return cached

    guide = fetch_character_guide(display_name)
    if guide:
        _cache_set(avatar_id, guide)
    return guide