import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

def load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config["llm"]["api_key"] = os.environ["OPENROUTER_API_KEY"]
    return config