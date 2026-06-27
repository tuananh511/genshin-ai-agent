from dataclasses import dataclass
from genshin_agent.data_collector import Character, Artifact, Weapon
from genshin_agent.knowledge_collector import (
    get_characters_data,
    get_loc_data,
    get_avatar_name,
    get_avatar_element,
    get_skill_name,
)
from genshin_agent.guide_collector import get_character_guide
from genshin_agent.llm_client import safe_llm_call


MAX_ARTIFACT_LEVEL = 20
MIN_TALENT_LEVEL = 6

FRIENDLY_STAT_LABELS = {
    "FIGHT_PROP_CRITICAL": "Crit Rate",
    "FIGHT_PROP_CRITICAL_HURT": "Crit DMG",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "Energy Recharge",
    "FIGHT_PROP_ELEMENT_MASTERY": "Elemental Mastery",
    "FIGHT_PROP_HP_PERCENT": "HP%",
    "FIGHT_PROP_ATTACK_PERCENT": "ATK%",
    "FIGHT_PROP_DEFENSE_PERCENT": "DEF%",
    "FIGHT_PROP_HEAL_ADD": "Healing Bonus",
    "FIGHT_PROP_FIRE_ADD_HURT": "Pyro DMG%",
    "FIGHT_PROP_WATER_ADD_HURT": "Hydro DMG%",
    "FIGHT_PROP_GRASS_ADD_HURT": "Dendro DMG%",
    "FIGHT_PROP_ELEC_ADD_HURT": "Electro DMG%",
    "FIGHT_PROP_ICE_ADD_HURT": "Cryo DMG%",
    "FIGHT_PROP_WIND_ADD_HURT": "Anemo DMG%",
    "FIGHT_PROP_ROCK_ADD_HURT": "Geo DMG%",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "Physical DMG%",
}


@dataclass
class ArtifactIssue:
    slot: str
    level: int
    issue: str


@dataclass
class CharacterScore:
    avatar_id: int
    name: str
    element: str
    level: int
    constellation_count: int
    stats: dict
    artifact_issues: list[ArtifactIssue]
    low_talents: dict  # skill_name -> level


@dataclass
class AccountAnalysis:
    scores: list[CharacterScore]   # đã sắp xếp theo thứ tự nên build trước
    llm_advice: str
    guide_sources: list[dict]


def _aggregate_stats(weapon: Weapon | None, artifacts: list[Artifact]) -> dict:
    totals: dict[str, float] = {}

    def add(prop_id: str, value: float):
        totals[prop_id] = totals.get(prop_id, 0.0) + value

    if weapon:
        for s in weapon.base_stats:
            add(s.prop_id, s.value)
    for a in artifacts:
        add(a.main_stat.prop_id, a.main_stat.value)
        for s in a.sub_stats:
            add(s.prop_id, s.value)
    return {k: round(v, 1) for k, v in totals.items()}


def _check_artifact_issues(artifacts: list[Artifact]) -> list[ArtifactIssue]:
    return [
        ArtifactIssue(slot=a.slot, level=a.level, issue="not_maxed")
        for a in artifacts if a.level < MAX_ARTIFACT_LEVEL
    ]


def _check_low_talents(skill_levels: dict, avatar_id: int, char_data: dict) -> dict:
    return {
        get_skill_name(avatar_id, skill_id, char_data): level
        for skill_id, level in skill_levels.items()
        if level < MIN_TALENT_LEVEL
    }


def score_character(char: Character, name: str, element: str, char_data: dict) -> CharacterScore:
    return CharacterScore(
        avatar_id=char.avatar_id,
        name=name,
        element=element,
        level=char.level,
        constellation_count=char.constellation_count,
        stats=_aggregate_stats(char.weapon, char.artifacts),
        artifact_issues=_check_artifact_issues(char.artifacts),
        low_talents=_check_low_talents(char.skill_levels, char.avatar_id, char_data),
    )


def format_stats(stats: dict) -> str:
    parts = [f"{FRIENDLY_STAT_LABELS[pid]}={val}" for pid, val in stats.items() if pid in FRIENDLY_STAT_LABELS]
    return ", ".join(parts) if parts else "(không có stat đáng chú ý)"


def _build_summary_text(scores: list[CharacterScore], guides: dict) -> str:
    lines = []
    for s in scores:
        issues = [f"{ai.slot} chưa +20 (đang +{ai.level})" for ai in s.artifact_issues]
        issues += [f"{name} level {lv} (nên >= {MIN_TALENT_LEVEL})" for name, lv in s.low_talents.items()]
        issue_text = ", ".join(issues) if issues else "không có vấn đề rõ ràng"

        guide = guides.get(s.avatar_id, {})
        guide_text = ""
        if guide.get("artifact_section") or guide.get("weapon_section"):
            guide_text = (
                f"\n  [Guide KeqingMains] Artifact: {guide.get('artifact_section', '')[:300]}"
                f"\n  [Guide KeqingMains] Weapon: {guide.get('weapon_section', '')[:300]}"
            )

        lines.append(
            f"- {s.name} ({s.element}) Lv{s.level} C{s.constellation_count}: {format_stats(s.stats)} "
            f"| Vấn đề: {issue_text}{guide_text}"
        )
    return "\n".join(lines)


def analyze_account(characters: list[Character]) -> AccountAnalysis:
    char_data = get_characters_data()
    loc = get_loc_data("en")

    scores = []
    for char in characters:
        name = get_avatar_name(char.avatar_id, char_data, loc)
        element = get_avatar_element(char.avatar_id, char_data)
        scores.append(score_character(char, name, element, char_data))

    # Sắp xếp TOÀN BỘ theo mức cần build trước — dùng cho cả report và chọn 6 nhân vật gửi LLM
    scores.sort(key=lambda s: len(s.artifact_issues) + len(s.low_talents), reverse=True)
    top_scores = scores[:6]

    guides = {s.avatar_id: get_character_guide(s.avatar_id, s.name) for s in top_scores}
    summary = _build_summary_text(top_scores, guides)

    prompt = f"""Bạn là chuyên gia Genshin Impact, đang giải thích cho người mới.
QUAN TRỌNG: KHÔNG dùng thuật ngữ mà không giải thích ngắn kèm theo (ví dụ nếu nói "Energy Recharge" hãy giải thích là "tốc độ hồi năng lượng để dùng chiêu cuối").

6 nhân vật cần xem xét nhiều nhất, kèm dữ liệu build thật từ KeqingMains (nếu có):

{summary}

Trả lời theo đúng cấu trúc:
1. Với MỖI nhân vật trên, 1-2 câu: stat hiện tại có khớp đề xuất từ guide không (dùng "ổn"/"cần cải thiện"), lệch ở đâu. Đừng đoán nếu không có guide.
2. Chốt: 3 việc nên làm trước tiên.

Tiếng Việt đơn giản, ngắn gọn, không thuật ngữ khó hiểu."""

    advice = safe_llm_call([
        prompt,
        f"Genshin Impact account:\n{summary}\nĐề xuất 3 cải thiện quan trọng nhất. Tiếng Việt đơn giản, ngắn gọn.",
    ])
    if not advice.strip():
        advice = "Không lấy được phân tích từ AI (rate limit hoặc lỗi server). Chạy lại sau vài giây."

    guide_sources = [
        {"name": s.name, "url": f"https://keqingmains.com/{guides[s.avatar_id]['slug']}/"}
        for s in top_scores
        if guides.get(s.avatar_id, {}).get("slug")
    ]

    return AccountAnalysis(scores=scores, llm_advice=advice, guide_sources=guide_sources)