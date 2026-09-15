import feedparser
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import time
import os

# ============================================================
# 1. LISTE DES FLUX RSS (autres sites)
# ============================================================

RSS_FEEDS = {
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
# 2. SUPER FLUX FRANDROID (RSS + HTML pages 1→3)
# ============================================================

FRANDROID_RSS = "https://www.frandroid.com/feed"

FRANDROID_SECTIONS = {
    "Frandroid - Actualités": "https://www.frandroid.com/actualites",
    "Frandroid - Tests": "https://www.frandroid.com/test",
    "Frandroid - Bons plans": "https://www.frandroid.com/bon-plan"
}

OUTPUT_FILE = "output/rss_history.csv"

# ------------------------------------------------------------
# Récupération date exacte d’un article Frandroid
# ------------------------------------------------------------
def get_frandroid_date(url):
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            dt = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
            return dt
    except:
        return None

    return None

# ------------------------------------------------------------
# Scraping HTML Frandroid (pages 1→3)
# ------------------------------------------------------------
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
                time.sleep(0.5)

                articles.append({
                    "site": name,
                    "title": title,
                    "link": link,
                    "date": dt
                })

        except Exception as e:
            print(f"Erreur sur {url}: {e}")

    return articles

# ------------------------------------------------------------
# Scraping RSS Frandroid
# ------------------------------------------------------------
def scrape_frandroid_rss():
    print("[Frandroid] Scraping RSS...")
    feed = feedparser.parse(FRANDROID_RSS)
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

        articles.append({
            "site": "Frandroid - RSS",
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "date": dt
        })

    return articles

# ============================================================
# 3. SCRAPING RSS DES AUTRES SITES
# ============================================================

def scrape_rss_generic(name, url):
    print(f"[RSS] Scraping {name}...")
    feed = feedparser.parse(url)
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

        articles.append({
            "site": name,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "date": dt
        })

    return articles

# ============================================================
# 4. LECTURE DE L’ANCIEN CSV (historique dans output/)
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
# 5. FUSION DE TOUS LES ARTICLES
# ============================================================

def main():
    all_articles = []

    all_articles.extend(load_old_history())
    all_articles.extend(scrape_frandroid_rss())

    for name, url in FRANDROID_SECTIONS.items():
        all_articles.extend(scrape_frandroid_section(name, url))

    for name, url in RSS_FEEDS.items():
        all_articles.extend(scrape_rss_generic(name, url))

    unique = {}
    for a in all_articles:
        if a["link"] not in unique or (unique[a["link"]]["date"] is None and a["date"]):
            unique[a["link"]] = a

    articles = list(unique.values())

    articles.sort(key=lambda x: (x["date"] is None, x["date"]), reverse=False)

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
