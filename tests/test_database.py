import os
from dotenv import load_dotenv
from genshin_agent.data_collector import collect_account
from genshin_agent.database import init_db, save_snapshot, load_snapshot
from genshin_agent.asset_manager import asset_manager

load_dotenv()


def test_save_and_load_snapshot():
    uid = os.environ["GENSHIN_UID"]
    init_db()
    snapshot = collect_account(uid)
    save_snapshot(snapshot)
    loaded = load_snapshot(uid)

    assert loaded is not None
    assert loaded["uid"] == uid
    assert len(loaded["characters"]) > 0

    char = loaded["characters"][0]
    assert char["weapon"] is not None
    assert len(char["artifacts"]) <= 5


def test_asset_manager_cache():
    characters = asset_manager.characters
    assert len(characters) > 100

    # Ayaka luôn có trong game — dùng làm mốc kiểm tra cố định
    name = asset_manager.get_avatar_name(10000002)
    element = asset_manager.get_avatar_element(10000002)
    assert element == "Ice"
    assert "Ayaka" in name