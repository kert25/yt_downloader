import os
import time
import html
import shutil
import uuid
import threading
import yt_dlp
from flask import Flask, render_template, request, send_file, jsonify
import config as cfg

app = Flask(__name__)
app.secret_key = os.urandom(32).hex()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VALID_QUALITIES = {'360', '480', '720', '1080', 'max'}

settings = cfg.load()

DOWNLOAD_DIR = os.path.join(BASE_DIR, settings.get('download_path', 'downloads'))
FFMPEG_DIR = os.path.join(BASE_DIR, 'bin')

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FFMPEG_PATH = shutil.which('ffmpeg', path=FFMPEG_DIR) or shutil.which('ffmpeg')
FFPROBE_PATH = shutil.which('ffprobe', path=FFMPEG_DIR) or shutil.which('ffprobe')

downloads = {}

def sanitize_error(msg):
    return html.escape(msg, quote=False)

def background_download(url, fmt, quality, download_id, cancel_event):
    download_path = os.path.join(DOWNLOAD_DIR, download_id)
    os.makedirs(download_path, exist_ok=True)

    outtmpl = os.path.join(download_path, '%(title)s.%(ext)s')

    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [],
        'max_filesize': 4 * 1024 * 1024 * 1024,
        'socket_timeout': 30,
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
        ydl_opts['format'] = 'best' if quality == 'max' else f'best[height<={quality}]'

    def hook(d):
        if cancel_event.is_set():
            raise Exception('__cancel__')
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            if total:
                pct = min(int(downloaded / total * 100), 99)
                msg = f'Скачивание... {pct}%'
                if speed:
                    speed_mb = speed / 1048576
                    msg = f'Скачивание... {pct}% ({speed_mb:.1f} MB/s)'
                downloads[download_id] = {'status': 'downloading', 'percent': pct, 'message': msg}
        elif d['status'] == 'finished':
            downloads[download_id] = {'status': 'processing', 'percent': 100, 'message': 'Обработка...'}

    ydl_opts['progress_hooks'] = [hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        files = os.listdir(download_path)
        if not files:
            downloads[download_id] = {'status': 'error', 'percent': 0, 'message': 'Не удалось найти скачанный файл'}
            return

        if fmt == 'mp3':
            target = next((f for f in files if f.endswith('.mp3')), files[0])
        else:
            target = next((f for f in files if not f.endswith('.part')), files[0])

        filepath = os.path.join(download_path, target)
        title = info.get('title', 'video')

        safe_title = "".join(c for c in title if c.isalnum() or c in ' ._-()').strip()
        if not safe_title:
            safe_title = 'video'
        safe_title = safe_title[:100]

        ext = target.rsplit('.', 1)[-1] if '.' in target else fmt

        downloads[download_id] = {
            'status': 'complete',
            'percent': 100,
            'message': 'Готово',
            'filepath': filepath,
            'filename': f'{safe_title}.{ext}'
        }

    except Exception as e:
        if str(e) == '__cancel__':
            downloads[download_id] = {'status': 'cancelled', 'percent': 0, 'message': 'Отменено'}
            shutil.rmtree(download_path, ignore_errors=True)
        else:
            error_msg = str(e)
            if 'ffmpeg' in error_msg.lower() and fmt == 'mp3':
                error_msg = 'ffmpeg не найден. MP3 недоступен. Попробуй MP4.'
            downloads[download_id] = {'status': 'error', 'percent': 0, 'message': error_msg}
            shutil.rmtree(download_path, ignore_errors=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return 'Нет данных', 400

        if 'download_path' in data:
            path = data['download_path'].strip()
            if not path or '..' in path.split(os.sep) or path.startswith('/') or path.startswith('~'):
                return 'Недопустимый путь загрузки', 400
            data['download_path'] = path

        if 'max_quality' in data and data['max_quality'] not in VALID_QUALITIES:
            return 'Недопустимое качество', 400

        if 'cleanup_hours' in data:
            try:
                h = int(data['cleanup_hours'])
                if h < 1 or h > 168:
                    raise ValueError
                data['cleanup_hours'] = h
            except (TypeError, ValueError):
                return 'Недопустимое значение часов', 400

        if 'auto_cleanup' in data:
            data['auto_cleanup'] = bool(data['auto_cleanup'])

        if 'default_format' in data:
            if data['default_format'] not in ('mp4', 'mp3'):
                return 'Недопустимый формат', 400

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
def start_download():
    url = request.form.get('url', '').strip()
    fmt = request.form.get('format', settings.get('default_format', 'mp4'))
    quality = request.form.get('quality', settings.get('max_quality', '1080'))

    if not url:
        return 'Вставь ссылку на YouTube', 400

    if fmt not in ('mp4', 'mp3'):
        return 'Недопустимый формат', 400

    if quality not in VALID_QUALITIES:
        quality = settings.get('max_quality', '1080')
        if quality not in VALID_QUALITIES:
            quality = '1080'

    download_id = uuid.uuid4().hex[:8]
    cancel_event = threading.Event()

    downloads[download_id] = {'status': 'starting', 'percent': 0, 'message': 'Начинаем...', 'event': cancel_event}

    thread = threading.Thread(
        target=background_download,
        args=(url, fmt, quality, download_id, cancel_event),
        daemon=True
    )
    thread.start()

    return jsonify({'download_id': download_id})

@app.route('/progress/<download_id>')
def get_progress(download_id):
    info = downloads.get(download_id)
    if not info:
        return jsonify({'status': 'not_found', 'message': 'Загрузка не найдена'})
    return jsonify({
        'status': info.get('status'),
        'percent': info.get('percent', 0),
        'message': info.get('message', '')
    })

@app.route('/cancel/<download_id>', methods=['POST'])
def cancel_download(download_id):
    info = downloads.get(download_id)
    if not info:
        return jsonify({'status': 'not_found', 'message': 'Загрузка не найдена'})
    event = info.get('event')
    if event:
        event.set()
    return jsonify({'status': 'cancelling'})

@app.route('/file/<download_id>')
def get_file(download_id):
    info = downloads.get(download_id)
    if not info or info.get('status') != 'complete':
        return 'Файл не готов', 404

    filepath = info.get('filepath')
    filename = info.get('filename', 'video.mp4')

    if not filepath or not os.path.exists(filepath):
        return 'Файл не найден', 404

    response = send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )

    @response.call_on_close
    def cleanup():
        try:
            shutil.rmtree(os.path.dirname(filepath), ignore_errors=True)
        except Exception:
            pass
        downloads.pop(download_id, None)

    return response

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
    debug_mode = os.environ.get('YT_DEBUG', '').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_mode, threaded=True, host='127.0.0.1', port=5000)
