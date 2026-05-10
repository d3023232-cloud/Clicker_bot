"""Helper functions — без кэша экономики"""
import time
import random
import json
import os
import config
from telegram import Bot

# ── BotHost Shared Storage ──────────────────────────────────────────
SHARED_DIR = os.getenv("SHARED_DIR", "/app/shared")
os.makedirs(SHARED_DIR, exist_ok=True)

# 📊 ЭКОНОМИКА
ECONOMY_FILE = os.path.join(SHARED_DIR, "economy.json")

def load_economy():
    """📊 Загружает конфиг экономики — ВСЕГДА читает файл заново"""
    try:
        if os.path.exists(ECONOMY_FILE):
            with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки экономики: {e}")

    # Дефолтные значения
    default = {
        "income": {"click_base": 1.0, "daily_base": 20, "auto_cap_pct": 0.4, "inactive_decay_mult": 0.3},
        "pricing": {"cost_multiplier": 2.8, "diminishing_effect": True},
        "tax_rates": {"🥉 Бронза": 0.0, "🥈 Серебро": 0.005, "🥇 Золото": 0.01, "💎 Алмаз": 0.015},
        "games": {"max_bet_pct": 0.1, "house_edge": 0.02, "min_bet": 20},
        "limits": {"click_base": [0.1, 5.0], "cost_multiplier": [1.5, 5.0], "max_bet_pct": [0.01, 0.5]}
    }
    save_economy(default)
    return default

def get_econ(key: str, default=None):
    """📊 Безопасно достаёт значение по пути"""
    econ = load_economy()  # ВСЕГДА читаем свежий файл
    keys = key.split(".")
    val = econ
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            print(f"⚠️ Ключ экономики '{key}' не найден, используется дефолт: {default}")
            return default
    return val

def save_economy(data):
    """📊 Сохраняет изменения в economy.json"""
    try:
        with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Экономика сохранена: {ECONOMY_FILE}")
    except Exception as e:
        print(f"❌ Ошибка сохранения экономики: {e}")

# ── Оригинальные функции ────────────────────────────────────────────
def format_number(n: int) -> str:
    return f"{int(n):,}".replace(",", " ")

def generate_crash_multiplier() -> float:
    r = random.random()
    if r >= 0.9999:
        return 100.0
    crash = 0.99 / (1 - r)
    return min(100.0, round(crash, 2))

def get_time_greeting():
    hour = time.localtime().tm_hour
    if 0 <= hour < 7:
        return "Доброй ночи! 🌙"
    elif 7 <= hour < 12:
        return "Доброе утро! ☀️"
    elif 12 <= hour < 18:
        return "Добрый день! 🌤"
    else:
        return "Добрый вечер! 🌆"

def get_league(coins):
    for min_coins, name in reversed(config.LEAGUES):
        if coins >= min_coins:
            return name
    return config.LEAGUES[0][1]

def get_user_name(user):
    return user.full_name if user.full_name else f"ID{user.id}"

def is_premium_active(user_data):
    if not user_data.get("premium", False):
        return False
    if user_data.get("premium_until", 0) == 0:
        return True
    return time.time() < user_data["premium_until"]

async def check_subscription(user_id, context):
    """Проверяет подписку пользователя на канал"""
    if not config.CHANNEL_USERNAME or config.CHANNEL_USERNAME == "YOUR_CHANNEL_USERNAME":
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{config.CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ['left', 'kicked']:
            return False
        return True
    except Exception as e:
        print(f"🚫 Ошибка проверки подписки для user_id={user_id}: {e}")
        return False
