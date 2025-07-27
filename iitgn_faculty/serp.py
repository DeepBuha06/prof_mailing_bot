import os
import json
import re
import time
import traceback
from serpapi import GoogleSearch
import google.generativeai as genai
import concurrent.futures
import streamlit as st

# Load API keys

SERP_API_KEY = os.getenv("SERP_API_KEY")
GEMINI_API_KEY = os.getenv(st.secrets["GEMINI_API_KEY"])

# Configure Gemini model
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")  # or "gemini-pro"

# Search faculty pages using SerpAPI
def get_search_results(iit_name):
    query = f"{iit_name} faculty site:.ac.in"
    search = GoogleSearch({
        "q": query,
        "api_key": SERP_API_KEY,
        "num": 10
    })
    results = search.get_dict()
    links = []
    for res in results.get("organic_results", []):
        if "link" in res:
            links.append(res["link"])
    return links

# Gemini timeout-safe wrapper
def safe_generate(prompt, timeout_sec=20):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(lambda: model.generate_content(prompt))
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            return None

# Cleanly extract only relevant faculty page URLs
def extract_faculty_structure(iit_name, urls):
    prompt = f"""
You are given a list of URLs for {iit_name}. Your task is to identify only the faculty listing pages.
Some institutions have one single page, others have department-wise pages.

Return ONLY the relevant URLs from this list that directly show faculty members.
No explanation, no Python code, no markdown — just valid URLs in a list format.
Example:
["https://cse.iitb.ac.in/people/faculty", "https://me.iitb.ac.in/faculty"]

Here are the URLs:\n{json.dumps(urls, indent=2)}
"""

    try:
        print(f"\n🔍 Prompting Gemini for: {iit_name}")
        response = safe_generate(prompt)
        if response is None:
            raise TimeoutError("Gemini API timed out.")

        content = response.text.strip()
        print(f"\n--- Gemini response for {iit_name} ---\n{content[:400]}...\n")

        # Extract all valid URLs using regex
        all_links = re.findall(r'https?://[^\s\)\]"\'}<>]+', content)
        clean_links = list(sorted(set(link.strip().rstrip(".,") for link in all_links)))
        return {iit_name: clean_links if clean_links else ["Not found"]}
    except Exception as e:
        print(f"❌ Error parsing {iit_name}: {e}")
        traceback.print_exc()
        return {iit_name: ["Not found"]}

# Save to JSON incrementally
def write_partial_json(path, data):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}
    existing.update(data)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

# Main script loop
def main():
    iits = [
        "IIT Bombay", "IIT Delhi", "IIT Kanpur", "IIT Madras", "IIT Kharagpur",
        "IIT Guwahati", "IIT Roorkee", "IIT Hyderabad", "IIT Gandhinagar",
        "IIT Indore", "IIT Ropar", "IIT BHU", "IIT Dhanbad", "IIT Patna", "IIT Goa"
    ]

    output_path = "iit_faculty_pages.json"

    for iit in iits:
        print(f"\n🚀 Processing {iit}...")
        try:
            links = get_search_results(iit)
            result = extract_faculty_structure(iit, links)
            write_partial_json(output_path, result)
            print(f"✅ Done with {iit}")
        except Exception as e:
            print(f"❌ Failed for {iit}: {e}")
        time.sleep(2)  # avoid hitting API rate limits

    print(f"\n🎉 All done! Output saved to `{output_path}`")

if __name__ == "__main__":
    main()
