import os
import requests
import json
from datetime import datetime
import pytz
import feedparser
import re
import socket

# 💡 【超重要】すべての通信（feedparser含む）の待ち時間を最大「2秒」に世界一律で強制制限する
socket.setdefaulttimeout(2.0)

KEYWORDS_JSON_URL = "https://jpnhack.xyz/gov-news-bot/keywords.json"
EXISTING_JSON_URL = "https://jpnhack.xyz/gov-news-bot/news.json"

# 各省庁・専門メディアのソース
RSS_URLS = [
    "https://www.cas.go.jp/jp/seisaku/houan/index.xml",  # 内閣官房
    "https://www.meti.go.jp/press/index.xml",           # 経済産業省
    "https://www.fsa.go.jp/news/news.xml",              # 金融庁
    "https://www.digital.go.jp/news.xml",               # デジタル庁
    "https://www.nikkan.co.jp/rss/flash.xml"            # 日刊工業新聞
]

def main():
    print("--- ニュース取得ロボット起動 (完全タイムアウト制御版) ---")

    # 1. サーバーから最新のキーワードJSONを読み込む
    TARGET_KEYWORDS = []
    try:
        req = requests.get(KEYWORDS_JSON_URL, timeout=(2.0, 2.0))
        req.encoding = 'utf-8'
        if req.status_code == 200:
            TARGET_KEYWORDS = req.json()
            print(f"ロリポップから読み込んだキーワード: {TARGET_KEYWORDS}")
    except Exception as e:
        print(f"⚠️ キーワード取得スキップ（タイムアウトまたはブロック）: {e}")

    # 2. 既存のニュースデータを読み込む
    existing_articles = []
    try:
        response = requests.get(EXISTING_JSON_URL, timeout=(2.0, 2.0))
        response.encoding = 'utf-8'
        if response.status_code == 200:
            existing_articles = response.json()
    except Exception as e:
        print(f"既存ニュース読み込みスキップ: {e}")

    existing_links = {item["link"] for item in existing_articles if "link" in item}

    # 3. 各RSSフィードから最新ニュースをスキャン（2秒で冷酷に見切る）
    new_count = 0
    for url in RSS_URLS:
        print(f"📡 巡回中（最大2秒制限）: {url}")
        try:
            # socketのグローバルタイムアウトがここ（内部のurllib）に強制適用されます
            feed = feedparser.parse(url)
            
            if not feed.entries:
                print(f"   ℹ️ 応答なし、またはデータが空のためスキップします。")
                continue

            for entry in feed.entries:
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                summary = getattr(entry, 'summary', '').strip()
                
                if not summary and hasattr(entry, 'description'):
                    summary = entry.description.strip()
                
                summary = re.sub(r'<[^>]*?>', '', summary)

                if title and link and (link not in existing_links):
                    existing_articles.append({
                        "title": title,
                        "link": link,
                        "summary": summary[:200],
                        "fetched_at": datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M')
                    })
                    existing_links.add(link)
                    new_count += 1
        except Exception as e:
            print(f"   ❌ 2秒以内に応答がなかったため強制切断しました: {e}")

    print(f"📝 スキャン完了：新着ニュースを {new_count} 件追加しました。総蓄積数: {len(existing_articles)} 件")
    existing_articles = existing_articles[-500:]

    # 4. news.json をローカルに保存出力
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
            fetch('keywords.json' + cacheBuster).then(r => r.json()).catch(() => []),
            fetch('news.json' + cacheBuster).then(r => r.json()).catch(() => [])
        ]);

        let keywords = [];
        if (Array.isArray(keywordsRes)) {{
            keywords = keywordsRes;
        }} else if (typeof keywordsRes === 'object' && keywordsRes !== null) {{
            keywords = Object.values(keywordsRes);
        }} else if (typeof keywordsRes === 'string') {{
            keywords = [keywordsRes];
        }}
        
        keywords = keywords.map(k => String(k).trim()).filter(k => k !== "");

        const showAllMode = keywords.length === 0 || keywords.includes("の") || keywords.includes("について");

        if (keywords.length === 0) {{
            tagsContainer.innerHTML = '<span style="color:#6b7280;">未設定（全件表示モード）</span>';
        }} else {{
            tagsContainer.innerHTML = keywords.map(k => `<span class="tag">${{k}}</span>`).join('');
        }}

        const pattern = keywords.length > 0 ? new RegExp(keywords.map(k => k.replace(/[-\/\\\\^$*+?.()|[\]{{}}]/g, '\\\\$&')).join('|'), 'i') : null;
        let matchCount = 0;

        newsListContainer.innerHTML = '';
        noNewsMessage.style.display = 'none';

        newsRes.forEach(article => {{
            const inTitle = pattern ? pattern.test(article.title || '') : false;
            const inSummary = pattern ? pattern.test(article.summary || '') : false;

            if (showAllMode || inTitle || inSummary) {{
                matchCount++;

                let sourceName = "🏛️ 省庁ニュース";
                const urlStr = article.link || "";
                if (urlStr.includes("cas.go.jp")) sourceName = "🏛️ 内閣官房";
                else if (urlStr.includes("meti.go.jp")) sourceName = "🏭 経済産業省";
                else if (urlStr.includes("fsa.go.jp")) sourceName = "📈 金融庁";
                else if (urlStr.includes("digital.go.jp")) sourceName = "💻 デジタル庁";
                else if (urlStr.includes("nikkan.co.jp")) sourceName = "📰 日刊工業新聞";

                const card = document.createElement('div');
                card.className = 'card';
                card.style.display = 'block';
                card.innerHTML = `
                    <h3 class="card-title"><a href="${{article.link}}" target="_blank">${{article.title}}</a></h3>
                    <div style="margin-bottom: 12px; font-size: 0.85em;">
                        <span style="color: #6b7280;">情報元:</span> 
                        <span style="background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 4px; font-weight: bold;">
                            \${{sourceName}}
                        </span>
                    </div>
                    <div class="card-summary">\${{article.summary || '概要はありません。'}}</div>
                    <div class="card-meta">取得日時: \${{article.fetched_at}}</div>
                `;
                newsListContainer.appendChild(card);
            }}
        }});

        if (matchCount === 0) {{
            noNewsMessage.style.display = 'block';
        }}

    }} catch (error) {{
        console.error("エンジン駆動エラー:", error);
        tagsContainer.innerText = "エラーが発生しました。";
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
