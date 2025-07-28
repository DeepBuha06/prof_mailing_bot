import google.generativeai as genai
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from just_backup_data.interaction_logger import plan_followup, log_interaction
import datetime
import streamlit as st

def suggest_optimal_time():
    now = datetime.datetime.now()
    # Schedule for next weekday morning if it's weekend or past 6pm
    if now.weekday() >= 5 or now.hour >= 18:
        next_day = now + datetime.timedelta(days=(7 - now.weekday()) if now.weekday() >= 5 else 1)
        return datetime.datetime.combine(next_day.date(), datetime.time(9, 0))
    elif now.hour < 9:
        return datetime.datetime.combine(now.date(), datetime.time(9, 0))
    else:
        return now  

genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY"]))
model = genai.GenerativeModel("gemini-2.0-flash")

def draft_email(prof_name, prof_interest, student_name, student_academic_year, student_background, student_interest, goal, extra=""):
    prompt = f"""
You are an academic email assistant. Write a polite, professional email from a student to a professor.

Context:
- Student Name: {student_name}
- Student academic year: {student_academic_year}
- Professor Name: {prof_name}
- Intent: {goal}
- Additional Info (optional): {extra if extra else "None"}

Rules:
- If the goal is about a minor issue (like submission mistake or confirmation), keep the email short and focused. Avoid research interests or background info.
- If the goal is about collaboration (like research/project/internship), include a short self-introduction, interests, and a formal request.
- Always begin with "Dear Prof. {prof_name},"
- Use clear and professional language.
- End with a thank you and the student's name.

Write the email accordingly.
"""

    response = model.generate_content(prompt)
    email_text = response.text.strip()

    now = datetime.datetime.now()
    followup = plan_followup(now)

    log_entry = {
        "student_name": student_name,
        "professor_name": prof_name,
        "professor_interest": prof_interest,
        "professor_email": "UNKNOWN",  # fill in from UI
        "goal": goal,
        "extra_note": extra,
        "email_text": email_text,
        "sent_time": now.isoformat(),
        "followup_time": followup.isoformat(),
        "responded": False,
    }
    log_interaction(log_entry)
    return email_text


