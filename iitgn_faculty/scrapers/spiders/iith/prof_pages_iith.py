import json
import time
import os
from playwright.sync_api import sync_playwright

profile_urls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Opening faculty directory page...")
    page.goto("https://www.iith.ac.in/people/faculty/", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)

    prof = page.query_selector_all("div.facultycard div.text-center a")

    for p in prof:
        try:
            card = p.evaluate_handle("node => node.closest('.facultycard')")
            profile_url = "https://www.iith.ac.in/" + p.get_attribute("href").strip().replace("../../", "")
            name = card.query_selector("div.text-center h5 a").inner_text().strip()

            profile_urls.append({
                "name": name,
                "url": profile_url
            })
            print(f"Extracted profile: {name} - {profile_url}")
        except Exception as e:
            print(f"Error extracting one profile: {e}")
    
    browser.close()

print(f"Total extracted (with duplicates): {len(profile_urls)}")

unique_profiles = {}
for prof in profile_urls:
    unique_profiles[prof["url"]] = prof 
deduped_list = list(unique_profiles.values())
print(f"Unique profiles after deduplication: {len(deduped_list)}")

json_path = r"C:\Users\deep\summer siege\iitgn_faculty\iitgn_faculty\spiders\iith\prof_links_iith.json"
os.makedirs(os.path.dirname(json_path), exist_ok=True)

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(deduped_list, f, indent=2, ensure_ascii=False)

print("Data saved to", json_path)
print("Sample data:", json.dumps(deduped_list[:3], indent=2, ensure_ascii=False))
