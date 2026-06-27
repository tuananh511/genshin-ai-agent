from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
DEMO_UID = "DEMO_UID_CUA_BAN"  # << đổi thành 1 UID bạn chấp nhận công khai trước khi đẩy lên Github


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

    if not env.get("OPENROUTER_API_KEY"):
        print("=" * 60)
        print("THIẾT LẬP LẦN ĐẦU — cần OpenRouter API key (miễn phí)")
        print("=" * 60)
        print("1. Vào https://openrouter.ai/ , đăng ký miễn phí (Google/email)")
        print("2. Vào https://openrouter.ai/settings/keys , bấm 'Create Key'")
        print("3. Copy key (dạng sk-or-v1-...) và dán vào đây")
        print()
        print("Lưu ý: mỗi người PHẢI tự tạo key riêng — không thể dùng chung 1 key")
        print("qua source code public, vì ai cũng lấy được và sẽ làm hết quota free.")
        print()
        key = ""
        while not key.strip():
            key = input("Dán OpenRouter API key của bạn: ").strip()
        env["OPENROUTER_API_KEY"] = key

    if not env.get("GENSHIN_UID"):
        print()
        choice = input("Dùng UID Genshin của bạn? (Y/N — N = dùng UID demo công khai để xem thử): ").strip().lower()
        if choice == "y":
            uid = ""
            while not uid.strip():
                uid = input("Nhập UID Genshin (xem trong Pause Menu, 9 số): ").strip()
            env["GENSHIN_UID"] = uid
        else:
            print(f"  -> Dùng UID demo: {DEMO_UID}")
            env["GENSHIN_UID"] = DEMO_UID

    _write_env(env)
    print("\nĐã lưu vào .env — lần sau sẽ không hỏi lại.\n")