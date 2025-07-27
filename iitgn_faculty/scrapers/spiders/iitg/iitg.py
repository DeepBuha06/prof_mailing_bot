import json
import time
import os
from playwright.sync_api import sync_playwright

file_path = os.path.join(os.path.dirname(__file__), "iitg.json")
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

            name = page.query_selector("h2")
            name = name.inner_text().strip() if name else None

            designation = page.query_selector("h4")
            designation = designation.inner_text().strip() if designation else None

            
            try:
                email  = page.locator("p span.text-info").inner_text(timeout=3000).replace("⋅", ".").replace(" ", "")
            except Exception as e:
                email = None

            research_section = page.locator("text=Research Interest").first
            research_interests = None
            if research_section:
                elem = research_section.evaluate_handle("el => el.nextElementSibling")
                if elem:
                    research_interests = elem.inner_text().strip()

            website = None
            links = page.query_selector_all("a")
            for link in links:
                text = link.inner_text().lower()
                if "personal" in text or "website" in text:
                    href = link.get_attribute("href")
                    if href and href.startswith("http"):
                        website = href
                        break

            dept = None
            try:
                dept = page.locator("div.tags a").inner_text(timeout=2000)
            except:
                dept = "UNKNOWN"

            try:
                photo = None
                try:
                    photo = "https://www.iitg.ac.in/" +page.locator("div.thumb img.imgshadow").get_attribute("src")
                except:
                    photo = None  
            except:
                photo = None 

            final_data.append({
                "name": name,
                "designation": designation,
                "email": email,
                "website": website,
                "research_interests": research_interests,
                "department": dept,
                "photo": photo,
                "profile_url": profile_url
            })

        except Exception as e:
            print(f"Failed to scrape {profile_url}: {e}")
            continue

    browser.close()

output_path = os.path.join("iitgn_faculty", "faculty", "iitg_faculty.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)


print("Done! Saved full profiles to iitg_full_profiles.json")
