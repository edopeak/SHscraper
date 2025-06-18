# File: app.py (Cloud-Friendly with Shopify JSON API)

import streamlit as st
import json
import csv
import os
import re
import requests
from bs4 import BeautifulSoup

OUTPUT_CSV_PATH = './output/parsed_products.csv'
SHOPIFY_JSON_API = 'https://bumsandroses.com/collections/all/products.json?page={}'

# Scrape product listings from Shopify JSON API
def scrape_raw_products():
    products = []
    seen = set()

    for page in range(1, 6):  # fetch up to 5 pages (250 products max)
        res = requests.get(SHOPIFY_JSON_API.format(page), timeout=10)
        if res.status_code != 200:
            break

        data = res.json().get("products", [])
        if not data:
            break

        for item in data:
            title = item.get("title")
            handle = item.get("handle")
            if not title or not handle or handle in seen:
                continue
            seen.add(handle)
            products.append({
                "rank": len(products) + 1,
                "title": title,
                "url": f"https://bumsandroses.com/products/{handle}"
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
            'review_count': reviews
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
st.title("🛍️ Shopify Print Parser (Cloud-Only)")

if st.button("2️⃣ Scrape Bumsandroses Products"):
    with st.spinner("Scraping from Shopify JSON API..."):
        scraped = scrape_raw_products()
        st.session_state['scraped'] = scraped
        st.success(f"✅ Found {len(scraped)} products.")

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
    st.info("👆 Click above to scrape Bumsandroses products and extract print insights.")
