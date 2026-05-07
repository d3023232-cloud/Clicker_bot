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

REMINDER_INTERVAL_MIN = 3600
REMINDER_INTERVAL_MAX = 10800
DAILY_BONUS_BASE = 20
DAILY_BONUS_PREMIUM = 50
MIN_BET = 20
MAX_BET = 1000000
MIN_DUEL_BET = 100

LEAGUES = [
    (0, "Bronze"),
    (1000000, "Silver"),
    (10000000, "Gold"),
    (100000000, "Diamond"),
    (500000000, "Emerald"),
    (1000000000, "Ruby"),
    (50000000000, "Divine"),
    (100000000000, "Galactic"),
    (500000000000, "Legendary")
]

ACHIEVEMENTS = {
    "first_click": {"name": "First Click!", "desc": "Make your first click"},
    "click_100": {"name": "Click Machine", "desc": "100 clicks"},
    "rich_100": {"name": "First 100 Coins!", "desc": "Earn 100 coins"},
    "buy_upgrade": {"name": "Investor", "desc": "Buy first upgrade"},
    "auto_owner": {"name": "Robot Helper", "desc": "Buy auto-clicker"}
}

UPGRADES = {
    "double_click": {"name": "Click Doubler", "cost": 10, "effect": 2.0, "type": "click_power"},
    "auto_clicker": {"name": "Auto-Clicker", "cost": 30, "effect": 5.0, "type": "auto_clicker"}
}

TITLES = {
    "novice": {"name": "Novice", "cost": 0, "desc": "Just started"},
    "clicker": {"name": "Clicker", "cost": 100, "desc": "Not a newbie anymore!"},
    "millionaire": {"name": "Millionaire", "cost": 1000, "desc": "Rich clicker!"},
    "legend": {"name": "Legend", "cost": 5000, "desc": "Living legend!"}
}

DONAT_SHOP = {
    "premium": {"name": "Premium Status", "cost": 50, "stars": 100, "desc": "x2 auto, x1.5 click, +50 daily"},
    "bonus_100": {"name": "+100 Coins", "cost": 5, "stars": 10, "desc": "Instant +100 coins"},
    "click_power_5": {"name": "+5 Click Power", "cost": 20, "stars": 40, "desc": "Permanent +5 click power"}
}

REMINDER_MESSAGES = [
    "Come play! Your auto-clicker earned coins! /start",
    "You missed a lot of coins! Check the bot! /start",
    "Your auto-clicker is crying without you! /start",
    "Urgent! Your balance is growing! /start",
    "Click and get a bonus! /start",
    "You are close to a new league! /start",
    "Your auto-clicker worked for you! /start",
    "Don't sleep! Coins are waiting! /start",
    "You won't believe how many coins you have! /start",
    "Check the shop for new upgrades! /start"
]
