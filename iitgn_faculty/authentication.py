import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import streamlit as st
def log_email_history(sheet, student_name, prof_name, prof_email, intent, email_text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [timestamp, student_name, prof_name, prof_email, intent, email_text]
    sheet.append_row(row)

def connect_to_sheet(sheet_name: str):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(st.secrets["GOOGLE_SERVICE_ACCOUNT"], scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1  # You can choose specific worksheet here
    return sheet
