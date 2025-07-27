import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import os.path
import datetime
import streamlit as st

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/script.projects",
    "https://www.googleapis.com/auth/script.deployments",
    "https://www.googleapis.com/auth/script.scriptapp"
]


def get_credentials(user_email):
    token_path = f"C:\\Users\\deep\\summer siege\\iitgn_faculty\\tokens\\token_{user_email}.json"
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(st.secrets["CLIENT_SECRET_JSON"], SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    return creds


def send_email(creds, to_email, subject, message_text):
    service = build('gmail', 'v1', credentials=creds)
    message = MIMEText(message_text)
    message['to'] = to_email
    message['subject'] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message_body = {'raw': raw}

    try:
        sent = service.users().messages().send(userId='me', body=message_body).execute()
        print(f"Email sent to {to_email}. Message ID: {sent['id']}")
        thread_id = sent['threadId']
        return thread_id
    except Exception as e:
        print(f"Failed to send email: {e}")
        return None


def log_email_to_sheet(client, student_name, prof_name, prof_email, intent, email_text, thread_id, creds):
    sheet_title = f"{student_name} Outreach History"
    sheets_service = build("sheets", "v4", credentials=creds)

    spreadsheet_created = False

    try:
        spreadsheet = client.open(sheet_title)
        spreadsheet_id = spreadsheet.id
    except gspread.SpreadsheetNotFound:
        spreadsheet_data = sheets_service.spreadsheets().create(
            body={"properties": {"title": sheet_title}}
        ).execute()
        spreadsheet_id = spreadsheet_data["spreadsheetId"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        spreadsheet_created = True

    if spreadsheet_created:
        sheet = spreadsheet.sheet1
        sheet.append_row(["Timestamp", "Student", "Professor", "Email", "Intent", "Email Text", "Reply Status", "Thread ID"])
    else:
        sheet = spreadsheet.sheet1

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reply_status = "Awaiting Reply"
    row = [timestamp, student_name, prof_name, prof_email, intent, email_text, reply_status, thread_id]
    sheet.append_row(row)

    print(f"📬 Logged to sheet: {spreadsheet.url}")
    print(f"📎 Spreadsheet link: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    
    return spreadsheet_id


def attach_apps_script(creds, spreadsheet_id):
    script_service = build('script', 'v1', credentials=creds)

    try:
        project = script_service.projects().create(
            body={
                "title": "Reply Checker Script",
                "parentId": spreadsheet_id
            }
        ).execute()

        script_id = project['scriptId']
        print(f"Created Apps Script project: {script_id}")

        script_code = '''function checkRepliesAndUpdateSheet() {
  const SHEET_NAME = "Sheet1";

  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    if (!ss) {
      throw new Error("No active spreadsheet. Open the sheet and run this script from Apps Script editor.");
    }

    const sheet = ss.getSheetByName(SHEET_NAME);
    if (!sheet) {
      throw new Error(`Sheet named "${SHEET_NAME}" not found.`);
    }

    const data = sheet.getDataRange().getValues();

    for (let i = 1; i < data.length; i++) {
      const status = data[i][6];
      const threadId = data[i][7];

      if (status === "Awaiting Reply" && threadId) {
        try {
          const thread = GmailApp.getThreadById(threadId);
          const messages = thread.getMessages();

          if (messages.length > 1) {
            sheet.getRange(i + 1, 7).setValue("Replied");
            Logger.log(`Updated reply status for row ${i + 1}`);
          } else {
            Logger.log(`Still waiting for reply in row ${i + 1}`);
          }
        } catch (e) {
          Logger.log(`Invalid or expired threadId in row ${i + 1}: ${e}`);
        }
      }
    }

  } catch (err) {
    Logger.log(err.message);
  }
}'''

        manifest = '''{
  "timeZone": "Asia/Kolkata",
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.readonly"
  ]
}'''

        script_service.projects().updateContent(
            scriptId=script_id,
            body={
                "files": [
                    {
                        "name": "Code",
                        "type": "SERVER_JS",
                        "source": script_code
                    },
                    {
                        "name": "appsscript",
                        "type": "JSON",
                        "source": manifest
                    }
                ]
            }
        ).execute()

        print("Script uploaded successfully - manual execution only.")
        return script_id
    
    except Exception as e:
        print(f"Error creating script: {e}")
        return None



def prepare_sheet_and_suggest_best_time(student_name, client, creds):
    import pandas as pd

    sheet_title = f"{student_name} Outreach History"

    try:
        spreadsheet = client.open(sheet_title)
        spreadsheet_id = spreadsheet.id
        sheet = spreadsheet.sheet1
    except gspread.SpreadsheetNotFound:
        sheets_service = build("sheets", "v4", credentials=creds)
        spreadsheet_data = sheets_service.spreadsheets().create(
            body={"properties": {"title": sheet_title}}
        ).execute()
        spreadsheet_id = spreadsheet_data["spreadsheetId"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        sheet = spreadsheet.sheet1
        sheet.append_row(["Timestamp", "Student", "Professor", "Email", "Intent", "Email Text", "Reply Status", "Thread ID"])
        attach_apps_script(creds, spreadsheet_id)
        print(f"🧩 New sheet created and Apps Script attached: {spreadsheet_id}")

    print(f"📄 Sheet ready: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

    rows = sheet.get_all_values()
    if len(rows) <= 1:
        return spreadsheet_id, "Not enough data to suggest best timing."

    import pandas as pd
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
    df = df[df["Reply Status"] == "Replied"]

    if df.empty:
        return spreadsheet_id, "No replies yet to analyze best time."

    df["hour"] = df["Timestamp"].dt.hour
    df["weekday"] = df["Timestamp"].dt.dayofweek  # 0=Mon

    best_hour = df["hour"].mode()[0]
    best_day = df["weekday"].mode()[0]
    day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][best_day]
    suggestion = f"Suggested outreach time: {day_name} around {best_hour}:00 hrs"
    return spreadsheet_id, suggestion


if __name__ == "__main__":
    student_name = input("Enter your name: ").strip()
    prof_name = "Dr. Dummy"
    prof_email = "just.backup.op@gmail.com"
    intent = "Testing"
    email_text = "Hello Professor,\n\nThis is a test outreach email.\n\nBest,\n" + student_name

    user_email = input("Enter your Google email: ").strip()
    creds = get_credentials(user_email)
    client = gspread.authorize(creds)

    thread_id = send_email(creds, prof_email, f"Outreach: {student_name} - {intent}", email_text)

    if thread_id:
        spreadsheet_id = log_email_to_sheet(client, student_name, prof_name, prof_email, intent, email_text, thread_id, creds)
        
        spreadsheet_id, suggestion = prepare_sheet_and_suggest_best_time(student_name, client, creds)
        print(suggestion)

    else:
        print("Email sending failed. Please check your configuration.")