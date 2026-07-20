import os
from genshin_agent.paths import app_base_dir
import yaml
from dotenv import load_dotenv

_CONFIG_PATH = app_base_dir() / "config.yaml"

def load_config() -> dict:
    # override=True: đọc lại .env MỖI LẦN gọi (không chỉ 1 lần lúc import module).
    # Cần thiết cho GUI: người dùng có thể lưu API key ở tab Cài đặt SAU KHI app
    # đã khởi động — nếu chỉ load_dotenv() 1 lần lúc import, tiến trình đang chạy
    # sẽ không bao giờ thấy giá trị mới, gây KeyError dù .env đã có key.
    load_dotenv(override=True)

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Chưa có LLM_API_KEY. Vào tab Cài đặt (GUI) hoặc chạy lại main.py (CLI) "
            "để nhập Google AI Studio API key trước."
        )
    config["llm"]["api_key"] = api_key
    return config