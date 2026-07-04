import requests
from bs4 import BeautifulSoup

resp = requests.get("https://genshin-impact-helper-team.github.io/genshin-builds/en/bennett/")
soup = BeautifulSoup(resp.text, "html.parser")

# Leo cao hơn từ Weapons heading, in ra 5 tầng cha, kèm mọi attribute (không chỉ class)
headings = [t for t in soup.find_all(["h1", "h2", "h3"]) if t.get_text(strip=True) == "Weapons"]
for i, h in enumerate(headings):
    print(f"\n=== Weapons heading #{i} — leo lên 6 tầng cha ===")
    node = h
    for level in range(6):
        node = node.parent
        if node is None:
            break
        print(f"  level {level}: <{node.name}> attrs={node.attrs}")

# Xem xung quanh nút build-switcher-button để tìm attribute liên kết (aria-controls, id, data-target...)
print("\n=== build-switcher-button attrs ===")
for btn in soup.find_all("button", class_="build-switcher-button"):
    print(btn.attrs, "| text:", btn.get_text(strip=True))