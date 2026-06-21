import requests
import json
import os
from bs4 import BeautifulSoup

# -----------------------------
# Übersetzungsfunktion
# -----------------------------
def translate_to_german(text):
    try:
        r = requests.post(
            "https://libretranslate.de/translate",
            data={
                "q": text,
                "source": "auto",
                "target": "de",
                "format": "text"
            },
            timeout=10
        )
        return r.json().get("translatedText", text)
    except:
        return text

# -----------------------------
# History laden / speichern
# -----------------------------
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

# -----------------------------
# Telegram
# -----------------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Fehler beim Senden an Telegram:", e)

# -----------------------------
# Datenquellen
# -----------------------------
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
    except:
        return []

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

def search_medical_news():
    url = "https://news.google.com/rss/search?q=Becker+muscular+dystrophy+BMD+Dystrophinopathy&hl=de&gl=DE&ceid=DE:de"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            if 10 < len(title) < 200:
                results.append(title)
        return list(dict.fromkeys(results))[:10]
    except:
        return []

def search_orphanet():
    url = "https://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=DE&Expert=988"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for section in soup.find_all(["p", "h2", "h3"]):
            text = section.get_text(strip=True)
            if not text:
                continue
            t = text.lower()
            if any(k in t for k in ["becker", "dystrophin", "muskeldystrophie", "x-chromosomal"]):
                if 30 < len(text) < 400:
                    results.append(text)
        return results[:5]
    except:
        return []

# -----------------------------
# Neue Einträge erkennen
# -----------------------------
def detect_new_items(old_list, new_list):
    return [item for item in new_list if item not in old_list]

# -----------------------------
# Zusammenfassung
# -----------------------------
def summarize_results(pubmed, semantic, trials, news, orphanet):
    msg = "🧬 Neue Entwicklungen seit dem letzten Lauf:\n\n"
    msg += "🧬 PubMed:\n" + ("\n".join(f"- {p}" for p in pubmed) if pubmed else "- Keine neuen Studien.")
    msg += "\n\n📘 Semantic Scholar:\n" + ("\n".join(f"- {s}" for s in semantic) if semantic else "- Keine neuen wissenschaftlichen Veröffentlichungen.")
    msg += "\n\n🧪 Klinische Studien:\n" + ("\n".join(f"- {t}" for t in trials) if trials else "- Keine neuen klinischen Studien.")
    msg += "\n\n📰 Nachrichten:\n" + ("\n".join(f"- {n}" for n in news) if news else "- Keine neuen Nachrichten.")
    msg += "\n\n📚 Orphanet (Krankheitsinformationen):\n" + ("\n".join(f"- {o}" for o in orphanet) if orphanet else "- Keine neuen Informationen von Orphanet.")
    return msg

# -----------------------------
# Hauptfunktion
# -----------------------------
def run_bmd_monitor():
    history = load_history()

    # Daten abrufen
    pubmed = search_pubmed()
    semantic = search_semantic_scholar()
    trials = search_clinicaltrials()
    news = search_medical_news()
    orphanet = search_orphanet()

    # ALLES einzeln übersetzen
    pubmed = [translate_to_german(p) for p in pubmed]
    semantic = [translate_to_german(s) for s in semantic]
    trials = [translate_to_german(t) for t in trials]
    news = [translate_to_german(n) for n in news]
    orphanet = [translate_to_german(o) for o in orphanet]

    # Neue Einträge erkennen
    summary = summarize_results(
        detect_new_items(history["pubmed"], pubmed),
        detect_new_items(history["semantic"], semantic),
        detect_new_items(history["trials"], trials),
        detect_new_items(history["news"], news),
        detect_new_items(history["orphanet"], orphanet)
    )

    # Zusammenfassung selbst auch übersetzen
    summary = translate_to_german(summary)

    # Senden
    send_telegram(summary)

    # History aktualisieren
    history["pubmed"] = pubmed
    history["semantic"] = semantic
    history["trials"] = trials
    history["news"] = news
    history["orphanet"] = orphanet

    save_history(history)
    print("Telegram-Benachrichtigung gesendet.")

# -----------------------------
# Start
# -----------------------------
if __name__ == "__main__":
    run_bmd_monitor()
