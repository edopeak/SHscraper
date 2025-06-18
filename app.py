# File: app.py (Cloud-Friendly with HTML Pagination per Category + Browser Headers)

import streamlit as st
import json
import csv
import os
import re
import requests
from bs4 import BeautifulSoup

OUTPUT_CSV_PATH = './output/parsed_products.csv'
CATEGORY_ENDPOINTS = [
    "baby-bamboo-convertible-romper",
    "two-piece-bamboo-sets",
    "footies"
]

# Scrape product listings per category from rendered HTML pages
def scrape_category_products():
    base_url = 'https://bumsandroses.com/collections/{}/?page={}'
    products = []
    seen = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
    }

    for category in CATEGORY_ENDPOINTS:
        for page in range(1, 10):
            url = base_url.format(category, page)
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select('a.full-unstyled-link')
            if not items:
                break

            for link in items:
                title = link.get_text(strip=True)
                href = link.get('href')
                if not title or not href or href in seen:
                    continue
                seen.add(href)
                products.append({
                    "rank": len(products) + 1,
                    "title": title,
                    "url": f"https://bumsandroses.com{href}",
                    "category": category
                })

    return products

# Parser logic
def parse_title(title: str) -> dict:
    title = title.strip()
    patterns = [
        r'(?P<product_type>.+?)\s+[\u2013\-]\s+(?P<print_name>.+)',
        r'(?P<product_type>.+?)\s+in\s+(?P<print_name>.+)',
    ]
    for pattern in patterns:
        match = re.match(pattern, title)
        if match:
            return match.groupdict()
    return {'product_type': 'Unknown', 'print_name': title}

def scrape_reviews(product_url: str) -> tuple:
    try:
        response = requests.get(product_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        rating_elem = soup.select_one('[class*=jdgm-star-rating]')
        review_count_elem = soup.select_one('[class*=jdgm-all-reviews-rating-count]')

        rating = rating_elem['data-average-rating'] if rating_elem and rating_elem.has_attr('data-average-rating') else 'N/A'
        reviews = review_count_elem.text.strip() if review_count_elem else '0'
        return rating, reviews
    except Exception:
        return 'N/A', '0'

def parse_and_save(raw_data):
    if not raw_data:
        st.warning("⚠️ No products found.")
        return

    parsed_rows = []
    for entry in raw_data:
        parsed = parse_title(entry['title'])
        rating, reviews = scrape_reviews(entry['url'])
        parsed_rows.append({
            'rank': entry['rank'],
            'title': entry['title'],
            'url': entry['url'],
            'product_type': parsed['product_type'],
            'print_name': parsed['print_name'],
            'rating': rating,
            'review_count': reviews,
            'category': entry.get('category', 'N/A')
        })

    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)
    with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=parsed_rows[0].keys())
        writer.writeheader()
        writer.writerows(parsed_rows)

    st.success(f"✅ Parsed {len(parsed_rows)} products. Download CSV below.")
    return OUTPUT_CSV_PATH

# Streamlit UI
st.set_page_config(page_title="Shopify Print Parser", layout="centered")
st.title("🛍️ Shopify Print Parser (Paginated Category HTML)")

if st.button("2️⃣ Scrape Bumsandroses by Category"):
    with st.spinner("Scraping HTML pages from Bumsandroses.com..."):
        scraped = scrape_category_products()
        st.session_state['scraped'] = scraped
        st.success(f"✅ Found {len(scraped)} products across categories.")

if 'scraped' in st.session_state and st.button("3️⃣ Parse Products + Ratings"):
    with st.spinner("Parsing and enriching product data..."):
        csv_path = parse_and_save(st.session_state['scraped'])
        if csv_path and os.path.exists(csv_path):
            with open(csv_path, 'rb') as f:
                st.download_button(
                    label="⬇️ Download Parsed CSV",
                    data=f,
                    file_name="parsed_products.csv",
                    mime="text/csv"
                )
else:
    st.info("👆 Click above to scrape Bumsandroses category pages with full pagination support.")

