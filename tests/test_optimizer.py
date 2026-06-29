import os
from dotenv import load_dotenv
import pytest
from genshin_agent.data_collector import collect_account
from genshin_agent.optimizer import score_character, analyze_account
load_dotenv()

def test_score_character():
    uid = os.environ["GENSHIN_UID"]
    account = collect_account(uid)

    char = account.characters[0]
    score = score_character(char)

    assert isinstance(score.stats, dict)
    assert score.level > 0
    assert score.name != ""
    print(f"\n{score.name}: {score.stats}")


@pytest.mark.llm
def test_analyze_account():
    uid = os.environ["GENSHIN_UID"]
    account = collect_account(uid)

    analysis = analyze_account(account.characters)

    assert len(analysis.scores) > 0
    assert analysis.llm_advice
    print(f"\nLLM advice:\n{analysis.llm_advice}")