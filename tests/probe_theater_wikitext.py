"""
Probe script — Imaginarium Theater wikitext structure
=======================================================
Mục đích: lấy wikitext thô (raw) của 1 trang mùa Nhà Hát ĐÃ có đủ dữ liệu
Battles (Act 1-10, enemy list), qua đúng MediaWiki Action API pattern đã
dùng cho Abyss/Gift Codes (action=parse&prop=wikitext).

Cách chạy:
    uv run probe_theater_wikitext.py

Kết quả mong đợi: in ra toàn bộ wikitext thô của section "Battles" —
từ đó xác định:
  1. Tên template dùng để list enemy mỗi Act (có phải {{Domain Enemies}}
     giống Abyss không, hay 1 template khác hoàn toàn — vì bản HTML render
     cho thấy layout khác: liệt kê phẳng "Lv. N Enemy" thay vì
     Floor/Chamber/Half như Abyss).
  2. Field nào chứa "Stage Effects" (buff/hazard như "Treacherous Thunder").
  3. Cách phân biệt Act thường vs Arcana Challenge (I/II) trong wikitext.

KHÔNG suy đoán field tên — chỉ dùng đúng những gì script này in ra thật.
"""

import requests
import json

API_BASE = "https://genshin-impact.fandom.com/api.php"

# Season 24 (2026-06-01) — đã xác nhận có đủ dữ liệu Battles qua search snippet,
# khác với Season 25 (mùa hiện tại) đang thiếu section này.
PAGE_TITLE = "Imaginarium_Theater/Seasons/2026-06-01"

# Cùng HEADERS pattern đã dùng cho abyss_collector.py / promo_code_pipeline.py
# để né bot-detection khi fetch trực tiếp trang /wiki/.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


def fetch_wikitext(page_title: str) -> str:
    params = {
        "action": "parse",
        "page": page_title,
        "format": "json",
        "prop": "wikitext",
    }
    resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"MediaWiki API error: {data['error']}")

    return data["parse"]["wikitext"]["*"]


def main():
    print(f"Fetching wikitext cho page: {PAGE_TITLE}\n")
    wikitext = fetch_wikitext(PAGE_TITLE)

    # Lưu toàn bộ ra file để đọc kỹ / paste lại cho Claude phân tích tiếp
    out_path = "theater_wikitext_raw.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(wikitext)
    print(f"Đã lưu toàn bộ wikitext thô vào: {out_path}")
    print(f"Độ dài: {len(wikitext)} ký tự\n")

    # In riêng phần quanh "Battles" / "Act " để xem nhanh cấu trúc template
    idx = wikitext.find("Battles")
    if idx == -1:
        idx = wikitext.find("Act 1")
    if idx != -1:
        print("=" * 60)
        print("Đoạn wikitext quanh 'Battles' (2000 ký tự đầu):")
        print("=" * 60)
        print(wikitext[idx:idx + 2000])
    else:
        print("Không tìm thấy chuỗi 'Battles' hoặc 'Act 1' trong wikitext — "
              "cần xem toàn bộ file theater_wikitext_raw.txt để tìm thủ công.")


if __name__ == "__main__":
    main()
