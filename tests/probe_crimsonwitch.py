from crimsonwitch_collector import get_all_builds
from genshin_agent.asset_manager import asset_manager

all_builds = get_all_builds()
print("Tổng số nhân vật có build:", len(all_builds))

# Test khớp tên với vài nhân vật trong account thật của bạn
for avatar_id in [10000032, 10000025, 10000065]:  # Bennett, Xingqiu, Kuki Shinobu
    name_en = asset_manager.get_avatar_name_en(avatar_id)
    match = all_builds.get(name_en)
    print(f"avatar_id={avatar_id} -> EN name='{name_en}' -> {'CÓ' if match else 'KHÔNG'} khớp trong crimsonwitch")