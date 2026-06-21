ALWAYS_SEND = True

import requests
import json
import os
from bs4 import BeautifulSoup

# -----------------------------
# Hilfsfunktion: Mini-KI-Zusammenfassung
# -----------------------------
def summarize_text(text, max_len=200):
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    # einfache heuristische Zusammenfassung
    sentences = text.split(".")
    if len(sentences) > 1:
        return sentences[0].strip() + "."
    return text[:max_len] + "..."

# -----------------------------
# Übersetzung
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
# History
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
# Telegram (mit Auto-Split)
# -----------------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    max_len = 3500
    parts = [msg[i:i+max_len] for i in range(0, len(msg), max_len)]
    for idx, part in enumerate(parts, start=1):
        if len(parts) > 1:
            part = f"Teil {idx}/{len(parts)}\n\n{part}"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": part})
        print("Telegram-Status:", r.status_code, r.text)

# -----------------------------
# Europe PMC (PubMed Ersatz)
# -----------------------------
def search_pubmed():
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": "Becker muscular dystrophy", "format": "json", "pageSize": 10}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        results = []
        for hit in data.get("resultList", {}).get("result", []):
            title = hit.get("title", "Kein Titel")
            abstract = summarize_text(hit.get("abstractText", "Keine Zusammenfassung"))
            link = f"https://europepmc.org/article/{hit.get('source', '')}/{hit.get('id', '')}"
            results.append(f"**{title}**\n{abstract}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# CrossRef
# -----------------------------
def search_semantic_scholar():
    url = "https://api.crossref.org/works"
    params = {"query": "Becker muscular dystrophy", "rows": 10}
    try:
        r = requests.get(url, params=params, timeout=10)
        items = r.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            title = item.get("title", ["Kein Titel"])[0]
            abstract = summarize_text(item.get("abstract", "Keine Zusammenfassung"))
            doi = item.get("DOI", "")
            link = f"https://doi.org/{doi}" if doi else "Kein Link"
            results.append(f"**{title}**\n{abstract}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# EU Clinical Trials
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
            results.append(f"**{title}**\nStatus: {status}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# NewsAPI
# -----------------------------
def search_medical_news():
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "Becker muscular dystrophy",
        "language": "de",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": "demo"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        articles = r.json().get("articles", [])
        results = []
        for a in articles:
            title = a.get("title", "Kein Titel")
            source = a.get("source", {}).get("name", "Unbekannte Quelle")
            link = a.get("url", "")
            results.append(f"**{title}**\nQuelle: {source}\n🔗 {link}")
        return results
    except:
        return []

# -----------------------------
# Orphanet
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
                results.append(summarize_text(text) + f"\n🔗 {url}")
        return results[:3]
    except:
        return []

# -----------------------------
# Zusammenfassung
# -----------------------------
def summarize_results(pubmed, semantic, trials, news, orphanet):
    msg = "🧬 **Aktuelle Entwicklungen zur Becker-Muskeldystrophie**\n\n"

    def block(title, items):
        if not items:
            return f"**{title}:**\n- Keine Informationen.\n\n"
        return f"**{title}:**\n" + "\n".join(f"- {i}" for i in items) + "\n\n"

    msg += block("Forschung (PubMed)", pubmed)
    msg += block("Wissenschaftliche Veröffentlichungen", semantic)
    msg += block("Klinische Studien", trials)
    msg += block("Nachrichten", news)
    msg += block("Orphanet (medizinische Infos)", orphanet)

    return msg

# -----------------------------
# Hauptfunktion
# -----------------------------
def run_bmd_monitor():
    pubmed = search_pubmed()
    semantic = search_semantic_scholar()
    trials = search_clinicaltrials()
    news = search_medical_news()
    orphanet = search_orphanet()

    # Übersetzen
    pubmed = [translate_to_german(p) for p in pubmed]
    semantic = [translate_to_german(s) for s in semantic]
    trials = [translate_to_german(t) for t in trials]
    news = [translate_to_german(n) for n in news]
    orphanet = [translate_to_german(o) for o in orphanet]

    summary = summarize_results(pubmed, semantic, trials, news, orphanet)
    send_telegram(summary)

# -----------------------------
# Start
# -----------------------------
if __name__ == "__main__":
    run_bmd_monitor()
