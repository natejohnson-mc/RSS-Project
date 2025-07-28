def get_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
    client = gspread.authorize(creds)

    # 🔍 Debug: list spreadsheets the service account has access to
    print("📄 Listing accessible spreadsheets...")
    for sheet in client.openall():
        print("✅ Found:", sheet.title)

    # 🔁 Then try your target sheet
    return client.open(GOOGLE_SHEET_NAME).sheet1
