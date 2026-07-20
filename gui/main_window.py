import os
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from genshin_agent import setup_wizard
from genshin_agent.services import analyze_uid, analyze_abyss, analyze_theater
from genshin_agent.report_generator import generate_reports
from gui.workers import Worker


def _page_header(title: str, subtitle: str) -> QVBoxLayout:
    """Tiêu đề + mô tả ngắn cho đầu mỗi trang — thay cho tên tab khô khan."""
    header = QLabel(title)
    header.setObjectName("pageHeader")
    sub = QLabel(subtitle)
    sub.setObjectName("pageSubtitle")
    sub.setWordWrap(True)

    layout = QVBoxLayout()
    layout.setSpacing(2)
    layout.addWidget(header)
    layout.addWidget(sub)
    return layout


def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #2a2a4a;")
    return line


class LogPanel(QPlainTextEdit):
    """Ô log dùng chung cho các trang — chỉ đọc, tự cuộn xuống dòng mới nhất."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumBlockCount(2000)
        self.setPlaceholderText("Log sẽ hiện ở đây khi chạy...")

    def append_line(self, text: str):
        self.appendPlainText(text)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class SettingsPage(QWidget):
    """Nhập API key + UID, lưu vào .env — thay cho ensure_config() (input() qua terminal)."""

    def __init__(self):
        super().__init__()
        env = setup_wizard.read_env()

        self.api_key_input = QLineEdit(env.get("LLM_API_KEY", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.uid_input = QLineEdit(env.get("GENSHIN_UID", ""))

        form_box = QGroupBox("Thông tin cấu hình")
        form = QFormLayout(form_box)
        form.addRow("Google AI Studio API key:", self.api_key_input)
        form.addRow("UID Genshin Impact:", self.uid_input)

        save_btn = QPushButton("Lưu")
        save_btn.clicked.connect(self._save)

        hint = QLabel(
            "Lấy API key miễn phí tại aistudio.google.com/apikey (nút \"Create API key\").\n"
            "UID xem trong Pause Menu (ESC trong game) — nhớ bật \"Tủ trưng bày nhân vật\"."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(14)
        layout.addLayout(_page_header("⚙️ Cài đặt", "API key và UID mặc định — chỉ cần nhập 1 lần."))
        layout.addWidget(_hline())
        layout.addWidget(form_box)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(hint)
        layout.addStretch()

    def _save(self):
        env = setup_wizard.read_env()
        env["LLM_API_KEY"] = self.api_key_input.text().strip()
        env["GENSHIN_UID"] = self.uid_input.text().strip()
        setup_wizard.write_env(env)
        # Cập nhật luôn process hiện tại — không bắt người dùng phải khởi động lại app.
        os.environ["LLM_API_KEY"] = env["LLM_API_KEY"]
        os.environ["GENSHIN_UID"] = env["GENSHIN_UID"]
        QMessageBox.information(self, "Đã lưu", "Đã lưu vào .env.")

    def current_uid(self) -> str:
        return self.uid_input.text().strip()


class AccountPage(QWidget):
    """Phân tích account theo UID — độc lập với Abyss/Theater."""

    def __init__(self, settings_page: SettingsPage, on_done):
        super().__init__()
        self._settings_page = settings_page
        self._on_done = on_done
        self._worker = None

        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("Để trống để dùng UID đã lưu ở Cài đặt")
        self.update_guides_cb = QCheckBox("Cập nhật guide build mới nhất từ genshin-builds")
        self.run_btn = QPushButton("▶  Chạy phân tích Account")
        self.run_btn.clicked.connect(self._run)
        self.log_panel = LogPanel()

        input_box = QGroupBox("Thiết lập")
        form = QFormLayout(input_box)
        form.addRow("UID:", self.uid_input)
        form.addRow("", self.update_guides_cb)

        log_box = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)
        log_layout.addWidget(self.log_panel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(14)
        layout.addLayout(_page_header(
            "👤 Account",
            "Lấy character/vũ khí/Thánh Di Vật từ Enka Network và đối chiếu build với guide.",
        ))
        layout.addWidget(_hline())
        layout.addWidget(input_box)
        layout.addWidget(self.run_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(log_box, stretch=1)

    def _run(self):
        uid = self.uid_input.text().strip() or self._settings_page.current_uid()
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


class _SimpleAnalysisPage(QWidget):
    """Base dùng chung cho AbyssPage/TheaterPage — cùng bố cục nút + log."""

    icon_title = ""
    subtitle = ""
    button_label = ""
    error_title = ""

    def __init__(self, fn, on_done, **fn_kwargs):
        super().__init__()
        self._fn = fn
        self._fn_kwargs = fn_kwargs
        self._on_done = on_done
        self._worker = None

        self.run_btn = QPushButton(f"▶  {self.button_label}")
        self.run_btn.clicked.connect(self._run)
        self.log_panel = LogPanel()

        log_box = QGroupBox("Log")
        log_layout = QVBoxLayout(log_box)
        log_layout.addWidget(self.log_panel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(14)
        layout.addLayout(_page_header(self.icon_title, self.subtitle))
        layout.addWidget(_hline())
        layout.addWidget(self.run_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(log_box, stretch=1)

    def _run(self):
        self.run_btn.setEnabled(False)
        self.log_panel.clear()
        self._worker = Worker(self._fn, **self._fn_kwargs)
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
        QMessageBox.critical(self, self.error_title, message)


class AbyssPage(_SimpleAnalysisPage):
    icon_title = "🌀 Spiral Abyss"
    subtitle = "Coach mùa hiện tại — cảnh báo quái nên dùng/tránh nguyên tố nào."
    button_label = "Chạy phân tích Spiral Abyss"
    error_title = "Lỗi phân tích Spiral Abyss"

    def __init__(self, on_done):
        super().__init__(analyze_abyss, on_done, force_refresh=True)


class TheaterPage(_SimpleAnalysisPage):
    icon_title = "🎭 Imaginarium Theater"
    subtitle = "Coach mùa hiện tại — cảnh báo quái nên dùng/tránh nguyên tố nào."
    button_label = "Chạy phân tích Imaginarium Theater"
    error_title = "Lỗi phân tích Imaginarium Theater"

    def __init__(self, on_done):
        super().__init__(analyze_theater, on_done, force_refresh=True)


class ReportPage(QWidget):
    """Xuất report.html từ những phân tích đã chạy trong phiên này (bất kỳ tổ hợp nào)."""

    def __init__(self, state: dict):
        super().__init__()
        self._state = state
        self._html_path = None

        self.status_account = QLabel()
        self.status_abyss = QLabel()
        self.status_theater = QLabel()

        status_box = QGroupBox("Trạng thái các luồng phân tích")
        status_layout = QVBoxLayout(status_box)
        for lbl in (self.status_account, self.status_abyss, self.status_theater):
            status_layout.addWidget(lbl)

        self.export_btn = QPushButton("📄  Xuất report.html")
        self.export_btn.clicked.connect(self._export)
        self.open_btn = QPushButton("🌐  Mở report.html")
        self.open_btn.setObjectName("secondaryButton")
        self.open_btn.clicked.connect(self._open)
        self.open_btn.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(self.open_btn)
        btn_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(14)
        layout.addLayout(_page_header(
            "📊 Report",
            "Xuất report.html tổng hợp từ những phân tích đã chạy — không cần chạy đủ cả 3.",
        ))
        layout.addWidget(_hline())
        layout.addWidget(status_box)
        layout.addLayout(btn_row)
        layout.addStretch()

        self.refresh_status()

    def refresh_status(self):
        def line(label: str, ok: bool) -> str:
            return f"{'✅' if ok else '—'}  {label}"

        self.status_account.setText(line("Account", "uid_result" in self._state))
        self.status_abyss.setText(line("Spiral Abyss", "abyss_result" in self._state))
        self.status_theater.setText(line("Imaginarium Theater", "theater_result" in self._state))

        for lbl, ok in (
            (self.status_account, "uid_result" in self._state),
            (self.status_abyss, "abyss_result" in self._state),
            (self.status_theater, "theater_result" in self._state),
        ):
            lbl.setObjectName("statusOk" if ok else "statusPending")
            lbl.style().unpolish(lbl)
            lbl.style().polish(lbl)

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
    NAV_ITEMS = [
        ("👤  Account", "account"),
        ("🌀  Spiral Abyss", "abyss"),
        ("🎭  Imaginarium Theater", "theater"),
        ("📊  Report", "report"),
        ("⚙️  Cài đặt", "settings"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Genshin AI Account Manager")
        self.resize(900, 640)

        # State chung của phiên làm việc — mỗi luồng ghi kết quả riêng vào đây,
        # ReportPage đọc lại để xuất report tổ hợp bất kỳ lúc nào.
        self._state: dict = {}

        self.settings_page = SettingsPage()
        self.report_page = ReportPage(self._state)
        self.account_page = AccountPage(self.settings_page, self._on_account_done)
        self.abyss_page = AbyssPage(self._on_abyss_done)
        self.theater_page = TheaterPage(self._on_theater_done)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.account_page)
        self.stack.addWidget(self.abyss_page)
        self.stack.addWidget(self.theater_page)
        self.stack.addWidget(self.report_page)
        self.stack.addWidget(self.settings_page)

        sidebar = self._build_sidebar()

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(sidebar)
        root.addWidget(self.stack, stretch=1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)

        title = QLabel("Genshin AI")
        title.setObjectName("appTitle")
        subtitle = QLabel("Account Manager")
        subtitle.setObjectName("appSubtitle")

        nav_list = QListWidget()
        for label, _key in self.NAV_ITEMS:
            nav_list.addItem(QListWidgetItem(label))
        nav_list.setCurrentRow(0)
        nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(nav_list, stretch=1)
        return sidebar

    def _on_account_done(self, result):
        self._state["uid_result"] = result
        self.report_page.refresh_status()

    def _on_abyss_done(self, result):
        self._state["abyss_result"] = result
        self.report_page.refresh_status()

    def _on_theater_done(self, result):
        self._state["theater_result"] = result
        self.report_page.refresh_status()
