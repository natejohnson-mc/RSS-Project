import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

# === CONFIGURATION ===
TMDB_API_KEY = 'b7bbd8aa9c2da9716e1787de38e56329'
TMDB_ACCESS_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiN2JiZDhhYTljMmRhOTcxNmUxNzg3ZGUzOGU1NjMyOSIsIm5iZiI6MTc1MzY0ODA0NC4zMTUsInN1YiI6IjY4ODY4YmFjYzc0YjMyN2Y1YTM4ZmYwMyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.eW1WZVcCVPyqEgXzmxodjd_9A4nq_Yl3AJPajU1rwuM'
TMDB_USERNAME = 'naterspotaters'
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

def get_user_tmdb_ids():
    headers = {
        'Authorization': f'Bearer {TMDB_ACCESS_TOKEN}'
    }

    # Step 1: Get account ID from /account
    account_resp = requests.get(
        "https://api.themoviedb.org/3/account",
        headers=headers
    ).json()
    
    account_id = account_resp.get("id")
    if not account_id:
        print("0 Failed to get account ID from TMDb.")
        return set(), set()

    # Step 2: Get rated movie IDs
    rated_ids = set()
    page = 1
    while True:
        url = f"https://api.themoviedb.org/3/account/{account_id}/rated/movies"
        res = requests.get(url, headers=headers, params={'page': page}).json()
        results = res.get("results", [])
        print(f"📄 Rated page {page}: {len(results)} items")
        for r in results:
            rated_ids.add(str(r["id"]))
        if page >= res.get("total_pages", 1):
            break
        page += 1

    # Step 3: Get watchlist movie IDs
    watchlist_ids = set()
    page = 1
    while True:
        url = f"https://api.themoviedb.org/3/account/{account_id}/watchlist/movies"
        res = requests.get(url, headers=headers, params={'page': page}).json()
        results = res.get("results", [])
        print(f"📄 Watchlist page {page}: {len(results)} items")
        for r in results:
            watchlist_ids.add(str(r["id"]))
        if page >= res.get("total_pages", 1):
            break
        page += 1

    return rated_ids, watchlist_ids


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
        print("1 Found:", sheet.title)

    # 1 This must be returned for the rest of the script to work
    return client.open(GOOGLE_SHEET_NAME).sheet1

# === EXCLUDE SHORT FILMS ===
def is_short_film(tmdb_id):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/keywords"
    res = requests.get(url, params={'api_key': TMDB_API_KEY}).json()
    keywords = [kw['name'].lower() for kw in res.get('keywords', [])]
    return 'short film' in keywords

# === MAIN LOGIC ===
def update_sheet_with_new_movies():
    # Load sheets
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
    client = gspread.authorize(creds)

    rulebook_sheet = client.open(RULEBOOK_SHEET_NAME).sheet1
    result_sheet = client.open(RESULT_SHEET_NAME).sheet1

    # Load user's rated/watchlist TMDb IDs once
    rated_ids, watchlist_ids = get_user_tmdb_ids()

    rules = rulebook_sheet.get_all_records()
    existing_ids = set(row[2] for row in result_sheet.get_all_values()[1:] if len(row) >= 3)
    new_entries = []

    for rule in rules:
        rule_id = rule['Rule ID'].strip()
        name = rule['Name'].strip()
        role = rule['Role'].strip().lower()  # director or actor
        media_type = rule['Type'].strip().lower()  # Feature Film, TV Show, etc.

        # TMDb person search
        person_resp = requests.get(f"https://api.themoviedb.org/3/search/person", params={
            "api_key": TMDB_API_KEY,
            "query": name
        }).json()

        if not person_resp['results']:
            print(f"⚠️ No TMDb match for name: {name}")
            continue

        person_id = person_resp['results'][0]['id']

        # Get their credits
        credits_resp = requests.get(f"https://api.themoviedb.org/3/person/{person_id}/movie_credits", params={
            "api_key": TMDB_API_KEY
        }).json()

        if role == 'actor':
            matching_credits = credits_resp.get('cast', [])
        elif role == 'director':
            matching_credits = [
                c for c in credits_resp.get('crew', [])
                if c.get('job') == 'Director'
            ]
        else:
            print(f"⚠️ Unsupported role '{role}' in rule {rule_id}")
            continue

        for movie in matching_credits:
            tmdb_id = str(movie['id'])
            title = movie.get('title') or movie.get('name') or '(Untitled)'
            release_date = movie.get('release_date') or movie.get('first_air_date', '')
            media_type_val = 'Feature Film' if movie.get('media_type') == 'movie' or 'title' in movie else 'TV Show'


            if not release_date:
                continue  # skip unreleased or unannounced projects

            # Skip short films
            if is_short_film(tmdb_id):
                print(f"⏩ Skipping short film: {title}")
                continue

            if media_type != "any" and media_type.lower() not in media_type_val.lower():
                continue

            if tmdb_id not in existing_ids:
                already_rated = 1 if tmdb_id in rated_ids else 0
                in_watchlist = 1 if tmdb_id in watchlist_ids else 0

                new_entries.append([
                    title,
                    release_date,
                    tmdb_id,
                    datetime.now().strftime('%Y-%m-%d %H:%M'),
                    rule_id,
                    media_type_val,
                    already_rated,
                    in_watchlist
                ])

                existing_ids.add(tmdb_id)

    if new_entries:
        result_sheet.append_rows(new_entries)
        print(f"1 Added {len(new_entries)} new movie(s) to the sheet.")
    else:
        print("No new matches.")


if __name__ == '__main__':
    update_sheet_with_new_movies()
