from langchain_openai import ChatOpenAI
from genshin_agent.config import load_config

def get_llm() -> ChatOpenAI:
    cfg = load_config()["llm"]
    return ChatOpenAI(
        model=cfg["model"],
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
    )

import time

MAX_RESPONSE_CHARS = 3000

VIETNAMESE_CHARS = "ăâđêôơưàằầậảẩẫáắấậạéèẻẽẹêềếểễệíìỉĩịóòỏõọôồốổỗộơờớởỡợúùủũụưừứửữựýỳỷỹỵ"


def _looks_broken(text: str) -> bool:
    """Phát hiện response bị lặp vòng, rỗng, hoặc không phải tiếng Việt — lỗi thường gặp ở model free."""
    if not text or not text.strip():
        return True
    if len(text) > MAX_RESPONSE_CHARS:
        return True
    if len(text) > 60 and not any(c in VIETNAMESE_CHARS for c in text.lower()):
        return True  # dài nhưng không có dấu tiếng Việt -> nhiều khả năng trả lời bằng tiếng Anh
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 15]
    if sentences:
        most_common_count = max(sentences.count(s) for s in set(sentences))
        if most_common_count >= 4:
            return True
    return False


def safe_llm_call(prompts: list[str], retry_delay: int = 5) -> str:
    """Thử từng prompt trong list (ví dụ: prompt đầy đủ, rồi prompt rút gọn dự phòng).
    Tự phát hiện response lặp/hỏng và thử lại. Trả về '' nếu tất cả thất bại."""
    llm = get_llm()
    for i, prompt in enumerate(prompts):
        if i > 0:
            time.sleep(retry_delay)
        try:
            response = llm.invoke(prompt)
            text = response.content if isinstance(response.content, str) else ""
        except Exception as e:
            print(f"  [warn] Lỗi khi gọi LLM: {e}")
            continue
        if not _looks_broken(text):
            return text
        print("  [warn] Response có vẻ bị lặp/hỏng, thử lại...")
    return ""