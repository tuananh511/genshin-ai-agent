"""
debug_guide_structure.py
Mục đích: in ra cấu trúc thật `guide["weapons"]` / `guide["artifact_sets"]`
và dữ liệu equip thật (`weapon_name`, `artifact_sets`) cho vài nhân vật cụ thể,
để xác nhận trước khi viết logic so khớp bằng code (thay cho để LLM tự đoán).

Cách dùng: KHÔNG chạy file này độc lập. Chèn vào main.py ngay sau dòng
gọi analyze_account(...), dùng đúng data thật của 1 lần chạy `uv run main.py`
để tránh lệch avatar_id / cấu trúc so với account thật.

Ví dụ chèn vào main.py:

    analysis = analyze_account(characters)
    from debug_guide_structure import debug_dump
    debug_dump(analysis, names=["Bennett", "Xingqiu", "Kuki Shinobu"])
    # thêm tên bất kỳ nhân vật nào bạn nghi có build 2 set 2 mảnh (VD Nahida, Kazuha lai EM)
"""

import json


def debug_dump(analysis, names: list[str]):
    scores_by_name = {s.name: s for s in analysis.scores}

    for name in names:
        score = scores_by_name.get(name)
        if score is None:
            print(f"[SKIP] Không tìm thấy nhân vật '{name}' trong account.")
            continue

        guide = analysis.guides.get(score.avatar_id) or {}

        print(f"\n===== {name} (avatar_id={score.avatar_id}) =====")
        print("-- ĐANG DÙNG (equip thật) --")
        print("weapon_name:", repr(score.weapon_name))
        print("artifact_sets:", score.artifact_sets)

        print("-- GUIDE (đầy đủ, KHÔNG cắt [:5]/[:3] như prompt hiện tại) --")
        print("weapons:")
        print(json.dumps(guide.get("weapons", []), ensure_ascii=False, indent=2))
        print("artifact_sets:")
        print(json.dumps(guide.get("artifact_sets", []), ensure_ascii=False, indent=2))