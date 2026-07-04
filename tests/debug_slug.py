# debug_slug.py — chạy: uv run debug_slug.py
from genshin_agent.asset_manager import asset_manager

# thay 10000002 bằng avatar_id thật của 1 nhân vật trong account bạn (xem log lúc chạy main.py, hoặc SQLite)
test_id = 10000002

print("Tên (theo VI/loc, hàm cũ):", asset_manager.get_avatar_name(test_id))
print("Tên EN (hàm mới):", repr(asset_manager.get_avatar_name_en(test_id)))

char_data = asset_manager.characters.get(str(test_id), {})
name_hash = char_data.get("NameTextMapHash")
print("name_hash:", name_hash, type(name_hash))
print("hash có trong textmap_en không:", str(name_hash) in asset_manager.textmap_en)
print("Số lượng key trong textmap_en:", len(asset_manager.textmap_en))
print("---")
print("Số lượng key trong textmap_vi:", len(asset_manager.textmap_vi))
print("Số lượng key trong loc_vi:", len(asset_manager.loc_vi))
print("hash có trong textmap_vi không:", str(name_hash) in asset_manager.textmap_vi)
print("hash có trong loc_vi không:", str(name_hash) in asset_manager.loc_vi)

# thử vài key mẫu trong textmap_en để xem định dạng key thật trông ra sao
sample_keys = list(asset_manager.textmap_en.keys())[:5]
print("5 key mẫu trong textmap_en:", sample_keys)
print("kiểu dữ liệu key mẫu:", type(sample_keys[0]))