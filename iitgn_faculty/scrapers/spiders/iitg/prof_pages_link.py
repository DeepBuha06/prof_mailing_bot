import json
import os
from playwright.sync_api import sync_playwright

faculty_links = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Opening faculty directory page...")
    page.goto("https://www.iitg.ac.in/iitg_faculty_all", timeout=60000)

    page.wait_for_timeout(5000)

    links = page.query_selector_all("h3 > a")
    base_url = "https://www.iitg.ac.in/"

    for link in links:
        try:
            name = link.inner_text().strip()
            href = link.get_attribute("href")
            if href:
                full_url = href if href.startswith("http") else base_url + href.lstrip("/")
                faculty_links.append({
                    "name": name,
                    "profile_url": full_url
                })
        except Exception as e:
            print("Error parsing link:", e)

    browser.close()

print(f"Extracted {len(faculty_links)} links")
print("Sample data:", json.dumps(faculty_links[:3], indent=2))

json_path = os.path.join(os.getcwd(), "iitg.json")
print("Writing to:", json_path)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(faculty_links, f, indent=4, ensure_ascii=False)

print("Done writing to iitg.json")
