import os
import time
import shutil
import uuid
import yt_dlp
from flask import Flask, render_template, request, send_file, jsonify
import config as cfg

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

settings = cfg.load()

DOWNLOAD_DIR = os.path.join(BASE_DIR, settings.get('download_path', 'downloads'))
FFMPEG_DIR = os.path.join(BASE_DIR, 'bin')

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FFMPEG_PATH = shutil.which('ffmpeg', path=FFMPEG_DIR) or shutil.which('ffmpeg')
FFPROBE_PATH = shutil.which('ffprobe', path=FFMPEG_DIR) or shutil.which('ffprobe')

def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded = d.get('downloaded_bytes', 0)
        if total:
            pct = downloaded / total * 100
            print(f"  [{d['filename']}] {pct:.1f}%")
    elif d['status'] == 'finished':
        print(f"  Download finished, processing...")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return 'Нет данных', 400
        cfg.save(data)
        global settings, DOWNLOAD_DIR
        settings = cfg.load()
        new_dir = os.path.join(BASE_DIR, settings.get('download_path', 'downloads'))
        if new_dir != DOWNLOAD_DIR:
            DOWNLOAD_DIR = new_dir
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        return jsonify(settings)
    return jsonify(settings)

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url', '').strip()
    fmt = request.form.get('format', settings.get('default_format', 'mp4'))
    quality = request.form.get('quality', settings.get('max_quality', '1080'))

    if not url:
        return 'Вставь ссылку на YouTube', 400

    download_id = uuid.uuid4().hex[:8]
    download_path = os.path.join(DOWNLOAD_DIR, download_id)
    os.makedirs(download_path, exist_ok=True)

    outtmpl = os.path.join(download_path, '%(title)s.%(ext)s')

    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
    }

    if FFMPEG_PATH:
        ydl_opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)

    if fmt == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        if quality == 'max':
            ydl_opts['format'] = 'best'
        else:
            ydl_opts['format'] = f'best[height<={quality}]'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        files = os.listdir(download_path)
        if not files:
            return 'Не удалось найти скачанный файл', 500

        if fmt == 'mp3':
            mp3_files = [f for f in files if f.endswith('.mp3')]
            target = mp3_files[0] if mp3_files else files[0]
        else:
            video_files = [f for f in files if not f.endswith('.part')]
            target = video_files[0] if video_files else files[0]

        filepath = os.path.join(download_path, target)
        title = info.get('title', 'video')

        safe_title = "".join(c for c in title if c.isalnum() or c in ' ._-()').strip()
        if not safe_title:
            safe_title = 'video'
        safe_title = safe_title[:100]

        ext = target.rsplit('.', 1)[-1] if '.' in target else fmt

        response = send_file(
            filepath,
            as_attachment=True,
            download_name=f"{safe_title}.{ext}",
            mimetype='application/octet-stream'
        )

        @response.call_on_close
        def cleanup():
            try:
                shutil.rmtree(download_path, ignore_errors=True)
            except Exception:
                pass

        return response

    except Exception as e:
        error_msg = str(e)
        if 'ffmpeg' in error_msg.lower() and fmt == 'mp3':
            error_msg = 'ffmpeg не найден. MP3 недоступен. Попробуй MP4.'
        return f'Ошибка: {error_msg}', 500

@app.teardown_appcontext
def cleanup_old_downloads(exc=None):
    if not settings.get('auto_cleanup', True):
        return
    hours = settings.get('cleanup_hours', 1)
    try:
        for item in os.listdir(DOWNLOAD_DIR):
            item_path = os.path.join(DOWNLOAD_DIR, item)
            if os.path.isdir(item_path):
                age = os.path.getmtime(item_path)
                if time.time() - age > hours * 3600:
                    shutil.rmtree(item_path, ignore_errors=True)
    except Exception:
        pass

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='127.0.0.1', port=5000)
