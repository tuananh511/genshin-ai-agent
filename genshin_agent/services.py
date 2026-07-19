"""
Tách 3 luồng phân tích thành function độc lập, không phụ thuộc lẫn nhau:
- analyze_uid()     : phân tích account theo UID (Enka + Optimizer + lưu DB)
- analyze_abyss()   : phân tích Spiral Abyss mùa hiện tại
- analyze_theater() : phân tích Imaginarium Theater mùa hiện tại

Mỗi hàm có thể gọi độc lập (CLI hoặc GUI đều dùng chung), không bắt buộc phải
chạy theo thứ tự hay chạy đủ cả 3 như main.py bản cũ.

Tham số `log`: callable(str) -> None, mặc định print. GUI truyền vào 1 hàm
để đẩy log ra text box thay vì stdout.
"""

from dataclasses import dataclass
from typing import Callable

from genshin_agent.data_collector import collect_account, AccountSnapshot
from genshin_agent.database import init_db, save_snapshot
from genshin_agent.optimizer import analyze_account, AccountAnalysis
from genshin_agent.llm_client import safe_llm_call
from genshin_agent.abyss_pipeline import get_abyss_data
from genshin_agent.abyss_planner import generate_warnings as generate_abyss_warnings
from genshin_agent.theater_pipeline import get_theater_data
from genshin_agent.theater_planner import generate_theater_warnings
from genshin_agent.theater_collector import TheaterDataError

LogFn = Callable[[str], None]


def _default_log(msg: str) -> None:
    print(msg)


@dataclass
class UidAnalysisResult:
    snapshot: AccountSnapshot
    analysis: AccountAnalysis


@dataclass
class AbyssAnalysisResult:
    period_title: str
    floors: list
    warnings: list


@dataclass
class TheaterAnalysisResult:
    period_title: str
    acts: list
    warnings: list


def analyze_uid(uid: str, update_guides: bool = False, log: LogFn = _default_log) -> UidAnalysisResult:
    """Phân tích account theo UID: lấy dữ liệu Enka, lưu DB, chấm điểm build + đối
    chiếu guide qua AI. Độc lập hoàn toàn với Abyss/Theater."""
    log(f"Lấy dữ liệu account UID {uid} từ Enka...")
    snapshot = collect_account(uid)
    log(f"-> {snapshot.nickname} | AR {snapshot.adventure_rank} | {len(snapshot.characters)} nhân vật")

    log("Lưu snapshot vào database...")
    init_db()
    save_snapshot(snapshot)

    log("Optimizer đang phân tích (gọi AI, có thể mất 10-30s)...")
    analysis = analyze_account(snapshot.characters, update_guides=update_guides)

    return UidAnalysisResult(snapshot=snapshot, analysis=analysis)


def analyze_abyss(force_refresh: bool = True, log: LogFn = _default_log) -> AbyssAnalysisResult:
    """Phân tích Spiral Abyss mùa hiện tại. Độc lập hoàn toàn với UID/Theater."""
    log("Thu thập dữ liệu Spiral Abyss...")
    period_title, floors = get_abyss_data(llm_call=safe_llm_call, force_refresh=force_refresh)
    warnings = generate_abyss_warnings(floors)
    log(f"-> Xong: {period_title}")
    return AbyssAnalysisResult(period_title=period_title, floors=floors, warnings=warnings)


def analyze_theater(force_refresh: bool = True, log: LogFn = _default_log) -> TheaterAnalysisResult:
    """Phân tích Imaginarium Theater mùa hiện tại. Độc lập hoàn toàn với UID/Abyss.
    Raise TheaterDataError nếu mùa hiện tại chưa có dữ liệu trên nguồn (không fallback mùa cũ)."""
    log("Thu thập dữ liệu Nhà Hát Ảo Ảnh (Imaginarium Theater)...")
    period_title, acts = get_theater_data(force_refresh=force_refresh)
    warnings = generate_theater_warnings(acts)
    log(f"-> Xong: {period_title}")
    return TheaterAnalysisResult(period_title=period_title, acts=acts, warnings=warnings)
