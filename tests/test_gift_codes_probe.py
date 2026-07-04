# test_gift_codes_probe.py — chạy 1 lần trên máy có mạng thật để xem field name
# thật của initialCodes. Chạy: uv run python test_gift_codes_probe.py
import json
from genshin_agent.gift_codes_pipeline import get_raw_codes

codes = get_raw_codes()
print(f"Số code lấy được: {len(codes)}")
print("\n--- Toàn bộ dữ liệu (để xác nhận field name thật) ---")
print(json.dumps(codes, indent=2, ensure_ascii=False))