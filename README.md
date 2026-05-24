# YT Downloader

Минималистичное десктопное веб-приложение для скачивания видео с YouTube без рекламы, регистрации и лишнего мусора.

## Возможности

- Скачивание видео в MP4 (до 1080p)
- Скачивание аудио в MP3 (192 kbps)
- Чистый интерфейс на одной странице
- Автоматическая очистка временных файлов
- Полная бесплатность и отсутствие рекламы

## Требования

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) (для конвертации в MP3)

## Установка

```bash
git clone https://github.com/kert25/yt_downloader.git
cd yt_downloader

python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

Убедитесь, что `ffmpeg` доступен в системе:

```bash
# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Скачайте с https://ffmpeg.org/download.html и добавьте в PATH
```

## Запуск

```bash
source venv/bin/activate
python3 app.py
```

Откройте в браузере: [http://127.0.0.1:5000](http://127.0.0.1:5000)

Вставьте ссылку на YouTube, выберите формат (MP4 или MP3), нажмите «Скачать».

## Структура проекта

```
yt_downloader/
├── app.py              # Серверная часть (Flask)
├── templates/
│   └── index.html      # Веб-интерфейс
├── requirements.txt    # Зависимости Python
├── downloads/          # Временные файлы (автоочистка)
└── .gitignore
```

## Технологии

- [Flask](https://flask.palletsprojects.com/) — веб-фреймворк
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — движок загрузки видео
- [ffmpeg](https://ffmpeg.org/) — обработка аудио/видео

## Лицензия

MIT
