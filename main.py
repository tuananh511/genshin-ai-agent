import os
from dotenv import load_dotenv

from genshin_agent.report_generator import generate_reports
from genshin_agent.setup_wizard import ensure_config
from genshin_agent.services import analyze_uid, analyze_abyss, analyze_theater
from genshin_agent.theater_collector import TheaterDataError


def _ask_yn(question: str) -> bool:
    return input(f"{question} (Y/N): ").strip().lower() == "y"


def main():
    ensure_config()
    load_dotenv()
    uid = os.environ["GENSHIN_UID"]

    # ── Phân tích account theo UID (bắt buộc — cần cho report chính) ──────────
    update_guides = _ask_yn("Cập nhật guide build mới nhất từ genshin-builds?")
    result = analyze_uid(uid, update_guides=update_guides)
    snapshot, analysis = result.snapshot, result.analysis

    # ── Spiral Abyss (độc lập, tuỳ chọn) ──────────────────────────────────────
    abyss_data = None
    if _ask_yn("Coach Spiral Abyss mùa này?"):
        try:
            r = analyze_abyss(force_refresh=True)
            abyss_data = (r.period_title, r.floors, r.warnings)
        except Exception as e:
            print(f"  [warn] Abyss gặp lỗi, bỏ qua: {e}")

    # ── Imaginarium Theater (độc lập, tuỳ chọn) ───────────────────────────────
    theater_data = None
    if _ask_yn("Coach Nhà Hát Ảo Ảnh (Imaginarium Theater) mùa này?"):
        try:
            r = analyze_theater(force_refresh=True)
            theater_data = (r.period_title, r.acts, r.warnings)
        except TheaterDataError as e:
            print(f"  [warn] Nhà Hát: {e}")
        except Exception as e:
            print(f"  [warn] Theater gặp lỗi, bỏ qua: {e}")

    print("Xuất report...")
    html_path, _ = generate_reports(
        nickname=snapshot.nickname,
        ar=snapshot.adventure_rank,
        analysis=analysis,
        abyss_data=abyss_data,
        theater_data=theater_data,
    )

    print(f"\nHoàn tất! Xem report tại:\n  - {html_path}")


if __name__ == "__main__":
    main()
