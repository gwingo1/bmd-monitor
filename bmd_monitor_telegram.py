import requests
from datetime import datetime

# JSON + Dateisystem für History
import json
import os

# ---------------------------------------------------------
# HISTORY LADEN / SPEICHERN
# ---------------------------------------------------------

# Lädt die gespeicherten Ergebnisse aus history.json
def load_history():
    # Falls Datei noch nicht existiert → leere Struktur zurückgeben
    if not os.path.exists("history.json"):
        return {"pubmed": [], "trials": [], "news": [], "orphanet": []}

    # Datei öffnen und JSON laden
    with open("history.json", "r") as f:
        return json.load(f)

# Speichert die aktualisierte History zurück in die Datei
def save_history(history):
    with open("history.json", "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------------------------------------
# 1) TELEGRAM PUSH
# ---------------------------------------------------------

TOKEN = "8731047806:AAF9wgMqNyuDJi--gkC4sWqZfXCBdWre_t8"
CHAT_ID = "798837741"

# Sendet eine Nachricht an Telegram
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Fehler beim Senden an Telegram:", e)


# ---------------------------------------------------------
# 2) PUBMED API
# ---------------------------------------------------------

# Holt wissenschaftliche Publikationen zu BMD
def search_pubmed():
    url = "https://api.ncbi.nlm.nih.gov/lit/ctxp/v1/pubmed/"
    queries = [
        '"Becker muscular dystrophy"',
        '"BMD"',
        '"Becker-Kiener"',
        '"Dystrophinopathy"',
        '"gene therapy" AND "dystrophin"'
    ]

    results = []
    for q in queries:
        try:
            r = requests.get(url, params={"format": "json", "term": q}, timeout=10)
            data = r.json()
            if "records" in data:
                results.extend(data["records"])
        except:
            continue

    return results


# ---------------------------------------------------------
# 3) CLINICALTRIALS API
# ---------------------------------------------------------

# Holt klinische Studien zu BMD
def search_clinicaltrials():
    url = "https://clinicaltrials.gov/api/query/study_fields"
    params = {
        "expr": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "fields": "NCTId,Condition,InterventionName,Phase,Status,BriefTitle",
        "min_rnk": 1,
        "max_rnk": 50,
        "fmt": "json"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return data.get("StudyFieldsResponse", {}).get("StudyFields", [])
    except:
        return []


# ---------------------------------------------------------
# 3b) NEWS SCRAPER (Bing)
# ---------------------------------------------------------

# Holt Nachrichten zu BMD
def search_medical_news():
    url = "https://www.bing.com/news/search"
    params = {
        "q": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "setlang": "en"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        results = []

        # Bing News Headlines stehen in <a class="title">
        for a in soup.find_all("a", {"class": "title"}):
            title = a.get_text(strip=True)
            if 10 < len(title) < 200:
                results.append(title)

        # Duplikate entfernen
        results = list(dict.fromkeys(results))

        return results[:10]

    except Exception as e:
        print("News-Fehler:", e)
        return []



# ---------------------------------------------------------
# 3c) ORPHANET SCRAPER
# ---------------------------------------------------------

from bs4 import BeautifulSoup

# Holt medizinische Hintergrundinfos aus Orphanet
def search_orphanet():
    url = "https://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=EN&Expert=988"

    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        results = []

        # Extrahiert Absätze und Überschriften
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
# 4) RELEVANZFILTER
# ---------------------------------------------------------

# Klassifiziert Text nach Relevanz
def classify_relevance(text):
    t = text.lower()

    if "duchenne" in t and "becker" not in t:
        return "gering"

    if "becker" in t or "bmd" in t:
        return "hoch"

    if any(k in t for k in ["dystrophin", "gene therapy", "crispr", "aav", "exon"]):
        return "mittel"

    return "gering"


# ---------------------------------------------------------
# 5) ZUSAMMENFASSUNG (nur NEUE Ergebnisse)
# ---------------------------------------------------------

def summarize_results(pubmed, trials, news, orphanet):
    message = "🧬 *Neue Entwicklungen seit dem letzten Lauf:*\n\n"

    # PubMed
    message += "🧬 PubMed:\n"
    if pubmed:
        for p in pubmed:
            message += f"- {p}\n"
    else:
        message += "- Keine neuen Studien.\n"

    # ClinicalTrials
    message += "\n🧪 ClinicalTrials:\n"
    if trials:
        for t in trials:
            message += f"- {t}\n"
    else:
        message += "- Keine neuen Trials.\n"

    # News
    message += "\n📰 Medizinische Nachrichten:\n"
    if news:
        for n in news:
            message += f"- {n}\n"
    else:
        message += "- Keine neuen Nachrichten.\n"

    # Orphanet
    message += "\n📚 Orphanet:\n"
    if orphanet:
        for o in orphanet:
            message += f"- {o}\n"
    else:
        message += "- Keine neuen Orphanet-Informationen.\n"

    return message


# ---------------------------------------------------------
# 5b) NEUE EINTRÄGE ERKENNEN
# ---------------------------------------------------------

# Vergleicht alte und neue Listen und gibt nur NEUES zurück
def detect_new_items(old_list, new_list):
    return [item for item in new_list if item not in old_list]


# ---------------------------------------------------------
# 6) HAUPTFUNKTION
# ---------------------------------------------------------

def run_bmd_monitor():
    # 1. Alte Ergebnisse laden
    history = load_history()

    # 2. Neue Ergebnisse abrufen
    pubmed = search_pubmed()
    trials = search_clinicaltrials()
    news = search_medical_news()
    orphanet = search_orphanet()

    # 3. Titel extrahieren (falls nötig)
    pubmed_titles = pubmed
    trial_titles = trials
    news_titles = news
    orphanet_texts = orphanet

    # 4. Neue Einträge erkennen
    new_pubmed = detect_new_items(history["pubmed"], pubmed_titles)
    new_trials = detect_new_items(history["trials"], trial_titles)
    new_news = detect_new_items(history["news"], news_titles)
    new_orphanet = detect_new_items(history["orphanet"], orphanet_texts)

    # 5. Zusammenfassung erzeugen
    summary = summarize_results(new_pubmed, new_trials, new_news, new_orphanet)

    # 6. Telegram senden
    send_telegram(summary)

    # 7. History aktualisieren
    history["pubmed"] = pubmed_titles
    history["trials"] = trial_titles
    history["news"] = news_titles
    history["orphanet"] = orphanet_texts

    save_history(history)

    print("Telegram-Benachrichtigung gesendet.")


# ---------------------------------------------------------
# 7) SCRIPT STARTEN
# ---------------------------------------------------------

if __name__ == "__main__":
    run_bmd_monitor()
