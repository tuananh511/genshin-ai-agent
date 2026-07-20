"""
Chuẩn hoá đường dẫn cho toàn bộ project — dùng thay cho rải rác
`Path(__file__).resolve().parent.parent` hoặc path tương đối ở từng file.

Có 2 khái niệm khác nhau, PHẢI phân biệt rõ để đóng gói PyInstaller (--onefile)
không bị vỡ:

- app_base_dir(): thư mục GHI ĐƯỢC, tồn tại lâu dài — nơi đặt .env, config.yaml,
  genshin_agent.db, report.html, abyss_cache.json, theater_cache.json.
  + Chạy từ source: thư mục gốc project (cạnh main.py/gui_app.py).
  + Chạy từ .exe (PyInstaller --onefile): thư mục CHỨA file .exe — KHÔNG PHẢI
    sys._MEIPASS (thư mục tạm, bị xoá khi app thoát — nếu lỡ ghi report/db vào
    đó thì mất hết dữ liệu mỗi lần đóng app).

- bundled_resource_dir(): thư mục chứa resource ĐÓNG GÓI SẴN, chỉ đọc —
  templates/, gui/style.qss, config.yaml mặc định lúc build.
  + Chạy từ source: thư mục gốc project.
  + Chạy từ .exe: sys._MEIPASS (thư mục PyInstaller giải nén resource ra lúc
    chạy, đúng nơi --add-data đã đóng gói vào).
"""

import sys
from pathlib import Path


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundled_resource_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent
