from google import genai
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

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY2")
client = genai.Client(api_key=api_key)

def draft_email(prof_name, prof_interest, student_name, student_academic_year, student_background, student_interest, goal, extra="", scraped_context=""):
    prompt = f"""
You are an academic email assistant. Write a polite, professional email from a student to a professor.

Context:
- Student Name: {student_name}
- Student academic year: {student_academic_year}
- Professor Name: {prof_name}
- Professor Research Interests: {prof_interest}
- Agent Scraped Context (Recent Publication): {scraped_context}
- Intent: {goal}
- Additional Info (optional): {extra if extra else "None"}

Rules for a 10/10 Academic Email:
1. NO GENERIC FLUFF: Do NOT use template phrases like "I have been following your work with great fascination" or "deeply resonated with my growing interest".
2. NO EMPTY ADJECTIVES: Strictly avoid words like "keen interest", "great fascination", "incredibly insightful", "particularly captivated". Be direct and concise.
3. SHOW, DON'T TELL (THE PAPER DISCUSSION): If 'Agent Scraped Context' is provided, do NOT just say "I read your paper and found it insightful". You MUST extract one concrete, technical takeaway or question from the abstract and mention it directly. 
   - Good Example: "I found the idea of using [technique] to study [topic] particularly interesting because it connects [concept A] with [concept B]." 
   - It MUST sound like intellectual curiosity, NOT praise.
4. CONCISE REQUEST: Do not say "I am eager to gain practical research experience and contribute to the field" (everyone says this). Instead, cleanly state your request. 
   - Good Example: "I was wondering if you might be accepting undergraduate interns for the upcoming semester or summer. If so, I would be grateful for an opportunity to contribute to your research."
5. If the intent is NOT about research (e.g., a minor issue), keep it extremely short and focused, ignoring the rules above.
6. Always begin with "Dear Prof. {prof_name}," and end with "Sincerely, \n{student_name}".

Write the email accordingly.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
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


