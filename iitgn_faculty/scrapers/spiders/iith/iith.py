import json
import time
import os
from playwright.sync_api import sync_playwright
import urllib.parse

file_path = os.path.join(os.path.dirname(__file__), "prof_links_iith.json")
with open(file_path, "r", encoding="utf-8") as f:
    faculty_links = json.load(f)

final_data = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for faculty in faculty_links:
        profile_url = faculty["url"]
        print(f"🔍 Scraping: {profile_url}")

        try:
            page.goto(profile_url, timeout=60000)
            page.wait_for_timeout(2000)  

            name = faculty["name"]

            h6_elem = page.query_selector("h6")
            page.evaluate("el => el.querySelector('strong')?.remove()", h6_elem)
            designation = h6_elem.inner_text().strip()

            strong_elem = page.query_selector('strong:text("Department(s):")')

            h6_elem = strong_elem.evaluate_handle("node => node.closest('h6')")
            ul_elem = h6_elem.evaluate_handle("node => node.nextElementSibling")

            department_lis = ul_elem.query_selector_all("li.text-left")
            departments = [li.inner_text().strip() for li in department_lis]
            department = ", ".join(departments)

            common_parent = ul_elem.evaluate_handle("node => node.parentElement")

            all_uls = common_parent.query_selector_all("ul")

            if len(all_uls) > 1:
                research_ul = all_uls[1]
                research_lis = research_ul.query_selector_all("li.text-left")
                research_interests_list = [li.inner_text().strip() for li in research_lis]
                research_interests = ", ".join(research_interests_list)
            else:
                research_interests = ""

            encoded_email = page.query_selector('h6 strong a').get_attribute("href").strip()
            first_decode = urllib.parse.unquote(encoded_email)
            second_decode = urllib.parse.unquote(first_decode)
            email = second_decode.replace("mailto:", "")
            print("Extracted email:", email)

            website = None
            
            photo = page.query_selector("div.col-sm-3 img").get_attribute("src").replace("../../", "https://www.iith.ac.in/")

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

            
            print(f"Successfully scraped: {name}")
        except Exception as e:
            print(f"Failed to scrape {profile_url}: {e}")

    browser.close()

save_path = r"C:\Users\deep\summer siege\iitgn_faculty\faculty\iith_faculty.json"
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=2, ensure_ascii=False)

print("Data saved to:", save_path)
