import requests
from datetime import datetime

import json
import os

def load_history():
    if not os.path.exists("history.json"):
        return {"pubmed": [], "trials": [], "news": [], "orphanet": []}

    with open("history.json", "r") as f:
        return json.load(f)

def save_history(history):
    with open("history.json", "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------------------------------------
# 1) Telegram Push
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
# 2) PubMed API (robust)
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

    results = []
    for q in queries:
        try:
            r = requests.get(url, params={"format": "json", "term": q}, timeout=10)
            data = r.json()
            if "records" in data:
                results.extend(data["records"])
        except:
            continue  # Fehler ignorieren, weiter zur nächsten Query

    return results


# ---------------------------------------------------------
# 3) ClinicalTrials API (robust)
# ---------------------------------------------------------
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
        return []  # API nicht erreichbar → leere Liste zurückgeben
    

# ---------------------------------------------------------
# 3b) Medical News (Bing News Search)
# ---------------------------------------------------------
def search_medical_news():
    url = "https://www.bing.com/news/search"
    params = {
        "q": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "form": "NWRFSH",
        "setlang": "en"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        html = r.text.lower()

        # Sehr einfacher Filter: wir suchen nach Titeln in <a> Tags
        results = []
        for line in html.split("<a"):
            if "becker" in line or "bmd" in line or "dystrophin" in line:
                # Titel extrahieren
                start = line.find(">") + 1
                end = line.find("<", start)
                title = line[start:end].strip()
                if 5 < len(title) < 200:
                    results.append(title)

        return results[:10]  # nur die ersten 10 News
    except:
        return []

from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 3c) Orphanet (Disease Information, sauber geparst)
# ---------------------------------------------------------
def search_orphanet():
    url = "https://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=EN&Expert=988"

    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        results = []

        # Wir extrahieren die wichtigsten Abschnitte
        for section in soup.find_all(["p", "h2", "h3"]):
            text = section.get_text(strip=True)
            if not text:
                continue

            # Relevanzfilter direkt hier
            t = text.lower()
            if any(k in t for k in ["becker", "dystrophin", "muscular", "x-linked"]):
                if 30 < len(text) < 400:
                    results.append(text)

        return results[:5]  # die 5 wichtigsten Abschnitte
    except Exception as e:
        print("Orphanet-Fehler:", e)
        return []


# ---------------------------------------------------------
# 4) Relevanzfilter
# ---------------------------------------------------------
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
# 5) Zusammenfassung
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


    # Fazit
    message += "\n📌 Fazit:\n"
    if found_pubmed or found_trials:
        message += "Es gibt neue relevante Entwicklungen zur Becker-Muskeldystrophie."
    else:
        message += "Seit der letzten Abfrage wurden keine neuen relevanten Veröffentlichungen gefunden."

    return message

    # Medical News
    message += "\n📰 Medizinische Nachrichten:\n"
    found_news = False
    for title in news[:10]:
        relevance = classify_relevance(title)
        if relevance == "gering":
            continue
        found_news = True
        message += f"- {title} (Relevanz: {relevance})\n"

    if not found_news:
        message += "- Keine relevanten Nachrichten gefunden.\n"

        # Orphanet
    message += "\n📚 Orphanet – Krankheitsinformationen:\n"
    found_orpha = False
    for text in orphanet[:5]:
        relevance = classify_relevance(text)
        if relevance == "gering":
            continue
        found_orpha = True
        message += f"- {text} (Relevanz: {relevance})\n"

    if not found_orpha:
        message += "- Keine relevanten Orphanet-Informationen gefunden.\n"
    


# ---------------------------------------------------------
# 6) Hauptfunktion
# ---------------------------------------------------------
def run_bmd_monitor():
    # Alte Ergebnisse laden
    history = load_history()

    # Neue Ergebnisse abrufen
    pubmed = search_pubmed()
    trials = search_clinicaltrials()
    news = search_medical_news()
    orphanet = search_orphanet()

    # Nur die Titel extrahieren (falls nötig)
    pubmed_titles = pubmed
    trial_titles = trials
    news_titles = news
    orphanet_texts = orphanet

    # Neue Einträge erkennen
    new_pubmed = detect_new_items(history["pubmed"], pubmed_titles)
    new_trials = detect_new_items(history["trials"], trial_titles)
    new_news = detect_new_items(history["news"], news_titles)
    new_orphanet = detect_new_items(history["orphanet"], orphanet_texts)

    # Zusammenfassung erzeugen
    summary = summarize_results(new_pubmed, new_trials, new_news, new_orphanet)

    # Telegram senden
    send_telegram(summary)

    # History aktualisieren
    history["pubmed"] = pubmed_titles
    history["trials"] = trial_titles
    history["news"] = news_titles
    history["orphanet"] = orphanet_texts

    save_history(history)

    print("Telegram-Benachrichtigung gesendet.")




# ---------------------------------------------------------
# 7) Script ausführen
# ---------------------------------------------------------
if __name__ == "__main__":
    run_bmd_monitor()
