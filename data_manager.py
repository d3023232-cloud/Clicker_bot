"""Data management — надёжное сохранение с проверкой путей"""
import json
import os
import time
import atexit
import threading
from collections import defaultdict
import config

# ── Пробуем несколько путей для сохранения ─────────────────────────
_POSSIBLE_PATHS = [
    os.getenv("SHARED_DIR", ""),           # BotHost переменная
    "/app/shared",                          # BotHost shared
    "/data",                                # Railway/Render
    os.path.join(os.getcwd(), "data"),      # Локальная подпапка
    os.getcwd(),                            # Текущая директория (fallback)
]

DATA_PATH = None

def _find_working_path():
    """Находит первый рабочий путь для сохранения данных"""
    global DATA_PATH

    for path in _POSSIBLE_PATHS:
        if not path:
            continue
        try:
            os.makedirs(path, exist_ok=True)
            test_file = os.path.join(path, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            with open(test_file, "r") as f:
                assert f.read() == "test"
            os.remove(test_file)
            DATA_PATH = os.path.join(path, "clicker_data.json")
            print(f"✅ Найден рабочий путь: {DATA_PATH}")
            return True
        except Exception as e:
            print(f"❌ Путь {path} не работает: {e}")
            continue

    # Крайний fallback — текущая директория
    DATA_PATH = os.path.join(os.getcwd(), "clicker_data.json")
    print(f"⚠️ Используем fallback: {DATA_PATH}")
    return True

_find_working_path()

user_data = defaultdict(lambda: {
    "clicks": 0, "coins": 0, "click_power": 1.0, "auto_clicker": 0.0,
    "last_click": time.time(), "last_daily": 0, "achievements": set(),
    "title": "Novice", "league": "Bronze", "premium": False,
    "premium_until": 0, "donate_coins": 0, "referrer_id": None,
    "last_reminder": 0, "reminders_enabled": True, "banned": False
})

user_names = {}
_autosave_timer = None

def save_data():
    """Сохраняет данные атомарно"""
    global DATA_PATH
    if DATA_PATH is None:
        print("❌ DATA_PATH не определён!")
        return False

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

        temp_path = DATA_PATH + ".tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump({"user_data": serializable, "user_names": user_names}, f, ensure_ascii=False, indent=2)

        if os.path.exists(DATA_PATH):
            os.replace(temp_path, DATA_PATH)
        else:
            os.rename(temp_path, DATA_PATH)

        # Проверяем
        if os.path.exists(DATA_PATH):
            size = os.path.getsize(DATA_PATH)
            print(f"💾 Сохранено: {DATA_PATH} ({len(user_data)} игроков, {size} bytes)")
            return True
        else:
            print(f"❌ Файл не создан: {DATA_PATH}")
            return False

    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_data():
    """Загружает данные"""
    global user_data, user_names, DATA_PATH

    if DATA_PATH is None:
        _find_working_path()

    if not os.path.exists(DATA_PATH):
        print(f"📁 Файл не найден: {DATA_PATH}")
        print(f"📁 Будет создан при первом сохранении")
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
        import traceback
        traceback.print_exc()

def _schedule_autosave():
    """Автосохранение каждые 30 секунд"""
    global _autosave_timer
    save_data()
    _autosave_timer = threading.Timer(30.0, _schedule_autosave)
    _autosave_timer.daemon = True
    _autosave_timer.start()

def start_autosave():
    """Запускает автосохранение"""
    global _autosave_timer
    if _autosave_timer is None:
        print("🔄 Автосохранение запущено (каждые 30 сек)")
        _schedule_autosave()

def stop_autosave():
    """Останавливает автосохранение"""
    global _autosave_timer
    if _autosave_timer:
        _autosave_timer.cancel()
        _autosave_timer = None

atexit.register(save_data)

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
