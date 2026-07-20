import re
from pathlib import Path
from datetime import datetime
from genshin_agent.paths import app_base_dir, bundled_resource_dir
from jinja2 import Environment, FileSystemLoader
import markdown
from genshin_agent.optimizer import AccountAnalysis
from genshin_agent.asset_manager import asset_manager
from genshin_agent import background_collector

def generate_reports(nickname, ar, analysis,
                     abyss_data=None, theater_data=None) -> tuple[Path, Path]:
    """Xuất report.html. Trả tuple (html_path, html_path) để main.py không cần sửa unpack."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    context = _build_context(
        nickname=nickname, ar=ar, analysis=analysis,
        abyss_data=abyss_data, theater_data=theater_data,
    )
    context["background_image_url"] = background_collector.get_random_background_url()

    html_template = env.get_template("report.html.j2")
    html_path = OUTPUT_DIR / "report.html"
    html_path.write_text(html_template.render(context), encoding="utf-8")

    return html_path, html_path

_PERIOD_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
TEMPLATES_DIR = bundled_resource_dir() / "templates"
OUTPUT_DIR = app_base_dir()
GUIDE_BASE_URL = "https://genshin-impact-helper-team.github.io/genshin-builds/en"

STAT_COLUMNS = [
    ("ATK%", "FIGHT_PROP_ATTACK_PERCENT",
     "Tăng % Tấn Công cơ bản. Hầu hết sát thương thường/kỹ năng đều tính theo ATK, nên đa số DPS cần chỉ số này."),
    ("HP%", "FIGHT_PROP_HP_PERCENT",
     "Tăng % HP tối đa. Quan trọng với nhân vật tính sát thương/khiên/hồi máu theo HP tối đa (VD Đại Chú Tể, Kokomi)."),
    ("DEF%", "FIGHT_PROP_DEFENSE_PERCENT",
     "Tăng % Phòng Ngự. Quan trọng với nhân vật tính sát thương/khiên theo DEF (VD Noelle, Đại Chú Tể khi chắn)."),
    ("EM", "FIGHT_PROP_ELEMENT_MASTERY",
     "Tinh Thông Nguyên Tố — tăng sát thương phản ứng nguyên tố (Bốc Hơi, Tan Chảy, Siêu Dẫn, Cháy...). Quan trọng với build carry theo phản ứng."),
    ("ER%", "FIGHT_PROP_CHARGE_EFFICIENCY",
     "Hiệu Quả Nạp Nguyên Tố — tăng tốc độ hồi năng lượng để dùng chiêu cuối (Q) thường xuyên hơn. Quan trọng với nhân vật cần Q liên tục hoặc chi phí Q cao."),
    ("Crit Rate%", "FIGHT_PROP_CRITICAL",
     "Tỉ lệ gây sát thương bạo kích (crit) trên mỗi đòn đánh."),
    ("Crit DMG%", "FIGHT_PROP_CRITICAL_HURT",
     "Lượng sát thương tăng thêm khi đòn đánh bạo kích trúng. Thường build theo tỉ lệ 1 Crit Rate : 2 Crit DMG."),
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

def _build_guide_url(name_en: str) -> str:
    if not name_en:
        return ""
    slug = name_en.strip().lower().replace(" ", "_")
    return f"https://genshin-builds.com/vi/character/{slug}"

from genshin_agent import crimsonwitch_collector


def _format_stat_recommendations(build: dict) -> str:
    """Gộp 2 nguồn: energy (ER range, gần như build nào cũng có) và stat_recommendations
    (ngưỡng số cụ thể khác ATK/DEF/EM..., chỉ ~23/213 build có, thường là DPS chính).
    Cả 2 cùng đổ vào khung "Stat Recommendations" trên trang gốc crimsonwitch.com."""
    parts = []

    energy = build.get("energy")
    if energy and (energy.get("min") is not None or energy.get("max") is not None):
        lo, hi = energy.get("min"), energy.get("max")
        if lo is not None and hi is not None:
            parts.append(f"ER {lo}–{hi}%")
        elif lo is not None:
            parts.append(f"ER ≥ {lo}%")
        elif hi is not None:
            parts.append(f"ER ≤ {hi}%")

    for r in build.get("stat_recommendations", []):
        text = f"{r['stat']} {r['prefix']} {r['value']}"
        if r.get("condition"):
            text += f" ({r['condition']})"
        parts.append(text)

    return "; ".join(parts) if parts else "(không có khuyến nghị chỉ số cụ thể)"


def _get_crimsonwitch_builds_safe() -> dict[str, list[dict]]:
    """Fetch build data 1 lần cho cả report (không phải 1 lần/nhân vật).
    Nếu crimsonwitch.com lỗi/sập, trả {} — report vẫn tiếp tục chạy bình thường,
    chỉ thiếu phần badge stat recommendation (không crash toàn bộ report)."""
    try:
        return crimsonwitch_collector.get_all_builds()
    except Exception as e:
        print(f"  [warn] Không lấy được Stat Recommendations từ crimsonwitch.com: {e}")
        return {}


def _build_score_rows(scores, all_builds: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for s in scores:
        dmg_prop = ELEMENT_DMG_PROP.get(s.element)
        name_en = asset_manager.get_avatar_name_en(s.avatar_id)

        char_builds = all_builds.get(name_en, [])
        stat_builds = [
            {
                "label": b.get("build_name", f"Build {i+1}"),
                "tooltip": _format_stat_recommendations(b),   # đổi: truyền cả b, không phải b.get("stat_recommendations", [])
            }
            for i, b in enumerate(char_builds)
        ]

        rows.append({
            "name": s.name,
            "build_guide_url": _build_guide_url(name_en),
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
            "stat_values": [s.stats.get(prop_id, 0) for _, prop_id, _ in STAT_COLUMNS],
            "dmg_bonus": s.stats.get(dmg_prop, 0) if dmg_prop else 0,
            "artifact_issue_count": len(s.artifact_issues),
            "low_talent_names": list(s.low_talents.keys()),
            "stat_builds": stat_builds,
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


def _build_abyss_context(abyss_data) -> dict | None:
    """abyss_data: None hoặc tuple (period_title, list[FloorData], list[FloorWarning])
    từ abyss_pipeline.get_abyss_data() + abyss_planner.generate_warnings()."""
    if abyss_data is None:
        return None
    period_title, floors, warnings = abyss_data
    warnings_by_floor = {w.floor_number: w for w in warnings}

    floor_ctx = []
    for floor in floors:
        fw = warnings_by_floor.get(floor.floor_number)
        chambers_ctx = []
        for idx, ch in enumerate(floor.chambers, start=1):
            cw = next((c for c in fw.chambers if c.chamber_index == idx), None) if fw else None
            halves_ctx = []
            if cw:
                for hw in cw.halves:
                    halves_ctx.append({
                        "half": hw.half,
                        "enemies": [
                            {
                                "name":    ew.enemy_name,
                                "count":   ew.count,
                                "use":     ew.use,
                                "avoid":   ew.avoid,
                                "note":    ew.note,
                                "unknown": ew.unknown,
                            }
                            for ew in hw.enemies
                        ],
                    })
            chambers_ctx.append({
                "chamber_index": idx,
                "level":         ch.level,
                "target":        ch.target,
                "note_vi":       getattr(ch, "note_vi", "") or "",
                "halves":        halves_ctx,
            })
        floor_ctx.append({
            "floor_number":       floor.floor_number,
            "ley_line_disorder":  floor.ley_line_disorder,
            "chambers":           chambers_ctx,
        })

    date_match = _PERIOD_DATE_RE.search(period_title)
    period_label = f"Kỳ bắt đầu {date_match.group(1)}" if date_match else period_title

    return {
        "period_title": period_title,
        "period_label": period_label,
        "floors":       floor_ctx,
    }


def _build_context(nickname, ar, analysis: AccountAnalysis,
                   abyss_data=None, theater_data=None) -> dict:
    all_builds = _get_crimsonwitch_builds_safe()
    score_rows = _build_score_rows(analysis.scores, all_builds)
    accordions = _build_guide_accordions(analysis.scores, analysis.guides)
    icon_map   = _build_item_icon_map(score_rows, accordions)
    llm_advice_html = _wrap_known_items(markdown.markdown(analysis.llm_advice), icon_map)

    return {
        "report_date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nickname":         nickname,
        "ar":               ar,
        "stat_columns": [(label, tip) for label, _, tip in STAT_COLUMNS],
        "scores":           score_rows,
        "llm_advice":       analysis.llm_advice,
        "llm_advice_html":  llm_advice_html,
        "guide_accordions": accordions,
        "abyss":            _build_abyss_context(abyss_data),
        "theater":          _build_theater_context(theater_data),
    }

def _build_guide_url(name_en: str) -> str:
    if not name_en:
        return ""
    slug = name_en.strip().lower().replace(" ", "_")
    return f"https://genshin-builds.com/vi/character/{slug}"

def _build_theater_context(theater_data) -> dict | None:
    """theater_data: None hoặc tuple (period_title, list[ActData], list[ActWarning])
    từ theater_pipeline.get_theater_data() + theater_planner.generate_theater_warnings()."""
    if theater_data is None:
        return None
    period_title, acts, act_warnings = theater_data

    acts_ctx = []
    for aw in act_warnings:
        battles_ctx = []
        for bw in aw.battles:
            variants_ctx = []
            for vw in bw.variants:
                variants_ctx.append({
                    "variant_index": vw.variant_index,
                    "target":        vw.target,
                    "level_raw":     vw.level_raw,
                    "advantage":     vw.advantage,
                    "waves": [
                        [
                            {
                                "name":             ew.enemy_name,
                                "count":            ew.count,
                                "aura":             ew.aura,
                                "is_bounty_target": ew.is_bounty_target,
                                "use":              ew.use,
                                "avoid":            ew.avoid,
                                "note":             ew.note,
                                "unknown":          ew.unknown,
                            }
                            for ew in wave
                        ]
                        for wave in vw.waves
                    ],
                })
            battles_ctx.append({
                "battle_name":   bw.battle_name,
                "stage_effects": bw.stage_effects,
                "variants":      variants_ctx,
            })
        acts_ctx.append({
            "act_name":    aw.act_name,
            "description": aw.description,
            "battles":     battles_ctx,
        })

    date_match = _PERIOD_DATE_RE.search(period_title)
    period_label = f"Kỳ bắt đầu {date_match.group(1)}" if date_match else period_title

    return {
        "period_title": period_title,
        "period_label": period_label,
        "acts":          acts_ctx,
    }