import re
import os
import json
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import google.generativeai as genai
import streamlit as st

genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY1"]))
model = genai.GenerativeModel("gemini-2.0-flash")

def find_faculty_page_ai(dept_url, max_links=100):
    """
    Automatically finds the most likely faculty listing page for an academic department
    using Gemini-2.0-Flash and semantic understanding of link text and URLs.
    """

    all_links = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        try:
            print(f"Visiting: {dept_url}")
            page.goto(dept_url, timeout=40000, wait_until="load")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Page load error: {e}")
            return None

        anchors = page.locator("a").all()
        for a in anchors:
            try:
                text = a.inner_text().strip()
                href = a.get_attribute("href")
                if href and not href.startswith("#"):
                    full_url = urljoin(dept_url, href)
                    all_links.append({"text": text, "url": full_url})
            except:
                continue
        browser.close()

    trimmed_links = all_links[:max_links]  

    prompt = f"""
You are a web analysis AI helping identify academic faculty listing pages from university department websites.
From the following list of links found on a department homepage, identify the single URL most likely to list
**multiple faculty members** (not individual profiles).

Criteria:
- It should contain names, photos, designations, emails, or office details.
- It should be hosted on an official IIT website or Google Sites.
- It should NOT be a PDF, DOC, or a profile page of a single professor.
- Return only the most appropriate full URL.

Here is the list of links:

{json.dumps(trimmed_links, indent=2)}

Return only the best faculty listing page URL.
"""

    try:
        response = model.generate_content(prompt)
        match = re.search(r"https?://[\w\-./?=&%]+", response.text)
        if match:
            result = match.group(0)
            if not result.endswith((".pdf", ".doc", ".docx")) and any(domain in result for domain in ["iit", "google"]):
                print("Gemini selected faculty page:", result)
                return result
            else:
                print("Gemini returned irrelevant file/link.")
        else:
            print("Gemini did not return a valid URL.")
    except Exception as e:
        print("Gemini error:", e)

    return None
