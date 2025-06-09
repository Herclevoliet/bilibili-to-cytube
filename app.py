import base64
import os
import urllib.parse

from flask import Flask, render_template, request, Response, abort, url_for, send_from_directory
import yt_dlp
import requests

# --- Çerez dosyasını ENV'den oluştur ---
encoded = os.environ.get('BILI_COOKIES')
if encoded:
    with open("bilicookies.txt", "wb") as f:
        f.write(base64.b64decode(encoded))

# --- Uygulama ve klasör hazırlıkları ---
app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- Video link’den doğrudan akış URL’i al ---
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
            direct = info.get('url')
            if direct and (direct.endswith('.m3u8') or direct.endswith('.mp4')):
                return direct
            formats = info.get('formats') or []
            # HLS manifest
            hls = [f for f in formats if f.get('protocol','').startswith('m3u8')]
            if hls:
                return hls[-1]['url']
            # Tam MP4 container
            mp4s = [f for f in formats if f.get('ext') == 'mp4' and f.get('url')]
            if mp4s:
                best_mp4 = sorted(mp4s, key=lambda f: f.get('height', 0))[-1]
                return best_mp4['url']
            # Fallback
            for f in formats:
                if f.get('url'):
                    return f['url']
            return 'No direct link found.'
    except Exception as e:
        return f"Error: {str(e)}"

# --- Ana sayfa (link dönüştürme) ---
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        urls = request.form['urls'].strip().split('\n')
        for u in urls:
            direct = get_direct_url(u.strip())
            results.append({'source': u.strip(), 'direct': direct})
    return render_template('index.html', results=results)

# --- Proxy endpoint (CORS için) ---
@app.route('/proxy')
def proxy():
    video_url = request.args.get('url')
    if not video_url:
        abort(400, "Missing url parameter")
    parsed = urllib.parse.urlparse(video_url)
    allowed_hosts = ('akamaized.net', 'bilivideo.com')
    if not any(d in parsed.netloc for d in allowed_hosts):
        abort(403, "Forbidden")
    upstream = requests.get(video_url, stream=True)
    headers = {
        'Content-Type': upstream.headers.get('Content-Type', 'application/octet-stream'),
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=86400',
    }
    return Response(upstream.iter_content(chunk_size=8192), headers=headers)

# --- İndir & birleştir MP4 endpoint’i ---
@app.route('/download', methods=['POST'])
def download_video():
    url = request.form.get('url')
    if not url:
        abort(400, "Missing url parameter")
    ydl_opts = {
        'format': 'bv*+ba/best',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            filename = f"{video_id}.mp4"
    except Exception as e:
        return f"Error during download: {e}", 500
    file_url = url_for('download_file', filename=filename, _external=True)
    return f"İndirilen dosya linki:<br><a href=\"{file_url}\">{file_url}</a>"

@app.route('/downloads/<path:filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=False)

# --- Uygulamayı çalıştır ---
if __name__ == '__main__':
    app.run(debug=True)
