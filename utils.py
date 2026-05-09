"""Helper functions"""
import time
import random
import config
from telegram import Bot

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
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{config.CHANNEL_USERNAME}", user_id=user_id)
        # left - был и вышел, kicked - забанен, restricted - ограничен
        if member.status in ['left', 'kicked']:
            return False
        return True
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        # Если ошибка (например, бот не админ в канале), считаем что подписан, чтобы не ломать игру
        return True
