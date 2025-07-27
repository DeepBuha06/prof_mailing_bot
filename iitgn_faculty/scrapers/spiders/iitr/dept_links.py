import json
from playwright.sync_api import sync_playwright

dept_links = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    print("Opening faculty directory page...")
    page.goto("https://iitr.ac.in/Departments/", timeout=60000)
    page.wait_for_timeout(5000)

    blocks = page.query_selector_all("div.content")

    for block in blocks:
        dept_name_el = block.query_selector("div.ui.sub-heading")
        link_el = block.query_selector("a.ui.button")

        if dept_name_el and link_el:
            dept_name = dept_name_el.inner_text().strip()
            href = link_el.get_attribute("href").strip()

            dept_links.append({
                "dept_name": dept_name,
                "profile_url": href
            })
            print(dept_name, "=>", href)

    browser.close()

print(f"Extracted {len(dept_links)} links")
print("Sample data:", json.dumps(dept_links[:3], indent=2))


json_path = "iitr_departments.json"

try:
    with open(json_path, "r", encoding="utf-8") as f:
        existing_data = json.load(f)
except:
    existing_data = []

existing_data += dept_links

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(existing_data, f, indent=2, ensure_ascii=False)

print("Data saved to iitr_departments.json")
