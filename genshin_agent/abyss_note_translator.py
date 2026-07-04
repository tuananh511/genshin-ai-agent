"""
abyss_note_translator.py — Dịch field note_en (spawn order) sang tiếng Việt qua LLM.

Nhận raw wikitext ('''...''', <br> còn nguyên) — prompt dặn AI tự bỏ markup.
Không strip trước bằng code (quyết định phiên 2026-07-01, ưu tiên ít code hơn).

Hàm này KHÔNG tự gọi LLM client — nhận callable `llm_call(prompt: str) -> str`
từ bên ngoài để không phụ thuộc cứng vào llm_client.py của Enka pipeline.
"""
from __future__ import annotations

TRANSLATE_PROMPT = """\
Dịch đoạn mô tả sau sang tiếng Việt ngắn gọn, tự nhiên.
Bỏ hết wiki markup ('''...''', <br>, thẻ HTML). Giữ nguyên tên quái (in đậm hoặc không đều được).
Chỉ trả lời bằng bản dịch, không giải thích thêm.

Đoạn cần dịch:
{note_en}"""


def translate_note(note_en: str, llm_call: callable) -> str:
    """
    Dịch 1 note_en sang tiếng Việt.
    llm_call: hàm nhận prompt string, trả về response string (do caller cung cấp).
    Nếu note_en rỗng/None → trả chuỗi rỗng ngay, không gọi LLM.
    """
    if not note_en or not note_en.strip():
        return ""
    prompt = TRANSLATE_PROMPT.format(note_en=note_en.strip())
    result = llm_call([prompt])
    return result.strip() if result else ""


def translate_all_notes(floors: list, llm_call: callable) -> list:
    """
    Nhận list[FloorData] từ abyss_collector, dịch tất cả note_en != None.
    Trả về list[FloorData] với note_vi đã điền (thêm field mới vào dataclass).
    Vì FloorData/ChamberData là dataclass, ta set trực tiếp attribute mới.
    """
    for floor in floors:
        for chamber in floor.chambers:
            if chamber.note_en:
                chamber.note_vi = translate_note(chamber.note_en, llm_call)
            else:
                chamber.note_vi = ""
    return floors
