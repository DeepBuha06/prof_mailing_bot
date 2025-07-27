from playwright.sync_api import sync_playwright
import google.generativeai as genai
from urllib.parse import urljoin
import json
import os
import streamlit as st

genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY1"]))
model = genai.GenerativeModel("gemini-2.0-flash")

def find_dept_links(main_url):
    raw_links = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        try:
            print(f"Visiting {main_url}")
            page.goto(main_url, timeout=40000, wait_until="load")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Page load error: {e}")
            return []

        anchors = page.locator("a").all()
        for a in anchors:
            try:
                text = a.inner_text().strip()
                href = a.get_attribute("href")
                if text and href:
                    full_url = urljoin(main_url, href)
                    raw_links.append({
                        "dept_name": text, 
                        "dept_url": full_url
                        })
            except:
                continue

        browser.close()

    joined_links = "\n".join([f"{link['dept_name']} -> {link['dept_url']}" for link in raw_links])

    prompt = f"""
                Below are links from a college website. From these, identify only the academic department links such as CSE, ECE, Mechanical, etc which are the pages of listing of faculty of department. Output only a list of such department links as JSON like where text is the name of the department:
                [{{"dept_name": "...", "dept_url": "..."}}] Be exhaustive, do not skip any link which can be a faculty page in higher chances.
                Links: {joined_links} """

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        json_start = raw_text.find("[")
        json_end = raw_text.rfind("]") + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON array found in model response.")

        json_str = raw_text[json_start:json_end]

        json_str = json_str.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")

        filtered_links = json.loads(json_str)
        return filtered_links

    except Exception as e:
        print("AI Filtering Failed:", e)
        return []