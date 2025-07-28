import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("nolan-watch-tracker-8bb0aeecdc41.json", scope)
client = gspread.authorize(creds)

print("📄 Listing accessible spreadsheets...")
for spreadsheet in client.openall():
    print("✅", spreadsheet.title)
