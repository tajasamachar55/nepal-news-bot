import os
import feedparser
import requests
from datetime import datetime, timedelta, timezone
import time
import re

GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

RSS_FEEDS = [
    {"name": "Kantipur",        "url": "https://ekantipur.com/rss"},
    {"name": "Onlinekhabar",    "url": "https://www.onlinekhabar.com/feed"},
    {"name": "Setopati",        "url": "https://www.setopati.com/feed"},
    {"name": "Ratopati",        "url": "https://ratopati.com/rss"},
    {"name": "Nepal Khabar",    "url": "https://www.nepalkhabar.com/feed"},
    {"name": "Nagarik News",    "url": "https://nagariknews.nagariknetwork.com/feed"},
    {"name": "Nepal News",      "url": "https://nepalnews.com/feed"},
    {"name": "Naya Patrika",    "url": "https://www.nayapatrikadaily.com/feed"},
    {"name": "Himalkhabar",     "url": "https://himalkhabar.com/feed"},
    {"name": "Republica",       "url": "https://myrepublica.nagariknetwork.com/feed"},
    {"name": "Himalayan Times", "url": "https://thehimalayantimes.com/feed"},
    {"name": "Kathmandu Post",  "url": "https://kathmandupost.com/rss"},
    {"name": "BBC World",       "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Al Jazeera",      "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Karobar",         "url": "https://karobardaily.com/feed"},
    {"name": "ShareSansar",     "url": "https://www.sharesansar.com/feed"},
]

HOURS_BACK = 24

def scrape_news():
    print("Scraping news feeds...")
    all_articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_BACK)
    for feed_info in RSS_FEEDS:
        try:
            feed  = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if published is None or published >= cutoff:
                    title   = entry.get("title", "").strip()
                    summary = entry.get("summary", entry.get("description", "")).strip()
                    summary = re.sub(r"<[^>]+>", "", summary)[:200]
                    if title:
                        all_articles.append({
                            "source":   feed_info["name"],
                            "title":    title,
                            "summary":  summary,
                        })
                        count += 1
            print(f"  {feed_info['name']}: {count} articles")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {feed_info['name']}: Failed ({e})")
    print(f"Total articles collected: {len(all_articles)}")
    return all_articles

def pick_best_articles(articles):
    """Pick top articles per category to stay within Groq token limit."""
    nepal_sources = ["Kantipur","Onlinekhabar","Setopati","Ratopati",
                     "Nepal Khabar","Nagarik News","Nepal News",
                     "Naya Patrika","Himalkhabar","Republica",
                     "Himalayan Times","Kathmandu Post"]
    world_sources = ["BBC World","Al Jazeera"]
    biz_sources   = ["Karobar","ShareSansar"]

    nepal  = [a for a in articles if a["source"] in nepal_sources][:25]
    world  = [a for a in articles if a["source"] in world_sources][:8]
    biz    = [a for a in articles if a["source"] in biz_sources][:6]

    return nepal, world, biz

def format_articles(arts):
    text = ""
    for i, a in enumerate(arts, 1):
        text += f"{i}. [{a['source']}] {a['title']}\n"
        if a["summary"]:
            text += f"   {a['summary']}\n"
    return text

def write_script_with_groq(articles):
    if not articles:
        return "कुनै समाचार फेला परेन।"

    nepal, world, biz = pick_best_articles(articles)
    today    = datetime.now().strftime("%Y-%m-%d")
    day_name = datetime.now().strftime("%A")

    prompt = f"""तपाईं नेपालका एक वरिष्ठ समाचार एंकर हुनुहुन्छ। तलका समाचारबाट २०-२५ मिनेटको रेडियो/यूट्युब स्क्रिप्ट लेख्नुस्।

मिति: {today}, {day_name}

नियमहरू:
- कम्तीमा ५००० अक्षर लेख्नुस्
- स्टोरीटेलिङ शैली — हरेक समाचारलाई कथाजस्तो बनाउनुस्
- सानो समाचारमा पनि पृष्ठभूमि, कारण र असर थप्नुस्
- "साथीहरू", "हाम्रा दर्शकहरू" भनी श्रोतालाई सम्बोधन गर्नुस्
- शुद्ध नेपाली भाषा प्रयोग गर्नुस्
- हरेक खण्डबीच सहज transition राख्नुस्

स्क्रिप्टको ढाँचा:

[परिचय — १५ सेकेन्ड]
आकर्षक उद्घाटन। आजका मुख्य समाचारको टिजर।

🔴 प्रमुख समाचार — २ मिनेट
४-५ वटा सबैभन्दा महत्त्वपूर्ण समाचार। छोटो बुलेटिन शैलीमा।

🇳🇵 राष्ट्रिय समाचार — ८-१० मिनेट
७-८ वटा राष्ट्रिय समाचार। प्रत्येकलाई विस्तृत स्टोरीटेलिङ शैलीमा।
पृष्ठभूमि, कारण, असर र भविष्यको विश्लेषण थप्नुस्।

🌍 अन्तर्राष्ट्रिय समाचार — ४ मिनेट
३-४ वटा विश्व समाचार। नेपालमा पर्ने प्रभाव उल्लेख गर्नुस्।

💰 आर्थिक समाचार — ३ मिनेट
बजार, व्यापार, रोजगारी सम्बन्धी समाचार विस्तृत रूपमा।

🏏 खेलकुद — २ मिनेट
क्रिकेट, फुटबल र अन्य खेल समाचार।

🌤️ मौसम तथा अन्य — १ मिनेट
मौसम अपडेट र छोटा समाचार।

[समापन]
धन्यवाद सन्देश।

━━━ समाचार स्रोतहरू ━━━

🇳🇵 नेपाली समाचार ({len(nepal)} वटा):
{format_articles(nepal)}

🌍 अन्तर्राष्ट्रिय ({len(world)} वटा):
{format_articles(world)}

💰 आर्थिक ({len(biz)} वटा):
{format_articles(biz)}

━━━━━━━━━━━━━━━━━━━━━━━━
अब पूरा स्क्रिप्ट लेख्नुस् — कम्तीमा ५००० अक्षर:"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "तपाईं नेपालका एक वरिष्ठ समाचार एंकर हुनुहुन्छ। स्टोरीटेलिङ शैलीमा लामो, विस्तृत र आकर्षक समाचार स्क्रिप्ट लेख्नुहुन्छ। शुद्ध नेपाली भाषामा मात्र जवाफ दिनुस्। कम्तीमा ५००० अक्षरको स्क्रिप्ट लेख्नुस्।"
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
    header = (
        f"🇳🇵 ताजा समाचार स्क्रिप्ट\n"
        f"📅 {today}\n"
        f"📰 {article_count} समाचारबाट संकलित\n"
        f"📻 अवधि: २०-२५ मिनेट\n\n"
    )
    full_message = header + script
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
