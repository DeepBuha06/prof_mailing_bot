from playwright.sync_api import sync_playwright
import google.generativeai as genai
from urllib.parse import urljoin
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

def extract_department_links():
    dept_links = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.iiti.ac.in/departments", timeout=60000)
        page.wait_for_timeout(5000)

        blocks = page.query_selector_all("div.caption")
        for block in blocks:
            dept_name_el = block.query_selector("h4.heading")
            link_el = block.query_selector("a")
            if dept_name_el and link_el:
                dept_name = dept_name_el.inner_text().strip()
                href = link_el.get_attribute("href").strip()
                full_url = href if href.startswith("http") else "https://www.iiti.ac.in/" + href.lstrip("/")
                dept_links.append({
                    "dept_name": dept_name,
                    "profile_url": full_url
                })
                print(f"{dept_name}: {full_url}")
        browser.close()
    return dept_links

def find_faculty_page_ai(dept_url):
    links = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        try:
            print(f"*******Visiting {dept_url} (full load)...*******")
            page.goto(dept_url, timeout=40000, wait_until="load")
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Load error: {e}")

        anchors = page.locator("a").all()
        for a in anchors:
            try:
                text = a.inner_text().strip()
                href = a.get_attribute("href")
                if href and not href.startswith("#"):
                    full = urljoin(dept_url, href)
                    links.append({"text": text, "url": full})
            except:
                continue
        browser.close()

    faculty_keywords = ["faculty", "people", "team", "group", "core", "staff", "profile", "research"]
    filtered_links = []
    for l in links:
        url = l["url"].lower()
        text = l["text"].lower()

        if not any(k in text or k in url for k in faculty_keywords):
            continue
        if url.strip("/") == dept_url.strip("/"):
            continue
        if url.endswith((".pdf", ".doc", ".docx", "#", "/#")):
            continue
        if re.search(r"/(prof|dr)[\w\-]+/?$", url) or re.search(r"/~[\w\-]+/?$", url):
            continue
        if not any(domain in url for domain in ["iiti.ac.in", "iit.ac.in", "google.com"]):
            continue

        filtered_links.append(l)

    if filtered_links:
        def score(link):
            url = link["url"].lower()
            text = link["text"].lower()
            score = 0
            score += sum(k in text for k in faculty_keywords) * 100
            score += sum(k in url for k in faculty_keywords) * 50
            if "index.php" in url:
                score += 30
            if "people" in url and "people" in text:
                score += 40
            if url.count("/") >= 5:
                score += 10
            return score

        best_link = sorted(filtered_links, key=score, reverse=True)[0]
        print("Best match by scoring:", best_link["url"])
        return best_link["url"]

    prompt = (
        "From the list of department website links, select the one that most likely leads to a page listing "
        "multiple faculty members (NOT individual professor profile pages). "
        "Ignore any link that is not part of the academic department's website or hosted by IIT or Google Sites.\n\n"
        "This page usually contains names, photos, designations, emails, or office details.\n\n"
        f"{json.dumps(links[:30], indent=2)}"
    )

    try:
        response = model.generate_content(prompt)
        match = re.search(r"https?://[^\s\"')\]]+", response.text)
        if match:
            chosen = match.group(0).strip()
            if (
                chosen != dept_url
                and not re.search(r"/(prof|dr)[\w\-]+/?$", chosen.lower())
                and not chosen.lower().endswith((".pdf", ".doc", ".docx"))
                and any(domain in chosen for domain in ["iiti.ac.in", "iit.ac.in", "google.com"])
            ):
                print("Gemini chose:", chosen)
                return chosen
            else:
                print("Gemini returned invalid or deep URL, skipping.")
    except Exception as e:
        print("Gemini error:", e)

    print("No valid faculty link found.")
    return None


json_path = r"C:\Users\deep\summer siege\iitgn_faculty\scrapers\spiders\iiti\iiti_faculty_pages.json"

dept_links = extract_department_links()
result = []

for dept in dept_links:
    print(f"\nSearching for faculty page of: {dept['dept_name']}")
    link = find_faculty_page_ai(dept["profile_url"])
    print("Suggested faculty page:", link)
    result.append({
        "dept_name": dept["dept_name"],
        "dept_url": link
    })

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(f"\nFaculty links saved to {json_path}")

