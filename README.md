# Genshin AI Account Manager

AI Agent phân tích account Genshin Impact và đối chiếu build với guide thật — có GUI desktop (PySide6) và CLI (`python main.py`), không phải chatbot hỏi-đáp.

## Pipeline

Data Collector (Enka API)
→ AssetManager (tra tên nhân vật/vũ khí/set: Enka loc.json → TextMap tiếng Việt/Anh)
→ Guide Collector (build guide thật từ genshin-builds.github.io, cache, cập nhật theo yêu cầu)
→ Optimizer (code tính stat + Gemini Flash đối chiếu guide, phát hiện cầm sai vũ khí/set)
→ Report Generator (report.html với Accordion + ảnh hover)

Nguyên tắc: việc tính được bằng công thức (parse dữ liệu, tra tên) dùng code thuần. AI chỉ dùng để đọc hiểu/diễn giải (đối chiếu build với guide, viết nhận xét).

## 3 luồng phân tích độc lập

`genshin_agent/services.py` tách 3 luồng phân tích thành 3 hàm độc lập, không phụ thuộc lẫn nhau, có thể chạy riêng lẻ (GUI có nút bấm riêng cho từng luồng):

- `analyze_uid(uid)` — phân tích account theo UID (Enka + Optimizer, lưu DB)
- `analyze_abyss()` — coach Spiral Abyss mùa hiện tại
- `analyze_theater()` — coach Imaginarium Theater mùa hiện tại

Report (`report.html`) có thể xuất bất cứ lúc nào từ những luồng đã chạy trong phiên làm việc — không bắt buộc phải chạy đủ cả 3.

## Tính năng

- Lấy character/weapon/artifact/talent/constellation/level thật từ Enka Network (qua UID)
- Tra tên nhân vật/vũ khí/Thánh Di Vật sang tiếng Việt qua `AssetManager` (Enka data + TextMap chính thức từ game)
- Crawl build guide thật từ genshin-builds.github.io cho từng nhân vật trong account — vũ khí/set/chỉ số/kỹ năng xếp theo độ ưu tiên
- Phát hiện khi đang dùng vũ khí/set KHÁC với đề xuất guide
- Report dạng Accordion (1 nhân vật/mục), kèm ảnh hover khi rê chuột vào tên vũ khí/Thánh Di Vật, có link tới guide gốc
- Coach Spiral Abyss + Imaginarium Theater mùa hiện tại (cảnh báo quái nên dùng/tránh nguyên tố nào)
- Xuất `report.html` (dark theme, màu theo hệ nguyên tố)

> Đã bỏ: checklist farm hôm nay (Required/Optional) và mục Gift Code — không còn nằm trong scope của tool này nữa.

## Yêu cầu

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- 1 Google AI Studio API key — **miễn phí**, lấy tại [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (free tier: 1500 request/ngày cho model Flash, không cần thẻ tín dụng)
- UID Genshin Impact của bạn (xem trong Pause Menu) + đã bật **"Tủ trưng bày nhân vật"**

## Cài đặt & chạy

### GUI (khuyến nghị)

**Cách 1 — double-click, không cần gõ lệnh:** chạy `run_gui.bat` (tự cài dependency qua `uv sync` lần đầu nếu cần, rồi mở app).

**Cách 2 — dòng lệnh:**
```
git clone <repo-url>
cd genshin-ai-agent
uv run gui_app.py
```

Lần đầu mở app, vào tab **Cài đặt** để nhập API key + UID (lưu vào `.env`, chỉ hỏi 1 lần). Sau đó dùng 3 tab **Account**, **Spiral Abyss**, **Imaginarium Theater** để chạy từng phân tích riêng — mỗi tab có nút bấm và log riêng, không phụ thuộc nhau. Tab **Report** dùng để xuất/mở `report.html` bất cứ lúc nào từ các phân tích đã chạy.

### Đóng gói thành file .exe standalone (tuỳ chọn)

Chạy `build_exe.bat` **trên máy Windows** (không build được từ Linux/sandbox — PyInstaller đóng gói cho đúng hệ điều hành đang chạy nó). Kết quả nằm ở `dist\GenshinAIAccountManager.exe` kèm `dist\config.yaml` — giữ 2 file này cùng thư mục, đừng tách riêng. Lần đầu chạy `.exe` sẽ tự tạo `.env` / `genshin_agent.db` / các file cache ngay cạnh nó.

### CLI

```
uv run main.py
```

Lần đầu chạy sẽ hỏi API key + UID. Mỗi luồng (guide update / Spiral Abyss / Imaginarium Theater) đều hỏi Y/N riêng — chọn N để bỏ qua luồng đó, không ảnh hưởng các luồng còn lại.

## Giới hạn cần biết

- **LLM**: dùng Gemini Flash qua endpoint tương thích OpenAI của Google AI Studio. Nếu model lỗi/quá tải liên tục ở CLI, tool sẽ hỏi bạn nhập tên model khác (xem danh sách tại [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)) và tự lưu lại cho lần sau. Ở GUI (không có terminal tương tác), bước hỏi đổi model này tự động bỏ qua và trả lỗi thẳng ra log.
- **Tra tên item**: dùng dữ liệu Enka + TextMap chính thức từ game (qua `AssetManager`). Một số ít vũ khí/set (khoảng 10 trong toàn bộ game, đã xác minh kỹ) có hash không khớp với bất kỳ nguồn TextMap nào tìm được — hiển thị `(chưa rõ tên #hash)`, không suy đoán. Đây là giới hạn dữ liệu cộng đồng đã biết, không phải lỗi.
- **Guide build**: crawl từ genshin-builds.github.io — chỉ hoạt động với nhân vật có trang guide đầy đủ trên đó.
- **Imaginarium Theater**: nếu mùa hiện tại chưa có dữ liệu Battles trên nguồn, `analyze_theater()` raise `TheaterDataError` — không fallback về mùa cũ (tránh coach sai mùa).
- **Wish Advisor** (`genshin_agent/wish_advisor.py`): đã viết nhưng **chưa nối vào pipeline chính** — tư vấn chiến lược roll banner cần model mạnh hơn free tier hiện tại để đủ tin cậy. Giữ lại để dễ nối lại sau.

## Cấu trúc project

```
genshin-ai-agent/
├── main.py                  # CLI entry point
├── gui_app.py                # GUI entry point (PySide6)
├── run_gui.bat                # double-click chạy GUI, không cần gõ lệnh
├── build_exe.bat              # đóng gói .exe standalone (chạy trên Windows)
├── config.yaml
├── genshin_agent/
│   ├── paths.py             # chuẩn hoá đường dẫn (chạy từ source vs .exe đóng gói)
│   ├── config.py            # đọc .env + config.yaml
│   ├── llm_client.py        # get_llm() + safe_llm_call() — tự retry, tự hỏi đổi model khi lỗi (CLI)
│   ├── setup_wizard.py      # hỏi API key/UID lần đầu chạy (CLI)
│   ├── services.py          # analyze_uid() / analyze_abyss() / analyze_theater() — 3 luồng độc lập
│   ├── data_collector.py    # fetch + parse Enka API
│   ├── database.py          # SQLite save/load
│   ├── asset_manager.py     # tra tên nhân vật/vũ khí/set (Enka data + TextMap VI/EN)
│   ├── guide_collector.py   # crawl build guide từ genshin-builds.github.io + cache
│   ├── optimizer.py         # tính stat (code) + đối chiếu guide, phát hiện sai build (AI)
│   ├── abyss_pipeline.py / abyss_planner.py       # Spiral Abyss
│   ├── theater_pipeline.py / theater_planner.py   # Imaginarium Theater
│   ├── wish_advisor.py      # (chưa nối vào main.py — xem Giới hạn)
│   └── report_generator.py  # xuất report.html
├── gui/
│   ├── main_window.py        # sidebar (QListWidget) + QStackedWidget — Account/Abyss/Theater/Report/Cài đặt
│   ├── style.qss               # theme dark-gold, đồng bộ màu report.html
│   └── workers.py              # QThread wrapper cho services.py (không đơ UI)
├── templates/
└── tests/
```

## Roadmap

- [ ] Multi-account
- [ ] Discord/Telegram bot
- [ ] Gợi ý banner nên roll (cần nguồn dữ liệu banner thời gian thực, chưa nghiên cứu)

## Disclaimer

Project cá nhân/học tập, không liên kết HoYoverse. Chỉ đọc dữ liệu công khai (Enka Character Showcase người chơi tự bật, trang guide công khai genshin-builds.github.io).
