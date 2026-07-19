"""Worker thread dùng chung cho mọi tác vụ nặng/blocking (gọi Enka API, crawl guide,
gọi LLM...) — chạy trong QThread để không đơ giao diện PySide6."""

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """Chạy `fn(*args, log=<callback>, **kwargs)` trong thread riêng.

    Signals:
        log(str)          — mỗi dòng log từ fn (fn nhận tham số `log` để gọi)
        finished_ok(object) — fn chạy xong, trả về kết quả
        finished_err(str)   — fn raise exception, trả về str(e)
    """

    log = Signal(str)
    finished_ok = Signal(object)
    finished_err = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, log=self.log.emit, **self._kwargs)
        except Exception as e:  # noqa: BLE001 — muốn bắt mọi lỗi để hiện lên GUI, không crash app
            self.finished_err.emit(f"{type(e).__name__}: {e}")
            return
        self.finished_ok.emit(result)
