import os
from dotenv import load_dotenv
import pytest
from genshin_agent.data_collector import collect_account
from genshin_agent.optimizer import score_character, analyze_account
from genshin_agent.knowledge_collector import get_characters_data, get_loc_data, get_avatar_name, get_avatar_element
load_dotenv()

def test_score_character():
    uid = os.environ["GENSHIN_UID"]
    account = collect_account(uid)

    char_data = get_characters_data()
    loc = get_loc_data("en")

    char = account.characters[0]
    name = get_avatar_name(char.avatar_id, char_data, loc)
    element = get_avatar_element(char.avatar_id, char_data)
    score = score_character(char, name, element, char_data)

    assert isinstance(score.stats, dict)
    assert score.level > 0
    assert score.name != ""
    print(f"\n{score.name}: {score.stats}")
    print(f"  Artifact issues: {score.artifact_issues}")
    print(f"  Low talents: {score.low_talents}")


@pytest.mark.llm
def test_analyze_account():
    uid = os.environ["GENSHIN_UID"]
    account = collect_account(uid)

    analysis = analyze_account(account.characters)

    assert len(analysis.scores) > 0
    assert analysis.llm_advice
    print(f"\nLLM advice:\n{analysis.llm_advice}")