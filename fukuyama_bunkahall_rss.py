import requests
import hashlib
import time
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


# --------------------------------------------------
# REST API取得
#
# タイムアウト・403・503などの場合は再試行。
# それでも取得できなければ既存RSSを維持して正常終了。
# --------------------------------------------------

response = None
MAX_RETRIES = 3

for attempt in range(1, MAX_RETRIES + 1):

    try:
        print(f"REST API取得 {attempt}/{MAX_RETRIES}")

        r = requests.get(
            API_URL,
            params=params,
            headers=headers,
            timeout=30
        )

        print("REST API HTTP:", r.status_code)

        r.raise_for_status()

        response = r
        break

    except requests.RequestException as e:

        print("取得失敗:", e)

        if attempt < MAX_RETRIES:
            print("10秒待って再試行します。")
            time.sleep(10)


# --------------------------------------------------
# 3回とも取得できなかった場合
# --------------------------------------------------

if response is None:

    print()
    print("ふくやま文化ホールのREST APIを取得できませんでした。")
    print("今回はRSSを更新しません。")
    print("既存の fukuyama_bunkahall.xml をそのまま維持します。")
    print("次回の定期実行で再度確認します。")

    # GitHub ActionsはSuccessとして終了
    raise SystemExit(0)


# --------------------------------------------------
# JSON解析
# --------------------------------------------------

try:
    posts = response.json()

except (ValueError, requests.exceptions.JSONDecodeError) as e:

    print()
    print("REST APIのJSON解析に失敗しました:", e)
    print("今回はRSSを更新しません。")
    print("既存の fukuyama_bunkahall.xml をそのまま維持します。")

    raise SystemExit(0)


print("取得件数:", len(posts))


# --------------------------------------------------
# 0件の場合は既存RSSを上書きしない
# --------------------------------------------------

if len(posts) == 0:

    print()
    print("公演情報が0件でした。")
    print("異常取得の可能性があるため今回はRSSを更新しません。")
    print("既存の fukuyama_bunkahall.xml をそのまま維持します。")

    raise SystemExit(0)


# --------------------------------------------------
# RSS作成
# --------------------------------------------------

rss = Element("rss", version="2.0")
channel = SubElement(rss, "channel")

SubElement(channel, "title").text = "ふくやま文化ホール 公演情報"
SubElement(channel, "link").text = SITE_URL
SubElement(channel, "description").text = "ふくやま文化ホールの公演情報"
SubElement(channel, "language").text = "ja"

valid_count = 0

for i, post in enumerate(posts, 1):

    title = post.get(
        "title",
        {}
    ).get(
        "rendered",
        ""
    ).strip()

    link = post.get(
        "link",
        ""
    ).strip()

    date_str = post.get(
        "date",
        ""
    )

    if not title or not link or not date_str:
        continue

    try:
        # WordPressのdateはサイトのローカル時刻（日本時間）
        dt = datetime.fromisoformat(
            date_str
        ).replace(
            tzinfo=JST
        )

    except ValueError:
        print(
            f"[スキップ] 日付解析失敗: "
            f"{date_str} {title}"
        )
        continue

    item = SubElement(
        channel,
        "item"
    )

    SubElement(
        item,
        "title"
    ).text = title

    SubElement(
        item,
        "link"
    ).text = link

    guid = SubElement(
        item,
        "guid",
        isPermaLink="false"
    )

    guid.text = hashlib.sha256(
        link.encode("utf-8")
    ).hexdigest()

    SubElement(
        item,
        "pubDate"
    ).text = format_datetime(dt)

    valid_count += 1

    print(
        f"[{i}] "
        f"{date_str} "
        f"{title}"
    )


# --------------------------------------------------
# 有効な記事が0件なら既存RSSを上書きしない
# --------------------------------------------------

if valid_count == 0:

    print()
    print("有効な公演情報を1件も取得できませんでした。")
    print("今回はRSSを更新しません。")
    print("既存の fukuyama_bunkahall.xml をそのまま維持します。")

    raise SystemExit(0)


# --------------------------------------------------
# XML保存
#
# 正常に取得・解析できた場合だけ上書き
# --------------------------------------------------

tree = ElementTree(rss)

tree.write(
    OUTPUT_FILE,
    encoding="utf-8",
    xml_declaration=True
)

print()
print("RSS作成成功")
print("有効件数:", valid_count)
print("保存:", OUTPUT_FILE)
