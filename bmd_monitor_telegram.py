import requests
import json
import os
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# HISTORY LADEN / SPEICHERN
# ---------------------------------------------------------

def load_history():
    if not os.path.exists("history.json"):
        return {
            "pubmed": [],
            "semantic": [],
            "trials": [],
            "news": [],
            "orphanet": []
        }

    with open("history.json", "r") as f:
        history = json.load(f)

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
    url = "https://clinicaltrials.gov/api/query/st
