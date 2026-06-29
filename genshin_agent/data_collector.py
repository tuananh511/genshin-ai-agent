import requests

ENKA_BASE_URL = "https://enka.network/api/uid"
USER_AGENT = "genshin-ai-agent/0.1 (personal-project; contact: your-email-or-discord)"

def fetch_raw_profile(uid: str) -> dict:
    url = f"{ENKA_BASE_URL}/{uid}/"
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()  # tự raise lỗi nếu status code là 4xx/5xx
    return response.json()

from dataclasses import dataclass

PROP_LEVEL = "4001"
PROP_ASCENSION = "1002"

EQUIP_SLOT_MAP = {
    "EQUIP_BRACER": "flower",
    "EQUIP_NECKLACE": "plume",
    "EQUIP_SHOES": "sands",
    "EQUIP_RING": "goblet",
    "EQUIP_DRESS": "circlet",
}

@dataclass
class StatValue:
    prop_id: str
    value: float

@dataclass
class Weapon:
    item_id: int
    level: int
    ascension: int
    refinement: int
    rarity: int
    base_stats: list[StatValue]
    name_hash: str
    icon: str

@dataclass
class Artifact:
    item_id: int
    set_id: int
    slot: str
    level: int
    rarity: int
    main_stat: StatValue
    sub_stats: list[StatValue]
    name_hash: str
    set_name_hash: str
    icon: str

@dataclass
class Character:
    avatar_id: int
    level: int
    ascension: int
    constellation_count: int
    skill_levels: dict
    weapon: Weapon
    artifacts: list[Artifact]

@dataclass
class AccountSnapshot:
    uid: str
    nickname: str
    adventure_rank: int
    characters: list[Character]


def _parse_stat(d: dict) -> StatValue:
    return StatValue(prop_id=d.get("appendPropId") or d.get("mainPropId"), value=d["statValue"])

def _parse_weapon(equip: dict) -> Weapon:
    w = equip["weapon"]
    flat = equip["flat"]
    affix_level = next(iter(w.get("affixMap", {}).values()), 0)
    return Weapon(
        item_id=equip["itemId"],
        level=w["level"],
        ascension=w.get("promoteLevel", 0),
        refinement=affix_level + 1,
        rarity=flat["rankLevel"],
        base_stats=[_parse_stat(s) for s in flat.get("weaponStats", [])],
        name_hash=flat["nameTextMapHash"],
        icon=flat.get("icon", ""),
    )

def _parse_artifact(equip: dict) -> Artifact:
    r = equip["reliquary"]
    flat = equip["flat"]
    return Artifact(
        item_id=equip["itemId"],
        set_id=flat["setId"],
        slot=EQUIP_SLOT_MAP.get(flat["equipType"], flat["equipType"]),
        level=r["level"] - 1,
        rarity=flat["rankLevel"],
        main_stat=_parse_stat(flat["reliquaryMainstat"]),
        sub_stats=[_parse_stat(s) for s in flat.get("reliquarySubstats", [])],
        name_hash=flat["nameTextMapHash"],
        set_name_hash=flat["setNameTextMapHash"],
        icon=flat.get("icon", ""),
    )

def _parse_character(raw: dict) -> Character:
    prop = raw["propMap"]
    weapon = None
    artifacts = []
    for equip in raw["equipList"]:
        if "weapon" in equip:
            weapon = _parse_weapon(equip)
        elif "reliquary" in equip:
            artifacts.append(_parse_artifact(equip))

    return Character(
        avatar_id=raw["avatarId"],
        level=int(prop[PROP_LEVEL]["val"]),
        ascension=int(prop.get(PROP_ASCENSION, {}).get("val", 0)),
        constellation_count=len(raw.get("talentIdList") or []),
        skill_levels=raw.get("skillLevelMap", {}),
        weapon=weapon,
        artifacts=artifacts,
    )

def collect_account(uid: str) -> AccountSnapshot:
    raw = fetch_raw_profile(uid)
    player = raw["playerInfo"]
    characters = [_parse_character(c) for c in raw.get("avatarInfoList", [])]
    return AccountSnapshot(
        uid=raw["uid"],
        nickname=player.get("nickname", ""),
        adventure_rank=player.get("level", 0),
        characters=characters,
    )