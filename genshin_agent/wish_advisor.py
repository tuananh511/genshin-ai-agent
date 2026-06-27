from dataclasses import dataclass
from genshin_agent.optimizer import AccountAnalysis, format_stats
from genshin_agent.llm_client import safe_llm_call


@dataclass
class WishAdvice:
    recommendation: str


def _element_distribution(scores) -> str:
    counts: dict[str, int] = {}
    for s in scores:
        counts[s.element] = counts.get(s.element, 0) + 1
    return ", ".join(f"{el}: {n}" for el, n in sorted(counts.items(), key=lambda x: -x[1]))


def get_wish_advice(analysis: AccountAnalysis) -> WishAdvice:
    char_lines = [
        f"- {s.name} ({s.element}) Lv{s.level} C{s.constellation_count}: {format_stats(s.stats)}"
        for s in analysis.scores
    ]
    char_summary = "\n".join(char_lines)
    element_dist = _element_distribution(analysis.scores)

    prompt = f"""Bạn là chuyên gia Genshin Impact, tư vấn nên roll banner nào tiếp theo.

BẮT BUỘC:
- CHỈ trả lời bằng tiếng Việt. Không viết bất kỳ câu tiếng Anh nào.
- Không nói chung/mơ hồ kiểu "nên cân nhắc", "tuỳ ý". Luôn nêu TÊN nhân vật/Constellation cụ thể.
- CHỈ đề xuất nhân vật/vũ khí 5 SAO. Không đề xuất 4 sao.
- Nếu đề xuất Constellation, nói rõ nó làm gì (ví dụ "C2 Xiangling tăng % sát thương Pyro").

Nhân vật hiện có:
{char_summary}

Phân bố nguyên tố hiện có (tính từ account, không phải đoán): {element_dist}

Trả lời dưới 150 từ, đúng cấu trúc:
1. Nguyên tố/vai trò nào account ĐANG THIẾU rõ nhất (dựa vào phân bố nguyên tố trên) — nêu tên 1-2 nhân vật 5 sao cụ thể phù hợp để bổ sung.
2. Trong số nhân vật ĐÃ CÓ, Constellation nào đáng lên nhất và vì sao (1 câu)."""

    advice = safe_llm_call([
        prompt,
        f"Genshin Impact account, nguyên tố hiện có: {element_dist}.\n{char_summary}\n"
        f"CHỈ TIẾNG VIỆT. Nêu tên nhân vật 5 sao cụ thể nên roll để bổ sung nguyên tố đang thiếu.",
    ])
    if not advice.strip():
        advice = "Không lấy được lời khuyên từ AI (rate limit hoặc lỗi server). Chạy lại sau."

    return WishAdvice(recommendation=advice)