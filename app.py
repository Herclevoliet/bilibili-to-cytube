import base64
import os
from flask import Flask, render_template, request
import yt_dlp

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
        # Önce MP4 akışları, değilse en iyisi
        'format': 'bv*+ba/best[ext=mp4]/best',
        'cookiefile': 'bilicookies.txt',
        'source_address': '0.0.0.0',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # 1) Direkt url alanı varsa onu döndür
            direct = info.get('url')
            if direct:
                return direct
            # 2) formats listesi varsa içinden ext=mp4 olanı seç
            formats = info.get('formats') or []
            # MP4 ve HTTPS protokollü olanları filtrele
            mp4_formats = [f for f in formats if f.get('ext') == 'mp4' and f.get('url')]
            if mp4_formats:
                # En yüksek çözünürlükte olanı seç
                best_mp4 = sorted(mp4_formats, key=lambda f: f.get('height', 0))[-1]
                return best_mp4['url']
            # 3) Hiç MP4 yoksa, formats listesinden sonuncuyu döndür
            if formats:
                return formats[-1].get('url', 'No direct link found.')
            return 'No direct link found.'
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        urls = request.form['urls'].strip().split('\n')
        for url in urls:
            direct = get_direct_url(url.strip())
            results.append({'source': url.strip(), 'direct': direct})
    return render_template('index.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)
