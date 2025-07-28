import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

# === CONFIGURATION ===
TMDB_API_KEY = 'b7bbd8aa9c2da9716e1787de38e56329'
GOOGLE_SHEET_NAME = 'Nolan Watch Tracker'
GOOGLE_CREDS_FILE = 'nolan-watch-tracker-8bb0aeecdc41.json'  # JSON from service account
RULEBOOK_SHEET_NAME = 'Rulebook'
RESULT_SHEET_NAME = 'Nolan Watch Tracker'  # same sheet as before, or new if you prefer

# === TMDB HELPER ===
def get_nolan_directed_movies():
    nolan_id = 525  # Christopher Nolan's TMDb person ID
    url = f"https://api.themoviedb.org/3/person/{nolan_id}/movie_credits?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    # Filter for movies where he's the director and already released
    directed_movies = [
        {
            'title': m['title'],
            'release_date': m.get('release_date', ''),
            'id': m['id']
        }
        for m in data.get('crew', [])
        if m['job'] == 'Director' and m.get('release_date')
    ]
    return directed_movies

# === GOOGLE SHEETS SETUP ===
def get_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
    client = gspread.authorize(creds)

    # Optional debug (you can delete this part)
    print("📄 Listing accessible spreadsheets...")
    for sheet in client.openall():
        print("✅ Found:", sheet.title)

    # ✅ This must be returned for the rest of the script to work
    return client.open(GOOGLE_SHEET_NAME).sheet1


# === MAIN LOGIC ===
def update_sheet_with_new_movies():
    sheet = get_sheet()
    existing_ids = set(row[2] for row in sheet.get_all_values()[1:] if len(row) >= 3)

    new_movies = get_nolan_directed_movies()
    new_entries = []

    for movie in new_movies:
        if str(movie['id']) not in existing_ids:
            new_entries.append([
                movie['title'],
                movie['release_date'],
                str(movie['id']),
                datetime.now().strftime('%Y-%m-%d %H:%M'),
                'No'
            ])

    if new_entries:
        sheet.append_rows(new_entries)
        print(f"✅ Added {len(new_entries)} new movie(s) to the sheet.")
    else:
        print("No new movies found.")

if __name__ == '__main__':
    update_sheet_with_new_movies()
