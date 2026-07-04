# test_abyss_pipeline.py — để ở root project, chạy 1 lần để xác nhận
from genshin_agent.llm_client import safe_llm_call   # dùng lại LLM client đã có
from genshin_agent.abyss_pipeline import get_abyss_data

period, floors = get_abyss_data(llm_call=safe_llm_call, force_refresh=True)
print(f"Kỳ: {period}")
for f in floors:
    print(f"\n=== Floor {f.floor_number} ===")
    for i, ch in enumerate(f.chambers, 1):
        print(f"  Chamber {i}: {ch.target}")
        if ch.note_vi:
            print(f"  → note_vi: {ch.note_vi}")

from genshin_agent.abyss_planner import generate_warnings, format_warnings
warnings = generate_warnings(floors)
print(format_warnings(warnings))