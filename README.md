# **[Professor Mailing Bot](https://prof-mailing-bot.streamlit.app/)**

An intelligent faculty outreach system that enables students to discover and contact professors across multiple IITs using semantic search, AI-powered scraping, and automated email logging.

---

## Features

### Semantic Faculty Recommender

* Search for professors by describing your research interests in natural language
* Chroma vector store for fast similarity search and retrieval
* Uses **cosine similarity** to rank professors by how closely their research interests align with the query
* Filters and deduplicates results based on research interest clusters
* Supports professors from multiple IITs (e.g., IITGN, IITJ, IITR, IITBHU, IITG, IITI, IITD, IITH)

### Scraping Pipeline: Three-Stage Evolution

1. **Basic Scrapy Spider**

   * Initial structured crawling of faculty directories
   * Handles static pages and simple layouts

2. **Playwright Manual Scraping**

   * Used to handle JavaScript-rendered or deeply nested websites
   * Extracted faculty lists with custom selectors 

3. **Playwright + Gemini-AI Assisted Scraping**

   * Integrated Gemini models to automatically detect department and faculty page URLs
   * Structured output generation via JSON
   * Significantly improved scalability and generalization across diverse college websites

### Data Quality Enhancements

* Faculty metadata enriched with inferred college names
* Factorization of research interests into unique tags (`tag_id`)
* Clean fallback defaults for missing fields like profile URL, photo, website
* Duplicate removal based on `(name, department)` key

---

## Technology Stack

* **Python 3.10+**
* **LangChain** + **Google Generative AI** (Gemini)
* **Chroma** for persistent vector storage
* **Playwright** for web scraping (headless browser automation)
* **Streamlit** for frontend interface (not included here)
* **Pandas**, **Seaborn**, **Matplotlib** for analysis
* **LangChain TextSplitter** for document preprocessing

---

## Project Structure

```
prof_mailing_bot/
├── faculty/                     # JSON files per IIT, containing scraped faculty data
├── iitgn_faculty/
│   ├── app.py                   # main file from streamlit front end
│   ├── recommender.py           # Core semantic search logic
|   ├── email_drafter.py         # email drafting agent
│   ├── email_records.py         # (Planned) email sending and tracking
│   └── ...
├── scrapers/
│   ├── spiders/           # Initial Scrapy spider
│       ├── general scrapers/
              ├── main scrapers to scrap any website     # ai based scrapers (using gemeini)
│       └──  college wise scrapers                       # includes mostly codes with general scrapers with some default code 
└── README.md
```

---

## Setup Instructions

**IMPORTANT: consider using Python 3.10 version **

1. **Clone the repository**

```bash
git clone https://github.com/DeepBuha06/prof_mailing_bot.git
cd prof_mailing_bot
```

2. **Set up environment variables**

```bash
make a .env file in root folder and add gemini api key there.
#if working with email_records.py consider adding client_secret.json in iitgn_faculty
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run vectorstore initialization**
   This will embed faculty profiles and build a Chroma index.

```python
from iitgn_faculty.recommender import load_vectorstore
load_vectorstore()
```

5. **Use the recommender**

```python
from iitgn_faculty.recommender import retrieve_symantic_recommendations
retrieve_symantic_recommendations("Sensor networks and sustainable ML")
```

---

## Future Roadmap

* Scheduled email delivery via Gmail API
* Individualized outreach logging in Google Sheets
* Advanced filters for search results (e.g., designation, college, publication count)
* addition of reserch interest of professors from their personal websites

---
