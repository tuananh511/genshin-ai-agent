from genshin_agent.theater_collector import _extract_danger_suffix, _parse_enemy_field

s = "Tepetlisaurus{ text = - $ danger = 1 }"
print("raw:", repr(s))
print("extract:", _extract_danger_suffix(s))

raw_field = "Tepetlisaurus{ text = - $ danger = 1 };Yumkasaurus{ text = - $ danger = 1 };Qucusaurus Chick*-"
print("full field:", _parse_enemy_field(raw_field))