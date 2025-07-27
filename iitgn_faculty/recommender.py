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

# Initialize API and models
try:
    api_key = st.secrets.get("GEMINI_API_KEY2", os.getenv("GEMINI_API_KEY2"))
    embedding_model = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    genai.configure(api_key=api_key)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    st.error(f"Error initializing API: {e}")
    st.stop()

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
                        if not isinstance(prof, dict):
                            continue
                        
                        # Ensure all required fields exist with defaults
                        prof["college_name"] = college_name
                        prof["profile_url"] = prof.get("profile_url", "#")
                        prof["photo"] = prof.get("photo", "")
                        prof["academic_background"] = prof.get("academic_background", "")
                        prof["work_experience"] = prof.get("work_experience", "")
                        prof["selected_publications"] = prof.get("selected_publications", "")
                        prof["research_interests"] = prof.get("research_interests", "")
                        prof["name"] = prof.get("name", "")
                        prof["department"] = prof.get("department", "")

                        all_faculty_data.append(prof)

                except Exception as e:
                    print(f"Failed to load {file}: {e}")

    return all_faculty_data

# Load data
load_all_faculty_data()

# Create DataFrame with proper error handling
try:
    df = pd.DataFrame(all_faculty_data)
    
    # If no data was loaded, create a dataframe with the expected columns
    if df.empty:
        df = pd.DataFrame(columns=["name", "department", "research_interests", "college_name", 
                                 "profile_url", "photo", "academic_background", 
                                 "work_experience", "selected_publications"])
    
    # Ensure required columns exist
    required_columns = ["name", "department", "research_interests", "college_name"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = ""
    
    # Clean and fill missing values
    df["research_interests"] = df["research_interests"].fillna("").astype(str)
    df["name"] = df["name"].fillna("").astype(str)
    df["department"] = df["department"].fillna("").astype(str)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=["name", "department"], keep='first')
    
    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")
    
except Exception as e:
    print(f"Error creating DataFrame: {e}")
    # Create empty DataFrame with required columns as fallback
    df = pd.DataFrame(columns=["name", "department", "research_interests", "college_name"])

# Process research interests for vectorization
try:
    # Create cleaned interests column
    df["cleaned_interests"] = df["research_interests"].fillna("").replace("", "no research interests specified")
    
    # Create tag IDs
    df["tag_id"], unique_interests = pd.factorize(df["cleaned_interests"])
    
    # Create tagged research interests for embedding
    df["tagged_research_interests"] = df["tag_id"].astype(str) + " " + df["cleaned_interests"]
    df["tagged_research_interests"] = df["tagged_research_interests"].str.replace(r"\\,", ",", regex=True)
    
    print(f"Processed research interests. Unique interests: {len(unique_interests)}")
    
except Exception as e:
    print(f"Error processing research interests: {e}")
    # Create fallback columns
    df["cleaned_interests"] = "no research interests specified"
    df["tag_id"] = 0
    df["tagged_research_interests"] = "0 no research interests specified"

# Create documents for vectorization
from langchain_core.documents import Document

try:
    raw_documents = [
        Document(page_content=text)
        for text in df["tagged_research_interests"].tolist()
        if text and isinstance(text, str)
    ]
    
    if not raw_documents:
        # Create a dummy document if no valid documents exist
        raw_documents = [Document(page_content="0 no research interests specified")]
    
    text_splitter = CharacterTextSplitter(chunk_size=1000000, chunk_overlap=0, separator="\n")
    documents = text_splitter.split_documents(raw_documents)
    
    print(f"Created {len(documents)} documents for vectorization")
    
except Exception as e:
    print(f"Error creating documents: {e}")
    documents = [Document(page_content="0 no research interests specified")]

# Vectorstore setup
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
        print(f"Error loading vectorstore: {e}")
        # Return None or create a minimal vectorstore
        return None

# Load vectorstore
db_df = load_vectorstore()

def retrieve_symantic_recommendations(query: str, top_k: int = 10) -> list[dict]:
    """
    Retrieve semantic recommendations based on query
    """
    try:
        if db_df is None:
            print("Vectorstore not available")
            return []
        
        # Search for similar documents
        recs = db_df.similarity_search(query, k=min(top_k * 10, len(documents)))
        
        if not recs:
            print("No recommendations found")
            return []
        
        prof_ids = []
        seen = set()
        
        for doc in recs:
            try:
                # Extract tag ID from document content
                content = doc.page_content.strip('"')
                if not content:
                    continue
                    
                tag_str = content.split()[0]
                if not tag_str.isdigit():
                    continue
                    
                tag = int(tag_str)
                if tag not in seen and tag in df["tag_id"].values:
                    prof_ids.append(tag)
                    seen.add(tag)
                    
                if len(prof_ids) >= top_k:
                    break
                    
            except (ValueError, IndexError) as e:
                print(f"Error processing document: {e}")
                continue
        
        if not prof_ids:
            print("No valid professor IDs found")
            return []
        
        # Filter DataFrame and return results
        result_df = df[df["tag_id"].isin(prof_ids)].copy()
        
        # Remove internal columns
        columns_to_drop = ["tag_id", "tagged_research_interests", "cleaned_interests"]
        result_df = result_df.drop(columns=[col for col in columns_to_drop if col in result_df.columns])
        
        return result_df.to_dict(orient="records")
        
    except Exception as e:
        print(f"Error in retrieve_symantic_recommendations: {e}")
        return []

# Test the function (optional)
if __name__ == "__main__":
    test_query = "machine learning"
    results = retrieve_symantic_recommendations(test_query, top_k=5)
    print(f"Test query '{test_query}' returned {len(results)} results")