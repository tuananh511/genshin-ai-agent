import re
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import markdown
from genshin_agent.optimizer import AccountAnalysis
from genshin_agent.planner import DailyPlan
from genshin_agent.asset_manager import asset_manager

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
OUTPUT_DIR = Path(__file__).resolve().parent.parent
GUIDE_BASE_URL = "https://genshin-impact-helper-team.github.io/genshin-builds/en"

STAT_COLUMNS = [
    ("ATK%", "FIGHT_PROP_ATTACK_PERCENT"), ("HP%", "FIGHT_PROP_HP_PERCENT"),
    ("DEF%", "FIGHT_PROP_DEFENSE_PERCENT"), ("EM", "FIGHT_PROP_ELEMENT_MASTERY"),
    ("ER%", "FIGHT_PROP_CHARGE_EFFICIENCY"), ("Crit Rate%", "FIGHT_PROP_CRITICAL"),
    ("Crit DMG%", "FIGHT_PROP_CRITICAL_HURT"),
]
ELEMENT_DMG_PROP = {
    "Fire": "FIGHT_PROP_FIRE_ADD_HURT", "Water": "FIGHT_PROP_WATER_ADD_HURT",
    "Electric": "FIGHT_PROP_ELEC_ADD_HURT", "Ice": "FIGHT_PROP_ICE_ADD_HURT",
    "Wind": "FIGHT_PROP_WIND_ADD_HURT", "Rock": "FIGHT_PROP_ROCK_ADD_HURT",
    "Grass": "FIGHT_PROP_GRASS_ADD_HURT",
}
ELEMENT_VI = {
    "Fire": "Hoả", "Water": "Thuỷ", "Electric": "Lôi", "Grass": "Thảo",
    "Ice": "Băng", "Wind": "Phong", "Rock": "Nham",
}
ELEMENT_COLORS = {
    "Fire": "#ef7530", "Water": "#3fb6f3", "Electric": "#b380e0", "Grass": "#a4cf3c",
    "Ice": "#9fd5e6", "Wind": "#6dcebb", "Rock": "#f6b73c",
}
SLOT_LABELS_VI = {"Sands": "Đồng hồ", "Goblet": "Cốc", "Circlet": "Vương Miện"}
TALENT_LABELS_VI = {"Burst": "Trảm nộ", "Skill": "Kỹ năng nguyên tố", "Normal Attack": "Đòn thường"}
STAT_TERMS_VI = {
    "Energy Recharge": "Tốc độ hồi năng lượng", "ATK%": "ATK%", "ATK": "ATK",
    "DEF%": "DEF%", "DEF": "DEF", "HP%": "HP%", "HP": "HP",
    "CRIT Rate": "Tỉ lệ bạo kích", "CRIT DMG": "Sát thương bạo kích",
    "Elemental Mastery": "Tinh thông nguyên tố", "Flat HP": "HP cố định",
    "Pyro DMG": "Sát thương Hoả", "Hydro DMG": "Sát thương Thuỷ", "Electro DMG": "Sát thương Lôi",
    "Cryo DMG": "Sát thương Băng", "Anemo DMG": "Sát thương Phong", "Geo DMG": "Sát thương Nham",
    "Dendro DMG": "Sát thương Thảo", "Physical DMG": "Sát thương Vật lý", "Healing Bonus": "Hiệu quả trị liệu",
}


def _translate_phrase(text: str, terms: dict) -> str:
    parts = [p.strip() for p in text.split("/")]
    return " / ".join(terms.get(p, p) for p in parts)


def _build_score_rows(scores) -> list[dict]:
    rows = []
    for s in scores:
        dmg_prop = ELEMENT_DMG_PROP.get(s.element)
        rows.append({
            "name": s.name,
            "element_vi": ELEMENT_VI.get(s.element, s.element),
            "element_color": ELEMENT_COLORS.get(s.element, "#7eb8d4"),
            "level": s.level,
            "constellation_count": s.constellation_count,
            "weapon_name": s.weapon_name,
            "weapon_icon_url": s.weapon_icon_url,
            "sets": [
                {"name": n, "count": c, "icon_url": s.artifact_set_icons.get(n, "")}
                for n, c in s.artifact_sets.items()
            ],
            "stat_values": [s.stats.get(prop_id, 0) for _, prop_id in STAT_COLUMNS],
            "dmg_bonus": s.stats.get(dmg_prop, 0) if dmg_prop else 0,
            "artifact_issue_count": len(s.artifact_issues),
            "low_talent_names": list(s.low_talents.keys()),
        })
    return rows


def _build_guide_accordions(scores, guides: dict) -> list[dict]:
    accordions = []
    for s in scores:
        guide = guides.get(s.avatar_id)
        if not guide or not guide.get("slug"):
            continue
        main_stats_vi = {
            SLOT_LABELS_VI.get(slot, slot): _translate_phrase(val, STAT_TERMS_VI)
            for slot, val in guide.get("artifact_stats", {}).get("main_stats", {}).items()
        }
        weapons_vi = [
            {"name": asset_manager.translate_en_name(w["name"]), "icon_url": w.get("image_url", "")}
            for w in guide.get("weapons", [])[:6]
        ]
        sets_vi = []
        for a in guide.get("artifact_sets", [])[:4]:
            label = f"{a['name']} ({a['pieces']})" if a.get("pieces") else a["name"]
            sets_vi.append({"label": asset_manager.translate_set_label(label), "icon_url": a.get("image_url", "")})

        accordions.append({
            "name": s.name,
            "element_vi": ELEMENT_VI.get(s.element, s.element),
            "element_color": ELEMENT_COLORS.get(s.element, "#7eb8d4"),
            "url": f"{GUIDE_BASE_URL}/{guide['slug']}",
            "weapons": weapons_vi,
            "artifact_sets": sets_vi,
            "main_stats": main_stats_vi,
            "substats": [_translate_phrase(x, STAT_TERMS_VI) for x in guide.get("artifact_stats", {}).get("substats", [])],
            "talents": [TALENT_LABELS_VI.get(t, t) for t in guide.get("talents", [])],
        })
    return accordions

def _build_item_icon_map(score_rows: list[dict], accordions: list[dict]) -> dict[str, str]:
    """Gộp tất cả tên item (đã dịch VI) -> icon url, dùng để bôi hover trong text AI."""
    icon_map: dict[str, str] = {}
    for row in score_rows:
        if row["weapon_name"] and row["weapon_icon_url"]:
            icon_map.setdefault(row["weapon_name"], row["weapon_icon_url"])
        for s in row["sets"]:
            if s["icon_url"]:
                icon_map.setdefault(s["name"], s["icon_url"])
    for acc in accordions:
        for w in acc["weapons"]:
            if w["icon_url"]:
                icon_map.setdefault(w["name"], w["icon_url"])
        for s in acc["artifact_sets"]:
            if s["icon_url"]:
                base_name = s["label"].split(" (")[0]
                icon_map.setdefault(base_name, s["icon_url"])
    return icon_map


def _wrap_known_items(html: str, icon_map: dict[str, str]) -> str:
    """Bôi tooltip ảnh hover cho các tên item đã biết, xuất hiện trong text AI.
    Thay 1 lần bằng regex (không lặp), tên dài xét trước để tránh khớp nhầm chuỗi con."""
    if not icon_map:
        return html
    names = sorted((n for n in icon_map if n.strip()), key=len, reverse=True)
    if not names:
        return html
    pattern = re.compile("|".join(re.escape(n) for n in names))

    def _replace(match):
        name = match.group(0)
        icon = icon_map[name]
        return f'<span class="item-tip">{name}<img class="tip-img" src="{icon}" loading="lazy"></span>'

    return pattern.sub(_replace, html)

def _build_context(nickname, ar, analysis: AccountAnalysis, plan: DailyPlan) -> dict:
    score_rows = _build_score_rows(analysis.scores)
    accordions = _build_guide_accordions(analysis.scores, analysis.guides)
    icon_map = _build_item_icon_map(score_rows, accordions)
    llm_advice_html = _wrap_known_items(markdown.markdown(analysis.llm_advice), icon_map)

    return {
        "report_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nickname": nickname,
        "ar": ar,
        "stat_columns": [label for label, _ in STAT_COLUMNS],
        "scores": score_rows,
        "llm_advice": analysis.llm_advice,
        "llm_advice_html": llm_advice_html,
        "guide_accordions": accordions,
        "day_of_week": plan.day_of_week,
        "required_todos": plan.required_todos,
        "optional_todos": plan.optional_todos,
    }


def generate_reports(nickname, ar, analysis, plan) -> tuple[Path, Path]:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    context = _build_context(nickname, ar, analysis, plan)

    html_template = env.get_template("report.html.j2")
    html_path = OUTPUT_DIR / "report.html"
    html_path.write_text(html_template.render(context), encoding="utf-8")

    md_template = env.get_template("report.md.j2")
    md_path = OUTPUT_DIR / "report.md"
    md_path.write_text(md_template.render(context), encoding="utf-8")

    return html_path, md_path