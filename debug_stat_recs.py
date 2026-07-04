# debug_bennett_energy.py
from genshin_agent import crimsonwitch_collector
from genshin_agent.asset_manager import asset_manager

all_builds = crimsonwitch_collector.get_all_builds()
name_en = asset_manager.get_avatar_name_en(10000032)  # Bennett

for b in all_builds.get(name_en, []):
    print(f"\nbuild_name: {b.get('build_name')}")
    print("energy:", b.get("energy"))
    print("stat_recommendations:", b.get("stat_recommendations"))