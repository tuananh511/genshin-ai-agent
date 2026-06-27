import sqlite3
import json
from pathlib import Path
from genshin_agent.data_collector import AccountSnapshot

DB_PATH = Path(__file__).resolve().parent.parent / "genshin_agent.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # trả về dict thay vì tuple
    return conn


def init_db():
    """Tạo các bảng nếu chưa có. Chạy an toàn nhiều lần (IF NOT EXISTS)."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            uid         TEXT PRIMARY KEY,
            nickname    TEXT,
            ar          INTEGER,
            updated_at  TEXT DEFAULT (datetime('now'))
        );
                       
        CREATE TABLE IF NOT EXISTS character_guides (
            avatar_id        INTEGER PRIMARY KEY,
            slug             TEXT,
            artifact_section TEXT,
            weapon_section   TEXT,
            fetched_at       TEXT
        );              

        CREATE TABLE IF NOT EXISTS characters (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            uid                 TEXT,
            avatar_id           INTEGER,
            level               INTEGER,
            ascension           INTEGER,
            constellation_count INTEGER,
            skill_levels        TEXT,
            FOREIGN KEY (uid) REFERENCES accounts(uid)
        );

        CREATE TABLE IF NOT EXISTS weapons (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            char_id     INTEGER,
            item_id     INTEGER,
            level       INTEGER,
            ascension   INTEGER,
            refinement  INTEGER,
            rarity      INTEGER,
            base_stats  TEXT,
            name_hash   TEXT,
            FOREIGN KEY (char_id) REFERENCES characters(id)
        );

        CREATE TABLE IF NOT EXISTS artifacts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            char_id         INTEGER,
            item_id         INTEGER,
            set_id          INTEGER,
            slot            TEXT,
            level           INTEGER,
            rarity          INTEGER,
            main_stat       TEXT,
            sub_stats       TEXT,
            name_hash       TEXT,
            set_name_hash   TEXT,
            FOREIGN KEY (char_id) REFERENCES characters(id)
        );

        CREATE TABLE IF NOT EXISTS asset_cache (
            key         TEXT PRIMARY KEY,
            value       TEXT,
            fetched_at  TEXT
        );
    """)
    conn.commit()
    conn.close()


def save_snapshot(snapshot: AccountSnapshot):
    """Xoá dữ liệu cũ của uid này rồi ghi lại toàn bộ từ snapshot mới."""
    conn = get_connection()

    # Xoá dữ liệu cũ theo thứ tự ngược (con trước, cha sau)
    # để không vi phạm FOREIGN KEY
    conn.execute("""
        DELETE FROM artifacts WHERE char_id IN (
            SELECT id FROM characters WHERE uid = ?
        )
    """, (snapshot.uid,))
    conn.execute("""
        DELETE FROM weapons WHERE char_id IN (
            SELECT id FROM characters WHERE uid = ?
        )
    """, (snapshot.uid,))
    conn.execute("DELETE FROM characters WHERE uid = ?", (snapshot.uid,))
    conn.execute("DELETE FROM accounts WHERE uid = ?", (snapshot.uid,))

    # Ghi account
    conn.execute(
        "INSERT INTO accounts (uid, nickname, ar) VALUES (?, ?, ?)",
        (snapshot.uid, snapshot.nickname, snapshot.adventure_rank)
    )

    # Ghi từng nhân vật
    for char in snapshot.characters:
        cursor = conn.execute(
            """INSERT INTO characters
               (uid, avatar_id, level, ascension, constellation_count, skill_levels)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                snapshot.uid,
                char.avatar_id,
                char.level,
                char.ascension,
                char.constellation_count,
                json.dumps(char.skill_levels),
            )
        )
        char_id = cursor.lastrowid

        # Ghi weapon
        if char.weapon:
            w = char.weapon
            conn.execute(
                """INSERT INTO weapons
                   (char_id, item_id, level, ascension, refinement, rarity, base_stats, name_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    char_id,
                    w.item_id,
                    w.level,
                    w.ascension,
                    w.refinement,
                    w.rarity,
                    json.dumps([{"prop_id": s.prop_id, "value": s.value} for s in w.base_stats]),
                    w.name_hash,
                )
            )

        # Ghi artifacts
        for a in char.artifacts:
            conn.execute(
                """INSERT INTO artifacts
                   (char_id, item_id, set_id, slot, level, rarity, main_stat, sub_stats, name_hash, set_name_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    char_id,
                    a.item_id,
                    a.set_id,
                    a.slot,
                    a.level,
                    a.rarity,
                    json.dumps({"prop_id": a.main_stat.prop_id, "value": a.main_stat.value}),
                    json.dumps([{"prop_id": s.prop_id, "value": s.value} for s in a.sub_stats]),
                    a.name_hash,
                    a.set_name_hash,
                )
            )

    conn.commit()
    conn.close()


def load_snapshot(uid: str) -> dict | None:
    """Đọc lại toàn bộ dữ liệu của 1 uid từ database, trả về dict."""
    conn = get_connection()

    account = conn.execute(
        "SELECT * FROM accounts WHERE uid = ?", (uid,)
    ).fetchone()

    if not account:
        conn.close()
        return None

    characters = conn.execute(
        "SELECT * FROM characters WHERE uid = ?", (uid,)
    ).fetchall()

    result = {
        "uid": account["uid"],
        "nickname": account["nickname"],
        "ar": account["ar"],
        "characters": []
    }

    for char in characters:
        weapon = conn.execute(
            "SELECT * FROM weapons WHERE char_id = ?", (char["id"],)
        ).fetchone()

        artifacts = conn.execute(
            "SELECT * FROM artifacts WHERE char_id = ?", (char["id"],)
        ).fetchall()

        result["characters"].append({
            "avatar_id": char["avatar_id"],
            "level": char["level"],
            "constellation_count": char["constellation_count"],
            "skill_levels": json.loads(char["skill_levels"]),
            "weapon": dict(weapon) if weapon else None,
            "artifacts": [dict(a) for a in artifacts],
        })

    conn.close()
    return result

