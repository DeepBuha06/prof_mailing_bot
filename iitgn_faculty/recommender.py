import pandas as pd
import os
import json
import google.generativeai as genai
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import GoogleGenerativeAI

import streamlit as st

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv(st.secrets["GEMINI_API_KEY2"])
)
genai.configure(api_key=os.getenv(st.secrets["GEMINI_API_KEY2"]))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

all_faculty_data = []

import re

def infer_college_name(filename: str) -> str:
    name_map = {
        "iitgn": "IIT Gandhinagar",
        "iitj": "IIT Jodhpur",
        "iitg": "IIT Guwahati",
        "iitr": "IIT Roorkee",
        "iitbhu": "IIT BHU (Varanasi)",
        "iith": "IIT Hyderabad",
        "iiti": "IIT Indore",
        "iitd": "IIT Delhi",
    }
    for key, val in name_map.items():
        if key in filename.lower():
            return val
    return "Unknown"

def load_all_faculty_data(folder_path="iitgn_faculty/faculty"):
    global all_faculty_data
    if all_faculty_data:  # Already loaded
        return all_faculty_data

    # Handle missing directory gracefully
    if not os.path.exists(folder_path):
        print(f"[WARN] Faculty data folder not found: {folder_path}")
        return []

    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            full_path = os.path.join(folder_path, file)
            with open(full_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = [data]

                    college_name = infer_college_name(file)
                    for prof in data:
                        prof["college_name"] = college_name
                        prof["profile_url"] = prof.get("profile_url", "#")
                        prof["photo"] = prof.get("photo", "")
                        prof["academic_background"] = prof.get("academic_background", "")
                        prof["work_experience"] = prof.get("work_experience", "")
                        prof["selected_publications"] = prof.get("selected_publications", "")

                    all_faculty_data.extend(data)

                except Exception as e:
                    print(f"Failed to load {file}: {e}")

    return all_faculty_data

# Load faculty data
load_all_faculty_data()

# Create DataFrame
df = pd.DataFrame(all_faculty_data)

# COMPREHENSIVE FIX for research_interests column
def ensure_research_interests_column(df):
    """Ensure research_interests column exists with meaningful defaults"""
    
    if "research_interests" in df.columns:
        # Column exists, just fill NaN values
        df["research_interests"] = df["research_interests"].fillna("General Research")
        print("[INFO] research_interests column found, filled NaN values")
        return df
    
    # Column doesn't exist, try alternatives
    alternative_fields = [
        "research_interest", "interests", "research_areas", 
        "specialization", "research_focus", "expertise", "fields"
    ]
    
    for alt_field in alternative_fields:
        if alt_field in df.columns:
            df["research_interests"] = df[alt_field].fillna("General Research")
            print(f"[INFO] Using '{alt_field}' as research_interests")
            return df
    
    # No alternatives found, create intelligent defaults
    if "department" in df.columns:
        df["research_interests"] = df["department"].apply(
            lambda dept: f"{dept} Research" if pd.notna(dept) and str(dept).strip() != "" else "General Research"
        )
        print("[INFO] Created research_interests based on department")
    else:
        df["research_interests"] = "General Research"
        print("[INFO] Created generic research_interests column")
    
    return df

# Apply the fix
df = ensure_research_interests_column(df)

# Remove duplicates
df = df.drop_duplicates(subset=["name", "department"])

print(f"DataFrame shape: {df.shape}")
print(f"Sample research_interests: {df['research_interests'].head().tolist()}")

# Now safe to proceed with factorization
df["tag_id"], _ = pd.factorize(df["research_interests"])
df["tagged_research_interests"] = df["tag_id"].astype(str) + " " + df["research_interests"].fillna("")
df["tagged_research_interests"] = df["tagged_research_interests"].str.replace(r"\\,", ",", regex=True)

from langchain_core.documents import Document

raw_documents = [
    Document(page_content=text if text.strip() else "General Research")
    for text in df["tagged_research_interests"].tolist()
]
text_splitter = CharacterTextSplitter(chunk_size=1000000, chunk_overlap=0, separator="\n")
documents = text_splitter.split_documents(raw_documents)

import tempfile
from langchain.vectorstores import Chroma as ChromaBase
import shutil

CHROMA_PATH = "./.chroma_index"

@st.cache_resource
def load_vectorstore():
    try:
        if not os.path.exists(CHROMA_PATH):
            os.makedirs(CHROMA_PATH)
            chroma = ChromaBase.from_documents(
                documents=documents,
                embedding=embedding_model,
                persist_directory=CHROMA_PATH
            )
            chroma.persist()
        else:
            chroma = ChromaBase(
                embedding_function=embedding_model,
                persist_directory=CHROMA_PATH
            )
        return chroma
    except Exception as e:
        print(f"[ERROR] Failed to load vectorstore: {e}")
        return None

db_df = load_vectorstore()

def retrieve_symantic_recommendations(query: str, top_k: int = 10) -> list[dict]:
    if db_df is None:
        print("[WARN] Vectorstore not available, returning empty results")
        return []
    
    try:
        recs = db_df.similarity_search(query, k=top_k * 10)  

        prof_ids = []
        seen = set()

        for doc in recs:
            try:
                content = doc.page_content.strip('"')
                if not content:
                    continue
                    
                tag = int(content.split()[0])
                if tag not in seen:
                    prof_ids.append(tag)
                    seen.add(tag)
                if len(prof_ids) >= top_k:
                    break
            except (ValueError, IndexError) as e:
                print(f"[WARN] Could not parse tag from document: {doc.page_content[:50]}...")
                continue

        result_df = df[df["tag_id"].isin(prof_ids)]
        result_df = result_df.drop(columns=["tag_id", "tagged_research_interests"], errors="ignore")

        return result_df.to_dict(orient="records")
    
    except Exception as e:
        print(f"[ERROR] Error in retrieve_symantic_recommendations: {e}")
        return []