import streamlit as st
import json
import re
import urllib.parse
from collections import defaultdict
import requests
from PIL import Image
from io import BytesIO
import certifi
import os

from email_drafter import draft_email
from recommender import retrieve_symantic_recommendations
from scholar_agent import scrape_scholar_list
from evaluator_agent import evaluate_best_paper

FALLBACK_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/en/3/3e/IIT_Delhi_Logo.png"
st.set_page_config(page_title="IIT Faculty Hub", layout="wide")

def proxy_image_url(url: str) -> str:
    if not url:
        return FALLBACK_IMAGE_URL
    return f"https://images.weserv.nl/?url={urllib.parse.quote(url, safe='')}&w=300"

@st.cache_data(show_spinner=False)
def safe_load_image(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=4, verify=certifi.where())
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            return Image.open(BytesIO(response.content))
    except Exception as e:
        print("Image load error:", e)
    return None

@st.cache_data
def load_data():
    all_data = []
    base_dir = os.path.dirname(__file__)

    with open(os.path.join(base_dir, "faculty/iitgn_faculty.json"), "r", encoding="utf-8") as f:
        gn_data = json.load(f)
        for prof in gn_data:
            match = re.search(r'/faculty/([^/]+)', prof.get("profile_url", ""))
            prof["department"] = match.group(1).upper() if match else "UNKNOWN"
            prof["college_name"] = "IIT Gandhinagar"
        all_data.extend(gn_data)
    
    with open(os.path.join(base_dir, "faculty/iitj_faculty.json"), "r", encoding="utf-8") as f:
        j_data = json.load(f)
        for prof in j_data:
            prof["department"] = prof.get("department", "UNKNOWN").strip()
            prof["profile_url"] = prof.get("profile_url", "#")
            prof["college_name"] = "IIT jodhpur"
        all_data.extend(j_data)

    with open(os.path.join(base_dir, "faculty/iitg_faculty.json"), "r", encoding="utf-8") as f:
        g_data = json.load(f)
        for prof in g_data:
            prof["department"] = prof.get("department", "UNKNOWN").strip()
            prof["college_name"] = "IIT Guwahati"
        all_data.extend(g_data)

    with open(os.path.join(base_dir, "faculty/iitr_faculty.json"), "r", encoding="utf-8") as f:
        r_data = json.load(f)
        for prof in r_data:
            prof["department"] = prof.get("department", "UNKNOWN").strip()
            prof["profile_url"] = prof.get("profile_url", "#").replace(" ", "%20")
            prof["college_name"] = "IIT Roorkee"
        all_data.extend(r_data)

    with open(os.path.join(base_dir, "faculty/iitbhu_faculty.json"), "r", encoding="utf-8") as f:
        bhu_data = json.load(f)
        for prof in bhu_data:
            prof["department"] = prof.get("department", "UNKNOWN").strip()
            prof["profile_url"] = prof.get("profile_url", "#")
            prof["college_name"] = "IIT BHU (Varanasi)"
        all_data.extend(bhu_data)

    with open(os.path.join(base_dir, "faculty/iith_faculty.json"), "r", encoding="utf-8") as f:
        h_data = json.load(f)
        for prof in h_data:
            prof["department"] = prof.get("department", "UNKNOWN").strip()
            prof["profile_url"] = prof.get("profile_url", "#")
            prof["college_name"] = "IIT Hyderabad"
        all_data.extend(h_data)

    with open(os.path.join(base_dir, "faculty/iiti_faculty.json"), "r", encoding="utf-8") as f:
        i_data = json.load(f)
        for prof in i_data:
            prof["department"] = prof.get("department", "UNKNOWN").strip()
            prof["profile_url"] = prof.get("profile_url", "#")
            prof["college_name"] = "IIT Indore"
        all_data.extend(i_data)

    with open(os.path.join(base_dir, "faculty/iitd_faculty.json"), "r", encoding="utf-8") as f:
        d_data = json.load(f)
        for prof in d_data:
            prof["department"] = prof.get("department", "UNKNOWN").strip()
            prof["profile_url"] = prof.get("profile_url", "#")
            prof["college_name"] = "IIT delhi"
        all_data.extend(d_data)

    return all_data

# --- LOAD DATA ---
with st.spinner("Loading faculty data..."):
    data = load_data()

# --- INITIALIZE STATE ---
filter_keys = {
    "selected_dept": "All",
    "search_name": "",
    "search_interest": "",
    "search_college": "All",
    "student_name": "",
    "student_background": "",
    "student_interest": "",
    "student_academic_year": "1st Year",
    "top_k_value": 5,
    "suggested_profs": [],
    "use_ai_goal": False,
    "intent_note": "",
    "selected_goal": "Internship",
    "goal": "Internship",
    "extra_note": "",
    "generated_email": None
}
for key, default in filter_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default


# --- 1. SIDEBAR (Persistent Global Settings) ---
with st.sidebar:
    st.header("Your Profile")
    st.caption("Saved persistently for all agents.")
    st.text_input("Your Name*", key="student_name")
    
    academic_years = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "Postgraduate", "PhD"]
    st.selectbox("Academic Year*", academic_years, key="student_academic_year")
    
    st.text_area("Academic Background*", placeholder="CGPA, previous research, technical skills...", key="student_background")
    st.text_input("Research Interests*", key="student_interest")

    st.markdown("---")
    st.header("Directory Filters")
    departments = sorted(set(p.get("department", "UNKNOWN") for p in data if p.get("department")))
    college_options = sorted(set(p.get("college_name", "Unknown") for p in data))
    
    st.selectbox("Select Department", ["All"] + departments, key="selected_dept")
    st.selectbox("Select College", ["All"] + college_options, key="search_college")
    st.text_input("Search by Name", key="search_name")
    st.text_input("Search by Research Interest", key="search_interest")


# --- FILTER LOGIC ---
filtered = [
    p for p in data
    if (st.session_state.selected_dept in ["All", "", None] or (p.get("department", "") or "").strip().lower() == st.session_state.selected_dept.strip().lower())
    and (not st.session_state.search_name or st.session_state.search_name.lower() in (p.get("name", "") or "").strip().lower())
    and (not st.session_state.search_interest or st.session_state.search_interest.lower() in (p.get("research_interests", "") or "").strip().lower())
    and (st.session_state.search_college in ["All", "", None] or (p.get("college_name", "") or "").strip().lower() == st.session_state.search_college.strip().lower())
]


# --- HELPER: RENDER PROFESSOR CARD ---
def render_professor_card(prof):
    prof_name = prof.get('name', 'Unknown')
    prof_email = prof.get('email', 'N/A')
    designation = prof.get('designation', 'N/A')
    department = prof.get('department', 'N/A')
    college = prof.get('college_name', 'N/A')
    
    research_raw = prof.get("research_interests") or "N/A"
    interests = [s.strip(" ●,|") for s in re.split(r"[●•,|]", research_raw) if s.strip()]
    research_html = " &bull; ".join(interests) if interests else "N/A"
    
    encoded_name = urllib.parse.quote(prof_name)
    fallback_img = f"https://ui-avatars.com/api/?name={encoded_name}&background=333333&color=ffffff&rounded=true&size=200"
    image_url = proxy_image_url(prof.get("photo", "")) if prof.get("photo") else fallback_img
    
    website_html = f"<a href='{prof.get('website')}' target='_blank' style='color: #0d6efd; text-decoration: none; margin-left: 15px; font-weight: 500;'>🌐 Website</a>" if prof.get("website") else ""
    
    html_card = f"""
<div style="border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid rgba(128,128,128,0.2); background-color: rgba(128,128,128,0.05); display: flex; gap: 20px;">
<div style="flex-shrink: 0; display: flex; flex-direction: column; align-items: center;">
<img src="{image_url}" onerror="this.onerror=null; this.src='{fallback_img}';" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 2px solid rgba(128,128,128,0.2);">
</div>
<div style="flex-grow: 1;">
<h3 style="margin: 0 0 8px 0; font-size: 22px;">{prof_name}</h3>
<div style="margin-bottom: 12px;">
<span style="background: rgba(128,128,128,0.2); padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600;">{designation}</span>
<span style="border: 1px solid rgba(128,128,128,0.4); padding: 3px 11px; border-radius: 20px; font-size: 13px; font-weight: 600; margin-left: 8px;">{department}</span>
</div>
<p style="margin: 0 0 8px 0; font-size: 14px;"><strong>College:</strong> {college} &nbsp;|&nbsp; <strong>Email:</strong> <a href="mailto:{prof_email}" style="color: #0d6efd; text-decoration: none;">{prof_email}</a></p>
<div style="margin-top: 12px; background: rgba(128,128,128,0.1); padding: 12px; border-radius: 8px; border-left: 3px solid rgba(128,128,128,0.5);">
<p style="margin: 0 0 4px 0; font-size: 13px; font-weight: 700; text-transform: uppercase;">Research Interests</p>
<p style="margin: 0; font-size: 14px; line-height: 1.5;">{research_html}</p>
</div>
<div style="margin-top: 16px; display: flex; align-items: center;">
<a href="{prof.get('profile_url', '#')}" target="_blank" style="background: rgba(128,128,128,0.2); padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; color: inherit;">View Full Profile</a>
{website_html}
</div>
</div>
</div>
"""
    st.markdown(html_card, unsafe_allow_html=True)

    if prof.get("selected_publications"):
        with st.expander("Selected Publications (Local Data)"):
            pubs = prof["selected_publications"]
            if isinstance(pubs, list):
                for pub in pubs:
                    st.markdown(f"- {pub}")
            else:
                st.markdown(pubs)


# --- 2. MAIN CONTENT (Tabs) ---
st.title("IIT Faculty Hub")
st.markdown("Discover professors, run semantic matching, and autonomously draft highly-tailored academic emails.")

tab1, tab2, tab3 = st.tabs(["Faculty Directory", "AI Matchmaker", "Agentic Email Studio"])

# --- TAB 1: FACULTY DIRECTORY ---
with tab1:
    st.markdown("### Browse Faculty")
    if not filtered:
        st.warning("No matching faculty found based on sidebar filters.")
    else:
        total_results = len(filtered)
        page_size = 20
        total_pages = max(1, (total_results - 1) // page_size + 1)
        
        st.markdown(f"**Found {total_results} matching faculty**")
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page_number = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
        else:
            page_number = 1
            
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size
        paged_filtered = filtered[start_idx:end_idx]
        
        grouped = defaultdict(list)
        for prof in paged_filtered:
            grouped[prof["department"]].append(prof)

        for dept, profs in sorted(grouped.items()):
            for prof in profs:
                with st.container():
                    render_professor_card(prof)


# --- TAB 2: AI MATCHMAKER ---
with tab2:
    st.markdown("### Semantic AI Matchmaker")
    st.caption("Search our Vector Database to find professors whose research mathematically aligns with your background.")
    
    st.session_state.top_k_value = st.number_input("Number of Suggestions", min_value=1, max_value=20, value=st.session_state.top_k_value, step=1)
    
    if st.button("Find My Best Matches"):
        if not (st.session_state.student_background and st.session_state.student_interest):
            st.error("Please fill out your 'Academic Background' and 'Research Interests' in the sidebar first.")
        else:
            with st.spinner("Querying ChromaDB Vector Store..."):
                suggested_names = retrieve_symantic_recommendations(
                    query=f"{st.session_state.student_background} {st.session_state.student_interest}",
                    top_k=st.session_state.top_k_value,
                    college_filter=st.session_state.search_college,
                    dept_filter=st.session_state.selected_dept
                )
                if not suggested_names:
                    st.warning("No suggestions found.")
                else:
                    st.session_state["suggested_profs"] = suggested_names
                    st.success("Matches found!")
                    
    if st.session_state["suggested_profs"]:
        st.markdown("---")
        st.markdown("### Top AI Matches")
        if st.button("Clear Matches"):
            st.session_state["suggested_profs"] = []
            st.rerun()
            
        for prof in st.session_state["suggested_profs"]:
            render_professor_card(prof)


# --- TAB 3: AGENTIC EMAIL STUDIO ---
with tab3:
    st.markdown("### Agentic Email Studio")
    st.caption("Deploy AI agents to fetch recent publications, mathematically evaluate the best fit, and draft a hyper-tailored email.")
    
    # 1. Target Selection
    st.markdown("#### 1. Select Target Professor")
    
    # Options: All filtered, or just AI matches? Let's use all filtered for flexibility.
    if not filtered:
        st.warning("No professors match your sidebar filters.")
    else:
        prof_names = [p["name"] for p in filtered]
        selected_prof_name = st.selectbox("Professor Name", options=prof_names, index=0)
        selected_prof = next((p for p in filtered if p["name"] == selected_prof_name), None)

        if selected_prof:
            st.markdown("---")
            st.markdown("#### 2. Define Intent")
            
            use_ai_goal = st.checkbox("Let AI detect my intent from a short note", value=st.session_state.use_ai_goal)
            if use_ai_goal:
                goal = "AI_DETECT"
                intent_note = st.text_area("Describe your intent (AI will detect goal)*", value=st.session_state.intent_note)
            else:
                goals = ["Internship", "Research guidance", "Project collaboration", "Clarify a doubt", "Request a meeting", "Thank you / appreciation", "Personal/emergency concern", "Other"]
                goal_idx = goals.index(st.session_state.selected_goal) if st.session_state.selected_goal in goals else 0
                selected_goal = st.selectbox("Choose Purpose*", goals, index=goal_idx)
                
                if selected_goal == "Other":
                    goal = st.text_input("Describe your goal:", value=st.session_state.goal)
                else:
                    goal = selected_goal
                intent_note = ""

            extra_note = st.text_area("Additional message (optional)", value=st.session_state.extra_note)
            
            st.markdown("---")
            st.markdown("#### 3. Agentic Configuration & Launchpad")
            
            # Manual Paper Override UI
            st.write("**Manual Override (Optional)**")
            cache_key = f"papers_{selected_prof_name}"
            if cache_key not in st.session_state:
                st.session_state[cache_key] = []
                
            col_a, col_b = st.columns([1, 2])
            with col_a:
                if st.button("Fetch Papers (Web Surfer Only)"):
                    with st.spinner("Fetching papers..."):
                        papers = scrape_scholar_list(selected_prof['name'], selected_prof.get('college_name', ''))
                        st.session_state[cache_key] = papers
            
            with col_b:
                papers_list = st.session_state.get(cache_key, [])
                paper_options = ["None (Do not mention any specific paper)"]
                if papers_list:
                    paper_options.extend([p["title"] for p in papers_list])
                    
                selected_paper_title = st.selectbox("Manual Selection:", paper_options)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Launch Buttons
            col1, col2 = st.columns(2)
            with col1:
                manual_btn = st.button("Generate Draft (Manual Paper)", use_container_width=True)
            with col2:
                auto_btn = st.button("Run Fully Autonomous Agent", type="primary", use_container_width=True)

            if manual_btn or auto_btn:
                if not (st.session_state.student_name and st.session_state.student_background and st.session_state.student_academic_year and st.session_state.student_interest and (goal or intent_note)):
                    st.error("Please complete your '👤 Your Profile' in the sidebar and define your intent.")
                else:
                    final_goal = intent_note if use_ai_goal else goal
                    
                    with st.status("Agentic Workflow Deploying...", expanded=True) as status:
                        if auto_btn:
                            status.write("`Web Surfer:` Autonomously fetching recent publications from Global Database...")
                            papers = scrape_scholar_list(selected_prof['name'], selected_prof.get('college_name', ''), status)
                            selected_paper_context = evaluate_best_paper(st.session_state.student_background, st.session_state.student_interest, papers, status)
                        else:
                            selected_paper_context = ""
                            if selected_paper_title != "None (Do not mention any specific paper)":
                                status.write(f"`Web Surfer:` Using manually selected paper: '{selected_paper_title}'")
                                for p in papers_list:
                                    if p["title"] == selected_paper_title:
                                        selected_paper_context = p["context_str"]
                                        break
                                
                        status.write("`Email Drafter:` Crafting contextual email with Gemini 2.5...")

                    email = draft_email(
                        prof_name=selected_prof['name'],
                        prof_interest=selected_prof.get('research_interests', ''),
                        student_name=st.session_state.student_name,
                        student_academic_year=st.session_state.student_academic_year,
                        student_background=st.session_state.student_background,
                        student_interest=st.session_state.student_interest,
                        goal=final_goal,
                        extra=extra_note,
                        scraped_context=selected_paper_context
                    )
                    st.session_state.generated_email = email
                    status.update(label="Agentic Workflow Complete!", state="complete", expanded=False)

            # Display Generated Email natively in the tab
            if st.session_state.generated_email:
                st.markdown("---")
                st.markdown("### Final Output")
                st.markdown("<div style='background-color: rgba(128,128,128,0.1); padding: 20px; border-radius: 10px; border-left: 4px solid #0d6efd;'>", unsafe_allow_html=True)
                st.markdown(st.session_state.generated_email)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Send Buttons
                prof_email = selected_prof.get('email', 'N/A')
                subject = f"Inquiry from {st.session_state.student_name}"
                safe_body = st.session_state.generated_email if len(st.session_state.generated_email) < 1800 else st.session_state.generated_email[:1800] + "\n\n[Trimmed for URL limits]"
                
                encoded_subject = urllib.parse.quote(subject)
                encoded_body = urllib.parse.quote(safe_body)
                mailto_link = f"mailto:{prof_email}?subject={encoded_subject}&body={encoded_body}"
                gmail_link = f"https://mail.google.com/mail/?view=cm&fs=1&to={prof_email}&su={encoded_subject}&body={encoded_body}"

                st.markdown("<br>", unsafe_allow_html=True)
                col_btn1, col_btn2, _ = st.columns([1, 1, 3])
                with col_btn1:
                    st.markdown(f'<a href="{mailto_link}" style="text-decoration: none;"><div style="background-color: #0d6efd; color: white; padding: 10px; text-align: center; border-radius: 5px; font-weight: bold;">Open Mail App</div></a>', unsafe_allow_html=True)
                with col_btn2:
                    st.markdown(f'<a href="{gmail_link}" target="_blank" style="text-decoration: none;"><div style="background-color: #ea4335; color: white; padding: 10px; text-align: center; border-radius: 5px; font-weight: bold;">Open in Gmail</div></a>', unsafe_allow_html=True)
