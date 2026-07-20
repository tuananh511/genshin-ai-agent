import sys

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from genshin_agent.paths import bundled_resource_dir

STYLE_PATH = bundled_resource_dir() / "gui" / "style.qss"


def _load_stylesheet() -> str:
    """Đọc theme dark-gold (đồng bộ màu report.html) — nếu vì lý do gì đó thiếu
    file thì app vẫn chạy được với theme mặc định, không crash."""
    try:
        return STYLE_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def main():
    load_dotenv()
    app = QApplication(sys.argv)
    app.setStyleSheet(_load_stylesheet())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
