import requests
import hashlib
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree

API_URL = "https://www.fukuyamabunkahall.jp/wp-json/wp/v2/concert"
SITE_URL = "https://www.fukuyamabunkahall.jp/concert/"
OUTPUT_FILE = "fukuyama_bunkahall.xml"

# 日本標準時（UTC+9）
JST = timezone(timedelta(hours=9))

params = {
    "per_page": 100,
    "orderby": "date",
    "order": "desc",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(API_URL, params=params, headers=headers, timeout=30)
print("REST API HTTP:", r.status_code)
r.raise_for_status()

posts = r.json()
print("取得件数:", len(posts))

rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "ふくやま文化ホール 公演情報"
SubElement(channel, "link").text = SITE_URL
SubElement(channel, "description").text = "ふくやま文化ホールの公演情報"
SubElement(channel, "language").text = "ja"

for i, post in enumerate(posts, 1):
    title = post.get("title", {}).get("rendered", "").strip()
    link = post.get("link", "").strip()
    date_str = post.get("date", "")

    if not title or not link or not date_str:
        continue

    # WordPressのdateはサイトのローカル時刻（日本時間）
    dt = datetime.fromisoformat(date_str).replace(tzinfo=JST)

    item = SubElement(channel, "item")

    SubElement(item, "title").text = title
    SubElement(item, "link").text = link

    guid = SubElement(item, "guid", isPermaLink="false")
    guid.text = hashlib.sha256(link.encode("utf-8")).hexdigest()

    SubElement(item, "pubDate").text = format_datetime(dt)

    print(f"[{i}] {date_str} {title}")

tree = ElementTree(rss)
tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print()
print("保存:", OUTPUT_FILE)