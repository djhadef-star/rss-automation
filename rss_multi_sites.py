import feedparser
import csv
from datetime import datetime

# Liste des flux RSS à récupérer
RSS_FEEDS = [
    "https://www.frandroid.com/feed",
    "https://www.phonandroid.com/feed",
    "https://www.clubic.com/feed/news.xml",
    "https://www.lesnumeriques.com/rss.xml"
]

# Fichier de sortie dans le dossier output/
OUTPUT_FILE = "output/rss_history.csv"

def fetch_rss():
    all_items = []

    for url in RSS_FEEDS:
        feed = feedparser.parse(url)

        for entry in feed.entries:
            item = {
                "source": feed.feed.get("title", "Inconnu"),
                "titre": entry.get("title", ""),
                "lien": entry.get("link", ""),
                "date": entry.get("published", "")
            }
            all_items.append(item)

    return all_items

def save_to_csv(items):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "titre", "lien", "date"])

        for item in items:
            writer.writerow([
                item["source"],
                item["titre"],
                item["lien"],
                item["date"]
            ])

def main():
    print("Récupération des flux RSS...")
    items = fetch_rss()
    print(f"{len(items)} articles récupérés.")

    print("Écriture dans le fichier CSV...")
    save_to_csv(items)

    print("✔ Fichier CSV généré :", OUTPUT_FILE)

if __name__ == "__main__":
    main()
