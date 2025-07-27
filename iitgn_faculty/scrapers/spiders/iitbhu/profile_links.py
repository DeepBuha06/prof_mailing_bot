import json
import time
import os
from playwright.sync_api import sync_playwright

profile_urls = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("🔄 Opening faculty directory page...")
    page.goto("https://prev.iitbhu.ac.in/all/faculty", timeout=60000)
    page.wait_for_timeout(5000)

    prof = page.query_selector_all("td.views-field.views-field-field-full-name.views-align-left.priority-low")
    
    for p in prof:
        name = p.inner_text().strip().split("\n")[0]
        link = "https://prev.iitbhu.ac.in" + p.query_selector("a").get_attribute("href").strip()
        profile_urls.append({
            "name": name,
            "profile_url": link
        })
        print(name, "=>", link)
    browser.close()

print(f"✅ Extracted {len(profile_urls)} links")

json_path = r"C:\Users\deep\summer siege\iitgn_faculty\iitgn_faculty\spiders\iitbhu\profile_links_iitbhu.json"

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(profile_urls, f, indent=2, ensure_ascii=False)

print("✅ Data saved to", json_path)
print("📦 Sample data:", json.dumps(profile_urls[:3], indent=2, ensure_ascii=False))
