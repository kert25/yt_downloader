import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')

DEFAULT_CONFIG = {
    "default_format": "mp4",
    "max_quality": "1080",
    "download_path": "downloads",
    "auto_cleanup": True,
    "cleanup_hours": 1
}

def load():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save(settings):
    config = load()
    config.update(settings)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return config
