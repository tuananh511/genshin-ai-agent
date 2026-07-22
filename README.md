# Genshin AI Agent

> Analyze your Genshin Impact account and recommend today's farming priorities.

[![Release](https://img.shields.io/github/v/tag/tuananh511/genshin-ai-agent?label=release)](https://github.com/tuananh511/genshin-ai-agent/tags)
[![License](https://img.shields.io/github/license/tuananh511/genshin-ai-agent)](https://github.com/tuananh511/genshin-ai-agent/blob/main/LICENSE)
[![Build](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/tuananh511/genshin-ai-agent/actions)

## Overview

AI Agent tự động phân tích account Genshin Impact và đề xuất việc nên làm hôm nay — chạy bằng `python main.py`, không phải chatbot hỏi-đáp.

**Pipeline:**

```
Data Collector (Enka API)
  → AssetManager (tra tên nhân vật/vũ khí/set: Enka loc.json → TextMap tiếng Việt/Anh)
  → Guide Collector (build guide thật từ genshin-builds.github.io, cache, cập nhật theo yêu cầu)
  → Optimizer (code tính stat + Gemini Flash đối chiếu guide, phát hiện cầm sai vũ khí/set)
  → Planner (checklist farm gì hôm nay)
  → Report Generator (report.html với Accordion + ảnh hover, report.md cho Github)
```

Nguyên tắc: việc tính được bằng công thức (lịch server, parse dữ liệu, tra tên) dùng code thuần. AI chỉ dùng để đọc hiểu/diễn giải (đối chiếu build với guide, viết nhận xét).

## Features

- Lấy character/weapon/artifact/talent/constellation/level thật từ Enka Network (qua UID)
- Tra tên nhân vật/vũ khí/Thánh Di Vật sang tiếng Việt qua `AssetManager` (Enka data + TextMap chính thức từ game)
- Crawl build guide thật từ genshin-builds.github.io cho từng nhân vật trong account — vũ khí/set/chỉ số/kỹ năng xếp theo độ ưu tiên
- Phát hiện khi đang dùng vũ khí/set khác với đề xuất guide, gợi ý nên farm gì thay thế
- Report dạng Accordion (1 nhân vật/mục), kèm ảnh hover khi rê chuột vào tên vũ khí/Thánh Di Vật, có link tới guide gốc
- Checklist farm hôm nay (Required) + nhắc nhở phụ (Optional: HoYoLAB check-in, event, transformer, teapot)
- Xuất `report.html` (dark theme, màu theo hệ nguyên tố) và `report.md` (đọc trên Github)

## Installation

**Yêu cầu:**

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- 1 Google AI Studio API key — miễn phí, lấy tại [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (free tier: 1500 request/ngày cho model Flash, không cần thẻ tín dụng)
- UID Genshin Impact của bạn (xem trong Pause Menu) + đã bật "Tủ trưng bày nhân vật"

```bash
git clone https://github.com/tuananh511/genshin-ai-agent.git
cd genshin-ai-agent
uv run main.py
```

## Usage

Lần đầu chạy sẽ hỏi API key + UID (hoặc N để dùng UID demo). Mỗi lần chạy sẽ hỏi "Cập nhật guide build mới nhất?" — chọn N để dùng cache cũ (nhanh, không gọi mạng), chọn Y khi muốn crawl lại (ví dụ sau khi game ra bản cập nhật mới).

**Giới hạn cần biết:**

- **LLM**: dùng Gemini Flash qua endpoint tương thích OpenAI của Google AI Studio. Nếu model lỗi/quá tải liên tục, tool sẽ hỏi bạn nhập tên model khác và tự lưu lại cho lần sau.
- **Tra tên item**: một số ít vũ khí/set (khoảng 10 trong toàn bộ game, đã xác minh kỹ) có hash không khớp với bất kỳ nguồn TextMap nào tìm được — hiển thị `(chưa rõ tên #hash)`, không suy đoán.
- **Guide build**: crawl từ genshin-builds.github.io — chỉ hoạt động với nhân vật có trang guide đầy đủ trên đó.
- **Wish Advisor** (`genshin_agent/wish_advisor.py`): đã viết nhưng chưa nối vào pipeline chính — cần model mạnh hơn free tier hiện tại để đủ tin cậy.

## Roadmap

- [ ] Multi-account
- [ ] Discord/Telegram bot
- [ ] Web Dashboard
- [ ] Gợi ý banner nên roll (cần nguồn dữ liệu banner thời gian thực, chưa nghiên cứu)

## License

MIT — xem [LICENSE](./LICENSE).

> Project cá nhân/học tập, không liên kết HoYoverse. Chỉ đọc dữ liệu công khai (Enka Character Showcase người chơi tự bật, trang guide công khai genshin-builds.github.io).
