import os
from dotenv import load_dotenv
from genshin_agent.data_collector import collect_account

load_dotenv()

def test_collect_account_returns_valid_data():
    uid = os.environ["GENSHIN_UID"]
    account = collect_account(uid)

    assert account.uid == uid
    assert len(account.characters) > 0

    c = account.characters[0]
    assert 1 <= c.level <= 90
    assert c.weapon is not None
    assert 1 <= c.weapon.refinement <= 5
    assert len(c.artifacts) <= 5