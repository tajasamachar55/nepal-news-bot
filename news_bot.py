import os
import feedparser
import requests
from datetime import datetime, timedelta, timezone
import time
import re

GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Many more RSS feeds ────────────────────────────────────────
RSS_FEEDS = [
    # Nepali language
    {"name": "Kantipur",          "url": "https://ekantipur.com/rss"},
    {"name": "Onlinekhabar",      "url": "https://www.onlinekhabar.com/feed"},
    {"name": "Setopati",          "url": "https://www.setopati.com/feed"},
    {"name": "Ratopati",          "url": "https://ratopati.com/rss"},
    {"name": "Nepal Khabar",      "url": "https://www.nepalkhabar.com/feed"},
    {"name": "Nagarik News",      "url": "https://nagariknews.nagariknetwork.com/feed"},
    {"name": "Nepal News",        "url": "https://nepalnews.com/feed"},
    {"name": "Naya Patrika",      "url": "https://www.nayapatrikadaily.com/feed"},
    {"name": "Himalkhabar",       "url": "https://himalkhabar.com/feed"},
    {"name": "Khabarhub",         "url": "https://english.khabarhub.com/feed"},
    {"name": "Nepali Times",      "url": "https://nepalitimes.com/feed"},
    {"name": "Karobar",           "url": "https://karobardaily.com/feed"},
    {"name": "Arthik Abhiyan",    "url": "https://arthikabhiyan.com/feed"},
    # English Nepal news
    {"name": "Republica",         "url": "https://myrepublica.nagariknetwork.com/feed"},
    {"name": "Himalayan Times",   "url": "https://thehimalayantimes.com/feed"},
    {"name": "Kathmandu Post",    "url": "https://kathmandupost.com/rss"},
    # International (for world news section)
    {"name": "BBC World",         "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera",        "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    # Sports
    {"name": "ESPN Cricket",      "url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"},
    {"name": "Goal.com",          "url": "https://www.goal.com/feeds/en/news"},
    # Business/Finance Nepal
    {"name": "RONB",              "url": "https://www.ratopati.com/category/business/feed"},
    {"name": "ShareSansar",       "url": "https://www.sharesansar.com/feed"},
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
                    summary = re.sub(r"<[^>]+>", "", summary)[:500]
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
            time.sleep(0.5)
        except Exception as e:
            print(f"  {feed_info['name']}: Failed ({e})")
    print(f"Total articles: {len(all_articles)}")
    return all_articles

def write_script_with_groq(articles):
    if not articles:
        return "कुनै समाचार फेला परेन।"
    print("Sending to Groq AI...")

    # Separate Nepal news from international
    nepal_articles  = [a for a in articles if a["source"] not in ["BBC World", "Al Jazeera", "ESPN Cricket", "Goal.com"]]
    world_articles  = [a for a in articles if a["source"] in ["BBC World", "Al Jazeera"]]
    sports_articles = [a for a in articles if a["source"] in ["ESPN Cricket", "Goal.com"]]
    biz_articles    = [a for a in articles if a["source"] in ["RONB", "ShareSansar", "Karobar", "Arthik Abhiyan"]]

    def format_list(arts, limit=30):
        text = ""
        for i, a in enumerate(arts[:limit], 1):
            text += f"{i}. [{a['source']}] {a['title']}\n"
            if a['summary']:
                text += f"   {a['summary'][:400]}\n"
            text += "\n"
        return text

    today    = datetime.now().strftime("%Y-%m-%d")
    day_name = datetime.now().strftime("%A")

    prompt = f"""तपाईं नेपालको एक वरिष्ठ र अनुभवी समाचार एंकर हुनुहुन्छ जो रेडियो र यूट्युब च्यानलका लागि स्क्रिप्ट लेख्नुहुन्छ।

आजको मिति: {today}, {day_name}

तलका समाचारहरूबाट एउटा सम्पूर्ण र विस्तृत समाचार स्क्रिप्ट लेख्नुस् जुन बोल्दा २०-२५ मिनेट लाग्ने गरी कम्तीमा ५०००-६००० अक्षरको होस्।

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
महत्त्वपूर्ण निर्देशनहरू:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
१. स्टोरीटेलिङ शैली — हरेक समाचारलाई एउटा कथाजस्तो बनाउनुस्। पृष्ठभूमि, कारण, असर र भविष्यको अनुमान समावेश गर्नुस्।
२. सानो समाचारलाई पनि ठूलो बनाउनुस् — सन्दर्भ थप्नुस्, विश्लेषण गर्नुस्।
३. श्रोतालाई सम्बोधन गर्नुस् — "साथीहरू", "हाम्रा श्रोताहरू" भनी।
४. हरेक खण्डमा सहज transition राख्नुस्।
५. शुद्ध, सरल र बोधगम्य नेपाली भाषा प्रयोग गर्नुस्।

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
स्क्रिप्टको ढाँचा:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[परिचय — १५ सेकेन्ड]
आकर्षक उद्घाटन वाक्य। आजका मुख्य समाचारको संक्षिप्त टिजर।

🔴 प्रमुख समाचार — २ मिनेट
सबैभन्दा महत्त्वपूर्ण ४-५ समाचार। बुलेटिन शैलीमा। छोटो र स्पष्ट।

🇳🇵 राष्ट्रिय समाचार — ८-१० मिनेट
६-७ वटा राष्ट्रिय समाचार। प्रत्येकलाई ३-५ वाक्यमा विस्तृत स्टोरीटेलिङ शैलीमा। पृष्ठभूमि र विश्लेषण थप्नुस्।

🌍 अन्तर्राष्ट्रिय समाचार — ४-५ मिनेट
३-४ वटा विश्व समाचार। नेपालमा पर्ने प्रभाव उल्लेख गर्नुस्।

💰 आर्थिक तथा व्यापार समाचार — ३-४ मिनेट
शेयर बजार, बैंकिङ, व्यापार, रोजगारी सम्बन्धी समाचार।

🏏 खेलकुद समाचार — २-३ मिनेट
क्रिकेट, फुटबल र अन्य खेलकुद समाचार।

🌤️ मौसम र अन्य — १ मिनेट
मौसम अपडेट र छोटा समाचार।

[समापन — १५ सेकेन्ड]
धन्यवाद र अर्को अपडेटको जानकारी।

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
समाचार स्रोतहरू:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🇳🇵 नेपाली समाचार:
{format_list(nepal_articles, 40)}

🌍 अन्तर्राष्ट्रिय समाचार:
{format_list(world_articles, 10)}

💰 आर्थिक समाचार:
{format_list(biz_articles, 10)}

🏏 खेलकुद:
{format_list(sports_articles, 8)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
अब पूरा स्क्रिप्ट लेख्नुस् — कम्तीमा ५००० अक्षर। हरेक खण्डलाई विस्तृत र स्टोरीटेलिङ शैलीमा लेख्नुस्:"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "तपाईं नेपालका एक वरिष्ठ समाचार एंकर हुनुहुन्छ। तपाईं स्टोरीटेलिङ शैलीमा लामो, विस्तृत र आकर्षक समाचार स्क्रिप्ट लेख्नुहुन्छ। शुद्ध नेपाली भाषामा मात्र जवाफ दिनुस्। कम्तीमा ५००० अक्षरको स्क्रिप्ट लेख्नुस्।"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.75,
        "max_tokens": 8000
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data   = response.json()
        script = data["choices"][0]["message"]["content"]
        print(f"Script written! Length: {len(script)} characters")
        return script
    except Exception as e:
        error_msg = str(e)
        if GROQ_API_KEY in error_msg:
            error_msg = error_msg.replace(GROQ_API_KEY, "***hidden***")
        print(f"Groq error: {error_msg}")
        return "स्क्रिप्ट बनाउन असफल। कृपया पछि पुनः प्रयास गर्नुस्।"

def send_to_telegram(script, article_count):
    print("Sending to Telegram...")
    today  = datetime.now().strftime("%Y/%m/%d %H:%M")
    header = f"🇳🇵 *ताजा समाचार स्क्रिप्ट*\n📅 {today}\n📰 {article_count} समाचारबाट संकलित\n📻 अवधि: २०-२५ मिनेट\n\n"
    full_message = header + script

    # Split into 4000 char chunks for Telegram
    max_len = 4000
    parts   = []
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
            resp    = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                print(f"  Part {i+1}/{len(parts)} sent!")
            else:
                print(f"  Part {i+1} failed: {resp.text[:300]}")
            time.sleep(1)
        except Exception as e:
            print(f"  Telegram error: {e}")

def save_to_file(script):
    filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"Saved to {filename} ({len(script)} chars)")

def main():
    print("=" * 50)
    print("Nepal News AI Bot Starting...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not set!")
        return
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram credentials not set!")
        return

    articles = scrape_news()
    script   = write_script_with_groq(articles)
    save_to_file(script)
    send_to_telegram(script, len(articles))
    print("Done! Check your Telegram.")

if __name__ == "__main__":
    main()
