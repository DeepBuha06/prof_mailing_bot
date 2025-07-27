import json
import time
import os
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, unquote

def extract_department(profile_url):
    parsed = urlparse(profile_url)
    path_parts = unquote(parsed.path).split('/')

    if "Departments" in path_parts:
        idx = path_parts.index("Departments")
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1].replace(" Department", "").strip()

    for part in path_parts:
        if part.startswith("~"):
            return part[1:]  

    return "Unknown"


file_path = os.path.join(os.path.dirname(__file__), "iitr_prof_pages.json")
with open(file_path, "r", encoding="utf-8") as f:
    faculty_links = json.load(f)

final_data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for faculty in faculty_links:
        profile_url = faculty["profile_url"]
        print(f"Scraping: {profile_url}")
        try:
            page.goto(profile_url, timeout=60000)
            page.wait_for_timeout(2000)

            name = page.query_selector("div.second div.ui.intro-text").inner_text()

            elements = page.query_selector_all("div.second div.ui.description")

            designation = page.query_selector("div.second div.ui.description").inner_text()
            
            email = page.query_selector("div.info div.ui.icon-typography div.ui.intro-text").inner_text().strip().replace("[at]", "@")
            
            research_interests = elements[1].inner_text().strip()

            dept_name = extract_department(profile_url)

            photo = None

            final_data.append({
                "name": name,
                "designation": designation,
                "email": email,
                "website": None,
                "research_interests": research_interests,
                "department": dept_name,
                "photo": photo,
                "profile_url": profile_url
            })



            print(f"Collected data for: {name}")

        except Exception as e:
            print(f"Failed to scrape {profile_url}: {e}")
            continue
        
output_path = os.path.join("iitgn_faculty", "faculty", "iitr_faculty.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)


print("Done! Saved full profiles to iitr_faculty.json")