import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY2")
client = genai.Client(api_key=api_key)

def evaluate_best_paper(student_background, student_interest, papers_list, status_placeholder=None):
    """
    Evaluator Agent: Reads a list of papers and autonomously selects the one 
    that best matches the student's background and research interests.
    """
    if not papers_list:
        return None
        
    if status_placeholder:
        status_placeholder.write("`Evaluator Agent:` Booting up semantic evaluation engine...")

    papers_text = ""
    for i, p in enumerate(papers_list):
        papers_text += f"--- Paper {i+1} ---\n{p['context_str']}\n\n"

    prompt = f"""
You are an expert academic matching agent. Your job is to select the single best research paper for a student to reference in an internship cold email.

Student Background: {student_background}
Student Interests: {student_interest}

Available Papers:
{papers_text}

Task: Read the abstracts of the available papers. Compare them against the student's background and interests. 
Identify the ONE paper that provides the strongest mutual intersection. If none are a perfect match, pick the most relevant one.

You must return a raw JSON object (without markdown formatting blocks like ```json) with exactly these three keys:
- "selected_title": The exact title of the paper you chose.
- "reasoning": A concise, 1-sentence explanation (written in the first person as the AI) explaining exactly why this paper was the mathematically optimal semantic fit for the student.
- "selected_index": The integer index (1-based) of the paper you chose.
"""

    if status_placeholder:
        status_placeholder.write("`Evaluator Agent:` Cross-referencing papers against student vector profile...")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        
        result = json.loads(response.text.strip())
        
        if status_placeholder:
            status_placeholder.write(f"`Evaluator Agent:` Decision reached -> Selected '{result.get('selected_title')}'")
            status_placeholder.write(f"`Agent Reasoning:` {result.get('reasoning')}")
            
        # Find the selected paper context to return
        idx = result.get("selected_index", 1) - 1
        if 0 <= idx < len(papers_list):
            return papers_list[idx]["context_str"]
        else:
            # Fallback to the first paper if index is weird
            return papers_list[0]["context_str"]

    except Exception as e:
        if status_placeholder:
            status_placeholder.write(f"`Evaluator Agent Error:` Failed to process semantic evaluation: {str(e)}")
        # Fallback to the most recent paper
        return papers_list[0]["context_str"]
