"""
theater_planner.py — Sinh cảnh báo counter/tránh element cho từng variant
của Imaginarium Theater (Nhà Hát).

Mirror convention của abyss_planner.py, nhưng:
- Tái dùng nguyên ENEMY_DATA từ abyss_planner.py (cùng enemy pool với Abyss,
  không tạo bảng lookup riêng — tránh trùng lặp dữ liệu).
- Field 'advantage' (hệ có lợi thế) do wiki cho sẵn trực tiếp trong
  {{Domain Enemies}} — chỉ truyền thẳng qua, không suy luận thêm.
- Enemy field của Theater có thêm 'aura' và 'is_bounty_target' (xem
  theater_collector.py) — giữ nguyên 2 field này trong EnemyWarning để
  template render đủ, không có trong Abyss.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from genshin_agent.abyss_planner import ENEMY_DATA
from genshin_agent.theater_collector import ActData, BattleData, BattleVariant, EnemyEntry


@dataclass
class EnemyWarning:
    enemy_name: str
    count: int                 # -1 = liên tục/không giới hạn (giữ nguyên convention Abyss)
    aura: str | None
    is_bounty_target: bool
    use: list[str]
    avoid: list[str]
    note: str
    unknown: bool


@dataclass
class VariantWarning:
    variant_index: int         # 1-based, thứ tự N trong số các biến thể song song
    target: str | None
    level_raw: str | None
    advantage: str | None      # hệ có lợi thế, lấy thẳng từ wiki — không suy luận
    waves: list[list[EnemyWarning]] = field(default_factory=list)


@dataclass
class BattleWarning:
    battle_name: str | None
    stage_effects: list[str]
    variants: list[VariantWarning]


@dataclass
class ActWarning:
    act_name: str
    description: str | None
    battles: list[BattleWarning]


def _warn_enemy(entry: EnemyEntry) -> EnemyWarning:
    data = ENEMY_DATA.get(entry.name)
    if data is None:
        return EnemyWarning(
            enemy_name=entry.name, count=entry.count,
            aura=entry.aura, is_bounty_target=entry.is_bounty_target,
            use=[], avoid=[], note="", unknown=True,
        )
    return EnemyWarning(
        enemy_name=entry.name, count=entry.count,
        aura=entry.aura, is_bounty_target=entry.is_bounty_target,
        use=data.get("use", []),
        avoid=data.get("avoid", []),
        note=data.get("note", ""),
        unknown=False,
    )


def _warn_variant(idx: int, v: BattleVariant) -> VariantWarning:
    return VariantWarning(
        variant_index=idx,
        target=v.target,
        level_raw=v.level_raw,
        advantage=v.advantage,
        waves=[[_warn_enemy(e) for e in wave] for wave in v.enemies.waves],
    )


def _warn_battle(b: BattleData) -> BattleWarning:
    return BattleWarning(
        battle_name=b.battle_name,
        stage_effects=b.stage_effects,
        variants=[_warn_variant(i, v) for i, v in enumerate(b.variants, start=1)],
    )


def generate_theater_warnings(acts: list[ActData]) -> list[ActWarning]:
    """Entry point: nhận list[ActData] từ theater_pipeline, trả về list[ActWarning]."""
    return [
        ActWarning(
            act_name=a.act_name,
            description=a.description,
            battles=[_warn_battle(b) for b in a.battles],
        )
        for a in acts
    ]


def format_warnings(act_warnings: list[ActWarning]) -> str:
    """Render text thuần để in ra terminal hoặc debug — mirror format_warnings() của Abyss."""
    lines = []
    for aw in act_warnings:
        lines.append(f"=== {aw.act_name} ===")
        if aw.description:
            lines.append(f"  {aw.description}")
        for bw in aw.battles:
            label = bw.battle_name or "(mặc định)"
            lines.append(f"\n  Battle: {label}")
            if bw.stage_effects:
                lines.append("    Stage Effects:")
                for e in bw.stage_effects:
                    lines.append(f"      - {e}")
            for vw in bw.variants:
                lines.append(f"    Variant {vw.variant_index}: level={vw.level_raw!r} advantage={vw.advantage!r} target={vw.target!r}")
                for wave_idx, wave in enumerate(vw.waves, start=1):
                    lines.append(f"      Wave {wave_idx}:")
                    for ew in wave:
                        prefix = f"        [{ew.enemy_name} ×{ew.count}]"
                        if ew.is_bounty_target:
                            prefix += " ⚠️bounty"
                        if ew.aura:
                            prefix += f" (aura: {ew.aura})"
                        if ew.unknown:
                            lines.append(f"{prefix} — chưa có dữ liệu về quái tên \"{ew.enemy_name}\"")
                        else:
                            parts = []
                            if ew.use:
                                parts.append(f"dùng {'/'.join(ew.use)}")
                            if ew.avoid:
                                parts.append(f"tránh {'/'.join(ew.avoid)}")
                            if ew.note:
                                parts.append(ew.note)
                            lines.append(f"{prefix} — {' | '.join(parts) if parts else 'không có cảnh báo đặc biệt'}")
        lines.append("")
    return "\n".join(lines)