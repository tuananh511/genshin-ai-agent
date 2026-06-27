# Genshin AI Account Manager

AI Agent tự động phân tích account Genshin Impact của bạn và đề xuất việc nên làm hôm nay — không phải chatbot hỏi-đáp, mà là 1 pipeline tự động chạy bằng `python main.py`.

## Pipeline
Data Collector (Enka API)

→ Knowledge Collector (Enka static data + guide thật từ KeqingMains)

→ Optimizer (code tính stat + AI đối chiếu guide)

→ Planner (checklist farm gì hôm nay)

→ Report Generator (report.html + report.md)

Nguyên tắc: việc nào tính được bằng công thức (lịch server, ngày trong tuần, parse dữ liệu) thì dùng code thuần. AI chỉ dùng cho phần cần đọc hiểu/diễn giải (đối chiếu build với guide, viết nhận xét).

## Tính năng

- Lấy character/weapon/artifact/talent/constellation/level thật từ Enka Network (qua UID)
- Crawl guide build thật từ KeqingMains cho từng nhân vật trong account (tự dò URL, cache 7 ngày)
- Phân tích: nhân vật nào cần nâng talent, artifact nào chưa +20, đối chiếu stat hiện tại với guide
- Checklist farm hôm nay (Required) + nhắc nhở phụ (Optional: HoYoLAB check-in, event, transformer, teapot)
- Xuất `report.html` (dark theme) và `report.md` (đọc trên Github)

## Yêu cầu

- Python 3.12+, [uv](https://docs.astral.sh/uv/) để quản lý dependency
- 1 OpenRouter API key — **miễn phí**, đăng ký tại [openrouter.ai](https://openrouter.ai/), lấy key tại [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys)
- UID Genshin Impact của bạn (xem trong Pause Menu trong game) + **đã bật "Tủ trưng bày nhân vật"** cho các nhân vật muốn phân tích

## Cài đặt & chạy

```bash
git clone <repo-url>
cd genshin-ai-agent
uv run main.py
```

Lần đầu chạy, hệ thống sẽ hỏi bạn dán OpenRouter API key và UID (hoặc bấm N để dùng UID demo xem thử). Từ lần 2 sẽ không hỏi lại — thông tin lưu trong `.env` (không commit lên Github).

## Giới hạn cần biết

- **OpenRouter free tier**: 50 request/ngày nếu tài khoản chưa nạp gì, 1000/ngày nếu nạp $10 (1 lần, vẫn dùng model free — đây không phải mua model, chỉ là "tiền cược chống spam"). Project mặc định dùng `openrouter/free` (tự chọn model free khả dụng), có retry tự động khi model bị lặp/lỗi/rate-limit.
- **Guide từ KeqingMains**: chỉ crawl được nếu nhân vật có trang guide đầy đủ trên KeqingMails. Một vài nhân vật có thể không lấy được (hệ thống tự fallback, AI vẫn phân tích dựa trên kiến thức chung, chỉ là không có "nguồn tham khảo" kèm theo).
- **Wish Advisor** (`genshin_agent/wish_advisor.py`): đã viết nhưng **chưa nối vào pipeline chính** — model free hiện tại tư vấn chiến lược dài hạn (nên roll gì) không đủ tốt. Giữ lại để dễ nối lại nếu sau này dùng model mạnh hơn.

## Cấu trúc project
genshin-ai-agent/

├── main.py                       # Entry point — chạy toàn bộ pipeline

├── config.yaml                   # Cấu hình LLM (không bí mật)

├── genshin_agent/

│   ├── config.py                 # Đọc .env + config.yaml

│   ├── llm_client.py             # get_llm() + safe_llm_call() dùng chung

│   ├── setup_wizard.py           # Hỏi API key/UID lần đầu chạy

│   ├── data_collector.py         # Fetch + parse Enka API

│   ├── database.py               # SQLite save/load

│   ├── knowledge_collector.py    # Enka static data (tên nhân vật/vũ khí) + cache

│   ├── guide_collector.py        # Crawl guide thật từ KeqingMains + cache

│   ├── optimizer.py              # Tính stat (code) + đối chiếu guide (AI)

│   ├── planner.py                # Checklist farm hôm nay

│   ├── wish_advisor.py           # (chưa nối vào main.py — xem Giới hạn)

│   └── report_generator.py       # Xuất report.html/report.md

├── templates/                    # Jinja2 templates

└── tests/

## Roadmap

- [ ] Multi-account
- [ ] Discord/Telegram bot
- [ ] Web Dashboard
- [ ] Auto cập nhật theo patch mới

## Disclaimer

Project cá nhân/học tập, không liên kết với HoYoverse. Chỉ đọc dữ liệu công khai (Enka Character Showcase mà người chơi tự bật, trang guide công khai trên KeqingMains).