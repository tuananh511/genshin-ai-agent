from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import markdown
from genshin_agent.optimizer import AccountAnalysis
from genshin_agent.planner import DailyPlan

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
OUTPUT_DIR = Path(__file__).resolve().parent.parent

STAT_COLUMNS = [
    ("ATK%", "FIGHT_PROP_ATTACK_PERCENT"),
    ("HP%", "FIGHT_PROP_HP_PERCENT"),
    ("DEF%", "FIGHT_PROP_DEFENSE_PERCENT"),
    ("EM", "FIGHT_PROP_ELEMENT_MASTERY"),
    ("ER%", "FIGHT_PROP_CHARGE_EFFICIENCY"),
    ("Crit Rate%", "FIGHT_PROP_CRITICAL"),
    ("Crit DMG%", "FIGHT_PROP_CRITICAL_HURT"),
]

ELEMENT_DMG_PROP = {
    "Pyro": "FIGHT_PROP_FIRE_ADD_HURT", "Hydro": "FIGHT_PROP_WATER_ADD_HURT",
    "Electro": "FIGHT_PROP_ELEC_ADD_HURT", "Cryo": "FIGHT_PROP_ICE_ADD_HURT",
    "Anemo": "FIGHT_PROP_WIND_ADD_HURT", "Geo": "FIGHT_PROP_ROCK_ADD_HURT",
    "Dendro": "FIGHT_PROP_GRASS_ADD_HURT",
}


def _build_score_rows(scores) -> list[dict]:
    rows = []
    for s in scores:
        dmg_prop = ELEMENT_DMG_PROP.get(s.element)
        rows.append({
            "name": s.name,
            "element": s.element,
            "level": s.level,
            "constellation_count": s.constellation_count,
            "stat_values": [s.stats.get(prop_id, 0) for _, prop_id in STAT_COLUMNS],
            "dmg_bonus": s.stats.get(dmg_prop, 0) if dmg_prop else 0,
            "artifact_issue_count": len(s.artifact_issues),
            "low_talent_names": list(s.low_talents.keys()),
        })
    return rows


def _build_context(nickname, ar, analysis: AccountAnalysis, plan: DailyPlan) -> dict:
    return {
        "report_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nickname": nickname,
        "ar": ar,
        "stat_columns": [label for label, _ in STAT_COLUMNS],
        "scores": _build_score_rows(analysis.scores),
        "llm_advice": analysis.llm_advice,
        "llm_advice_html": markdown.markdown(analysis.llm_advice),
        "guide_sources": analysis.guide_sources,
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