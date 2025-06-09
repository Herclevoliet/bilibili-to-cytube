from flask import Flask, render_template, request
import yt_dlp

app = Flask(__name__)

def get_direct_url(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forceurl': True,
        'noplaylist': True,
        'format': 'bv+ba/best[ext=mp4]/best'  # 👈 önemli kısım
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
