import requests
from datetime import datetime

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
    message = f"BMD Update – {datetime.now().strftime('%d.%m.%Y')}\n\n"

    # PubMed
    message += "🧬 Neue wissenschaftliche Studien:\n"
    found_pubmed = False
    for rec in pubmed[:10]:
        title = rec.get("title", "")
        relevance = classify_relevance(title)
        if relevance == "gering":
            continue
        found_pubmed = True
        message += f"- {title} (Relevanz: {relevance})\n"

    if not found_pubmed:
        message += "- Keine neuen relevanten Studien gefunden.\n"

    # ClinicalTrials
    message += "\n🧪 Neue klinische Studien:\n"
    found_trials = False
    for s in trials[:10]:
        title = s.get("BriefTitle", [""])[0]
        relevance = classify_relevance(title)
        if relevance == "gering":
            continue
        found_trials = True
        status = s.get("Status", [""])[0]
        nct = s.get("NCTId", [""])[0]
        message += f"- {title} (Status: {status}, NCT: {nct}, Relevanz: {relevance})\n"

    if not found_trials:
        message += "- Keine neuen relevanten klinischen Studien gefunden.\n"

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
    pubmed = search_pubmed()
    trials = search_clinicaltrials()
    news = search_medical_news()
    orphanet = search_orphanet()

    summary = summarize_results(pubmed, trials, news, orphanet)
    send_telegram(summary)
    print("Telegram-Benachrichtigung gesendet.")



# ---------------------------------------------------------
# 7) Script ausführen
# ---------------------------------------------------------
if __name__ == "__main__":
    run_bmd_monitor()
