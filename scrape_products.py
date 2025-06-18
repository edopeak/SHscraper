# scrape_products.py
import json
import requests

COLLECTION = "footies"
BASE_URL = f"https://bumsandroses.com/collections/{COLLECTION}/products.json?page={{}}"
MAX_PAGES = 10
output = []

for page in range(1, MAX_PAGES + 1):
    res = requests.get(BASE_URL.format(page), timeout=10)
    if res.status_code != 200:
        break

    data = res.json().get("products", [])
    if not data:
        break

    for product in data:
        output.append({
            "rank": len(output) + 1,
            "title": product["title"],
            "url": f"https://bumsandroses.com/products/{product['handle']}",
            "category": COLLECTION
        })

with open("raw_products.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"✅ Saved {len(output)} products to raw_products.json")