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

def get_direct_url(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forceurl': True,
        'noplaylist': True,
        'cookiefile': 'bilicookies.txt',
        'source_address': '0.0.0.0',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # 1) Direkt info.url varsa ve manifest ya da mp4 ise kullan
            direct = info.get('url')
            if direct and (direct.endswith('.m3u8') or direct.endswith('.mp4')):
                return direct
            # 2) Tüm formatlar
            formats = info.get('formats') or []
            # 2a) HLS manifestler (protocol m3u8_native veya m3u8)
            hls = [f for f in formats if f.get('protocol', '').startswith('m3u8')]
            if hls:
                return hls[-1]['url']
            # 2b) Tam MP4 kapsayıcı (ext mp4)
            mp4s = [f for f in formats if f.get('ext') == 'mp4' and f.get('url')]
            if mp4s:
                best_mp4 = sorted(mp4s, key=lambda f: f.get('height', 0))[-1]
                return best_mp4['url']
            # 3) Hiçbiri yoksa ilk bulunan URL
            for f in formats:
                if f.get('url'):
                    return f['url']
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
