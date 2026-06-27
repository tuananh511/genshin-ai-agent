import os
from dotenv import load_dotenv
import pytest
from genshin_agent.data_collector import collect_account
from genshin_agent.optimizer import analyze_account
from genshin_agent.wish_advisor import get_wish_advice

load_dotenv()

@pytest.mark.llm
def test_wish_advice():
    uid      = os.environ["GENSHIN_UID"]
    account  = collect_account(uid)
    analysis = analyze_account(account.characters)
    advice   = get_wish_advice(analysis)

    print(f"\nLời khuyên wish:\n{advice.recommendation}")

    assert advice.recommendation