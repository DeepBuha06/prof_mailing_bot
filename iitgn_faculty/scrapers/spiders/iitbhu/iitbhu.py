import json
import time
import os
from playwright.sync_api import sync_playwright

file_path = os.path.join(os.path.dirname(__file__), "profile_links_iitbhu.json")
with open(file_path, "r", encoding="utf-8") as f:
    faculty_links = json.load(f)

final_data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for faculty in faculty_links:
        profile_url = faculty["profile_url"]
        print(f"🔍 Scraping: {profile_url}")

        try:
            page.goto(profile_url, timeout=60000)
            page.wait_for_timeout(2000)  # wait in case the content is JS-loaded

            data = page.query_selector_all("div.field-item.even")
            name = data[0].inner_text().strip()
            designation = data[1].inner_text().strip()
            department = data[2].inner_text().strip()
            email = data[3].inner_text().strip()
            research_interests = data[5].inner_text().strip()
            photo = page.query_selector("div.user-picture a.active img").get_attribute("src").strip()
            final_data.append({
                "name": name,
                "designation": designation,
                "department": department,
                "email": email,
                "website": None,
                "research_interests": research_interests,
                "photo": photo,
                "profile_url": profile_url
            })
            print(f"✅ Successfully scraped: {name}")
        except Exception as e:
            print(f"⚠️ Failed to scrape {profile_url}: {e}")

    browser.close()

# Save final_data to the desired file path
save_path = r"C:\Users\deep\summer siege\iitgn_faculty\faculty\iitbhu_faculty.json"
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=2, ensure_ascii=False)

print("✅ Data saved to:", save_path)
