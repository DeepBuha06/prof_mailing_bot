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
    st.markdown("## Suggested Professors")
    for prof in st.session_state["suggested_profs"]:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {prof.get('name', 'N/A')}")
                st.markdown(f"College: {prof.get('college_name', 'N/A')}")
                st.markdown(f"Designation: {prof.get('designation', 'N/A')}")
                st.markdown(f"Department: {prof.get('department', 'N/A')}")
                st.markdown(f"Email: `{prof.get('email', 'N/A')}`")

                if prof.get("website"):
                    st.markdown(f"[Website]({prof['website']})")

                research_raw = prof.get("research_interests") or ""
                interests = [s.strip(" ●,|") for s in re.split(r"[●•,|]", research_raw) if s.strip()]
                if interests:
                    st.markdown("Research Interests:")
                    for i in interests:
                        st.markdown(f"- {i}")
                else:
                    st.markdown("Research Interests: N/A")

                st.markdown(f"Academic Background: {prof.get('academic_background', 'N/A')}")
                st.markdown(f"Work Experience: {prof.get('work_experience', 'N/A')}")

                if prof.get("selected_publications"):
                    with st.expander("Selected Publications"):
                        pubs = prof["selected_publications"]
                        if isinstance(pubs, list):
                            for pub in pubs:
                                st.markdown(f"- {pub}")
                        else:
                            st.markdown(pubs)

                st.markdown(f"[🔗 Profile Link]({prof.get('profile_url', '#')})")

            with col2:
                if prof.get("photo"):
                    st.image(proxy_image_url(prof["photo"]), use_container_width=True)
            st.markdown("---")

if "suggested_profs" in st.session_state and st.session_state["suggested_profs"]:
    if st.button("Clear Suggestions"):
        st.session_state["suggested_profs"] = []
        st.success("Suggestions cleared!")

allow_filtering_ui = True

# Determine what data to filter: suggestions or all
if "suggested_profs" in st.session_state and st.session_state["suggested_profs"]:
    data_to_filter = st.session_state["suggested_profs"]
    show_filtered = False  # Don't show full filtered list again
else:
    data_to_filter = data
    show_filtered = True




st.markdown("Draft professional emails to professors for research, doubts, emergencies, or other interactions.")

with st.sidebar:
    view_mode = st.selectbox("🔽 Choose View", ["📧 Email Generator", "🔍 Filter Professors"])

filter_keys = {
    "selected_dept": "All",
    "search_name": "",
    "search_interest": "",
    "search_college": "",
    "search_department": "",
}
for key, default in filter_keys.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    if view_mode == "📧 Email Generator":
        st.header("Your Details")
        student_name = st.text_input("Your Name*", "")
        student_background = st.text_area("Academic Background*", "", placeholder="CGPA(depends), some research you did about the project which you are going to work under certain professor,some background of yours like knowledge of libraries")
        student_interest = st.text_input("Research/Academic Interests*", "")
        student_academic_year = st.selectbox("Current Academic Year*", [
            "1st Year",
            "2nd Year",
            "3rd Year",
            "4th Year",
            "5th Year",
            "Postgraduate",
            "PhD"
        ], index=0)
        st.markdown("---")
        top_k_value = st.number_input("🔍 Number of Suggestions", min_value=1, max_value=20, value=5, step=1)
        if st.button("🔍 Generate Suggestions"):
            if not (student_background and student_interest and student_academic_year):
                st.error("Please provide background, interests, and year for suggestions.")
            else:
                with st.spinner("Asking Gemini for suggestions..."):
                    suggested_names = retrieve_symantic_recommendations(
                        query=f"{student_background} {student_interest}",
                        top_k=top_k_value
                    )
                    if not suggested_names:
                        st.warning("No suggestions found.")
                    else:
                        st.session_state["suggested_profs"] = suggested_names
                        st.experimental_rerun()  

        st.markdown("---")



        filter_mode = st.checkbox("🔍 Show Filters", value=False)
        if filter_mode:
            st.header("🎯 Search Professors")
            departments = sorted(set(p.get("department", "UNKNOWN") for p in data if p.get("department")))
            st.selectbox("Select Department", ["All"] + departments, key="selected_dept")
            st.text_input("Search by Name", key="search_name").strip()
            college_options = sorted(set(p.get("college_name", "Unknown") for p in data))
            st.selectbox("Select College", [""] + college_options, key="search_college")

            st.text_input("Search by Research Interest", key="search_interest").strip()
        st.markdown("---")

        use_ai_goal = st.checkbox("🎯 Let AI detect my intent from a short note")
        if use_ai_goal:
            goal = "AI_DETECT"
            intent_note = st.text_area("Describe your intent (AI will detect goal)*", "")
        else:
            selected_goal = st.selectbox("Choose Purpose*", [
                "Internship",
                "Research guidance",
                "Project collaboration",
                "Clarify a doubt",
                "Request a meeting",
                "Thank you / appreciation",
                "Personal/emergency concern",
                "Other"
            ])
            goal = st.text_input("If 'Other', describe your goal:", "") if selected_goal == "Other" else selected_goal
            intent_note = ""

        extra_note = st.text_area("Additional message (optional)")
    else:
        st.header("🎯 Search Professors")
        departments = sorted(set(p.get("department", "UNKNOWN") for p in data if p.get("department")))
        st.selectbox("Select Department", ["All"] + departments, key="selected_dept")
        st.text_input("Search by Name", key="search_name").strip()
        st.text_input("Search by Research Interest", key="search_interest").strip()

filtered = [
    p for p in data_to_filter
    if (st.session_state.get("selected_dept", "All") == "All" or (p.get("department", "").strip().lower() == st.session_state.get("selected_dept", "").strip().lower()))
    and (st.session_state.get("search_name") or "").strip().lower() in (p.get("name", "") or "").strip().lower()
    and (st.session_state.get("search_interest") or "").strip().lower() in (p.get("research_interests", "") or "").strip().lower()
    and (st.session_state.get("search_college") or "").strip().lower() in (p.get("college_name", "") or "").strip().lower()
]


MAX_PROFS_TO_SHOW = 200
filtered = filtered[:MAX_PROFS_TO_SHOW]

email = None
selected_prof_name = None

if view_mode == "📧 Email Generator":
    with st.sidebar:
        st.markdown("---")
        st.header("✉️ Draft Email")
        if not filtered:
            st.info("No professors to choose from.")
        else:
            selected_prof_name = st.selectbox(
                "Choose a Professor",
                options=[prof["name"] for prof in filtered],
                index=0
            )

            if st.button("Generate Email"):
                if not (student_name and student_background and student_academic_year and student_interest and (goal or intent_note)):
                    st.error("Please complete all required fields.")
                else:
                    selected_prof = next((p for p in filtered if p["name"] == selected_prof_name), None)
                    if selected_prof:
                        final_goal = intent_note if use_ai_goal else goal
                        email = draft_email(
                            prof_name=selected_prof['name'],
                            prof_interest=selected_prof.get('research_interests', ''),
                            student_name=student_name,
                            student_academic_year=student_academic_year,
                            student_background=student_background,
                            student_interest=student_interest,
                            goal=final_goal,
                            extra=extra_note
                        )
                        with st.expander("📧 View Generated Email", expanded=True):
                            st.markdown(email)

                        prof_email = selected_prof.get('email', 'N/A')
                        subject = f"Inquiry from {student_name}"
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


                        st.markdown("### 📤 Send Email:")
                        st.markdown(f"""
                            <a href="{mailto_link}">
                                <button style='margin:5px;'>📨 Open in Mail App</button>
                            </a>
                            <a href="{gmail_link}" target="_blank">
                                <button style='margin:5px;'>📬 Open in Gmail</button>
                            </a>
                        """, unsafe_allow_html=True)


if show_filtered:
    if not filtered:
        st.warning("No matching faculty found.")
    else:
        grouped = defaultdict(list)
        for prof in filtered:
            grouped[prof["department"]].append(prof)

        for dept, profs in sorted(grouped.items()):
            for prof in profs:
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"###{prof.get('name', 'N/A')}")
                        st.markdown(f"College: {prof.get('college_name', 'N/A')}")
                        st.markdown(f"Designation:{prof.get('designation', 'N/A')}")
                        st.markdown(f"Department:{prof.get('department', 'N/A')}")
                        prof_email = prof.get('email', 'N/A')
                        st.markdown(f"Email:`{prof_email}`")
                        if prof.get("website"):
                            st.markdown(f"[Website]({prof['website']})")

                        research_raw = prof.get("research_interests") or ""
                        interests = [s.strip(" ●,|") for s in re.split(r"[●•,|]", research_raw) if s.strip()]
                        if interests:
                            st.markdown("Research Interests:")
                            for i in interests:
                                st.markdown(f"- {i}")
                        else:
                            st.markdown("Research Interests: N/A")

                        st.markdown(f"Academic Background: {prof.get('academic_background', 'N/A')}")
                        st.markdown(f"Work Experience: {prof.get('work_experience', 'N/A')}")

                        if prof.get("selected_publications"):
                            with st.expander("Selected Publications"):
                                pubs = prof["selected_publications"]
                                if isinstance(pubs, list):
                                    for pub in pubs:
                                        st.markdown(f"- {pub}")
                                else:
                                    st.markdown(pubs)

                        st.markdown(f"[🔗 Profile Link]({prof.get('profile_url', '#')})")

                        if view_mode == "📧 Email Generator" and prof["name"] == selected_prof_name and email:
                            subject = f"Inquiry from {student_name}"
                            safe_body = email if len(email) < 1800 else email[:1800] + "\n\n[Trimmed for URL]"
                            encoded_subject = urllib.parse.quote(subject)
                            encoded_body = urllib.parse.quote(safe_body)

                            mailto_link = f"mailto:{prof_email}?subject={encoded_subject}&body={encoded_body}"
                            gmail_link = f"https://mail.google.com/mail/?view=cm&fs=1&to={prof_email}&su={encoded_subject}&body={encoded_body}"

                            st.markdown(f"""
                                <a href="{mailto_link}">
                                    <button style='margin:5px;'>📨 Open in Mail App</button>
                                </a>
                                <a href="{gmail_link}" target="_blank">
                                    <button style='margin:5px;'>📬 Open in Gmail</button>
                                </a>
                            """, unsafe_allow_html=True)
                    with col2:
                        if prof.get("photo"):
                            image_url = proxy_image_url(prof.get("photo", ""))
                            st.image(image_url, use_container_width=True)
