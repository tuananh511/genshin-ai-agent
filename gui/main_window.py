import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from genshin_agent import setup_wizard
from genshin_agent.services import analyze_uid, analyze_abyss, analyze_theater
from genshin_agent.report_generator import generate_reports
from gui.workers import Worker


class LogPanel(QPlainTextEdit):
    """Ô log dùng chung cho các tab — chỉ đọc, tự cuộn xuống dòng mới nhất."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)

    def append_line(self, text: str):
        self.appendPlainText(text)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class SettingsTab(QWidget):
    """Nhập API key + UID, lưu vào .env — thay cho ensure_config() (input() qua terminal)."""

    def __init__(self):
        super().__init__()
        env = setup_wizard.read_env()

        self.api_key_input = QLineEdit(env.get("LLM_API_KEY", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.uid_input = QLineEdit(env.get("GENSHIN_UID", ""))

        form = QFormLayout()
        form.addRow("Google AI Studio API key:", self.api_key_input)
        form.addRow("UID Genshin Impact:", self.uid_input)

        save_btn = QPushButton("Lưu")
        save_btn.clicked.connect(self._save)

        hint = QLabel(
            "Lấy API key miễn phí tại aistudio.google.com/apikey (Create API key).\n"
            "UID xem trong Pause Menu (ESC trong game) — nhớ bật \"Tủ trưng bày nhân vật\"."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray;")

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(save_btn)
        layout.addWidget(hint)
        layout.addStretch()

    def _save(self):
        env = setup_wizard.read_env()
        env["LLM_API_KEY"] = self.api_key_input.text().strip()
        env["GENSHIN_UID"] = self.uid_input.text().strip()
        setup_wizard.write_env(env)
        QMessageBox.information(self, "Đã lưu", "Đã lưu vào .env.")

    def current_uid(self) -> str:
        return self.uid_input.text().strip()


class AccountTab(QWidget):
    """Phân tích account theo UID — độc lập với Abyss/Theater."""

    def __init__(self, settings_tab: SettingsTab, on_done):
        super().__init__()
        self._settings_tab = settings_tab
        self._on_done = on_done
        self._worker = None

        self.uid_input = QLineEdit()
        self.update_guides_cb = QCheckBox("Cập nhật guide build mới nhất từ genshin-builds")
        self.run_btn = QPushButton("Chạy phân tích Account")
        self.run_btn.clicked.connect(self._run)
        self.log_panel = LogPanel()

        top = QHBoxLayout()
        top.addWidget(QLabel("UID:"))
        top.addWidget(self.uid_input)
        top.addWidget(self.run_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.update_guides_cb)
        layout.addWidget(self.log_panel)

    def _run(self):
        uid = self.uid_input.text().strip() or self._settings_tab.current_uid()
        if not uid:
            QMessageBox.warning(self, "Thiếu UID", "Nhập UID hoặc lưu UID ở tab Cài đặt trước.")
            return

        self.run_btn.setEnabled(False)
        self.log_panel.clear()
        self._worker = Worker(analyze_uid, uid, update_guides=self.update_guides_cb.isChecked())
        self._worker.log.connect(self.log_panel.append_line)
        self._worker.finished_ok.connect(self._finished_ok)
        self._worker.finished_err.connect(self._finished_err)
        self._worker.start()

    def _finished_ok(self, result):
        self.run_btn.setEnabled(True)
        self.log_panel.append_line("=> Hoàn tất phân tích Account.")
        self._on_done(result)

    def _finished_err(self, message: str):
        self.run_btn.setEnabled(True)
        self.log_panel.append_line(f"[LỖI] {message}")
        QMessageBox.critical(self, "Lỗi phân tích Account", message)


class AbyssTab(QWidget):
    """Coach Spiral Abyss mùa hiện tại — độc lập với Account/Theater."""

    def __init__(self, on_done):
        super().__init__()
        self._on_done = on_done
        self._worker = None

        self.run_btn = QPushButton("Chạy phân tích Spiral Abyss")
        self.run_btn.clicked.connect(self._run)
        self.log_panel = LogPanel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.run_btn)
        layout.addWidget(self.log_panel)

    def _run(self):
        self.run_btn.setEnabled(False)
        self.log_panel.clear()
        self._worker = Worker(analyze_abyss, force_refresh=True)
        self._worker.log.connect(self.log_panel.append_line)
        self._worker.finished_ok.connect(self._finished_ok)
        self._worker.finished_err.connect(self._finished_err)
        self._worker.start()

    def _finished_ok(self, result):
        self.run_btn.setEnabled(True)
        self.log_panel.append_line(f"=> Hoàn tất: {result.period_title}")
        self._on_done(result)

    def _finished_err(self, message: str):
        self.run_btn.setEnabled(True)
        self.log_panel.append_line(f"[LỖI] {message}")
        QMessageBox.critical(self, "Lỗi phân tích Spiral Abyss", message)


class TheaterTab(QWidget):
    """Coach Imaginarium Theater mùa hiện tại — độc lập với Account/Abyss."""

    def __init__(self, on_done):
        super().__init__()
        self._on_done = on_done
        self._worker = None

        self.run_btn = QPushButton("Chạy phân tích Imaginarium Theater")
        self.run_btn.clicked.connect(self._run)
        self.log_panel = LogPanel()

        layout = QVBoxLayout(self)
        layout.addWidget(self.run_btn)
        layout.addWidget(self.log_panel)

    def _run(self):
        self.run_btn.setEnabled(False)
        self.log_panel.clear()
        self._worker = Worker(analyze_theater, force_refresh=True)
        self._worker.log.connect(self.log_panel.append_line)
        self._worker.finished_ok.connect(self._finished_ok)
        self._worker.finished_err.connect(self._finished_err)
        self._worker.start()

    def _finished_ok(self, result):
        self.run_btn.setEnabled(True)
        self.log_panel.append_line(f"=> Hoàn tất: {result.period_title}")
        self._on_done(result)

    def _finished_err(self, message: str):
        self.run_btn.setEnabled(True)
        self.log_panel.append_line(f"[LỖI] {message}")
        QMessageBox.critical(self, "Lỗi phân tích Imaginarium Theater", message)


class ReportTab(QWidget):
    """Xuất report.html từ những phân tích đã chạy trong phiên này (bất kỳ tổ hợp nào)."""

    def __init__(self, state: dict):
        super().__init__()
        self._state = state

        self.status_label = QLabel()
        self.export_btn = QPushButton("Xuất report.html")
        self.export_btn.clicked.connect(self._export)
        self.open_btn = QPushButton("Mở report.html")
        self.open_btn.clicked.connect(self._open)
        self.open_btn.setEnabled(False)
        self._html_path = None

        box = QGroupBox("Trạng thái các luồng phân tích")
        box_layout = QVBoxLayout(box)
        box_layout.addWidget(self.status_label)

        layout = QVBoxLayout(self)
        layout.addWidget(box)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.open_btn)
        layout.addStretch()

        self.refresh_status()

    def refresh_status(self):
        def mark(ok: bool) -> str:
            return "✅ đã chạy" if ok else "— chưa chạy"

        self.status_label.setText(
            f"Account:            {mark('uid_result' in self._state)}\n"
            f"Spiral Abyss:       {mark('abyss_result' in self._state)}\n"
            f"Imaginarium Theater: {mark('theater_result' in self._state)}"
        )

    def _export(self):
        uid_result = self._state.get("uid_result")
        if uid_result is None:
            QMessageBox.warning(
                self, "Chưa có dữ liệu Account",
                "Cần chạy phân tích Account trước — report chính dựa trên đó.",
            )
            return

        abyss_result = self._state.get("abyss_result")
        theater_result = self._state.get("theater_result")
        abyss_data = (
            (abyss_result.period_title, abyss_result.floors, abyss_result.warnings)
            if abyss_result else None
        )
        theater_data = (
            (theater_result.period_title, theater_result.acts, theater_result.warnings)
            if theater_result else None
        )

        try:
            html_path, _ = generate_reports(
                nickname=uid_result.snapshot.nickname,
                ar=uid_result.snapshot.adventure_rank,
                analysis=uid_result.analysis,
                abyss_data=abyss_data,
                theater_data=theater_data,
            )
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Lỗi xuất report", str(e))
            return

        self._html_path = html_path
        self.open_btn.setEnabled(True)
        QMessageBox.information(self, "Đã xuất report", f"Đã xuất:\n{html_path}")

    def _open(self):
        if self._html_path:
            webbrowser.open(self._html_path.as_uri())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Genshin AI Account Manager")
        self.resize(820, 620)

        # State chung của phiên làm việc — mỗi luồng ghi kết quả riêng vào đây,
        # ReportTab đọc lại để xuất report tổ hợp bất kỳ lúc nào.
        self._state: dict = {}

        self.settings_tab = SettingsTab()
        self.report_tab = ReportTab(self._state)
        self.account_tab = AccountTab(self.settings_tab, self._on_account_done)
        self.abyss_tab = AbyssTab(self._on_abyss_done)
        self.theater_tab = TheaterTab(self._on_theater_done)

        tabs = QTabWidget()
        tabs.addTab(self.account_tab, "Account")
        tabs.addTab(self.abyss_tab, "Spiral Abyss")
        tabs.addTab(self.theater_tab, "Imaginarium Theater")
        tabs.addTab(self.report_tab, "Report")
        tabs.addTab(self.settings_tab, "Cài đặt")

        self.setCentralWidget(tabs)

    def _on_account_done(self, result):
        self._state["uid_result"] = result
        self.report_tab.refresh_status()

    def _on_abyss_done(self, result):
        self._state["abyss_result"] = result
        self.report_tab.refresh_status()

    def _on_theater_done(self, result):
        self._state["theater_result"] = result
        self.report_tab.refresh_status()
