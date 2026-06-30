import json
import os
import time
from playwright.sync_api import sync_playwright

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "agent_memory.json")

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_memory(memory_data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, indent=4)

def scrape_scholar(prof_name, college_name, status_placeholder=None):
    """
    Uses Playwright to autonomously search Google Scholar for the professor's latest paper.
    Returns the title and abstract (or empty string if not found).
    """
    memory = load_memory()
    prof_key = f"{prof_name} - {college_name}"
    
    if prof_key in memory:
        if status_placeholder:
            status_placeholder.markdown("`Agent Memory:` Found cached context for this professor.")
        return memory[prof_key]

    if status_placeholder:
        status_placeholder.markdown("`Agent Memory:` No cache found. Initializing headless browser...")

    scraped_context = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Step 1: Search Google Scholar
            search_query = f"{prof_name} {college_name} research papers"
            if status_placeholder:
                status_placeholder.markdown(f"`Web Surfer:` Navigating to Google Scholar for '{search_query}'...")
            
            page.goto(f"https://scholar.google.com/scholar?q={search_query}")
            time.sleep(2) # Prevent rate limiting
            
            # Step 2: Extract top result title and snippet
            # Scholar results are usually in elements with class 'gs_ri'
            first_result = page.query_selector('.gs_ri')
            if first_result:
                if status_placeholder:
                    status_placeholder.markdown("`Web Surfer:` Successfully extracted top publication data.")
                
                title_elem = first_result.query_selector('.gs_rt')
                snippet_elem = first_result.query_selector('.gs_rs')
                
                title = title_elem.inner_text() if title_elem else "Unknown Title"
                snippet = snippet_elem.inner_text() if snippet_elem else "No abstract available."
                
                scraped_context = f"Recent Publication: {title}\nAbstract/Snippet: {snippet}"
            else:
                if status_placeholder:
                    status_placeholder.markdown("`Web Surfer:` No recent publications found on Scholar.")
            
            browser.close()
    except Exception as e:
        if status_placeholder:
            status_placeholder.markdown(f"`Error:` Web scraping failed: {str(e)}")

    # Update Memory
    if scraped_context:
        memory[prof_key] = scraped_context
        save_memory(memory)
        
    return scraped_context
