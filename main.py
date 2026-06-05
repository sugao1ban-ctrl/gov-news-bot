import datetime
import ftplib
import json
import os
import re
import feedparser

# --- 1. 設定項目 ---
# 監視対象RSS
RSS_URLS = [
    "https://www.kantei.go.jp/rss/shinwaku.rdf",  # 首相官邸
    "https://www3.nhk.or.jp/rss/news/cat0.xml",  # NHK
]
TARGET_KEYWORDS = r"給付金|増税|法改正|記者会見|緊急事態|閣議決定|補正予算"

# ムームーサーバーのFTP接続情報（コントロールパネルで確認してください）
FTP_HOST = "ftp.muumuu-server.com"  # もしくはロリポップの指定ホスト
FTP_USER = "your_ftp_username"
FTP_PASS = "your_ftp_password"
FTP_DIR = "/web"  # 公開ディレクトリ（環境に合わせて変更してください）

# 一時保存ファイル名
HTML_FILE = "index.html"
JSON_FILE = "news.json"


# --- 2. ニュース取得・HTML生成ロジック ---
def collect_and_generate():
    matched_articles = []

    for url in RSS_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            summary = entry.get("summary", "")
            link = entry.link
            date = entry.get("published", "")

            if re.search(TARGET_KEYWORDS, title) or re.search(
                TARGET_KEYWORDS, summary
            ):
                matched_articles.append(
                    {
                        "title": title,
                        "summary": summary,
                        "link": link,
                        "date": date,
                    }
                )

    if not matched_articles:
        print("合致する新しいニュースはありませんでした。")
        return False

    # HTMLの生成
    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>政府・政治 注目発言速報</title>
    <style>
        body {{ font-family: sans-serif; background: #f5f7fa; color: #333; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ border-bottom: 2px solid #0056b3; padding-bottom: 10px; color: #0056b3; }}
        .update-time {{ font-size: 0.9em; color: #666; text-align: right; }}
        .article {{ border-bottom: 1px solid #eee; padding: 15px 0; }}
        .article-title {{ font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }}
        .article-title a {{ color: #111; text-decoration: none; }}
        .article-title a:hover {{ text-decoration: underline; color: #0056b3; }}
        .summary {{ font-size: 0.95em; color: #555; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>政府・政治 注目発言速報</h1>
        <p class="update-time">最終更新日時: {now_str}</p>
    </div>
    <div class="container" style="margin-top: 20px;">
    """

    for item in matched_articles:
        html_content += f"""
        <div class="article">
            <div class="article-title"><a href="{item['link']}" target="_blank">{item['title']}</a></div>
            <div class="summary">{item['summary']}</div>
            <div style="font-size:0.8em; color:#999; margin-top:5px;">ソース元: {item['date']}</div>
        </div>
        """

    html_content += """
    </div>
</body>
</html>
"""

    # ファイルに書き出し
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(matched_articles, f, ensure_ascii=False, indent=4)

    return True


# --- 3. FTPアップロードロジック ---
def upload_to_muumuu():
    print("ムームーサーバーへ接続中...")
    try:
        # FTP接続 (必要に応じて FTP_TLS を使用)
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(user=FTP_USER, passwd=FTP_PASS)

        # ターゲットディレクトリへ移動
        ftp.cwd(FTP_DIR)

        # HTMLアップロード
        with open(HTML_FILE, "rb") as f:
            ftp.storbinary(f"STOR {HTML_FILE}", f)
        print(f"{HTML_FILE} をアップロードしました。")

        # JSONアップロード
        with open(JSON_FILE, "rb") as f:
            ftp.storbinary(f"STOR {JSON_FILE}", f)
        print(f"{JSON_FILE} をアップロードしました。")

        ftp.quit()
        print("アップロード完了。接続を閉じました。")

    except Exception as e:
        print(f"FTP転送中にエラーが発生しました: {e}")


if __name__ == "__main__":
    if collect_and_generate():
        upload_to_muumuu()
