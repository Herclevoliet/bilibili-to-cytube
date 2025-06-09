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
        # mp4’ü tercih et, yoksa genel en iyi seçeneği al
        'format': 'bv*+ba/best[ext=mp4]/best',
        'cookiefile': 'bilicookies.txt',
        'source_address': '0.0.0.0',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('url', 'No direct link found.')
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
