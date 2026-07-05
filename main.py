import os
from dotenv import load_dotenv

from genshin_agent.data_collector import collect_account
from genshin_agent.database import init_db, save_snapshot
from genshin_agent.optimizer import analyze_account
from genshin_agent.planner import make_resin_plan
from genshin_agent.report_generator import generate_reports
from genshin_agent.setup_wizard import ensure_config



def main():
    ensure_config()
    load_dotenv()
    uid = os.environ["GENSHIN_UID"]

    print("[1/5] Lấy dữ liệu account từ Enka...")
    snapshot = collect_account(uid)
    print(f"      -> {snapshot.nickname} | AR {snapshot.adventure_rank} | {len(snapshot.characters)} nhân vật")

    print("[2/5] Lưu snapshot vào database...")
    init_db()
    save_snapshot(snapshot)

    update_guides = input("Cập nhật guide build mới nhất từ genshin-builds? (Y/N): ").strip().lower() == "y"

    print("[3/5] Optimizer đang phân tích (gọi AI, có thể mất 10-30s)...")
    analysis = analyze_account(snapshot.characters, update_guides=update_guides)
    

    print("[4/5] Lập kế hoạch hôm nay...")
    plan = make_resin_plan(analysis)

    # ── Event Coaching: Spiral Abyss + Imaginarium Theater (gộp 1 câu hỏi) ──────
    abyss_data = None    # None nếu bỏ qua/lỗi. Nếu có: (period_title, floors, warnings)
    theater_data = None  # None — pipeline/planner cho Theater chưa nối (chỉ có collector), để sau
    want_coach = input("Coach Spiral Abyss + Nhà Hát mùa này? (Y/N): ").strip().lower() == "y"
    if want_coach:
        try:
            from genshin_agent.llm_client import safe_llm_call
            from genshin_agent.abyss_pipeline import get_abyss_data
            from genshin_agent.abyss_planner import generate_warnings

            print("[Abyss] Thu thập dữ liệu Spiral Abyss (auto update)...")
            period_title, floors = get_abyss_data(llm_call=safe_llm_call, force_refresh=True)
            warnings = generate_warnings(floors)
            abyss_data = (period_title, floors, warnings)
        except Exception as e:
            print(f"  [warn] Abyss Planner gặp lỗi, bỏ qua: {e}")
            abyss_data = None

        try:
            from genshin_agent.theater_pipeline import get_theater_data
            from genshin_agent.theater_planner import generate_theater_warnings
            from genshin_agent.theater_collector import TheaterDataError

            print("[Theater] Thu thập dữ liệu Nhà Hát (auto update)...")
            theater_period, acts = get_theater_data(force_refresh=True)
            theater_warnings = generate_theater_warnings(acts)
            theater_data = (theater_period, acts, theater_warnings)
        except TheaterDataError as e:
            print(f"  [warn] Nhà Hát: {e}")
            theater_data = None
        except Exception as e:
            print(f"  [warn] Theater Planner gặp lỗi, bỏ qua: {e}")
            theater_data = None
    # ──────────────────────────────────────────────────────────────────────────

    # ── Gift Codes (tuỳ chọn) ──────────────────────────────────────────────────
    promo_codes = None  # None nếu người dùng bỏ qua hoặc lỗi
    want_codes = input("Xem gift code Genshin đang active? (Y/N): ").strip().lower() == "y"
    if want_codes:
        try:
            from genshin_agent.promo_code_pipeline import get_active_promo_codes
            print("[GiftCodes] Lấy danh sách code từ Fandom Wiki...")
            promo_codes = get_active_promo_codes()
        except Exception as e:
            print(f"  [warn] Gift Codes gặp lỗi, bỏ qua: {e}")
            promo_codes = None
    # ──────────────────────────────────────────────────────────────────────────

    print("[5/5] Xuất report...")
    html_path, md_path = generate_reports(
        nickname=snapshot.nickname,
        ar=snapshot.adventure_rank,
        analysis=analysis,
        plan=plan,
        abyss_data=abyss_data,       # None nếu người dùng bỏ qua hoặc lỗi
        theater_data=theater_data,   # None nếu người dùng bỏ qua/lỗi/mùa chưa có data
        promo_codes=promo_codes,     # None nếu người dùng bỏ qua hoặc lỗi
    )

    print(f"\nHoàn tất! Xem report tại:\n  - {html_path}")


if __name__ == "__main__":
    main()