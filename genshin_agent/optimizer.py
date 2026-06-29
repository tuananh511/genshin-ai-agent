from dataclasses import dataclass
from genshin_agent.data_collector import Character, Artifact, Weapon
from genshin_agent.asset_manager import asset_manager
from genshin_agent.guide_collector import get_character_guide
from genshin_agent.llm_client import safe_llm_call

MAX_ARTIFACT_LEVEL = 20
MIN_TALENT_LEVEL = 6

FRIENDLY_STAT_LABELS = {
    "FIGHT_PROP_CRITICAL": "Crit Rate", "FIGHT_PROP_CRITICAL_HURT": "Crit DMG",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "Energy Recharge", "FIGHT_PROP_ELEMENT_MASTERY": "Elemental Mastery",
    "FIGHT_PROP_HP_PERCENT": "HP%", "FIGHT_PROP_ATTACK_PERCENT": "ATK%", "FIGHT_PROP_DEFENSE_PERCENT": "DEF%",
    "FIGHT_PROP_HEAL_ADD": "Healing Bonus", "FIGHT_PROP_FIRE_ADD_HURT": "Pyro DMG%",
    "FIGHT_PROP_WATER_ADD_HURT": "Hydro DMG%", "FIGHT_PROP_GRASS_ADD_HURT": "Dendro DMG%",
    "FIGHT_PROP_ELEC_ADD_HURT": "Electro DMG%", "FIGHT_PROP_ICE_ADD_HURT": "Cryo DMG%",
    "FIGHT_PROP_WIND_ADD_HURT": "Anemo DMG%", "FIGHT_PROP_ROCK_ADD_HURT": "Geo DMG%",
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
    weapon_name: str
    weapon_icon_url: str
    artifact_sets: dict
    artifact_set_icons: dict   # tên set -> icon url (đại diện, lấy icon đầu tiên gặp)
    artifact_issues: list[ArtifactIssue]
    low_talents: dict


@dataclass
class AccountAnalysis:
    scores: list[CharacterScore]
    llm_advice: str
    guide_sources: list[dict]
    guides: dict  # avatar_id -> guide dict, cho TẤT CẢ nhân vật (dùng cho Accordion)


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
    return [ArtifactIssue(slot=a.slot, level=a.level, issue="not_maxed") for a in artifacts if a.level < MAX_ARTIFACT_LEVEL]


def _check_low_talents(skill_levels: dict, avatar_id: int) -> dict:
    return {
        asset_manager.get_skill_name(avatar_id, skill_id): level
        for skill_id, level in skill_levels.items()
        if level < MIN_TALENT_LEVEL
    }


def score_character(char: Character) -> CharacterScore:
    weapon_name = asset_manager.resolve_name(char.weapon.name_hash) if char.weapon else "(không có)"
    weapon_icon_url = asset_manager.enka_icon_url(char.weapon.icon) if char.weapon else ""

    set_counts: dict[str, int] = {}
    set_icons: dict[str, str] = {}
    for a in char.artifacts:
        set_name = asset_manager.resolve_name(a.set_name_hash)
        if set_name == "(chưa rõ tên)":
            set_name = f"(chưa rõ tên #{a.set_name_hash})"
        set_counts[set_name] = set_counts.get(set_name, 0) + 1
        if set_name not in set_icons:
            set_icons[set_name] = asset_manager.enka_icon_url(a.icon)

    return CharacterScore(
        avatar_id=char.avatar_id,
        name=asset_manager.get_avatar_name(char.avatar_id),
        element=asset_manager.get_avatar_element(char.avatar_id),
        level=char.level,
        constellation_count=char.constellation_count,
        stats=_aggregate_stats(char.weapon, char.artifacts),
        weapon_name=weapon_name,
        weapon_icon_url=weapon_icon_url,
        artifact_sets=set_counts,
        artifact_set_icons=set_icons,
        artifact_issues=_check_artifact_issues(char.artifacts),
        low_talents=_check_low_talents(char.skill_levels, char.avatar_id),
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
        sets_text = ", ".join(f"{name} ({count})" for name, count in s.artifact_sets.items())

        guide = guides.get(s.avatar_id) or {}
        if guide:
            top_weapons = ", ".join(asset_manager.translate_en_name(w["name"]) for w in guide.get("weapons", [])[:5])
            top_sets = ", ".join(
                asset_manager.translate_set_label(f"{a['name']} ({a['pieces']})" if a.get("pieces") else a["name"])
                for a in guide.get("artifact_sets", [])[:3]
            )
            guide_text = f"\n  Guide đề xuất vũ khí (cao→thấp): {top_weapons}\n  Guide đề xuất set (cao→thấp): {top_sets}"
        else:
            guide_text = "\n  (Không có dữ liệu guide cho nhân vật này)"

        lines.append(
            f"- {s.name} ({s.element}) Lv{s.level} C{s.constellation_count}: {format_stats(s.stats)}\n"
            f"  Đang dùng vũ khí: {s.weapon_name}. Đang mặc set: {sets_text}\n"
            f"  Vấn đề: {issue_text}{guide_text}"
        )
    return "\n".join(lines)


def analyze_account(characters: list[Character], update_guides: bool = False) -> AccountAnalysis:
    scores = [score_character(char) for char in characters]
    scores.sort(key=lambda s: len(s.artifact_issues) + len(s.low_talents), reverse=True)

    # Lấy guide cho TẤT CẢ nhân vật — dùng cho cả Accordion (đủ 12) và prompt AI (chỉ top 6)
    guides = {s.avatar_id: get_character_guide(s.avatar_id, s.name, force_refresh=update_guides) for s in scores}

    top_scores = scores[:6]
    summary = _build_summary_text(top_scores, guides)

    prompt = f"""Bạn là chuyên gia Genshin Impact, đang giải thích cho người mới.

QUY TẮC BẮT BUỘC:
- Tiếng Việt đơn giản. Thuật ngữ tiếng Anh phải có chú thích ngắn trong ngoặc, ví dụ "Energy Recharge (tốc độ hồi năng lượng)".
- CHỈ dùng dữ liệu được cung cấp dưới đây. Không tự suy đoán số liệu cụ thể không có trong dữ liệu.
- Nếu vũ khí/set hiện ra là "(chưa rõ tên)" hoặc chứa "(chưa rõ tên", bỏ qua việc đối chiếu phần đó, không suy đoán tên thật.
- Không nhắc tên nguồn dữ liệu cụ thể.
- Định dạng: heading "##" cho mục lớn, gạch đầu dòng "-" cho danh sách — KHÔNG dùng số thứ tự (1. 2. 3.).
- Với mỗi nhân vật: nếu vũ khí/set đang dùng KHÔNG nằm trong nhóm đề xuất hàng đầu của guide, nói rõ và đề xuất nên farm gì thay thế. Không có guide thì nói rõ chưa có dữ liệu.

6 nhân vật cần xem xét nhiều nhất:

{summary}

Trả lời theo cấu trúc:
## Đánh giá từng nhân vật
- (mỗi nhân vật 1-2 câu, đối chiếu trực tiếp vũ khí/set đang dùng với guide)

## 3 việc nên làm trước
- (3 việc, ngắn gọn, cụ thể tên nhân vật)"""

    advice = safe_llm_call([prompt])
    if not advice.strip():
        advice = "Không lấy được phân tích từ AI (rate limit hoặc lỗi server). Chạy lại sau vài giây."

    guide_sources = [
        {"name": s.name, "url": f"https://genshin-impact-helper-team.github.io/genshin-builds/en/{guides[s.avatar_id]['slug']}"}
        for s in top_scores if guides.get(s.avatar_id, {}).get("slug")
    ]

    return AccountAnalysis(scores=scores, llm_advice=advice, guide_sources=guide_sources, guides=guides)