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
    return [
        ArtifactIssue(slot=a.slot, level=a.level, issue="not_maxed")
        for a in artifacts if a.level < MAX_ARTIFACT_LEVEL
    ]


def _check_low_talents(skill_levels: dict, avatar_id: int) -> dict:
    return {
        asset_manager.get_skill_name(avatar_id, skill_id): level
        for skill_id, level in skill_levels.items()
        if level < MIN_TALENT_LEVEL
    }


def score_character(char: Character) -> CharacterScore:
    # V3: dùng get_weapon_name(item_id, hash) thay vì resolve_name(hash)
    # → kích hoạt fallback gi.yatta.moe cho ~11 hash không có trong TextMap
    weapon_name = (
        asset_manager.get_weapon_name(char.weapon.item_id, char.weapon.name_hash)
        if char.weapon else "(không có)"
    )
    weapon_icon_url = asset_manager.enka_icon_url(char.weapon.icon) if char.weapon else ""

    set_counts: dict[str, int] = {}
    set_icons: dict[str, str] = {}
    for a in char.artifacts:
        # V3: dùng get_reliquary_name(set_id, hash) — tự fallback yatta + tự format hash
        set_name = asset_manager.get_reliquary_name(a.set_id, a.set_name_hash)
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

def _match_weapon_role(weapon_name_vi: str, roles: dict) -> dict:
    """So khớp vũ khí đang dùng (tên tiếng Việt, từ s.weapon_name) với vũ khí trong
    TẤT CẢ role của guide — code thuần, để tránh lặp lại bug cũ (LLM tự đối chiếu
    gây sai vặt không nhất quán, xem PROJECT_MEMORY.md mục Nhóm C)."""
    matches = []
    for role_name, role_data in roles.items():
        for w in role_data.get("weapons", []):
            if asset_manager.translate_weapon_name_en(w["name"]).strip().lower() == weapon_name_vi.strip().lower():
                matches.append(role_name)
                break
    return {"matched_roles": matches, "matched_any": bool(matches)}

def _match_artifact_sets_role(artifact_sets: dict[str, int], roles: dict) -> dict:
    """So khớp set ĐẠT ĐỦ 4 MẢNH (count >= 4) đang mặc với set "(4)" trong guide — code thuần.
    Build không đạt 4 mảnh ở set nào (combo 2+2, 3+2...) KHÔNG được phán đúng/sai ở đây —
    guide không ghi rõ set nào được đề xuất ghép cặp với set nào (chỉ liệt kê set đơn lẻ
    kèm số mảnh), phán thêm sẽ là suy đoán không có nguồn (xem PROJECT_MEMORY.md mục 13)."""
    full_sets = [name for name, count in artifact_sets.items() if count >= 4]
    if not full_sets:
        return {"status": "PARTIAL", "full_sets": [], "matched_roles": {}}

    matched_roles = {}
    for set_name_vi in full_sets:
        matched_roles[set_name_vi] = [
            role_name
            for role_name, role_data in roles.items()
            if any(
                asset_manager.translate_set_label_en(a["name"]).strip().lower() == set_name_vi.strip().lower()
                and a.get("pieces", "").strip() == "(4)"
                for a in role_data.get("artifact_sets", [])
            )
        ]
    return {"status": "EVALUATED", "full_sets": full_sets, "matched_roles": matched_roles}

def _build_summary_text(scores: list[CharacterScore], guides: dict) -> str:
    lines = []
    for s in scores:
        issues = [f"{ai.slot} chưa +20 (đang +{ai.level})" for ai in s.artifact_issues]
        issues += [f"{name} level {lv} (nên >= {MIN_TALENT_LEVEL})" for name, lv in s.low_talents.items()]
        issue_text = ", ".join(issues) if issues else "không có vấn đề rõ ràng"
        sets_text = ", ".join(f"{name} ({count})" for name, count in s.artifact_sets.items())

        guide = guides.get(s.avatar_id) or {}
        roles = guide.get("roles") or {}
        default_role = guide.get("default_role")

        if roles:
            blocks = []
            for role_name, role_data in roles.items():
                top_weapons = ", ".join(
                    asset_manager.translate_weapon_name_en(w["name"]) for w in role_data.get("weapons", [])[:5]
                )
                top_sets = ", ".join(
                    asset_manager.translate_set_label_en(
                        f"{a['name']} ({a['pieces']})" if a.get("pieces") else a["name"]
                    )
                    for a in role_data.get("artifact_sets", [])[:3]
                )
                tag = " [role mặc định/phổ biến nhất]" if role_name == default_role else " [role khác, vẫn hợp lệ theo guide]"
                blocks.append(
                    f"\n  Guide đề xuất (role: {role_name}{tag}) vũ khí (cao→thấp): {top_weapons}"
                    f"\n  Guide đề xuất (role: {role_name}{tag}) set (cao→thấp): {top_sets}"
                )
            guide_text = "".join(blocks)

            # MỚI: so khớp vũ khí bằng code thuần, kết luận sẵn — LLM không tự đối chiếu nữa
            verdict = _match_weapon_role(s.weapon_name, roles)
            if verdict["matched_any"] and default_role in verdict["matched_roles"]:
                weapon_status = "KHÔNG có vấn đề — vũ khí đang dùng khớp đúng role mặc định."
            elif verdict["matched_any"]:
                other = ", ".join(verdict["matched_roles"])
                weapon_status = (
                    f"KHÔNG phải vấn đề — vũ khí đang dùng khớp role khác hợp lệ ({other}), "
                    f"không khớp role mặc định ({default_role}). Chỉ cần 1 câu gợi ý ngắn nếu muốn đổi hướng."
                )
            else:
                weapon_status = "CÓ VẤN ĐỀ THẬT — vũ khí đang dùng không khớp bất kỳ role nào trong guide."
            guide_text += f"\n  Kết luận vũ khí (đã xác định sẵn, không tự đối chiếu lại): {weapon_status}"

            set_verdict = _match_artifact_sets_role(s.artifact_sets, roles)
            if set_verdict["status"] == "PARTIAL":
                worn = ", ".join(f"{n} ({c})" for n, c in s.artifact_sets.items())
                set_status = (
                    f"Không đạt đủ 4 mảnh ở set nào (đang mặc: {worn}) — guide không ghi rõ set nào "
                    f"được đề xuất ghép cặp 2 mảnh, không có dữ liệu để phán đúng/sai, chỉ nêu khách quan."
                )
            else:
                matched_default = [n for n in set_verdict["full_sets"] if default_role in set_verdict["matched_roles"].get(n, [])]
                matched_other = [n for n in set_verdict["full_sets"] if set_verdict["matched_roles"].get(n) and n not in matched_default]
                not_matched = [n for n in set_verdict["full_sets"] if not set_verdict["matched_roles"].get(n)]
                parts = []
                if matched_default:
                    parts.append(f"KHÔNG có vấn đề — bộ {', '.join(matched_default)} (4 mảnh) khớp đúng role mặc định.")
                if matched_other:
                    parts.append(
                        f"KHÔNG phải vấn đề — bộ {', '.join(matched_other)} (4 mảnh) khớp role khác hợp lệ, "
                        f"không khớp role mặc định ({default_role}). Chỉ cần 1 câu gợi ý ngắn nếu muốn đổi hướng."
                    )
                if not_matched:
                    parts.append(f"CÓ VẤN ĐỀ THẬT — bộ {', '.join(not_matched)} (4 mảnh) không khớp bất kỳ role nào trong guide.")
                set_status = " ".join(parts)
            guide_text += f"\n  Kết luận set (đã xác định sẵn, không tự đối chiếu lại): {set_status}"
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

    # Lấy guide cho TẤT CẢ nhân vật — dùng cho cả Accordion (đủ 12) và prompt AI (giờ cũng đủ 12)
    guides = {
        s.avatar_id: get_character_guide(s.avatar_id, s.name, force_refresh=update_guides)
        for s in scores
    }

    summary = _build_summary_text(scores, guides)

    prompt = f"""Bạn là chuyên gia Genshin Impact, đang giải thích cho người mới.

QUY TẮC BẮT BUỘC:
- Tiếng Việt đơn giản. Thuật ngữ tiếng Anh phải có chú thích ngắn trong ngoặc, ví dụ "Energy Recharge (tốc độ hồi năng lượng)".
- CHỈ dùng dữ liệu được cung cấp dưới đây. Không tự suy đoán số liệu cụ thể không có trong dữ liệu.
- Nếu vũ khí/set hiện ra là "(chưa rõ tên)" hoặc chứa "(chưa rõ tên", bỏ qua việc đối chiếu phần đó, không suy đoán tên thật.
- Không nhắc tên nguồn dữ liệu cụ thể.
- Định dạng: mỗi dòng là 1 gạch đầu dòng "-". KHÔNG dùng heading "##". KHÔNG đóng khung số lượng cố định (không viết kiểu "3 việc nên làm trước").
- Dòng "Kết luận set" trong dữ liệu mỗi nhân vật đã cho sẵn kết quả đối chiếu set — chỉ diễn đạt lại bằng tiếng Việt tự nhiên theo đúng nội dung đó, KHÔNG tự đối chiếu lại set với guide.
- Nếu "Kết luận set" bắt đầu bằng "Không đạt đủ 4 mảnh" (trường hợp không có dữ liệu để phán đúng/sai): KHÔNG coi đây là vấn đề thật, không dùng làm lý do liệt kê nhân vật vào danh sách — chỉ nêu khách quan set/mảnh đang mặc (không phán tốt/xấu) nếu nhân vật đã có vấn đề khác cần liệt kê.
- Nếu "Kết luận set" bắt đầu bằng "KHÔNG phải vấn đề" (khớp role khác): áp dụng đúng quy tắc bắt buộc thêm 1 câu ngắn giống rule đã có cho vũ khí.
- # MỚI: Nếu "Kết luận vũ khí" bắt đầu bằng "KHÔNG phải vấn đề" (khớp role khác, không phải role mặc định), nhân vật đó BẮT BUỘC phải có thêm đúng 1 câu ngắn nhắc việc này (VD "đang build theo hướng khác [role], có thể đổi sang [role mặc định] nếu muốn phổ biến hơn") — kể cả khi nhân vật đã có sẵn vấn đề khác (set/talent) trong dòng. KHÔNG được bỏ câu này vì lý do súc tích hoặc vì đây "không phải vấn đề thật" — đây là thông tin bắt buộc hiển thị, tách biệt với khái niệm "vấn đề".
- Chỉ liệt kê nhân vật THỰC SỰ có vấn đề: vũ khí/set đang dùng không nằm trong nhóm đề xuất hàng đầu của guide, hoặc chưa có dữ liệu để đối chiếu, hoặc có talent thấp đáng chú ý, hoặc có "Kết luận vũ khí" thuộc case nêu ở rule trên. Bỏ qua nhân vật đã ổn (mọi mặt đều "KHÔNG có vấn đề") — không cố liệt kê cho đủ số lượng.
- Mỗi dòng: tên nhân vật + vấn đề cụ thể + đề xuất nên farm/làm gì, viết liền trong 1-2 câu.

Toàn bộ 12 nhân vật cần xem xét (đã sắp theo mức độ vấn đề giảm dần):

{summary}

Trả lời chỉ bằng danh sách gạch đầu dòng theo đúng quy tắc trên, không thêm heading hay lời mở đầu/kết thúc."""

    advice = safe_llm_call([prompt])
    if not advice.strip():
        advice = "Không lấy được phân tích từ AI (rate limit hoặc lỗi server). Chạy lại sau vài giây."

    guide_sources = [
        {
            "name": s.name,
            "url": f"https://genshin-impact-helper-team.github.io/genshin-builds/en/{(guides.get(s.avatar_id) or {})['slug']}",
        }
        for s in scores if (guides.get(s.avatar_id) or {}).get("slug")
    ]

    return AccountAnalysis(scores=scores, llm_advice=advice, guide_sources=guide_sources, guides=guides)