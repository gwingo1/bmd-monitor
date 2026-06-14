import requests
from datetime import datetime
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
        return json.load(f)


def save_history(history):
    with open("history.json", "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------------------------------------
# TELEGRAM PUSH
# ---------------------------------------------------------

TOKEN = "8731047806:AAF9wgMqNyuDJi--gkC4sWqZfXCBdWre_t8"
CHAT_ID = "798837741"

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
# GOOGLE NEWS RSS
# ---------------------------------------------------------

def search_medical_news():
    url = "https://news.google.com/rss/search?q=Becker+muscular+dystrophy+BMD+Dystrophinopathy&hl=en-US&gl=US&ceid=US:en"

    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "xml")

        results = []
        for item in soup.find_all("item"):
            title = item.title.get_text(strip=True)
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

        for section in soup.find_all(["p", "h2", "h3"]):
            text = section.get_text(strip=True)
            if not text:
                continue

            t = text.lower()
            if any(k in t for k in ["becker", "dystrophin", "muscular", "x-linked"]):
                if 30 < len(text) < 400:
                    results.append(text)

        return results[:5]

    except Exception as e:
        print("Orphanet-Fehler:", e)
        return []


# ---------------------------------------------------------
# NEUE EINTRÄGE ERKENNEN
# ---------------------------------------------------------

def detect_new_items(old_list, new_list):
    return [item for item in new_list if item not in old_list]


# ---------------------------------------------------------
# ZUSAMMENFASSUNG
# ---------------------------------------------------------

def summarize_results(pubmed, semantic, trials, news, orphanet):
    message = "🧬 *Neue Entwicklungen seit dem letzten Lauf:*\n\n"

    message += "🧬 PubMed:\n" + ("\n".join(f"- {p}" for p in pubmed) if pubmed else "- Keine neuen Studien.") + "\n\n"
    message += "📘 Semantic Scholar:\n" + ("\n".join(f"- {s}" for s in semantic) if semantic else "- Keine neuen Paper.") + "\n\n"
    message += "🧪 ClinicalTrials:\n" + ("\n".join(f"- {t}" for t in trials) if trials else "- Keine neuen Trials.") + "\n\n"
    message += "📰 News:\n" + ("\n".join(f"- {n}" for n in news) if news else "- Keine neuen Nachrichten.") + "\n\n"
    message += "📚 Orphanet:\n" + ("\n".join(f"- {o}" for o in orphanet) if orphanet else "- Keine neuen Orphanet-Informationen.") + "\n"

    return message


# ---------------------------------------------------------
# HAUPTFUNKTION
# ---------------------------------------------------------

def run_bmd_monitor():
    history = load_history()

    pubmed = search_pubmed()
    semantic = search_semantic_scholar()
    trials = search_clinicaltrials()
    news = search_medical_news()
    orphanet = search_orphanet()

    new_pubmed = detect_new_items(history["pubmed"], pubmed)
    new_semantic = detect_new_items(history["semantic"], semantic)
    new_trials = detect_new_items(history["trials"], trials)
    new_news = detect_new_items(history["news"], news)
    new_orphanet = detect_new_items(history["orphanet"], orphanet)

    summary = summarize_results(new_pubmed, new_semantic, new_trials, new_news, new_orphanet)
    send_telegram(summary)

    history["pubmed"] = pubmed
    history["semantic"] = semantic
    history["trials"] = trials
    history["news"] = news
    history["orphanet"] = orphanet

    save_history(history)

    print("Telegram-Benachrichtigung gesendet.")


# ---------------------------------------------------------
# SCRIPT STARTEN
# ---------------------------------------------------------

if __name__ == "__main__":
    run_bmd_monitor()
