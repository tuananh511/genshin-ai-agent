import time
import yaml
from pathlib import Path
from langchain_openai import ChatOpenAI
from genshin_agent.config import load_config

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
MAX_RESPONSE_CHARS = 3000
VIETNAMESE_CHARS = "ăâđêôơưàằầậảẩẫáắấậạéèẻẽẹêềếểễệíìỉĩịóòỏõọôồốổỗộơờớởỡợúùủũụưừứửữựýỳỷỹỵ"


def get_llm(model: str | None = None) -> ChatOpenAI:
    cfg = load_config()["llm"]
    return ChatOpenAI(
        model=model or cfg["model"],
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
    )


def _save_model_to_config(model: str):
    """Lưu model mới vào config.yaml — lần chạy sau dùng luôn, không hỏi lại."""
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        full_config = yaml.safe_load(f)
    full_config["llm"]["model"] = model
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(full_config, f, allow_unicode=True, sort_keys=False)
    print(f"  [info] Đã lưu model '{model}' vào config.yaml cho các lần chạy sau")


def _looks_broken(text: str) -> bool:
    """Phát hiện response bị lặp vòng, rỗng, hoặc không phải tiếng Việt — lỗi thường gặp ở model free."""
    if not text or not text.strip():
        return True
    if len(text) > MAX_RESPONSE_CHARS:
        return True
    if len(text) > 60 and not any(c in VIETNAMESE_CHARS for c in text.lower()):
        return True
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 15]
    if sentences:
        most_common_count = max(sentences.count(s) for s in set(sentences))
        if most_common_count >= 4:
            return True
    return False


def _ask_user_for_alternative_model(first_prompt: str) -> str:
    print()
    print("=" * 60)
    print("Model hiện tại đang lỗi liên tục (server quá tải hoặc tên model không đúng).")
    print("Xem danh sách model hiện có tại:")
    print("https://ai.google.dev/gemini-api/docs/models?hl=vi")
    print("=" * 60)
    new_model = input("Nhập tên model khác để thử (Enter để bỏ qua): ").strip()
    if not new_model:
        return ""

    try:
        llm = get_llm(model=new_model)
        response = llm.invoke(first_prompt)
        text = response.content if isinstance(response.content, str) else ""
    except Exception as e:
        print(f"  [warn] Model '{new_model}' cũng lỗi: {e}")
        return ""

    if _looks_broken(text):
        print(f"  [warn] Model '{new_model}' trả lời không hợp lệ")
        return ""

    _save_model_to_config(new_model)
    return text


def safe_llm_call(prompts: list[str], retry_delay: int = 5) -> str:
    """Thử từng prompt trong list. Nếu hết tất cả mà vẫn lỗi, hỏi người dùng đổi model."""
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

    return _ask_user_for_alternative_model(prompts[0])