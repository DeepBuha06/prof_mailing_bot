import streamlit as st
import json
import re
import urllib.parse
from collections import defaultdict
from streamlit_pills import pills
from email_drafter import draft_email
import requests
from PIL import Image
from io import BytesIO
import certifi
import os
import urllib.parse
from recommender import retrieve_symantic_recommendations


def proxy_image_url(url: str) -> str:
    if not url:
        return FALLBACK_IMAGE_URL
    return f"https://images.weserv.nl/?url={urllib.parse.quote(url, safe='')}&w=300"


FALLBACK_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/en/3/3e/IIT_Delhi_Logo.png"
st.set_page_config(page_title="IIT Faculty Hub", layout="wide")

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

with st.spinner("Loading faculty data..."):
    data = load_data()

st.title("IIT Faculty Hub")
if "suggested_profs" in st.session_state and st.session_state["suggested_profs"]:
    st.markdown("## AI Recommended Matches")
    if st.button("Clear AI Suggestions (Return to Directory)"):
        st.session_state["suggested_profs"] = []
        st.rerun()
    data_to_filter = st.session_state["suggested_profs"]
else:
    st.markdown("## Faculty Directory")
    st.markdown("Draft professional emails to professors for research, doubts, emergencies, or other interactions.")
    data_to_filter = data

filter_keys = {
    "selected_dept": "All",
    "search_name": "",
    "search_interest": "",
    "search_college": "",
    "search_department": "",
    "student_name": "",
    "student_background": "",
    "student_interest": "",
    "student_academic_year": "1st Year",
    "top_k_value": 5,
    "use_ai_goal": False,
    "intent_note": "",
    "selected_goal": "Internship",
    "goal": "Internship",
    "extra_note": "",
}
for key, default in filter_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.header("1. Filter Directory")
    departments = sorted(set(p.get("department", "UNKNOWN") for p in data if p.get("department")))
    st.selectbox("Select Department", ["All"] + departments, key="selected_dept")
    st.text_input("Search by Name", key="search_name").strip()
    college_options = sorted(set(p.get("college_name", "Unknown") for p in data))
    st.selectbox("Select College", ["All"] + college_options, key="search_college")
    st.text_input("Search by Research Interest", key="search_interest").strip()

    st.markdown("---")
    
    st.header("2. AI Matchmaker")
    st.caption("Let AI find the perfect professors for you based on your background.")
    student_background = st.text_area("Academic Background*", placeholder="CGPA, previous research, technical skills...", key="student_background")
    student_interest = st.text_input("Research/Academic Interests*", key="student_interest")
    student_academic_year = st.selectbox("Current Academic Year*", [
        "1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "Postgraduate", "PhD"
    ], key="student_academic_year")
    top_k_value = st.number_input("Number of Suggestions", min_value=1, max_value=20, step=1, key="top_k_value")
    
    if st.button("Generate AI Suggestions"):
        if not (st.session_state.student_background and st.session_state.student_interest and st.session_state.student_academic_year):
            st.error("Please provide background, interests, and year for suggestions.")
        else:
            with st.spinner("Asking Gemini for suggestions..."):
                suggested_names = retrieve_symantic_recommendations(
                    query=f"{st.session_state.student_background} {st.session_state.student_interest}",
                    top_k=st.session_state.top_k_value
                )
                if not suggested_names:
                    st.warning("No suggestions found.")
                else:
                    st.session_state["suggested_profs"] = suggested_names

    st.markdown("---")
    
    st.header("3. Email Generator")
    student_name = st.text_input("Your Name*", key="student_name")
    
    use_ai_goal = st.checkbox("Let AI detect my intent from a short note", key="use_ai_goal")
    if use_ai_goal:
        goal = "AI_DETECT"
        intent_note = st.text_area("Describe your intent (AI will detect goal)*", key="intent_note")
    else:
        selected_goal = st.selectbox("Choose Purpose*", [
            "Internship", "Research guidance", "Project collaboration", "Clarify a doubt",
            "Request a meeting", "Thank you / appreciation", "Personal/emergency concern", "Other"
        ], key="selected_goal")
        goal = st.text_input("If 'Other', describe your goal:", key="goal") if st.session_state.selected_goal == "Other" else st.session_state.selected_goal
        intent_note = ""

    extra_note = st.text_area("Additional message (optional)", key="extra_note")

filtered = [
    p for p in data_to_filter
    if (st.session_state.get("selected_dept") in ["All", "", None] or (p.get("department", "") or "").strip().lower() == st.session_state.get("selected_dept", "").strip().lower())
    and (st.session_state.get("search_name", "") or "").strip().lower() in (p.get("name", "") or "").strip().lower()
    and (st.session_state.get("search_interest", "") or "").strip().lower() in (p.get("research_interests", "") or "").strip().lower()
    and (st.session_state.get("search_college") in ["All", "", None] or (p.get("college_name", "") or "").strip().lower() == st.session_state.get("search_college", "").strip().lower())
]

email = None
selected_prof_name = None

with st.sidebar:
    if not filtered:
        st.info("No professors match current filters.")
    else:
        selected_prof_name = st.selectbox(
            "Choose a Professor to Email",
            options=[prof["name"] for prof in filtered],
            index=0
        )

        if st.button("Generate Draft Email"):
            if not (st.session_state.student_name and st.session_state.student_background and st.session_state.student_academic_year and st.session_state.student_interest and (goal or intent_note)):
                st.error("Please complete your Student Details above.")
            else:
                selected_prof = next((p for p in filtered if p["name"] == selected_prof_name), None)
                if selected_prof:
                    final_goal = intent_note if use_ai_goal else goal
                    email = draft_email(
                        prof_name=selected_prof['name'],
                        prof_interest=selected_prof.get('research_interests', ''),
                        student_name=st.session_state.student_name,
                        student_academic_year=st.session_state.student_academic_year,
                        student_background=st.session_state.student_background,
                        student_interest=st.session_state.student_interest,
                        goal=final_goal,
                        extra=extra_note
                    )
                    with st.expander("View Generated Email", expanded=True):
                        st.markdown(email)

                    prof_email = selected_prof.get('email', 'N/A')
                    subject = f"Inquiry from {st.session_state.student_name}"
                    safe_body = email if len(email) < 1800 else email[:1800] + "\n\n[Trimmed for URL]"
                    encoded_subject = urllib.parse.quote(subject)
                    encoded_body = urllib.parse.quote(safe_body)

                    mailto_link = f"mailto:{prof_email}?subject={encoded_subject}&body={encoded_body}"
                    gmail_link = (
                        "https://accounts.google.com/AccountChooser?"
                        + "continue=" + urllib.parse.quote(
                            f"https://mail.google.com/mail/?view=cm&fs=1&to={prof_email}&su={encoded_subject}&body={encoded_body}"
                        )
                    )

                    st.markdown("### Send Email:")
                    st.markdown(f"""
                        <a href="{mailto_link}">
                            <button style='margin:5px;'>Open in Mail App</button>
                        </a>
                        <a href="{gmail_link}" target="_blank">
                            <button style='margin:5px;'>Open in Gmail</button>
                        </a>
                    """, unsafe_allow_html=True)


if True:
    if not filtered:
        st.warning("No matching faculty found.")
    else:
        total_results = len(filtered)
        page_size = 20
        total_pages = max(1, (total_results - 1) // page_size + 1)
        
        st.markdown(f"### Found {total_results} matching faculty")
        
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
                    prof_name = prof.get('name', 'Unknown')
                    prof_email = prof.get('email', 'N/A')
                    designation = prof.get('designation', 'N/A')
                    department = prof.get('department', 'N/A')
                    college = prof.get('college_name', 'N/A')
                    
                    # Formatting research interests cleanly
                    research_raw = prof.get("research_interests") or "N/A"
                    interests = [s.strip(" ●,|") for s in re.split(r"[●•,|]", research_raw) if s.strip()]
                    research_html = " &bull; ".join(interests) if interests else "N/A"
                    
                    # Formatting image and Instagram-style fallback
                    encoded_name = urllib.parse.quote(prof_name)
                    # Use a subtle grayish background with white text for the avatar so it looks professional in any theme
                    fallback_img = f"https://ui-avatars.com/api/?name={encoded_name}&background=333333&color=ffffff&rounded=true&size=200"
                    image_url = proxy_image_url(prof.get("photo", "")) if prof.get("photo") else fallback_img
                    
                    website_html = f"<a href='{prof.get('website')}' target='_blank' style='color: #0d6efd; text-decoration: none; margin-left: 15px; font-weight: 500;'>🌐 Website</a>" if prof.get("website") else ""
                    
                    # UNINDENTED HTML TO PREVENT STREAMLIT FROM RENDERING AS CODE BLOCK
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
                        with st.expander("Selected Publications"):
                            pubs = prof["selected_publications"]
                            if isinstance(pubs, list):
                                for pub in pubs:
                                    st.markdown(f"- {pub}")
                            else:
                                st.markdown(pubs)

                    if prof["name"] == selected_prof_name and email:
                        subject = f"Inquiry from {student_name}"
                        safe_body = email if len(email) < 1800 else email[:1800] + "\n\n[Trimmed for URL]"
                        encoded_subject = urllib.parse.quote(subject)
                        encoded_body = urllib.parse.quote(safe_body)

                        mailto_link = f"mailto:{prof_email}?subject={encoded_subject}&body={encoded_body}"
                        gmail_link = f"https://mail.google.com/mail/?view=cm&fs=1&to={prof_email}&su={encoded_subject}&body={encoded_body}"

                        st.markdown(f"""
<a href="{mailto_link}">
<button style='margin:5px;'>Open in Mail App</button>
</a>
<a href="{gmail_link}" target="_blank">
<button style='margin:5px;'>Open in Gmail</button>
</a>
                        """, unsafe_allow_html=True)
