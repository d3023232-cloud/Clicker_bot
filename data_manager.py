"""Data management with BotHost Shared Storage support"""
import json
import os
import time
from collections import defaultdict
import config

# ── BotHost Shared Storage ──────────────────────────────────────────
SHARED_DIR = os.getenv("SHARED_DIR", "/app/shared")
DATA_PATH = os.path.join(SHARED_DIR, "clicker_data.json")

# Пытаемся создать директорию, если не получается — используем текущую
try:
    os.makedirs(SHARED_DIR, exist_ok=True)
    print(f"📁 Директория данных: {SHARED_DIR}")
except Exception as e:
    print(f"⚠️ Не удалось создать {SHARED_DIR}: {e}")
    SHARED_DIR = os.getcwd()
    DATA_PATH = os.path.join(SHARED_DIR, "clicker_data.json")
    print(f"📁 Fallback директория: {SHARED_DIR}")

user_data = defaultdict(lambda: {
    "clicks": 0, "coins": 0, "click_power": 1.0, "auto_clicker": 0.0,
    "last_click": time.time(), "last_daily": 0, "achievements": set(),
    "title": "Novice", "league": "Bronze", "premium": False,
    "premium_until": 0, "donate_coins": 0, "referrer_id": None,
    "last_reminder": 0, "reminders_enabled": True, "banned": False
})

user_names = {}

def save_data():
    try:
        serializable = {}
        for uid, data in user_data.items():
            serializable[str(uid)] = {
                "clicks": data["clicks"], "coins": data["coins"],
                "click_power": data["click_power"], "auto_clicker": data["auto_clicker"],
                "last_click": data["last_click"], "last_daily": data["last_daily"],
                "achievements": list(data["achievements"]), "title": data["title"],
                "league": data["league"], "premium": data["premium"],
                "premium_until": data["premium_until"], "donate_coins": data["donate_coins"],
                "referrer_id": data["referrer_id"], "last_reminder": data["last_reminder"],
                "reminders_enabled": data["reminders_enabled"], "banned": data.get("banned", False)
            }
        with open(DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump({"user_data": serializable, "user_names": user_names}, f, ensure_ascii=False, indent=2)
        print(f"💾 Данные сохранены: {DATA_PATH} ({len(user_data)} игроков)")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

def load_data():
    global user_data, user_names
    if not os.path.exists(DATA_PATH):
        print(f"📁 Файл данных не найден. Создаём новый: {DATA_PATH}")
        return
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        loaded = data.get("user_data", {})
        loaded_names = data.get("user_names", {})

        new_user_data = defaultdict(lambda: {
            "clicks": 0, "coins": 0, "click_power": 1.0, "auto_clicker": 0.0,
            "last_click": time.time(), "last_daily": 0, "achievements": set(),
            "title": "Novice", "league": "Bronze", "premium": False,
            "premium_until": 0, "donate_coins": 0, "referrer_id": None,
            "last_reminder": 0, "reminders_enabled": True, "banned": False
        })

        for uid_str, ud in loaded.items():
            uid = int(uid_str)
            new_user_data[uid] = {
                "clicks": ud.get("clicks", 0), "coins": ud.get("coins", 0),
                "click_power": ud.get("click_power", 1.0), "auto_clicker": ud.get("auto_clicker", 0.0),
                "last_click": ud.get("last_click", time.time()), "last_daily": ud.get("last_daily", 0),
                "achievements": set(ud.get("achievements", [])), "title": ud.get("title", "Novice"),
                "league": ud.get("league", "Bronze"), "premium": ud.get("premium", False),
                "premium_until": ud.get("premium_until", 0), "donate_coins": ud.get("donate_coins", 0),
                "referrer_id": ud.get("referrer_id"), "last_reminder": ud.get("last_reminder", 0),
                "reminders_enabled": ud.get("reminders_enabled", True),
                "banned": ud.get("banned", False)
            }

        user_data = new_user_data
        user_names.update(loaded_names)
        print(f"✅ Загружено {len(user_data)} игроков из {DATA_PATH}")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")

def update_user_name(user_id, name):
    user_names[user_id] = name

def get_user_name_by_id(user_id):
    return user_names.get(user_id, f"ID{user_id}")

def reset_user_data(user_id):
    user_data[user_id] = {
        "clicks": 0, "coins": 0, "click_power": 1.0, "auto_clicker": 0.0,
        "last_click": time.time(), "last_daily": 0, "achievements": set(),
        "title": "Novice", "league": "Bronze", "premium": False,
        "premium_until": 0, "donate_coins": 0, "referrer_id": None,
        "last_reminder": 0, "reminders_enabled": True, "banned": False
    }
    save_data()
