import feedparser
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import os

OUTPUT_FILE = "output/rss_history.csv"
LOG_FILE = "output/log.txt"

# ============================================================
# Normalisation des dates
# ============================================================

def normalize_date(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# ============================================================
# Logging léger
# ============================================================

def log_error(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc)}] {msg}\n")

# ============================================================
# Flux RSS
# ============================================================

RSS_FEEDS = {
    "Frandroid - RSS": "https://www.frandroid.com/feed",
    "01net": "https://www.01net.com/feed/",
    "Numerama": "https://www.numerama.com/feed/",
    "CCM": "https://www.commentcamarche.net/rss/?output=xml",
    "KultureGeek": "http://feeds.feedburner.com/Kulturegeek",
    "JournalDuGeek": "https://www.journaldugeek.com/feed/",
    "LesNumeriques": "https://www.lesnumeriques.com/rss.xml",
    "Korben": "https://korben.info/feed",
    "NextInpact": "https://www.nextinpact.com/rss",
    "TomsHardware": "https://www.tomshardware.fr/feed/",
    "Clubic": "https://www.clubic.com/feed/"
}

# ============================================================
# Sections HTML Frandroid
# ============================================================

FRANDROID_SECTIONS = {
    "Frandroid - Actualités": "https://www.frandroid.com/actualites",
    "Frandroid - Tests": "https://www.frandroid.com/test",
    "Frandroid - Bons plans": "https://www.frandroid.com/bon-plan"
}

# ============================================================
# Date exacte Frandroid
# ============================================================

def get_frandroid_date(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            dt = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
            return normalize_date(dt)
    except Exception as e:
        log_error(f"Erreur date Frandroid {url}: {e}")
    return None

# ============================================================
# Scraping HTML Frandroid
# ============================================================

def scrape_frandroid_section(name, base_url):
    articles = []

    for page in range(1, 4):
        url = base_url if page == 1 else f"{base_url}/page/{page}"
        print(f"[Frandroid] Scraping {name} - page {page}...")

        try:
            html = requests.get(url, timeout=10).text
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("article")

            for card in cards:
                a = card.find("a")
                if not a:
                    continue

                link = a.get("href")
                title = a.get_text(strip=True)
                dt = get_frandroid_date(link)

                articles.append({
                    "site": name,
                    "title": title,
                    "link": link,
                    "date": normalize_date(dt)
                })

        except Exception as e:
            log_error(f"Erreur Frandroid {url}: {e}")

    return articles

# ============================================================
# Scraping RSS générique
# ============================================================

def scrape_rss(name, url):
    print(f"[RSS] Scraping {name}...")
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        log_error(f"Erreur RSS {name}: {e}")
        return []

    articles = []

    for entry in feed.entries:
        dt = None

        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except:
                dt = None

        if dt is None and hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except:
                dt = None

        if dt is None and hasattr(entry, "updated"):
            try:
                dt = datetime.fromisoformat(entry.updated.replace("Z", "+00:00"))
            except:
                dt = None

        dt = normalize_date(dt)

        articles.append({
            "site": name,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "date": dt
        })

    return articles

# ============================================================
# Lecture historique
# ============================================================

def load_old_history():
    history = []

    if not os.path.exists(OUTPUT_FILE):
        return history

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = datetime.fromisoformat(row["date"]) if row["date"] else None
                dt = normalize_date(dt)
            except:
                dt = None

            history.append({
                "site": row["source"],
                "title": row["titre"],
                "link": row["lien"],
                "date": dt
            })

    print(f"[Historique] Ancien articles chargés : {len(history)}")
    return history

# ============================================================
# MAIN
# ============================================================

def main():
    all_articles = []

    # Historique
    all_articles.extend(load_old_history())

    # Frandroid RSS
    all_articles.extend(scrape_rss("Frandroid - RSS", RSS_FEEDS["Frandroid - RSS"]))

    # Frandroid HTML
    for name, url in FRANDROID_SECTIONS.items():
        all_articles.extend(scrape_frandroid_section(name, url))

    # Autres sites RSS
    for name, url in RSS_FEEDS.items():
        if name != "Frandroid - RSS":
            all_articles.extend(scrape_rss(name, url))

    # Déduplication
    unique = {}
    for a in all_articles:
        if a["link"] not in unique or (unique[a["link"]]["date"] is None and a["date"]):
            unique[a["link"]] = a

    articles = list(unique.values())

    # Tri du plus récent au plus ancien
    articles.sort(key=lambda x: (x["date"] is None, x["date"]), reverse=True)

    # Écriture CSV
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "date", "titre", "lien"])

        for a in articles:
            date_str = a["date"].strftime("%Y-%m-%d %H:%M:%S") if a["date"] else ""
            writer.writerow([
                a["site"],
                date_str,
                a["title"],
                a["link"]
            ])

    print(f"✔ Fichier final généré : {OUTPUT_FILE}")
    print(f"✔ Articles exportés : {len(articles)}")

if __name__ == "__main__":
    main()
