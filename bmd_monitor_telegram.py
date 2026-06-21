ALWAYS_SEND = True

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
            data={"q": text, "source": "auto", "target": "de"},
            timeout=10
        )
        return r.json().get("translatedText", text)
    except:
        return text

# -----------------------------
# History laden / reparieren
# -----------------------------
def load_history():
    default = {"pubmed": [], "semantic": [], "trials": [], "news": [], "orphanet": []}
    if not os.path.exists("history.json"):
        return default
    try:
        with open("history.json", "r") as f:
            data = json.load(f)
    except:
        return default
    for key in default:
        if key not in data:
            data[key] = []
    return data

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
    max_len = 4000  # etwas unter 4096 bleiben

    # In Blöcke aufteilen
    parts = [msg[i:i+max_len] for i in range(0, len(msg), max_len)]

    for idx, part in enumerate(parts, start=1):
        # Optional: Teilnummer ergänzen, wenn mehrere Nachrichten
        if len(parts) > 1:
            part_to_send = f"Teil {idx}/{len(parts)}\n\n{part}"
        else:
            part_to_send = part

        r = requests.post(url, data={"chat_id": CHAT_ID, "text": part_to_send})
        print("Telegram-Status:", r.status_code, r.text)


# -----------------------------
# Europe PMC (PubMed Ersatz)
# -----------------------------
def search_pubmed():
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    query = "Becker muscular dystrophy OR BMD OR Dystrophinopathy"
    params = {"query": query, "format": "json", "pageSize": 20}

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        results = []
        for hit in data.get("resultList", {}).get("result", []):
            title = hit.get("title", "Kein Titel")
            abstract = hit.get("abstractText", "Keine Zusammenfassung")[:300] + "..."
            link = f"https://europepmc.org/article/{hit.get('source', '')}/{hit.get('id', '')}"
            results.append(f"{title}\n{abstract}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# CrossRef (Semantic Scholar Ersatz)
# -----------------------------
def search_semantic_scholar():
    url = "https://api.crossref.org/works"
    params = {"query": "Becker muscular dystrophy", "rows": 20}

    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            title = item.get("title", ["Kein Titel"])[0]
            year = item.get("created", {}).get("date-parts", [[None]])[0][0]
            doi = item.get("DOI", "")
            link = f"https://doi.org/{doi}" if doi else "Kein Link"
            abstract = item.get("abstract", "Keine Zusammenfassung")[:300] + "..."
            results.append(f"{title} ({year})\n{abstract}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# EU Clinical Trials Register
# -----------------------------
def search_clinicaltrials():
    url = "https://www.clinicaltrialsregister.eu/ctr-search/rest/search"
    params = {"query": "Becker muscular dystrophy"}

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        results = []
        for trial in data.get("results", []):
            title = trial.get("title", "Kein Titel")
            status = trial.get("trialStatus", "Unbekannt")
            link = f"https://www.clinicaltrialsregister.eu/ctr-search/trial/{trial.get('trialId', '')}"
            results.append(f"{title}\nStatus: {status}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# NewsAPI (Google News Ersatz)
# -----------------------------
def search_medical_news():
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "language": "de",
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": "demo"  # funktioniert über Proxy
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        articles = r.json().get("articles", [])
        results = []
        for a in articles:
            title = a.get("title", "Kein Titel")
            source = a.get("source", {}).get("name", "Unbekannte Quelle")
            link = a.get("url", "")
            results.append(f"{title}\nQuelle: {source}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# Orphanet (mit Browser-Headern)
# -----------------------------
def search_orphanet():
    url = "https://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=DE&Expert=988"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if "Becker" in text and len(text) > 80:
                results.append(text[:300] + "...\n🔗 " + url)
        return results[:5]
    except:
        return []

# -----------------------------
# Zusammenfassung
# -----------------------------
def summarize_results(pubmed, semantic, trials, news, orphanet):
    msg = "🧬 Neue Entwicklungen:\n\n"
    msg += "🧬 PubMed:\n" + ("\n\n".join(f"- {p}" for p in pubmed) if pubmed else "- Keine Studien.")
    msg += "\n\n📘 Wissenschaftliche Veröffentlichungen:\n" + ("\n\n".join(f"- {s}" for s in semantic) if semantic else "- Keine Veröffentlichungen.")
    msg += "\n\n🧪 Klinische Studien:\n" + ("\n\n".join(f"- {t}" for t in trials) if trials else "- Keine klinischen Studien.")
    msg += "\n\n📰 Nachrichten:\n" + ("\n\n".join(f"- {n}" for n in news) if news else "- Keine Nachrichten.")
    msg += "\n\n📚 Orphanet:\n" + ("\n\n".join(f"- {o}" for o in orphanet) if orphanet else "- Keine neuen Informationen.")
    return msg

# -----------------------------
# Hauptfunktion
# -----------------------------
def run_bmd_monitor():
    history = load_history()

    pubmed = search_pubmed()
    semantic = search_semantic_scholar()
    trials = search_clinicaltrials()
    news = search_medical_news()
    orphanet = search_orphanet()

    pubmed = [translate_to_german(p) for p in pubmed]
    semantic = [translate_to_german(s) for s in semantic]
    trials = [translate_to_german(t) for t in trials]
    news = [translate_to_german(n) for n in news]
    orphanet = [translate_to_german(o) for o in orphanet]

    if ALWAYS_SEND:
        summary = summarize_results(pubmed, semantic, trials, news, orphanet)
    else:
        summary = summarize_results(
            detect_new_items(history["pubmed"], pubmed),
            detect_new_items(history["semantic"], semantic),
            detect_new_items(history["trials"], trials),
            detect_new_items(history["news"], news),
            detect_new_items(history["orphanet"], orphanet)
        )

    send_telegram(summary)

    history["pubmed"] = pubmed
    history["semantic"] = semantic
    history["trials"] = trials
    history["news"] = news
    history["orphanet"] = orphanet
    save_history(history)

# -----------------------------
# Startpunkt
# -----------------------------
if __name__ == "__main__":
    run_bmd_monitor()
