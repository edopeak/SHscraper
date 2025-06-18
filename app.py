# File: app.py

import streamlit as st
import json
import csv
import os
import re
import requests
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import playwright.__main__ as pw_main

RAW_PRODUCTS_PATH = './data/raw_products.json'
OUTPUT_CSV_PATH = './output/parsed_products.csv'
TARGET_URL = 'https://bumsandroses.com/collections/all?sort_by=best-selling'

# Playwright scraper
async def scrape_products():
    os.makedirs(os.path.dirname(RAW_PRODUCTS_PATH), exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(TARGET_URL)

        prev_height = 0
        while True:
            curr_height = await page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)

        product_links = await page.query_selector_all('a.full-unstyled-link')
        seen_urls = set()
        results = []

        for i, link in enumerate(product_links):
            title = await link.inner_text()
            href = await link.get_attribute('href')
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)
            results.append({
                'rank': len(results) + 1,
                'title': title.strip(),
                'url': f"https://bumsandroses.com{href.strip()}"
            })

        await browser.close()

        with open(RAW_PRODUCTS_PATH, 'w') as f:
            json.dump(results, f, indent=2)

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

def parse_and_save():
    if not os.path.exists(RAW_PRODUCTS_PATH):
        st.error("❌ raw_products.json not found. Run scraper first.")
        return

    with open(RAW_PRODUCTS_PATH, 'r') as f:
        raw_data = json.load(f)

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
st.set_page_config(page_title="Shopify Print Scraper", layout="centered")
st.title("🛍️ Shopify Print Scraper")

if st.button("1️⃣ Install Playwright (1st time only)"):
    with st.spinner("Installing Playwright..."):
        pw_main.main(["install", "chromium"])
    st.success("✅ Playwright installed")

if st.button("2️⃣ Scrape Best-Selling Products"):
    with st.spinner("Scraping products..."):
        asyncio.run(scrape_products())
    st.success("✅ Products scraped!")

if st.button("3️⃣ Parse Products + Ratings"):
    with st.spinner("Parsing data and scraping reviews..."):
        csv_path = parse_and_save()
        if csv_path and os.path.exists(csv_path):
            with open(csv_path, 'rb') as f:
                st.download_button(
                    label="⬇️ Download Parsed CSV",
                    data=f,
                    file_name="parsed_products.csv",
                    mime="text/csv"
                )