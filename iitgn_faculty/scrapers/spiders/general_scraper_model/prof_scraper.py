from playwright.sync_api import sync_playwright
import google.generativeai as genai
from urllib.parse import urljoin
import json
import re
import os
import sys
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY1"]))
model = genai.GenerativeModel("gemini-2.0-flash")

def deduplicate_professors(prof_list: list[dict]) -> list[dict]:
    seen = {}

    def normalize(text):
        return (text or "").lower().strip()

    def name_similarity(name1, name2):
        return normalize(name1).replace("dr.", "").replace("prof.", "") == normalize(name2).replace("dr.", "").replace("prof.", "")

    for prof in prof_list:
        email = normalize(prof.get("email"))
        name = normalize(prof.get("name"))
        dept = normalize(prof.get("department"))

        if email:
            key = f"email:{email}"
        else:
            key = None
            for existing_key, existing_prof in seen.items():
                existing_name = normalize(existing_prof.get("name"))
                existing_dept = normalize(existing_prof.get("department"))
                if name_similarity(name, existing_name) and (dept in existing_dept or existing_dept in dept):
                    key = existing_key
                    break

        if not key:
            key = f"name:{name}|dept:{dept}"

        if key not in seen:
            seen[key] = prof
        else:
            existing = seen[key]

            for field in ["designation", "email", "website", "photo", "profile_url", "academic_background", "work_experience"]:
                if not existing.get(field) and prof.get(field):
                    existing[field] = prof[field]
                elif len(str(prof.get(field) or "")) > len(str(existing.get(field) or "")):
                    existing[field] = prof[field]

            int1 = set(re.split(r"[●•,|]", existing.get("research_interests") or ""))
            int2 = set(re.split(r"[●•,|]", prof.get("research_interests") or ""))
            merged = [i.strip() for i in int1.union(int2) if i.strip()]
            existing["research_interests"] = ", ".join(sorted(merged))

            dept1 = set(existing.get("department", "").split(" | "))
            dept2 = set(prof.get("department", "").split(" | "))
            existing["department"] = " | ".join(sorted(dept1.union(dept2) - {""}))

    return list(seen.values())


def clean_html(raw_html):
    raw_html = re.sub(r"<script[^>]*>.*?</script>", "", raw_html, flags=re.DOTALL)
    raw_html = re.sub(r"<style[^>]*>.*?</style>", "", raw_html, flags=re.DOTALL)
    raw_html = re.sub(r"<!--.*?-->", "", raw_html, flags=re.DOTALL)  
    raw_html = re.sub(r"\s{2,}", " ", raw_html) 
    return raw_html.strip() 

def split_html_for_prompt(html: str, max_chars: int = 12000) -> list[str]:
    """
    Splits HTML into safe chunks based on </div> tags, up to max_chars per chunk.
    """
    chunks = []
    while len(html) > max_chars:
        split_at = html.rfind("</div>", 0, max_chars)
        if split_at == -1:
            split_at = max_chars  
        chunks.append(html[:split_at])
        html = html[split_at:]
    chunks.append(html)
    return chunks

def make_prompt_from_chunk(page_content: str, dept_name: str, url: str) -> str:
    return f"""
You are extracting structured data from the HTML of an academic department faculty webpage.

ONLY include actual full-time faculty or professors — DO NOT include:
- students (PhD/Masters),
- interns,
- administrative staff,
- office assistants,
- lab technicians,
- or postdocs.

Each entry should be a professor or faculty member with a valid academic title like Assistant Professor, Associate Professor, or Professor.

For each valid professor, extract these fields:
- name
- designation
- email
- website (personal if available)
- research_interests (if multiple, return as one comma-separated string)
- department = "{dept_name}"
- photo (must be a full absolute URL)
- profile_url (must also be a full absolute URL)

*** extract data from both website and profileurl, but give only 1 json object per professor, dont have duplicate for both. and there will be almost alike cards like things which you are scraping in which professors details will be. so scrap them all, dont leave any, only leave when you find that the detail is not like a professor. ***

Resolve all relative links using the base URL: {url}

Here is the raw HTML:
{page_content}

Return only valid JSON list like:
[
  {{
    "name": "Dr. XYZ",
    "designation": "...",
    "email": "...",
    "website": "...",
    "research_interests": "...",
    "department": "...",
    "photo": "...",
    "profile_url": "..."
  }},
  ...
]
"""

def merge_professor_lists(list_of_lists: list[list[dict]]) -> list[dict]:
    merged = []
    for prof_list in list_of_lists:
        merged.extend(prof_list)
    return merged


def extract_professor_info(page_content, dept_name, url):
    html_chunks = split_html_for_prompt(page_content)

    all_results = []
    for i, chunk in enumerate(html_chunks):
        prompt = make_prompt_from_chunk(chunk, dept_name, url)
        try:
            response = model.generate_content(prompt)
            json_text = response.text.strip()
            match = re.search(r"\[\s*{.*?}\s*\]", json_text, re.DOTALL)
            if match:
                profs = json.loads(match.group(0))
                if isinstance(profs, list):
                    all_results.extend(profs)
                else:
                    print(f"Chunk {i+1}: Gemini response is not a list")

            else:
                print(f"Chunk {i+1}: Gemini did not return valid JSON.")
        except Exception as e:
            print(f"Chunk {i+1}: Gemini error: {e}")

    merged = deduplicate_professors(all_results)
    return merged
