import os
import feedparser
import requests
from datetime import datetime, timedelta, timezone
import time
import re

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

RSS_FEEDS = [
    {"name": "Kantipur",     "url": "https://ekantipur.com/rss"},
    {"name": "Onlinekhabar", "url": "https://www.onlinekhabar.com/feed"},
    {"name": "Setopati",     "url": "https://www.setopati.com/feed"},
    {"name": "Ratopati",     "url": "https://ratopati.com/rss"},
    {"name": "Nepal Khabar", "url": "https://www.nepalkhabar.com/feed"},
    {"name": "Nagarik News", "url": "https://nagariknews.nagariknetwork.com/feed"},
    {"name": "Nepal News",   "url": "https://nepalnews.com/feed"},
    {"name": "Republica",    "url": "https://myrepublica.nagariknetwork.com/feed"},
]

HOURS_BACK = 24

def scrape_news():
    print("Scraping news feeds...")
    all_articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)
    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if published is None or published >= cutoff:
                    title   = entry.get("title", "").strip()
                    summary = entry.get("summary", entry.get("description", "")).strip()
                    link    = entry.get("link", "")
                    summary = re.sub(r"<[^>]+>", "", summary)[:300]
                    if title:
                        all_articles.append({
                            "source":    feed_info["name"],
                            "title":     title,
                            "summary":   summary,
                            "link":      link,
                            "published": str(published)[:16] if published else "Unknown",
                        })
                        count += 1
            print(f"  {feed_info['name']}: {count} articles")
            time.sleep(1)
        except Exception as e:
            print(f"  {feed_info['name']}: Failed ({e})")
    print(f"Total articles: {len(all_articles)}")
    return all_articles

def write_script_with_gemini(articles):
    if not articles:
        return "कुनै समाचार फेला परेन।"
    print("Sending to Gemini AI...")
    article_text = ""
    for i, a in enumerate(articles[:60], 1):
        article_text += f"{i}. [{a['source']}] {a['title']}\n"
        if a['summary']:
            article_text += f"   सारांश: {a['summary'][:200]}\n"
        article_text += "\n"
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""तपाईं एक अनुभवी नेपाली समाचार एंकर हुनुहुन्छ। तल दिइएका पछिल्लो २४ घण्टाका समाचार शीर्षकहरूबाट एउटा पूर्ण प्रसारण समाचार स्क्रिप्ट लेख्नुस्।

आजको मिति: {today}

स्क्रिप्टको ढाँचा यसरी हुनुपर्छ:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 प्रमुख समाचार (पहिलो ३ मिनेट)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
(सबैभन्दा महत्त्वपूर्ण ५ वटा समाचार छान्नुस्। प्रत्येक समाचार ३-४ वाक्यमा बुलेटिन शैलीमा लेख्नुस्।)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 विस्तृत समाचार
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
(बाँकी ८-१० वटा महत्त्वपूर्ण समाचारहरू विस्तृत र व्याख्यात्मक तरिकाले लेख्नुस्।)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 अन्य छोटो समाचार
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
(बाँकी समाचारहरू एक-दुई वाक्यमा)

नियमहरू:
- शुद्ध नेपाली भाषामा लेख्नुस्
- प्रत्येक समाचारको स्रोत उल्लेख गर्नुस्
- नक्कली तथ्य नथप्नुस्

समाचारहरू:
{article_text}

अब स्क्रिप्ट लेख्नुस्:"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        script = data["candidates"][0]["content"]["parts"][0]["text"]
        print("Script written successfully!")
        return script
    except Exception as e:
        error_msg = str(e)
        if GEMINI_API_KEY in error_msg:
            error_msg = error_msg.replace(GEMINI_API_KEY, "***hidden***")
        print(f"Gemini error: {error_msg}")
        return "स्क्रिप्ट बनाउन असफल। कृपया पछि पुनः प्रयास गर्नुस्।"

def send_to_telegram(script, article_count):
    print("Sending to Telegram...")
    today = datetime.now().strftime("%Y/%m/%d %H:%M")
    header = f"🇳🇵 नेपाल समाचार स्क्रिप्ट\n📅 {today}\n📰 {article_count} समाचारबाट संकलित\n\n"
    full_message = header + script
    max_len = 4000
    parts = []
    while len(full_message) > max_len:
        split_at = full_message.rfind('\n', 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(full_message[:split_at])
        full_message = full_message[split_at:].lstrip()
    parts.append(full_message)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for i, part in enumerate(parts):
        try:
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": part}
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                print(f"  Part {i+1}/{len(parts)} sent!")
            else:
                print(f"  Part {i+1} failed: {resp.text[:200]}")
            time.sleep(1)
        except Exception as e:
            print(f"  Telegram error: {e}")

def save_to_file(script):
    filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Saved to {filename}")

def main():
    print("=" * 50)
    print("Nepal News AI Bot Starting...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set!")
        return
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM credentials not set!")
        return
    articles = scrape_news()
    script   = write_script_with_gemini(articles)
    save_to_file(script)
    send_to_telegram(script, len(articles))
    print("Done! Check your Telegram.")

if __name__ == "__main__":
    main()
