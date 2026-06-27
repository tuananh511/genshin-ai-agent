import os
from dotenv import load_dotenv
from genshin_agent.data_collector import collect_account
from genshin_agent.optimizer import analyze_account
from genshin_agent.planner import (
    get_day_name,
    make_resin_plan,
)
import pytest
load_dotenv()

@pytest.mark.llm
def test_make_resin_plan():
    uid      = os.environ["GENSHIN_UID"]
    account  = collect_account(uid)
    analysis = analyze_account(account.characters)

    plan = make_resin_plan(analysis=analysis)

    print(f"\nNgày: {plan.server_date} ({plan.day_of_week})")
    print(f"Required: {len(plan.required_todos)}, Optional: {len(plan.optional_todos)}")
    for todo in plan.required_todos:
        print(f"  [required] {todo.label}: {todo.reason}")
    assert isinstance(plan.required_todos, list)