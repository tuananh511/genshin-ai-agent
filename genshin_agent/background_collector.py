"""
background_collector.py — Lấy danh sách ảnh nền Genshin Impact từ alphacoders.com
để random 1 ảnh làm background report.html mỗi lần chạy main.py.

Nguồn xác nhận qua fetch thật (2026-07-04): https://alphacoders.com/genshin-impact-wallpapers
là HTML tĩnh (server-rendered), mỗi ảnh có dạng:
    https://images{N?}.alphacoders.com/{3digit}/thumbbig-{id}.webp
Trang mặc định ("Infinite" scroll mode) chỉ trả về ~15 ảnh qua fetch tĩnh — đã xác nhận
tham số `?page=2` KHÔNG hoạt động (trả về y hệt trang 1), nghĩa là các trang sau tải
qua AJAX/JS, không lấy được bằng requests thuần. Đây là giới hạn đã biết và được
người dùng chấp nhận (xem PROJECT_MEMORY.md mục 14) — không cố lấy thêm qua page khác.

Lưu ý bản quyền: theo Terms of Service của alphacoders.com, ảnh chỉ dùng
"private personal, non commercial use". Module này KHÔNG tải/lưu lại ảnh —
chỉ hotlink thẳng URL ảnh để trình duyệt người dùng tự tải khi mở report.html,
tương tự cách project đã hotlink ảnh nhân vật/vũ khí từ fandom.com.

Nguyên tắc: nếu fetch lỗi (mạng, site chặn, đổi cấu trúc HTML khiến regex không
khớp) → trả về None, KHÔNG raise lỗi làm hỏng cả report — nền chỉ là trang trí,
không phải dữ liệu game quan trọng.
"""
from __future__ import annotations

import random
import re

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
WALLPAPER_LIST_URL = "https://alphacoders.com/genshin-impact-wallpapers"

# Khớp đúng ảnh preview kích thước lớn (thumbbig-*), KHÔNG khớp ảnh nhỏ trong
# meta tag og:image (dạng thumb-1920-*.png) — đã test phân biệt 2 pattern này.
IMG_RE = re.compile(r"https://images\d*\.alphacoders\.com/\d+/thumbbig-\d+\.webp")


def fetch_wallpaper_urls() -> list[str]:
    """
    Fetch danh sách URL ảnh nền từ trang chủ Genshin Impact Wallpapers.
    Raise requests-related exception nếu fetch lỗi — caller (get_random_background_url)
    chịu trách nhiệm catch để không làm hỏng report generation.
    """
    resp = requests.get(WALLPAPER_LIST_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    urls = IMG_RE.findall(resp.text)
    # Loại trùng, giữ thứ tự xuất hiện
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def get_random_background_url() -> str | None:
    """
    Entry point: trả về 1 URL ảnh nền ngẫu nhiên, hoặc None nếu không lấy được
    (mất mạng, site chặn, đổi cấu trúc HTML). Gọi 1 lần mỗi khi main.py chạy —
    ảnh này cố định trong report.html cho tới lần chạy sau.
    """
    try:
        urls = fetch_wallpaper_urls()
    except requests.RequestException:
        return None

    if not urls:
        return None

    return random.choice(urls)


if __name__ == "__main__":
    urls = fetch_wallpaper_urls()
    print(f"Lấy được {len(urls)} URL ảnh nền:")
    for u in urls:
        print(f"  {u}")
    chosen = get_random_background_url()
    print(f"\nẢnh được chọn ngẫu nhiên cho lần chạy này: {chosen}")
