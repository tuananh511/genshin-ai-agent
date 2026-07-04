"""gift_codes_pipeline.py — Lấy danh sách gift code Genshin Impact còn hạn
từ crimsonwitch.com, qua RSC flight data (self.__next_f.push), không dùng
Playwright/Selenium.

Nguồn: https://www.crimsonwitch.com/codes/Genshin_Impact
Cơ chế: trang Next.js App Router, server serialize toàn bộ list code vào field
`initialCodes` trong RSC payload -- lấy bằng genshin_agent.nextjs_rsc.find_rsc_field.
"""
from __future__ import annotations
import requests

from genshin_agent.nextjs_rsc import find_rsc_field

CODES_URL   = "https://www.crimsonwitch.com/codes/Genshin_Impact"
USER_AGENT  = "genshin-ai-agent/3.0 (personal-project)"


class GiftCodesError(Exception):
    pass


def get_raw_codes() -> list:
    """Trả về list RAW (nguyên bản, chưa map field) lấy từ field `initialCodes`.

    CHƯA map sang dataclass/dict field cụ thể (code/rewards/expiry...) vì tại thời
    điểm viết hàm này chưa xác nhận được tên field thật bên trong mỗi code entry
    (theo nguyên tắc KHÔNG đoán dữ liệu). Xem test_gift_codes_probe.py để tự dump
    cấu trúc thật 1 lần, sau đó mới viết hàm map chính thức.
    """
    resp = requests.get(CODES_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    codes = find_rsc_field(resp.text, "initialCodes")
    if codes is None:
        raise GiftCodesError(
            "Không tìm thấy field 'initialCodes' trong RSC payload -- "
            "có thể crimsonwitch.com đã đổi cấu trúc trang, cần research lại."
        )
    if not isinstance(codes, list):
        raise GiftCodesError(f"initialCodes không phải list, mà là {type(codes)} -- research lại.")
    return codes