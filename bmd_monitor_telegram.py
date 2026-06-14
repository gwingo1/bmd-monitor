import requests
import json
import os
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# HISTORY LADEN / SPEICHERN
# ---------------------------------------------------------

def load_history():
    # Falls Datei nicht existiert → neue Struktur erzeugen
    if not os.path.exists("history.json"):
        return {
            "pubmed": [],
            "semantic": [],
            "trials": [],
            "news": [],
            "orphanet": []
        }

    # Datei laden
    with open("history.json", "r") as f:
        history = json.load(f)

    # Falls alte Datei ohne "semantic" → hinzufügen
    if "semantic" not in history:
        history["semantic"] = []

    return history


def save_history(history):
    with open("history.json", "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------------------------------------
# TELEGRAM PUSH
# ---------------------------------------------------------

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Fehler beim Senden an Telegram:", e)


# ---------------------------------------------------------
# PUBMED API
# ---------------------------------------------------------

def search_pubmed():
    url = "https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pubmed/"
    queries = [
        '"Becker muscular dystrophy"',
        '"BMD"',
        '"Becker-Kiener"',
        '"Dystrophinopathy"',
        '"gene therapy" AND "dystrophin"'
    ]

    titles = []

    for q in queries:
        try:
            r = requests.get(url, params={"format": "json", "term": q}, timeout=10)
            data = r.json()

            for rec in data.get("records", []):
                title = rec.get("title")
                if title and title not in titles:
                    titles.append(title)

        except:
            continue

    return titles


# ---------------------------------------------------------
# SEMANTIC SCHOLAR API
# ---------------------------------------------------------

def search_semantic_scholar():
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "limit": 20,
        "fields": "title,year"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        results = []
        for paper in data.get("data", []):
            title = paper.get("title")
            year = paper.get("year")
            if title:
                results.append(f"{title} ({year})")

        return results

    except Exception as e:
        print("Semantic Scholar Fehler:", e)
        return []


# ---------------------------------------------------------
# CLINICALTRIALS API
# ---------------------------------------------------------

def search_clinicaltrials():
    url = "https://clinicaltrials.gov/api/query/study_fields"
    params = {
        "expr": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "fields": "BriefTitle,Phase,Status",
        "min_rnk": 1,
        "max_rnk": 50,
        "fmt": "json"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        results = []
        for t in data.get("StudyFieldsResponse", {}).get("StudyFields", []):
            title = t.get("BriefTitle", [""])[0]
            phase = t.get("Phase", [""])[0]
            status = t.get("Status", [""])[0]

            results.append(f"{title} – Phase {phase}, Status: {status}")

        return results

    except:
        return []


# ---------------------------------------------------------
# GOOGLE NEWS RSS (HTML Parser – funktioniert überall)
# ---------------------------------------------------------

def search_medical_news():
    url = "https://news.google.com/rss/search?q=Becker+muscular+dystrophy+BMD+Dystrophinopathy&hl=en-US&gl=US&ceid=US:en"

    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")  # HTML statt XML

        results = []
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            if 10 < len(title) < 200:
                results.append(title)

        return list(dict.fromkeys(results))[:10]

    except Exception as e:
        print("News-Fehler:", e)
        return []


# ---------------------------------------------------------
# ORPHANET SCRAPER
# ---------------------------------------------------------

def search_orphanet():
    url = "https://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=EN&Expert=988"

    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        results = []

        for section in soup.find_all(["p", "
