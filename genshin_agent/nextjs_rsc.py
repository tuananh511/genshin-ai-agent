"""nextjs_rsc.py — Trích field từ RSC flight data (self.__next_f.push) của trang
Next.js App Router, dùng thư viện njsparser (https://github.com/novitae/njsparser).

Đã research + verify bằng HTML fixture thật (test fixture của chính njsparser,
không phải payload tự bịa) trước khi viết module này -- xem PROJECT_MEMORY.md
phần changelog để biết chi tiết quá trình verify.

Không tự cắt chuỗi/regex trên self.__next_f.push -- dùng njsparser để parse đúng
theo cấu trúc wire protocol thật của React Flight (RSC).
"""
from __future__ import annotations
import njsparser


def find_rsc_field(html: str, field_name: str):
    """Tìm field `field_name` trong bất kỳ Data object (dict) nào của RSC flight data.

    Trả về giá trị đầu tiên tìm được (đệ quy qua mọi Data/DataParent lồng nhau),
    hoặc None nếu trang không có flight data hoặc không tìm thấy field.

    Hàm này KHÔNG đặc thù cho crimsonwitch.com -- dùng lại được cho bất kỳ trang
    Next.js App Router nào khác cần lấy dữ liệu qua field name.
    """
    fd = njsparser.BeautifulFD(html)
    if not fd:
        return None
    for data in fd.find_iter([njsparser.T.Data]):
        if isinstance(data.content, dict) and field_name in data.content:
            return data.content[field_name]
    return None