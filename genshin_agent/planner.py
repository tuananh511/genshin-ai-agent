from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from genshin_agent.optimizer import AccountAnalysis

TZ_ASIA = timezone(timedelta(hours=8))
SERVER_RESET_HOUR = 4  # 4:00 AM UTC+8


@dataclass
class TodoItem:
    label: str
    reason: str
    category: str
    url: str | None = None
    icon_url: str | None = None


@dataclass
class DailyPlan:
    server_date: str
    day_of_week: str
    required_todos: list[TodoItem]
    optional_todos: list[TodoItem]


def get_server_now() -> datetime:
    """Trả về datetime hiện tại theo server Asia (UTC+8, sau reset 4AM)."""
    now_utc8 = datetime.now(TZ_ASIA)
    if now_utc8.hour < SERVER_RESET_HOUR:
        now_utc8 = now_utc8 - timedelta(days=1)
    return now_utc8


def get_day_of_week() -> int:
    """0=Thứ Hai ... 6=Chủ Nhật theo lịch server Asia."""
    return get_server_now().weekday()


def get_day_name() -> str:
    days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    return days[get_day_of_week()]


def is_weekly_boss_available() -> bool:
    """Không có dữ liệu claim thực từ game -> mặc định luôn nhắc."""
    return True


def make_resin_plan(analysis: AccountAnalysis) -> DailyPlan:
    """Checklist farm hôm nay — chỉ nói CẦN FARM CHO AI (dựa vào code tính toán,
    KHÔNG phụ thuộc domain mở ngày nào — người chơi tự kiểm tra trong game)."""
    required: list[TodoItem] = []

    chars_need_talent = [s.name for s in analysis.scores if s.low_talents]
    if chars_need_talent:
        required.append(TodoItem(
            label="Farm Talent (Domain Thiên Phú)",
            reason=f"Cần nâng talent cho: {', '.join(chars_need_talent)} — tự kiểm tra hôm nay domain nào mở",
            category="talent",
        ))

    chars_need_artifact = [s.name for s in analysis.scores if s.artifact_issues]
    if chars_need_artifact:
        required.append(TodoItem(
            label="Farm Artifact (Domain Thánh Di Vật / Boss)",
            reason=f"Cần +20 artifact cho: {', '.join(chars_need_artifact)}",
            category="artifact",
        ))

    if is_weekly_boss_available():
        required.append(TodoItem(
            label="Đánh Boss Tuần",
            reason="Reset mỗi Thứ Hai 4AM — nhớ đánh nếu tuần này chưa claim",
            category="weekly_boss",
        ))

    if not chars_need_talent and not chars_need_artifact:
        required.insert(0, TodoItem(
            label="Không có dữ liệu cụ thể từ phân tích",
            reason="Có thể do rate limit AI hoặc account đã build đầy đủ — farm domain nào cũng được hôm nay",
            category="info",
        ))

    optional: list[TodoItem] = [
        TodoItem(
            label="Thu Realm Currency trong Ấm Trần Ca",
            reason="Currency tích lũy theo giờ, đầy sẽ ngừng tích — thu định kỳ tránh lãng phí",
            category="teapot",
        ),
        TodoItem(
            label="Kiểm tra Parametric Transformer",
            reason="Cooldown 5 ngày để đổi nguyên liệu — đừng để \"ế\" không dùng",
            category="transformer",
            icon_url="https://static.wikia.nocookie.net/gensin-impact/images/f/f1/Item_Parametric_Transformer.png/revision/latest?cb=20210312183450",
        ),
        TodoItem(
            label="Daily Check-in trên HoYoLAB",
            reason="Primogem/Mora miễn phí mỗi ngày — mở link rồi tự tìm logo điểm danh/check-in trên trang",
            category="checkin",
            url="https://www.hoyolab.com/circles/2/27/official?page_type=27&page_sort=events",
        ),
        TodoItem(
            label="Xem event đang chạy",
            reason="Có thể có Primogem/vật phẩm free từ event giới hạn thời gian",
            category="event",
            url="https://www.hoyolab.com/circles/2/27/official?page_type=27&page_sort=events",
        ),
    ]

    server_now = get_server_now()
    return DailyPlan(
        server_date=server_now.strftime("%Y-%m-%d"),
        day_of_week=get_day_name(),
        required_todos=required,
        optional_todos=optional,
    )