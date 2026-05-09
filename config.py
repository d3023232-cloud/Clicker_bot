"""Конфигурация бота из переменных окружения хостинга"""
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set! Add it in hosting environment variables.")

ADMIN_ID_STR = os.getenv("ADMIN_ID", "0")
ADMIN_ID = int(ADMIN_ID_STR.split(",")[0].strip()) if ADMIN_ID_STR else 0

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip()]
if ADMIN_ID and ADMIN_ID not in ADMIN_IDS:
    ADMIN_IDS.insert(0, ADMIN_ID)

YOUR_BOT_USERNAME = os.getenv("YOUR_BOT_USERNAME", "")
if not YOUR_BOT_USERNAME:
    print("Warning: YOUR_BOT_USERNAME not set. Referral links may not work.")

DATA_FILE = os.getenv("DATA_FILE", "clicker_data.json")

# ID канала для проверки подписки (без @)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "YOUR_CHANNEL_USERNAME") 

REMINDER_INTERVAL_MIN = 3600
REMINDER_INTERVAL_MAX = 10800
DAILY_BONUS_BASE = 20
DAILY_BONUS_PREMIUM = 50
MIN_BET = 20
MAX_BET = 1000000
MIN_DUEL_BET = 100

LEAGUES = [
    (0, "🥉 Бронза"),
    (1000000, "🥈 Серебро"),
    (10000000, "🥇 Золото"),
    (100000000, "💎 Алмаз"),
    (500000000, "💚 Изумруд"),
    (1000000000, "❤️ Рубин"),
    (50000000000, "🔮 Божественный"),
    (100000000000, "🌌 Галактический"),
    (500000000000, "👑 Легендарный")
]

ACHIEVEMENTS = {
    "first_click": {"name": "Первый клик!", "desc": "Сделайте свой первый клик"},
    "click_100": {"name": "Клик-машина", "desc": "Сделайте 100 кликов"},
    "rich_100": {"name": "Первые 100 монет!", "desc": "Заработайте 100 монет"},
    "buy_upgrade": {"name": "Инвестор", "desc": "Купите первое улучшение"},
    "auto_owner": {"name": "Робо-помощник", "desc": "Купите авто-кликер"}
}

UPGRADES = {
    "double_click": {"name": "Удвоитель клика", "cost": 10, "effect": 2.0, "type": "click_power"},
    "auto_clicker": {"name": "Авто-кликер", "cost": 30, "effect": 5.0, "type": "auto_clicker"}
}

TITLES = {
    "novice": {"name": "Новичок", "cost": 0, "desc": "Только начал"},
    "clicker": {"name": "Кликер", "cost": 100, "desc": "Уже не новичок!"},
    "millionaire": {"name": "Миллионер", "cost": 1000, "desc": "Богатый кликер!"},
    "legend": {"name": "Легенда", "cost": 5000, "desc": "Живая легенда!"}
}

DONAT_SHOP = {
    "premium": {"name": "Premium Статус", "cost": 50, "stars": 100, "desc": "x2 авто, x1.5 клик, +50 ежедневный бонус"},
    "bonus_100": {"name": "+100 Монет", "cost": 5, "stars": 10, "desc": "Мгновенно +100 монет"},
    "click_power_5": {"name": "+5 Силы клика", "cost": 20, "stars": 40, "desc": "Постоянно +5 к силе клика"}
}

REMINDER_MESSAGES = [
    "Заходи поиграть! Твой авто-кликер заработал монеты! /start",
    "Ты пропустил кучу монет! Загляни в бота! /start",
    "Твой авто-кликер скучает без тебя! /start",
    "Срочно! Твой баланс растет! /start",
    "Кликай и получай бонусы! /start",
    "Ты близок к новой лиге! /start",
    "Твой авто-кликер работал для тебя! /start",
    "Не спи! Монеты ждут! /start",
    "Ты не поверишь, сколько у тебя монет! /start",
    "Проверь магазин, там новые улучшения! /start"
]
