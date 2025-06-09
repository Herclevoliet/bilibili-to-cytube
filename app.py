import base64
import os
import urllib.parse

from flask import Flask, render_template, request, Response, abort
import yt_dlp
import requests

# --- Base64 ile gönderilen çerezleri çözüp dosyaya yaz ---
encoded = os.environ.get('BILI_COOKIES')
if encoded:
    with open("bilicookies.txt", "wb") as f:
        f.write(base64.b64decode(encoded))

app = Flask(__name__)

# --- Doğrudan video linkini almak için fonksiyon ---
def get_direct_url(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forceurl': True,
        'noplaylist': True,
        'format': 'bv*+ba/best[ext=mp4]/best',
        'cookiefile': 'bilicookies.txt',
        'source_address': '0.0.0.0',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Öncelikle info['url']
            direct = info.get('url')
            if direct:
                return direct
            # Yoksa formats listesinden mp4 seç
            formats = info.get('formats') or []
            mp4_formats = [f for f in formats if f.get('ext') == 'mp4' and f.get('url')]
            if mp4_formats:
                best_mp4 = sorted(mp4_formats, key=lambda f: f.get('height', 0))[-1]
                return best_mp4['url']
            # Fallback
            if formats:
                return formats[-1].get('url', 'No direct link found.')
            return 'No direct link found.'
    except Exception as e:
        return f"Error: {str(e)}"

# --- Ana sayfa route’u ---
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        urls = request.form['urls'].strip().split('\n')
        for url in urls:
            direct = get_direct_url(url.strip())
            results.append({'source': url.strip(), 'direct': direct})
    return render_template('index.html', results=results)

# --- Basit proxy route’u CORS için ---
@app.route('/proxy')
def proxy():
    video_url = request.args.get('url')
    if not video_url:
        abort(400, "Missing url parameter")
    parsed = urllib.parse.urlparse(video_url)
    # Artık hem akamaized.net hem bilivideo.com mirror'larını kabul ediyoruz
    allowed_hosts = ('akamaized.net', 'bilivideo.com')
    if not any(domain in parsed.netloc for domain in allowed_hosts):
        abort(403, "Forbidden")
    upstream = requests.get(video_url, stream=True)
    headers = {
        'Content-Type': upstream.headers.get('Content-Type', 'application/octet-stream'),
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=86400',
    }
    return Response(upstream.iter_content(chunk_size=8192), headers=headers)

# --- Uygulamayı çalıştır ---
if __name__ == '__main__':
    app.run(debug=True)
