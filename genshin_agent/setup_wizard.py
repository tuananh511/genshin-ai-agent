from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"



def _read_env() -> dict:
    if not ENV_PATH.exists():
        return {}
    env = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def _write_env(env: dict):
    ENV_PATH.write_text("\n".join(f"{k}={v}" for k, v in env.items()) + "\n", encoding="utf-8")


def ensure_config() -> None:
    """Chạy 1 lần đầu nếu .env chưa đủ thông tin — hỏi người dùng nhập API key + UID."""
    env = _read_env()

    if not env.get("LLM_API_KEY"):
        print("=" * 60)
        print("THIẾT LẬP LẦN ĐẦU — cần Google AI Studio API key (miễn phí)")
        print("=" * 60)
        print("1. Vào https://aistudio.google.com/ , đăng nhập bằng Google account")
        print("2. Vào https://aistudio.google.com/apikey , bấm 'Create API key'")
        print("3. Copy key (dạng AIza...) và dán vào đây")
        print()
        print("Lưu ý: mỗi người PHẢI tự tạo key riêng — không thể dùng chung 1 key")
        print("qua source code public, vì ai cũng lấy được và sẽ làm hết quota free.")
        print()
        key = ""
        while not key.strip():
            key = input("Dán Google AI Studio API key của bạn: ").strip()
        env["LLM_API_KEY"] = key

    if not env.get("GENSHIN_UID"):
        print()
        print("Cần UID Genshin Impact của bạn để phân tích đúng account thật.")
        print("Xem UID trong Pause Menu (ESC trong game) — dãy 9 số ở góc dưới màn hình.")
        print("Nhớ đã bật 'Tủ trưng bày nhân vật' (Character Showcase) cho các nhân vật muốn phân tích.")
        uid = ""
        while not uid.strip():
            uid = input("Nhập UID Genshin của bạn: ").strip()
        env["GENSHIN_UID"] = uid

    _write_env(env)
    print("\nĐã lưu vào .env — lần sau sẽ không hỏi lại.\n")