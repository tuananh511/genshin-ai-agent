import os
from dotenv import load_dotenv
from genshin_agent.data_collector import collect_account
from genshin_agent.database import init_db, save_snapshot, load_snapshot
from genshin_agent.knowledge_collector import (
    get_characters_data,
    get_loc_data,
    get_avatar_name,
    get_avatar_element,
)

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

    from genshin_agent.knowledge_collector import (
    get_characters_data,
    get_loc_data,
    get_avatar_name,
    get_avatar_element,
)

def test_knowledge_collector_cache():
    characters = get_characters_data()
    loc = get_loc_data("en")

    assert len(characters) > 100
    assert len(loc) > 100

    # Ayaka luôn có trong game
    name = get_avatar_name(10000002, characters, loc)
    element = get_avatar_element(10000002, characters)

    assert name == "Kamisato Ayaka"
    assert element == "Ice"