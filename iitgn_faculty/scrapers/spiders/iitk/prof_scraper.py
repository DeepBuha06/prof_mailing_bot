from playwright.sync_api import sync_playwright
import google.generativeai as genai
from urllib.parse import urljoin
import json
import re
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from general_scraper_model.dept_link_scraper import find_dept_links
from general_scraper_model.faculty_page_finder import find_faculty_page_ai
from general_scraper_model.prof_scraper import extract_professor_info, clean_html, split_html_for_prompt
import streamlit as st

genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY1"]))
model = genai.GenerativeModel("gemini-2.0-flash")

url = "https://iitk.ac.in/new/iitk-faculty"

all_profs = []
 
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    try:
        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
        except:
            try:
                print(f"Retrying with wait_until='load' for {url}")
                page.goto(url, timeout=90000, wait_until="load")
            except:
                try:
                    print(f"Retrying with wait_until='commit' for {url}")
                    page.goto(url, timeout=90000, wait_until="commit")
                except Exception as e:
                    print(f"Final failure loading {url}: {e}")
        page.wait_for_timeout(5000)
        html = clean_html(page.content())
        print(f"Sending HTML of length: {len(html)} to Gemini")
        html_chunks = split_html_for_prompt(html)
        all_results = []
        for i, chunk in enumerate(html_chunks):
            prompt = f"""
You are extracting structured data from the HTML of an academic department faculty webpage. there are some toggle button kind of things which has professors inside them. so you have to scrap that all professors details.

ONLY include actual full-time faculty or professors — DO NOT include:
- students (PhD/Masters),
- interns,
- administrative staff,
- office assistants,
- lab technicians,
- or postdocs.

Each entry should be a professor or faculty member with a valid academic title like Assistant Professor, Associate Professor, or Professor.

For each valid professor, extract these fields:
- name
- designation
- email
- website (personal if available)
- research_interests (if multiple, return as one comma-separated string)
- department = "there is a toggle button like thing which has all professor of that named branch's professors,so this is that department"
- photo (must be a full absolute URL)
- profile_url (must also be a full absolute URL)

*** extract data from both website and profileurl, but give only 1 json object per professor, dont have duplicate for both. and there will be almost alike cards like things which you are scraping in which professors details will be. so scrap them all, dont leave any, only leave when you find that the detail is not like a professor. ***
Resolve all relative links using the base URL: {url}

Here is the raw HTML:
{chunk}

Return only valid JSON list like:
[
  {{
    "name": "Dr. XYZ",
    "designation": "...",
    "email": "...",
    "website": "...",
    "research_interests": "...",
    "department": "...",
    "photo": "...",
    "profile_url": "..."
  }},
  ...
]
"""
            try:
                response = model.generate_content(prompt)
                json_text = response.text.strip()
                match = re.search(r"\[\s*{.*?}\s*\]", json_text, re.DOTALL)
                if match:
                    profs = json.loads(match.group(0))
                    if isinstance(profs, list):
                        all_results.extend(profs)
                    else:
                        print(f"Chunk {i+1}: Gemini response is not a list")
                else:
                    print(f"Chunk {i+1}: Gemini did not return valid JSON.")
            except Exception as e:
                print(f"Chunk {i+1}: Gemini error: {e}")
        
        for prof in all_results:
            print(f"{prof["name"]} -> {prof["department"]} ->{prof["email"]}")
            if "email" in prof and isinstance(prof["email"], str):
                    prof["email"] = prof["email"].replace("[at]", "@").replace(" ", "").replace("[dot]", ".")
                    
    except Exception as e:
            print(f"Error loading {url}: {e}")
    