import os
import warnings
import uuid
import json
from typing import Dict, Any

EXT_PATH = os.path.join(os.path.dirname(__file__), "..")
CONFIG_FILE = os.path.join(EXT_PATH, "config.json")


def load_config(file_path: str) -> Dict[str, Any]:
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


config = load_config(CONFIG_FILE)

SECRET_KEY = os.getenv(config.get("secret_key_env", "SECRET_KEY"))

if not SECRET_KEY:
    warnings.warn(
        "The SECRET_KEY environment variable is not set. A random key will be used for this session. "
        "This will cause all users to log out on server restart."
    )
    SECRET_KEY = "".join([str(uuid.uuid4().hex) for _ in range(128)])

MATCH_HEADERS = {"X-Forwarded-Proto": "https"}

TOKEN_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * config.get("access_token_expiration_hours", 12)

USERS_FILE = os.path.join(EXT_PATH, config.get("users_db", "users_dp.json"))
LOG_FILE = os.path.join(EXT_PATH, config.get("log", "sentinels_log.log"))
LOG_LEVELS = config.get("log_levels", ["INFO"])

WHITELIST = os.path.join(EXT_PATH, config.get("whitelist", "whitelist.txt"))
BLACKLIST = os.path.join(EXT_PATH, config.get("blacklist", "blacklist.txt"))

BLACKLIST_AFTER_ATTEMPTS = config.get("blacklist_after_attempts")

FREE_MEMORY_ON_LOGOUT = config.get("free_memory_on_logout", False)
FORCE_HTTPS = config.get("force_https", False)

SEPERATE_USERS = config.get("seperate_users", False)

WEB_DIR = os.path.join(EXT_PATH, "sentinel-web")
HTML_DIR = WEB_DIR
CSS_DIR = os.path.join(WEB_DIR, "css")
JS_DIR = os.path.join(WEB_DIR, "js")
ASSETS_DIR = os.path.join(WEB_DIR, "assets")
