from playwright.sync_api import sync_playwright
import google.generativeai as genai
from urllib.parse import urljoin
import json
import re
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from general_scraper_model.dept_link_scraper import find_dept_links
from general_scraper_model.prof_scraper import extract_professor_info, clean_html

import streamlit as st
load_dotenv()
genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY1"]))
model = genai.GenerativeModel("gemini-2.0-flash")


url = "https://iitj.ac.in/main/en/faculty-members"
depts = find_dept_links(url)
for dept in depts:
    print(f"{dept['dept_name']} => {dept['dept_url']}")




all_profs = []
 
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for dept in depts:
        dept_url = dept["dept_url"]
        dept_name = dept.get("dept_name", "")
        print(f"\nVisiting: {dept_url}")
        try:
            try:
                page.goto(dept_url, timeout=90000, wait_until="domcontentloaded")
            except:
                try:
                    print(f"Retrying with wait_until='load' for {dept_url}")
                    page.goto(dept_url, timeout=90000, wait_until="load")
                except:
                    try:
                        print(f"Retrying with wait_until='commit' for {dept_url}")
                        page.goto(dept_url, timeout=90000, wait_until="commit")
                    except Exception as e:
                        print(f"Final failure loading {dept_url}: {e}")
                        continue

            page.wait_for_timeout(5000)
            html = clean_html(page.content())
            print(f"Sending HTML of length: {len(html)} to Gemini")
            profs = extract_professor_info(html, dept_name, dept_url)
            for prof in profs:
                if "email" in prof and isinstance(prof["email"], str):
                    prof["email"] = prof["email"].replace("[at]", "@").replace(" ", "").replace("[dot]", ".")

            print(f"Found {len(profs)} professors from {dept_name}")
            all_profs.extend(profs)

        except Exception as e:
            print(f"Error loading {dept_url}: {e}")
            continue

output_path = (r"C:\Users\deep\summer siege\iitgn_faculty\faculty\iitj_faculty.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_profs, f, indent=2, ensure_ascii=False)

print(f"All professor data saved to {output_path}")