ALWAYS_SEND = True

import requests
import json
import os
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

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
# History laden / reparieren
# -----------------------------
def load_history():
    default = {
        "pubmed": [],
        "semantic": [],
        "trials": [],
        "news": [],
        "orphanet": []
    }

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
    r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    print("Telegram-Status:", r.status_code, r.text)

# -----------------------------
# PubMed
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
    results = []

    for q in queries:
        try:
            r = requests.get(url, params={"format": "json", "term": q}, timeout=10)
            data = r.json()

            for rec in data.get("records", []):
                title = rec.get("title")
                pmid = rec.get("pmid")
                abstract = rec.get("abstract", "")
                snippet = abstract[:300] + "..." if abstract else "Keine Zusammenfassung verfügbar."

                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "Kein Link verfügbar"

                results.append(f"{title}\n{snippet}\n🔗 {link}")
        except:
            continue

    return results

# -----------------------------
# Semantic Scholar
# -----------------------------
def search_semantic_scholar():
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "limit": 20,
        "fields": "title,year,url,abstract"
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        results = []

        for paper in data.get("data", []):
            title = paper.get("title")
            year = paper.get("year")
            link = paper.get("url", "Kein Link")
            abstract = paper.get("abstract", "")
            snippet = abstract[:300] + "..." if abstract else "Keine Zusammenfassung verfügbar."

            results.append(f"{title} ({year})\n{snippet}\n🔗 {link}")

        return results
    except:
        return []

# -----------------------------
# ClinicalTrials
# -----------------------------
def search_clinicaltrials():
    url = "https://clinicaltrials.gov/api/query/study_fields"
    params = {
        "expr": "Becker muscular dystrophy OR BMD OR Dystrophinopathy",
        "fields": "BriefTitle,Phase,Status,StudyPageLink,BriefSummary",
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
            link = t.get("StudyPageLink", [""])[0]
            summary = t.get("BriefSummary", ["Keine Beschreibung verfügbar."])[0]
            snippet = summary[:300] + "..."

            results.append(f"{title}\nPhase: {phase}, Status: {status}\n{snippet}\n🔗 {link}")

        return results
    except:
        return []

# -----------------------------
# Google News
# -----------------------------
def search_medical_news():
    url = "https://news.google.com/rss/search?q=Becker+muscular+dystrophy+BMD+Dystrophinopathy&hl=de&gl=DE&ceid=DE:de"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "xml")
        results = []

        for item in soup.find_all("item"):
            title = item.title.get_text(strip=True)
            link = item.link.get_text(strip=True)
            source = item.source.get_text(strip=True) if item.source else "Unbekannte Quelle"
            date = item.pubDate.get_text(strip=True) if item.pubDate else "Kein Datum"

            results.append(f"{title}\nQuelle: {source}, Datum: {date}\n🔗 {link}")

        return results[:10]
    except:
        return []

# -----------------------------
# Orphanet
# -----------------------------
def search_orphanet():
    url = "https://www.orpha.net/consor/cgi-bin/OC_Exp.php?lng=DE&Expert=988"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        results = []

        for section in soup.find_all("p"):
            text = section.get_text(strip=True)
            if len(text) > 80 and "Becker" in text:
                snippet = text[:300] + "..."
                results.append(f"{snippet}\n🔗 {url}")

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
    msg = "🧬 Neue Entwicklungen:\n\n"
    msg += "🧬 PubMed:\n" + ("\n\n".join(f"- {p}" for p in pubmed) if pubmed else "- Keine Studien.")
    msg += "\n\n📘 Semantic Scholar:\n" + ("\n\n".join(f"- {s}" for s in semantic) if semantic else "- Keine Veröffentlichungen.")
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

    pubmed_new = detect_new_items(history["pubmed"], pubmed)
    semantic_new = detect_new_items(history["semantic"], semantic)
    trials_new = detect_new_items(history["trials"], trials)
    news_new = detect_new_items(history["news"], news)
    orphanet_new = detect_new_items(history["orphanet"], orphanet)

    # Testmodus → immer vollständige Nachricht
    if ALWAYS_SEND:
        summary = summarize_results(pubmed, semantic, trials, news, orphanet)
    else:
        summary = summarize_results(pubmed_new, semantic_new, trials_new, news_new, orphanet_new)

    summary = translate_to_german(summary)

    print("Anzahl PubMed:", len(pubmed))
    print("Anzahl Semantic:", len(semantic))
    print("Anzahl Trials:", len(trials))
    print("Anzahl News:", len(news))
    print("Anzahl Orphanet:", len(orphanet))
    print("Länge summary:", len(summary))

send_telegram("Testnachricht:\n\n" + summary[:3000])
  

# -----------------------------
# Startpunkt
# -----------------------------
if __name__ == "__main__":
    run_bmd_monitor()



