import datetime
import json
import os
import re
import feedparser
import requests

# --- 設定項目 ---
RSS_URLS = [
    "https://www.kantei.go.jp/rss/shinwaku.rdf",  # 首相官邸
    "https://www3.nhk.or.jp/rss/news/cat0.xml",  # NHK
]
# テスト用に、確実にヒットしやすいワード（「日本」など）を一時的に入れて実験するのをおすすめします
TARGET_KEYWORDS = r"給付金|増税|法改正|記者会見|緊急事態|閣議決定|補正予算|日本|アメリカ|原油|ナフサ|給付金|増税|法改正|記者会見|東京|天気|金曜"

JSON_FILE = "news.json"
HTML_FILE = "index.html"

# ムームーサーバー上の既存のnews.jsonのURL（あなたのドメインに合わせて変更してください）
EXISTING_JSON_URL = "https://jpnhack.xyz/gov-news-bot/news.json"


def collect_and_generate():
    # 1. サーバー上にある「過去の蓄積データ」をダウンロードして読み込む
    existing_articles = []
    try:
        response = requests.get(EXISTING_JSON_URL, timeout=10)
        if response.status_code == 200:
            existing_articles = response.json()
            print(f"過去のニュースを {len(existing_articles)} 件読み込みました。")
    except Exception as e:
        print(f"過去データの取得スキップ（初回、またはファイル未存在）: {e}")

    # 過去のURLリストを作成（重複して追加しないため）
    existing_links = {item["link"] for item in existing_articles}

    # 2. 最新のRSSからニュースを取得
    new_matched_count = 0
    for url in RSS_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            summary = entry.get("summary", "")
            link = entry.link
            date = entry.get("published", "")

            # キーワード判定
            if re.search(TARGET_KEYWORDS, title) or re.search(
                TARGET_KEYWORDS, summary
            ):
                # すでに保存済みのニュースでなければ追加
                if link not in existing_links:
                    existing_articles.append(
                        {
                            "title": title,
                            "summary": summary,
                            "link": link,
                            "date": date,
                        }
                    )
                    existing_links.add(link)
                    new_matched_count += 1

    print(f"新しく合致したニュース: {new_matched_count} 件")

    # 新しいニュースがなく、過去のデータも空なら何もしない
    if not existing_articles:
        print("表示すべきニュースがありません。")
        return False

    # ニュースを日付順（新しい順）に並び替える
    # ※日付フォーマットがバラバラな場合は簡易的な並び替えになります
    try:
        existing_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
    except Exception:
        pass

    # 3. JSONファイルとして書き出し（過去分 + 新着分）
    with open(
        os.path.join(os.path.dirname(__file__), JSON_FILE),
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(existing_articles, f, ensure_ascii=False, indent=4)

    # 4. HTMLファイルを生成
    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    display_keywords = TARGET_KEYWORDS.replace("|", ", ")

    # 登録されているRSSのURLを、HTMLの箇条書きの形に自動変換
    source_links_html = ""
    for url in RSS_URLS:
        source_name = "首相官邸 RSS" if "kantei.go.jp" in url else "NHKニュース RSS"
        source_links_html += (
            f'<li><a href="{url}" target="_blank">{source_name}</a></li>'
        )

    # 💡 変数の準備がすべて整ったあとに、HTMLの組み立て（f"""）を開始します
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>政府・政治 注目発言速報</title>
    <style>
        body {{ font-family: sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ border-bottom: 2px solid #0056b3; padding-bottom: 10px; color: #0056b3; margin-bottom: 5px; }}
        
        /* 設定情報エリアのスタイル */
        .info-box {{ background: #eef2f7; padding: 15px; border-radius: 4px; font-size: 0.9em; color: #4b5563; margin-bottom: 20px; border-left: 4px solid #0056b3; }}
        .info-box ul {{ margin: 5px 0 0 20px; padding: 0; }}
        .info-box li {{ margin-top: 5px; }}
        .info-box a {{ color: #0056b3; text-decoration: none; font-weight: bold; }}
        .info-box a:hover {{ text-decoration: underline; }}
        
        .article {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
        .article-title a {{ color: #111; text-decoration: none; font-weight: bold; font-size: 1.1em; }}
        .summary {{ color: #555; font-size: 0.95em; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>政府・政治 注目発言速報</h1>
        
        <div class="info-box">
            <div style="margin-bottom: 8px;"><strong>現在の監視キーワード：</strong> {display_keywords}</div>
            <div><strong>情報取得ソース（RSS）：</strong></div>
            <ul>
                {source_links_html}
            </ul>
        </div>

        <p style="text-align:right; color:#666; font-size: 0.9em;">最終更新: {now_str} (30分おき自動更新)</p>
    """

    for item in existing_articles:
        html_content += f"""
        <div class="article">
            <div class="article-title"><a href="{item['link']}" target="_blank">{item['title']}</a></div>
            <div class="summary">{item['summary']}</div>
            <div style="font-size:0.8em; color:#999; margin-top:5px;">発表日時: {item['date']}</div>
        </div>
        """

    html_content += """
    </div>
</body>
</html>
"""

    with open(
        os.path.join(os.path.dirname(__file__), HTML_FILE),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(html_content)

    return True


if __name__ == "__main__":
    if collect_and_generate():
        print("ファイルの生成が正常に完了しました。")
    else:
        print("更新が必要なニュースはありませんでした。")
