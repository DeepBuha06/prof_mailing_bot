import json
import time
import os
from playwright.sync_api import sync_playwright

file_path = os.path.join(os.path.dirname(__file__), "iitr_dept_links.json")
with open(file_path, "r", encoding="utf-8") as f:
    dept_links = json.load(f)

profile_urls = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for dept in dept_links:
        dept_url = dept["dept_url"]  

        print(f"Visiting: {dept_url}")
        try:
            page.goto(dept_url, timeout=60000)
            page.wait_for_timeout(2000)

            professors = page.query_selector_all("a.link-content")  

            for prof in professors:
                profile_url = prof.get_attribute("href").replace(" ", "%20")
                profile_urls.append({"profile_url": profile_url})
                print({"profile_url": profile_url})

        except Exception as e:
            print(f"Error loading {dept_url}: {e}")

    browser.close()

json_path = "iitr_prof_pages.json"

try:
    with open(json_path, "r", encoding="utf-8") as f:
        existing_data = json.load(f)
except:
    existing_data = []

existing_data += profile_urls

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(existing_data, f, indent=2, ensure_ascii=False)

print("Data saved to iitr_prof_pages.json")
