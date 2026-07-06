# Genshin AI Agent

AI Agent (không phải chatbot) hỗ trợ người chơi Genshin Impact — chạy 1 lệnh duy nhất, tự động lấy dữ liệu account thật, đối chiếu build với guide, lập checklist nên farm gì, và xuất report HTML đẹp.

```bash
uv run main.py
```

## Pipeline

```
Data Collector (Enka API)
  → AssetManager (tra tên nhân vật/vũ khí/set: Enka loc.json → TextMap VI/EN)
  → Guide Collector (build guide thật từ genshin-builds.github.io, có cache)
  → Optimizer (code tính stat + Gemini Flash đối chiếu guide)
  → Planner (checklist farm — code thuần)
  → [tuỳ chọn] Event Coaching: Spiral Abyss + Imaginarium Theater (Nhà Hát)
  → [tuỳ chọn] Gift Codes đang active
  → Report Generator → report.html
```

**Triết lý**: việc tính được bằng công thức/parse dữ liệu (lịch server, stat, JSON) dùng code thuần. AI chỉ dùng cho việc cần đọc hiểu/diễn giải (đối chiếu build với guide, viết nhận xét). Không bao giờ hallucinate — thiếu dữ liệu thật thì hiển thị rõ `(chưa rõ)`, không tự suy đoán.

## Tính năng

- Lấy character/weapon/artifact/talent/constellation/level thật từ Enka Network qua UID
- Tra tên nhân vật/vũ khí/Thánh Di Vật sang tiếng Việt
- Crawl build guide thật theo từng nhân vật, cache, cập nhật khi cần (hỏi Y/N)
- Phát hiện đang dùng vũ khí/set khác với guide, gợi ý nên farm gì thay thế
- Bảng Character Score: ảnh vũ khí/set, badge role + chỉ số khuyến nghị (Stat Recommendations), link thẳng tới trang build guide
- Checklist farm hôm nay (Required) + nhắc nhở phụ (HoYoLAB check-in, event, transformer, teapot)
- **Coach Sự Kiện**: cảnh báo counter/tránh element cho Spiral Abyss + Imaginarium Theater theo đúng kỳ hiện tại (hỏi Y/N, tự cập nhật)
- **Gift Codes**: danh sách code Genshin đang active, click-to-copy, tự đánh dấu code đã dùng
- Report HTML dark/light theme, 3 tab CSS-only (To Do / Coach Sự Kiện / Gift Codes), background ngẫu nhiên
- Setup wizard cho người dùng mới (nhập API key + UID lần đầu)

## Yêu cầu

- **Python 3.12+** và [uv](https://docs.astral.sh/uv/) (dùng để quản lý dependency + chạy project)
- 1 Google AI Studio API key — **miễn phí**, lấy tại [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (free tier 1500 request/ngày, không cần thẻ)
- UID Genshin Impact của bạn (xem trong Pause Menu) + đã bật **"Tủ trưng bày nhân vật"**

## Cài đặt & chạy

```bash
git clone https://github.com/tuananh511/genshin-ai-agent.git
cd genshin-ai-agent
uv run main.py
```

Lần đầu chạy sẽ hỏi API key + UID. Mỗi lần chạy sẽ hỏi có muốn cập nhật guide build / coach sự kiện / gift codes — chọn N để dùng cache cũ (nhanh), Y khi muốn lấy dữ liệu mới nhất.

## Lỗi thường gặp

### ❌ `'python' is not recognized` / `python: command not found`

Máy bạn chưa cài Python, hoặc đã cài nhưng chưa thêm vào PATH.

1. Tải Python 3.12+ tại [python.org/downloads](https://www.python.org/downloads/)
2. Khi cài trên **Windows**, nhớ tick vào ô **"Add python.exe to PATH"** ở màn hình đầu tiên của trình cài đặt — đây là nguyên nhân phổ biến nhất khiến lệnh không nhận
3. Kiểm tra lại bằng cách mở terminal mới (đóng terminal cũ đi, mở lại) và gõ:
   ```bash
   python --version
   ```
   Nếu ra số phiên bản (VD `Python 3.12.4`) là đã cài đúng.

### ❌ `'uv' is not recognized` / `uv: command not found`

Project dùng `uv` để quản lý dependency thay vì `pip` thông thường, nên cần cài riêng.

1. Cài theo hướng dẫn chính thức tại [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/):
   - **Windows** (PowerShell):
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - **macOS/Linux**:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
2. Đóng terminal cũ, mở terminal mới để PATH cập nhật
3. Kiểm tra lại: `uv --version`

> **Lưu ý**: project **không cần cài Node.js** — toàn bộ code là Python thuần (pipeline + Jinja2 template render ra HTML), không có phần nào build bằng JavaScript/npm.

## Giới hạn cần biết

- **LLM**: dùng Gemini Flash qua endpoint tương thích OpenAI của Google AI Studio. Nếu model lỗi/quá tải liên tục, tool sẽ hỏi bạn nhập tên model khác và tự lưu lại cho lần sau.
- **Tra tên item**: một số ít vũ khí/set có hash không khớp bất kỳ nguồn TextMap nào — hiển thị `(chưa rõ tên #hash)`, không suy đoán. Giới hạn dữ liệu cộng đồng đã biết.
- **Guide build**: crawl từ genshin-builds.github.io — chỉ hoạt động với nhân vật có trang guide đầy đủ trên đó.
- **Resin/daily commission**: không lấy được số thật (chỉ dùng Enka — public, không cần đăng nhập; đã từ chối HoYoLAB cookie API vì rủi ro bảo mật cho project chia sẻ công khai).
- **Gift Codes "đã dùng"**: lưu bằng `localStorage` của trình duyệt — đổi máy/trình duyệt hoặc xoá cache sẽ mất trạng thái đã đánh dấu.

## Cấu trúc project

```
genshin-ai-agent/
├── main.py
├── config.yaml
├── genshin_agent/
│   ├── config.py              # đọc .env + config.yaml
│   ├── llm_client.py          # get_llm() + safe_llm_call() — tự retry, tự hỏi đổi model
│   ├── setup_wizard.py        # hỏi API key/UID lần đầu chạy
│   ├── data_collector.py      # fetch + parse Enka API
│   ├── database.py            # SQLite save/load
│   ├── asset_manager.py       # tra tên nhân vật/vũ khí/set (Enka + TextMap VI/EN)
│   ├── guide_collector.py     # crawl build guide + cache
│   ├── optimizer.py           # tính stat (code) + đối chiếu guide (AI)
│   ├── planner.py             # checklist farm hôm nay
│   ├── abyss_collector.py / abyss_pipeline.py / abyss_planner.py / abyss_note_translator.py / abyss_cache.py
│   ├── theater_collector.py / theater_pipeline.py / theater_planner.py / theater_cache.py
│   ├── promo_code_pipeline.py # Gift Codes đang active
│   └── report_generator.py    # build context + render Jinja2 → report.html
├── templates/
│   └── report.html.j2
└── tests/
```

## Roadmap

- [ ] HoYoLAB integration (resin thật, daily commission thật) — nếu làm sẽ tách biệt hoàn toàn khỏi pipeline mặc định
- [ ] Tự động đánh giá lại meta sau mỗi bản patch mới

## Disclaimer

Project cá nhân/học tập, không liên kết HoYoverse. Chỉ đọc dữ liệu công khai (Enka Character Showcase người chơi tự bật, các trang guide/wiki công khai).
