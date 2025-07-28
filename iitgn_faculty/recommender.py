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
from langchain_chroma import Chroma  

embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY2")
)
genai.configure(api_key=os.getenv("GEMINI_API_KEY2"))
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

def load_all_faculty_data(folder_path=r"C:\Users\deep\summer siege\iitgn_faculty\faculty"):
    global all_faculty_data
    if all_faculty_data:  # Already loaded
        return all_faculty_data

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


load_all_faculty_data()

df = pd.DataFrame(all_faculty_data)
# print(df.shape)
df = df.drop_duplicates(subset=["name", "department"])

# print(df.shape)

# ax = plt.axes()

# sns.heatmap(df.isnull(), cbar=False, ax=ax)
# plt.title("Missing Values Heatmap")
# plt.xticks(rotation=45, fontsize=6)
# plt.yticks(fontsize=6)
# plt.show()
# def extract_useful_features(df):
#     df["missing_interests"] = df["research_interests"].isnull().astype(int)

#     df["has_website"] = df["website"].notnull().astype(int)

#     df["has_photo"] = df["photo"].notnull().astype(int)

#     df["num_keywords"] = df["research_interests"].apply(
#         lambda x: len(x.split(",")) if pd.notnull(x) else 0
#     )

#     df["profile_url_valid"] = df["profile_url"].apply(
#         lambda x: str(x).startswith("http")
#     ).astype(int)

#     def encode_designation(desig):
#         if not isinstance(desig, str):
#             return -1
#         d = desig.lower()
#         if "assistant" in d:
#             return 0
#         elif "associate" in d:
#             return 1
#         elif "professor" in d:
#             return 2
#         return -1

#     df["designation_level"] = df["designation"].apply(encode_designation)

#     return df
# df = extract_useful_features(df)

# column_of_interest = [
#     "missing_interests",
#     "has_website",
#     "has_photo",
#     "num_keywords",
#     "profile_url_valid",
#     "designation_level"
# ]


# correlation_matrix = df[column_of_interest].corr(method='spearman')

# sns.set_theme(style="white")
# plt.figure(figsize=(8, 10))

# heatmap = sns.heatmap(correlation_matrix, annot=True, fmt=".2f", cmap="coolwarm", cbar_kws={"label": "Spearman Correlation"})
# heatmap.set_title("Correlation Heatmap of Faculty Data", fontdict={"fontsize": 16}, pad=12)
# plt.xticks(rotation=45, fontsize=10)
# plt.yticks(fontsize=10)
# plt.tight_layout()
# plt.show()


print(df.shape)

df["tag_id"], _ = pd.factorize(df["research_interests"])
df["tagged_research_interests"] = df["tag_id"].astype(str) + " " + df["research_interests"].fillna("")
df["tagged_research_interests"] = df["tagged_research_interests"].str.replace(r"\\,", ",", regex=True)

from langchain_core.documents import Document

raw_documents = [
    Document(page_content=text)
    for text in df["tagged_research_interests"].tolist()
]
text_splitter = CharacterTextSplitter(chunk_size=0, chunk_overlap=0, separator="\n")
documents = text_splitter.split_documents(raw_documents)

import tempfile
from langchain_chroma import Chroma
from langchain.vectorstores import Chroma as ChromaBase
import shutil
import streamlit as st

CHROMA_PATH = "./.chroma_index"

@st.cache_resource
def load_vectorstore():
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

db_df = load_vectorstore()


# query = "Sensor networks, Machine learning with sustainibility"
# docs = db_df.similarity_search(query, k=10)

# tag_ids = [int(doc.page_content.split()[0]) for doc in docs]
# data = df[df["tag_id"].isin(tag_ids)]

def retrieve_symantic_recommendations(query: str, top_k: int = 10) -> list[dict]:
    recs = db_df.similarity_search(query, k=top_k * 10)  

    prof_ids = []
    seen = set()

    for doc in recs:
        tag = int(doc.page_content.strip('"').split()[0])
        if tag not in seen:
            prof_ids.append(tag)
            seen.add(tag)
        if len(prof_ids) >= top_k:
            break

    result_df = df[df["tag_id"].isin(prof_ids)]
    result_df = result_df.drop(columns=["tag_id", "tagged_research_interests"], errors="ignore")

    return result_df.to_dict(orient="records")





