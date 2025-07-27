import json
import os
from playwright.sync_api import sync_playwright
import google.generativeai as genai
import re
from dotenv import load_dotenv


def clean_html(raw_html):
    raw_html = re.sub(r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL)
    raw_html = re.sub(r"<style[^>]*>.*?</style>", "", raw_html, flags=re.DOTALL)
    raw_html = re.sub(r"<!--.*?-->", "", raw_html, flags=re.DOTALL)  
    raw_html = re.sub(r"\s{2,}", " ", raw_html) 
    return raw_html.strip() 
import streamlit as st
load_dotenv()
genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY"]))
model = genai.GenerativeModel("gemini-2.0-flash")

file_path = os.path.join(os.path.dirname(__file__), "iiti_faculty_pages.json")
with open(file_path, "r", encoding="utf-8") as f:
    dept_links = json.load(f)

def extract_professor_info(page_content, dept_name, url):
    prompt = f"""
You are extracting structured data from the HTML of an academic department faculty webpage.

Please identify and return structured information for **all professors** listed on the page. Be exhaustive — do not skip any professor. If a professor card has missing details, at least extract their name.

For each professor, extract these fields:
- name
- designation
- email
- website (personal if available)
- research_interests (if multiple, return as one comma-separated string)
- department = "{dept_name}"
- photo_url (must be a full absolute URL, not relative like './images/...')
- profile_url (must also be full absolute URL, not relative, this is the link from which you are scraping the details like not the url of departent f we have some cards like system which leads us to a page for the details of particular professor--> this is the profile url, else the department url will also work in case whre there is just a column of details where there is no links for particular professors.)

To resolve relative links, you MUST prefix them with the base URL: {url}

Here is the raw HTML content:

```html
{page_content}
```

Return only valid JSON list like:
[
  {{
    "name": "Dr. XYZ",
    "designation": "...",
    "email": "...",
    "website": "...",
    "research_interests": "...",
    "department": "...",
    "photo_url": "...",
    "profile_url": "..."
  }},
  ...
]
    """
    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip()

        match = re.search(r"\[\s*{.*}\s*\]", json_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            print("Gemini did not return valid JSON.")
            return []
    except Exception as e:
        print(f"Gemini error while extracting professors: {e}")
        return []

all_profs = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for dept in dept_links:
        dept_url = dept["dept_url"]
        dept_name = dept.get("dept_name", "")
        print(f"\nVisiting: {dept_url}")
        try:
            try:
                page.goto(dept_url, timeout=90000, wait_until="domcontentloaded")
            except:
                try:
                    print(f"Retrying with wait_until='load' for {dept_url}")
                    page.goto(dept_url, timeout=90000, wait_until="load")
                except:
                    try:
                        print(f"Retrying with wait_until='commit' for {dept_url}")
                        page.goto(dept_url, timeout=90000, wait_until="commit")
                    except Exception as e:
                        print(f"Final failure loading {dept_url}: {e}")
                        continue

            page.wait_for_timeout(5000)
            html = clean_html(page.content())

            profs = extract_professor_info(html, dept_name, dept_url)
            for prof in profs:
                if "email" in prof and isinstance(prof["email"], str):
                    prof["email"] = prof["email"].replace("[at]", "@").replace(" ", "").replace("[dot]", ".")

            print(f"Found {len(profs)} professors from {dept_name}")
            all_profs.extend(profs)

        except Exception as e:
            print(f"Error loading {dept_url}: {e}")
            continue

    browser.close()

output_path = os.path.join(os.path.dirname(__file__), "iiti_extracted_professors.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_profs, f, indent=2, ensure_ascii=False)

print(f"All professor data saved to {output_path}")