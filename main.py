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

    print("[4/5] Lập kế hoạch hôm nay")
    plan = make_resin_plan(analysis)

    print("[5/5] Xuất report...")
    html_path, md_path = generate_reports(
        nickname=snapshot.nickname,
        ar=snapshot.adventure_rank,
        analysis=analysis,
        plan=plan,
    )

    print(f"\nHoàn tất! Xem report tại:\n  - {html_path}\n  - {md_path}")


if __name__ == "__main__":
    main()