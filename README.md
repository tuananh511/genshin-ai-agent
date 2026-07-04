# Genshin AI Assistant

Một AI Agent (không phải chatbot) hỗ trợ người chơi Genshin Impact. Chạy bằng **1 lệnh duy nhất** — tự động lấy dữ liệu account thật, phân tích build theo build guide thật, lập checklist nên farm gì hôm nay, và xuất ra 1 file report HTML đẹp mắt.

Không cần tự nhớ nên farm gì, không cần tự đối chiếu build guide — chạy lệnh, mở file, đọc report.

## Tính năng

- **Phân tích build nhân vật**: lấy dữ liệu account thật qua Enka Network API, đối chiếu vũ khí/Thánh Di Vật đang dùng với build guide thật (genshin-builds.com), phát hiện khi bạn đang cầm sai vũ khí/đeo sai set so với khuyến nghị.
- **Checklist farm hôm nay**: gợi ý talent/nguyên liệu nên farm dựa trên lịch nguyên liệu theo ngày trong tuần + tài nguyên hiện có.
- **Cảnh báo La Hoàn Thâm Cảnh (Spiral Abyss)**: lấy dữ liệu enemy/buff kỳ hiện tại, gợi ý hệ nguyên tố nên dùng/nên tránh cho từng tầng.
- **Gift Codes**: tự tổng hợp code quà tặng đang hoạt động, click để copy, tự đánh dấu code đã dùng.
- **Report HTML**: giao diện đẹp, dark/light theme, hover xem ảnh vũ khí/Thánh Di Vật, giải thích ý nghĩa từng chỉ số (CRIT Rate, ER, EM...), background ngẫu nhiên đổi mỗi lần chạy.
- **Setup 1 lần**: lần đầu chạy sẽ hỏi API key (miễn phí, Google AI Studio) + UID Genshin của bạn, lưu lại cho các lần sau.

> 🎭 **Đang phát triển**: mở rộng cảnh báo sang Nhà Hát Ảo Ảnh (Imaginarium Theater) và Ảo Cảnh (Stygian Onslaught).

## Yêu cầu

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (trình quản lý package/môi trường)
- API key **miễn phí** từ [Google AI Studio](https://aistudio.google.com/) (dùng cho phần phân tích AI)
- UID Genshin Impact của bạn (để lấy dữ liệu account — cần bật hiển thị thông tin nhân vật ở phần cài đặt trong game/HoYoLAB)

## Cài đặt & Chạy

```bash
git clone https://github.com/tuananh511/genshin-ai-agent.git
cd genshin-ai-agent
uv run main.py
```

Lần chạy đầu tiên sẽ hỏi bạn nhập API key + UID — chỉ cần nhập 1 lần, những lần sau chạy thẳng `uv run main.py`.

Report sẽ được xuất ra file `report.html` ở thư mục gốc — mở bằng trình duyệt bất kỳ.

## Lưu ý bảo mật

- File `.env` (chứa API key của bạn) **không** được đưa lên Github (đã có trong `.gitignore`) — mỗi người tự dùng key riêng của mình.
- Project **không** dùng cookie/token HoYoLAB — chỉ dùng UID public qua Enka Network API, không có rủi ro bị đánh cắp tài khoản.

## Đóng góp

Đây là project cá nhân/cộng đồng, không nhận hỗ trợ chính thức nhưng luôn hoan nghênh issue/PR góp ý.

## License

Xem file [LICENSE](./LICENSE).