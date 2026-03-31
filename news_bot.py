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

SYSTEM_PROMPT = "तपाईं नेपालका एक वरिष्ठ समाचार एंकर हुनुहुन्छ। स्टोरीटेलिङ शैलीमा विस्तृत र आकर्षक समाचार स्क्रिप्ट लेख्नुहुन्छ। शुद्ध नेपाली भाषामा मात्र जवाफ दिनुस्।"

# ── Scrape ─────────────────────────────────────────────────────
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
                            "source":  feed_info["name"],
                            "title":   title,
                            "summary": summary,
                        })
                        count += 1
            print(f"  {feed_info['name']}: {count} articles")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {feed_info['name']}: Failed ({e})")
    print(f"Total articles: {len(all_articles)}")
    return all_articles

# ── Format article list ────────────────────────────────────────
def fmt(arts, limit=15):
    out = ""
    for i, a in enumerate(arts[:limit], 1):
        out += f"{i}. [{a['source']}] {a['title']}\n"
        if a["summary"]:
            out += f"   {a['summary']}\n"
    return out

# ── Single Groq call ───────────────────────────────────────────
def groq_call(prompt, max_tokens=2500):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json"
    }
    payload = {
        "model":    "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        "temperature": 0.75,
        "max_tokens":  max_tokens
    }
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=90
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        print(f"  Section done: {len(text)} chars")
        return text
    except Exception as e:
        err = str(e).replace(GROQ_API_KEY, "***")
        print(f"  Groq call failed: {err}")
        return ""

# ── Build full script in sections ─────────────────────────────
def build_full_script(articles):
    today = datetime.now().strftime("%Y-%m-%d")
    day   = datetime.now().strftime("%A")

    nepal  = [a for a in articles if a["source"] not in
              ["BBC World","Al Jazeera","Karobar","ShareSansar"]]
    world  = [a for a in articles if a["source"] in ["BBC World","Al Jazeera"]]
    biz    = [a for a in articles if a["source"] in ["Karobar","ShareSansar"]]

    sections = []

    # ── Section 1: Intro + Pramukh Samachar ───────────────────
    print("Writing Section 1: Intro + Pramukh Samachar...")
    p1 = groq_call(f"""मिति: {today}, {day}

तलका समाचारबाट यो स्क्रिप्ट लेख्नुस्:

[परिचय — १५ सेकेन्ड]
आकर्षक उद्घाटन वाक्यले सुरु गर्नुस्। आजका मुख्य ३ समाचारको टिजर दिनुस्। "नमस्कार साथीहरू, म [एंकर] बोल्दैछु" भनी सुरु गर्नुस्।

🔴 प्रमुख समाचार — २ मिनेट
तलका समाचारबाट सबैभन्दा महत्त्वपूर्ण ५ वटा छानेर बुलेटिन शैलीमा लेख्नुस्। प्रत्येक समाचार ३-४ वाक्यमा। स्पष्ट र प्रभावशाली।

समाचारहरू:
{fmt(nepal, 20)}

कम्तीमा ८०० अक्षर लेख्नुस्।""", max_tokens=1500)
    sections.append(p1)
    time.sleep(2)

    # ── Section 2: Rastriya Samachar ──────────────────────────
    print("Writing Section 2: Rastriya Samachar...")
    p2 = groq_call(f"""मिति: {today}

🇳🇵 राष्ट्रिय समाचार — ८-१० मिनेट

तलका नेपाली समाचारबाट ७-८ वटा छानेर स्टोरीटेलिङ शैलीमा लेख्नुस्।

हरेक समाचारको लागि:
- "साथीहरू, अब कुरा गरौं..." भनी सुरु गर्नुस्
- पृष्ठभूमि र इतिहास दिनुस्
- घटनाको कारण र असर विश्लेषण गर्नुस्
- भविष्यमा के हुन सक्छ भनी बताउनुस्
- प्रत्येक समाचार कम्तीमा १५० अक्षरमा लेख्नुस्

समाचारहरू:
{fmt(nepal, 20)}

कम्तीमा २००० अक्षर लेख्नुस्।""", max_tokens=3000)
    sections.append(p2)
    time.sleep(2)

    # ── Section 3: International + Business ───────────────────
    print("Writing Section 3: International + Business...")
    p3 = groq_call(f"""मिति: {today}

🌍 अन्तर्राष्ट्रिय समाचार — ४ मिनेट

तलका विश्व समाचारबाट ३-४ वटा छानेर लेख्नुस्। नेपालमा पर्ने प्रभाव अनिवार्य उल्लेख गर्नुस्। प्रत्येक समाचार कम्तीमा १५० अक्षरमा।

अन्तर्राष्ट्रिय समाचार:
{fmt(world, 8)}

💰 आर्थिक तथा व्यापार समाचार — ३ मिनेट

तलका आर्थिक समाचारबाट ३-४ वटा छानेर विस्तृत रूपमा लेख्नुस्। शेयर बजार, बैंकिङ, व्यापार, रोजगारीको जानकारी सरल भाषामा बुझाउनुस्।

आर्थिक समाचार:
{fmt(biz, 6)}

यदि आर्थिक समाचार कम छन् भने नेपाली समाचारबाट आर्थिक विषयका समाचार छान्नुस्:
{fmt([a for a in nepal if any(w in a['title'].lower() for w in ['बजार','बैंक','आर्थिक','व्यापार','रुपैयाँ','शेयर','लगानी','रोजगार'])], 5)}

कम्तीमा १५०० अक्षर लेख्नुस्।""", max_tokens=2500)
    sections.append(p3)
    time.sleep(2)

    # ── Section 4: Sports + Weather + Closing ─────────────────
    print("Writing Section 4: Sports + Weather + Closing...")
    p4 = groq_call(f"""मिति: {today}

🏏 खेलकुद समाचार — २ मिनेट

तलका समाचारबाट खेलकुद सम्बन्धी समाचार छानेर लेख्नुस्। क्रिकेट, फुटबल, र नेपाली खेलाडीका बारेमा लेख्नुस्।

{fmt([a for a in nepal if any(w in a['title'].lower() for w in ['क्रिकेट','फुटबल','खेल','खेलाडी','टिम','मैच','आइपीएल','विश्वकप'])], 6)}

🌤️ मौसम तथा अन्य छोटा समाचार — १ मिनेट

नेपालको आजको मौसम अवस्था बताउनुस् (वसन्त ऋतु, चैत महिना, तराईमा गर्मी, पहाडमा मनपर्दो मौसम)। तलका अन्य समाचार एक-दुई वाक्यमा:

{fmt(nepal[20:], 8)}

[समापन — १५ सेकेन्ड]
हार्दिक धन्यवाद सन्देश। अर्को अपडेटको जानकारी। च्यानल सब्स्क्राइब गर्न आग्रह।

कम्तीमा ८०० अक्षर लेख्नुस्।""", max_tokens=1500)
    sections.append(p4)

    # ── Combine all sections ───────────────────────────────────
    full_script = "\n\n".join(s for s in sections if s)
    total_chars = len(full_script)
    print(f"\nTotal script length: {total_chars} characters")

    if total_chars < 3000:
        print("WARNING: Script shorter than expected!")

    return full_script

# ── Send to Telegram ───────────────────────────────────────────
def send_to_telegram(script, article_count):
    print("Sending to Telegram...")
    today  = datetime.now().strftime("%Y/%m/%d %H:%M")
    header = (
        f"🇳🇵 ताजा समाचार स्क्रिप्ट\n"
        f"📅 {today}\n"
        f"📰 {article_count} समाचारबाट संकलित\n"
        f"📻 अवधि: २०-२५ मिनेट\n"
        f"{'─'*30}\n\n"
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
    print(f"Sending {len(parts)} messages to Telegram...")
    for i, part in enumerate(parts):
        try:
            resp = requests.post(
                url,
                json={"chat_id": TELEGRAM_CHAT_ID, "text": part},
                timeout=30
            )
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
    print(f"Saved: {filename} ({len(script)} chars)")

# ── Main ───────────────────────────────────────────────────────
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
    script   = build_full_script(articles)
    save_to_file(script)
    send_to_telegram(script, len(articles))
    print("\nDone! Check your Telegram.")

if __name__ == "__main__":
    main()
