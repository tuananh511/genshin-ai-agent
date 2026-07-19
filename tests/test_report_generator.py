import os
from pathlib import Path
from dotenv import load_dotenv
import pytest
from genshin_agent.data_collector import collect_account
from genshin_agent.optimizer import analyze_account
from genshin_agent.report_generator import generate_reports

load_dotenv()

@pytest.mark.llm
def test_generate_reports():
    uid      = os.environ["GENSHIN_UID"]
    account  = collect_account(uid)
    analysis = analyze_account(account.characters)

    html_path, md_path = generate_reports(
        nickname=account.nickname,
        ar=account.adventure_rank,
        analysis=analysis,
    )

    print(f"\nHTML: {html_path}")
    print(f"MD:   {md_path}")

    assert html_path.exists()
    assert md_path.exists()
    assert html_path.stat().st_size > 1000
    assert md_path.stat().st_size > 500