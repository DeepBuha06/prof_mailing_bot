import json
import os
import requests
import urllib.parse

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

def scrape_scholar_list(prof_name, college_name, status_placeholder=None):
    """
    Uses the Crossref API to robustly fetch the professor's latest 5 papers.
    Avoids Google Scholar CAPTCHA blocks.
    """
    memory = load_memory()
    prof_key = f"{prof_name} - {college_name}_list"
    
    if prof_key in memory:
        if status_placeholder:
            status_placeholder.write("`Agent Memory:` Found cached context for this professor.")
        return memory[prof_key]

    if status_placeholder:
        status_placeholder.write("`Agent Memory:` No cache found. Connecting to Global Publication Database...")

    scraped_papers = []
    try:
        query_general = urllib.parse.quote(f"{prof_name} {college_name}")
        url = f"https://api.crossref.org/works?query={query_general}&select=title,abstract,author,published-print&rows=5"
        
        if status_placeholder:
            status_placeholder.write(f"`Web Surfer:` Fetching recent publications for {prof_name} via CrossRef API...")
            
        headers = {'User-Agent': 'mailto:deep.buha@iitgn.ac.in (IITGN Scholar Agent)'}
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            items = data.get('message', {}).get('items', [])
            
            if items:
                if status_placeholder:
                    status_placeholder.write(f"`Web Surfer:` Successfully extracted {len(items)} publications.")
                
                for item in items:
                    title = item.get('title', ['Unknown Title'])[0]
                    context_str = f"Recent Publication Title: {title}"
                    
                    abstract = item.get('abstract')
                    if abstract:
                        abstract_clean = abstract.replace("<jats:p>", "").replace("</jats:p>", "").replace("<jats:title>", "").replace("</jats:title>", "")
                        context_str += f"\nAbstract/Snippet: {abstract_clean[:500]}..."
                        
                    scraped_papers.append({
                        "title": title,
                        "context_str": context_str
                    })
            else:
                if status_placeholder:
                    status_placeholder.write("`Web Surfer:` No recent publications found.")
        else:
            if status_placeholder:
                status_placeholder.write(f"`Web Surfer:` API returned status {r.status_code}")
                
    except Exception as e:
        if status_placeholder:
            status_placeholder.write(f"`Error:` Web scraping failed: {str(e)}")

    if scraped_papers:
        memory[prof_key] = scraped_papers
        save_memory(memory)
        
    return scraped_papers
