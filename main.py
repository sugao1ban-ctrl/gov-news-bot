import os
import requests
import json
from datetime import datetime
import pytz
import feedparser  # 💡 特殊な省庁RSSも確実に解析するライブラリ

# 環境変数から設定を取得
KEYWORDS_JSON_URL = "https://jpnhack.xyz/gov-news-bot/keywords.json"
EXISTING_JSON_URL = "https://jpnhack.xyz/gov-news-bot/news.json"

# 💡 投資用・国策特化型ソースリスト
RSS_URLS = [
    "https://www.cas.go.jp/jp/seisaku/houan/index.xml",  # 内閣官房
    "https://www.meti.go.jp/press/index.xml",           # 経済産業省
    "https://www.fsa.go.jp/news/news.xml",              # 金融庁
    "https://www.digital.go.jp/news.xml",               # デジタル庁
    "https://www.nikkan.co.jp/rss/flash.xml"            # 日刊工業新聞
]

def main():
    print("--- ニュース取得ロボット起動 (feedparser搭載版) ---")

    # 1. サーバーから最新のキーワードJSONを読み込む
    TARGET_KEYWORDS = []
    try:
        req = requests.get(KEYWORDS_JSON_URL, timeout=10)
        req.encoding = 'utf-8'
        if req.status_code == 200:
            TARGET_KEYWORDS = req.json()
    except Exception as e:
        print(f"キーワードJSONの取得に失敗: {e}")

    if not TARGET_KEYWORDS:
        TARGET_KEYWORDS = ["給付金", "増税", "法改正"]

    # 2. サーバー上にある「過去のニュースデータ」を読み込む
    existing_articles = []
    try:
        response = requests.get(EXISTING_JSON_URL, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            existing_articles = response.json()
    except Exception as e:
        print(f"過去データの取得スキップ: {e}")

    existing_links = {item["link"] for item in existing_articles}

    # 3. 各RSSフィードから最新ニュースをスキャン
    new_count = 0
    for url in RSS_URLS:
        print(f"フィード巡回中: {url}")
        try:
            # 💡 feedparserを使って安全かつ確実にパース
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                summary = getattr(entry, 'summary', '').strip()
                
                # 概要が空の場合は既存の他フィールドから補完を試みる
                if not summary and hasattr(entry, 'description'):
                    summary = entry.description.strip()
                
                # HTMLタグが混入している場合は簡易除去
                summary = re.sub(r'<[^>]*?>', '', summary)

                if title and link and (link not in existing_links):
                    existing_articles.append({
                        "title": title,
                        "link": link,
                        "summary": summary[:200], # 長すぎる場合は200文字でカット
                        "fetched_at": datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M')
                    })
                    existing_links.add(link)
                    new_count += 1
        except Exception as e:
            print(f"フィード取得エラー ({url}): {e}")

    print(f"新着ニュースを {new_count} 件追加しました。合計: {len(existing_articles)} 件")

    # 最大蓄積数を 500件 に設定
    existing_articles = existing_articles[-500:]

    # 4. news.json を保存出力
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(existing_articles, f, ensure_ascii=False, indent=4)

    # 5. index.html を生成
    jst = pytz.timezone('Asia/Tokyo')
    now_str = datetime.now(jst).strftime('%Y/%m/%d %H:%M:%S')

    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>省庁・閣議ニュース自動監視ボット</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; color: #111827; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e5e7eb; padding-bottom: 15px; margin-bottom: 25px; }}
        h1 {{ font-size: 1.5em; margin: 0; color: #1e3a8a; }}
        .btn-setting {{ background-color: #3b82f6; color: white; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 0.9em; }}
        .btn-setting:hover {{ background-color: #2563eb; }}
        .keyword-tag-box {{ background: #eff6ff; border: 1px solid #bfdbfe; padding: 12px; border-radius: 6px; margin-bottom: 20px; font-size: 0.95em; }}
        .tag {{ background: #3b82f6; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 5px; font-size: 0.85em; }}
        .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: none; }}
        .card-title {{ margin: 0 0 10px 0; font-size: 1.2em; }}
        .card-title a {{ color: #2563eb; text-decoration: none; }}
        .card-title a:hover {{ text-decoration: underline; }}
        .card-summary {{ color: #4b5563; font-size: 0.95em; line-height: 1.5; margin-bottom: 10px; }}
        .card-meta {{ color: #9ca3af; font-size: 0.85em; text-align: right; }}
        #no-news {{ text-align: center; color: #6b7280; padding: 40px; display: none; font-weight: bold; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>🏛️ 省庁ニュース 自動監視ボット</h1>
        <a href="admin.php" class="btn-setting" target="_blank">⚙ キーワードを変更する</a>
    </header>

    <div class="keyword-tag-box">
        📡 <strong>現在のリアルタイム監視キーワード:</strong> <span id="current-tags">読み込み中...</span>
    </div>

    <div style="margin-bottom: 25px;">
        <button onclick="initializeRealtimeEngine();" style="width: 100%; background-color: #10b981; color: white; border: none; padding: 12px; border-radius: 6px; font-size: 1em; font-weight: bold; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            🔄 情報を更新する（最新の状態にする）
        </button>
    </div>

    <div id="news-list"></div>
    <div id="no-news">現在、キーワードに一致する新着ニュースはありません。</div>

    <footer style="margin-top:40px; border-top:1px solid #e5e7eb; padding-top:15px;">
        <p style="text-align:right; color:#666; font-size: 0.9em;">システム同期時刻: {now_str} (30分おきRSS巡回)</p>
    </footer>
</div>

<script>
async function initializeRealtimeEngine() {{
    const newsListContainer = document.getElementById('news-list');
    const tagsContainer = document.getElementById('current-tags');
    const noNewsMessage = document.getElementById('no-news');

    try {{
        const cacheBuster = "?t=" + new Date().getTime();
        const [keywordsRes, newsRes] = await Promise.all([
            fetch('keywords.json' + cacheBuster),
            fetch('news.json' + cacheBuster)
        ]);

        const keywords = await keywordsRes.json();
        const articles = await newsRes.json();

        tagsContainer.innerHTML = keywords.map(k => `<span class="tag">${{k}}</span>`).join('');

        if (keywords.length === 0) {{
            noNewsMessage.style.display = 'block';
            return;
        }}

        const pattern = new RegExp(keywords.join('|'), 'i');
        let matchCount = 0;

        newsListContainer.innerHTML = '';
        articles.forEach(article => {{
            const inTitle = pattern.test(article.title || '');
            const inSummary = pattern.test(article.summary || '');

            if (inTitle || inSummary) {{
                matchCount++;

                let sourceName = "不明なソース";
                const urlStr = article.link || "";
                if (urlStr.includes("cas.go.jp")) sourceName = "🏛️ 内閣官房";
                else if (urlStr.includes("meti.go.jp")) sourceName = "🏭 経済産業省";
                else if (urlStr.includes("fsa.go.jp")) sourceName = "📈 金融庁";
                else if (urlStr.includes("digital.go.jp")) sourceName = "💻 デジタル庁";
                else if (urlStr.includes("nikkan.co.jp")) sourceName = "📰 日刊工業新聞";
                else if (urlStr.includes("nikkei.com")) sourceName = "📰 日本経済新聞";
                else if (urlStr.includes("impress")) sourceName = "📱 Impress Watch";

                const card = document.createElement('div');
                card.className = 'card';
                card.style.display = 'block';
                card.innerHTML = `
                    <h3 class="card-title"><a href="${{article.link}}" target="_blank">${{article.title}}</a></h3>
                    
                    <div style="margin-bottom: 12px; font-size: 0.85em;">
                        <span style="color: #6b7280;">情報元:</span> 
                        <a href="${{article.link}}" target="_blank" style="background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                            \${{sourceName}}
                        </a>
                    </div>

                    <div class="card-summary">${{article.summary || '概要はありません。'}}</div>
                    <div class="card-meta">取得日時: ${{article.fetched_at}}</div>
                `;
                newsListContainer.appendChild(card);
            }}
        }});

        if (matchCount === 0) {{
            noNewsMessage.style.display = 'block';
        }}

    }} catch (error) {{
        console.error("0秒反映エンジンの稼働エラー:", error);
        tagsContainer.innerText = "データの読み込みに失敗しました。";
    }}
}}

window.addEventListener('DOMContentLoaded', initializeRealtimeEngine);
</script>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("🌟 index.html の生成が完了しました。")

if __name__ == "__main__":
    main()
