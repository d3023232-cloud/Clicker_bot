"""Admin commands — интерактивная панель"""
import time
import config
import data_manager
from game_logic import update_league
from utils import format_number, is_premium_active


def is_admin(user_id):
    return user_id in config.ADMIN_IDS


def get_admin_panel_text():
    return "🛠 Админ-панель\n\nИспользуйте кнопки ниже для управления ботом."


def get_admin_main_keyboard():
    """Клавиатура админ-панели — возвращает InlineKeyboardMarkup"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("📈 Экономика", callback_data="admin_econ")],
        [InlineKeyboardButton("🔍 Поиск игрока", callback_data="admin_search_prompt")],
        [InlineKeyboardButton("➕ 💰 Выдать", callback_data="admin_action_add_coins"),
         InlineKeyboardButton("➖ 🔻 Забрать", callback_data="admin_action_remove_coins")],
        [InlineKeyboardButton("💎 Донат+", callback_data="admin_action_add_donate"),
         InlineKeyboardButton("💸 Донат-", callback_data="admin_action_remove_donate")],
        [InlineKeyboardButton("⭐ Премиум+", callback_data="admin_action_add_premium"),
         InlineKeyboardButton("❌ Премиум-", callback_data="admin_action_remove_premium")],
        [InlineKeyboardButton("🚫 Бан", callback_data="admin_action_ban"),
         InlineKeyboardButton("✅ Разбан", callback_data="admin_action_unban")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
         InlineKeyboardButton("🔄 Сброс", callback_data="admin_reset_user")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_command_description(cmd):
    desc = {
        "stats": "Статистика бота", "add_coins": "Выдать монеты", "give_donate": "Выдать донат",
        "give_premium": "Выдать премиум", "get_user": "Инфо о пользователе", "reset_user": "Сброс",
        "broadcast": "Рассылка", "ban_user": "Забанить", "debug": "Отладка", "econ": "Экономика"
    }
    return desc.get(cmd, "Неизвестная команда")


def handle_econ_command(user_id, args):
    total_coins = sum(u.get("coins", 0) for u in data_manager.user_data.values())
    total_spent = sum(u.get("total_spent", 0) for u in data_manager.user_data.values())
    total_issued = total_coins + total_spent
    active = len([u for u in data_manager.user_data.values() if u.get("coins", 0) > 0])
    return (
        "📈 Экономика:\n"
        f"💰 Выпущено: {format_number(int(total_issued))}\n"
        f"🔥 Потрачено: {format_number(int(total_spent))}\n"
        f"🪙 В обращении: {format_number(int(total_coins))}\n"
        f"👥 Активных: {active}"
    )


def find_user_by_query(query: str):
    query = query.strip().lower().lstrip('@')
    if query.isdigit() and int(query) in data_manager.user_data:
        uid = int(query)
        return uid, data_manager.user_data[uid]
    for uid, data in data_manager.user_data.items():
        name = data.get("name", "").lower()
        username = data.get("username", "").lower().lstrip('@')
        if query in name or (username and query == username):
            return uid, data
    return None, None


def get_user_display_name(uid, data):
    name = data.get("name", f"ID{uid}")
    username = data.get("username")
    return f"{name} (@{username})" if username else name


# === ДЕЙСТВИЯ ===
def action_add_coins(uid, amount: int):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["coins"] += amount
    update_league(uid)
    data_manager.save_data()
    return {"success": True, "message": f"✅ +{format_number(amount)} монет: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_remove_coins(uid, amount: int):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["coins"] = max(0, data_manager.user_data[uid]["coins"] - amount)
    update_league(uid)
    data_manager.save_data()
    return {"success": True, "message": f"✅ -{format_number(amount)} монет: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_add_donate(uid, amount: int):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["donate_coins"] += amount
    data_manager.save_data()
    return {"success": True, "message": f"✅ +{amount} ⭐: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_remove_donate(uid, amount: int):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["donate_coins"] = max(0, data_manager.user_data[uid]["donate_coins"] - amount)
    data_manager.save_data()
    return {"success": True, "message": f"✅ -{amount} ⭐: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_add_premium(uid, days: int):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    if days == 0:
        data_manager.user_data[uid]["premium"], data_manager.user_data[uid]["premium_until"] = True, 0
        desc = "навсегда"
    else:
        data_manager.user_data[uid]["premium"], data_manager.user_data[uid]["premium_until"] = True, time.time() + days * 86400
        desc = f"на {days} дней"
    data_manager.save_data()
    return {"success": True, "message": f"⭐ Премиум {desc}: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_remove_premium(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.user_data[uid]["premium"], data_manager.user_data[uid]["premium_until"] = False, 0
    data_manager.save_data()
    return {"success": True, "message": f"❌ Премиум снят: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_ban(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.user_data[uid]["banned"], data_manager.user_data[uid]["auto_clicker"] = True, 0
    data_manager.save_data()
    return {"success": True, "message": f"🚫 Забанен: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_unban(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.user_data[uid]["banned"] = False
    data_manager.save_data()
    return {"success": True, "message": f"✅ Разбанен: {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_reset_user(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.reset_user_data(uid)
    return {"success": True, "message": f"🔄 Сброшен: {get_user_display_name(uid, data_manager.user_data[uid])}"}


# === ИНФОРМАЦИЯ ===
def get_stats():
    total_players = len([u for u in data_manager.user_data if data_manager.user_data[u].get("coins", 0) > 0])
    total_coins = sum(u.get("coins", 0) for u in data_manager.user_data.values())
    total_donate = sum(u.get("donate_coins", 0) for u in data_manager.user_data.values())
    top = max(((uid, d["coins"]) for uid, d in data_manager.user_data.items() if d.get("coins", 0) > 0), key=lambda x: x[1], default=(None, 0))
    top_str = f"{get_user_display_name(top[0], data_manager.user_data[top[0]])} - {format_number(int(top[1]))} 💰" if top[0] else "-"
    return f"📊 Статистика:\n👥 Игроков: {total_players}\n💰 Монет: {format_number(int(total_coins))}\n💎 Донат: {int(total_donate)}\n🏆 Топ: {top_str}"

def get_user_info(uid):
    if uid not in data_manager.user_data:
        return "❌ Пользователь не найден"
    d = data_manager.user_data[uid]
    return (
        f"👤 {get_user_display_name(uid, d)} (ID: {uid})\n"
        f"💰 Монеты: {format_number(int(d.get('coins', 0)))}\n💎 Донат: {d.get('donate_coins', 0)}\n"
        f"🖱 Клики: {format_number(d.get('clicks', 0))}\n⚡ Сила: {d.get('click_power', 1)}\n"
        f"🤖 Авто: {d.get('auto_clicker', 0)}/мин\n🏅 Лига: {d.get('league', '-')}\n"
        f"📛 Звание: {d.get('title', '-')}\n⭐ Премиум: {'Да' if is_premium_active(d) else 'Нет'}\n"
        f"🚫 Бан: {'Да' if d.get('banned', False) else 'Нет'}"
    )

def get_econ_stats():
    total_coins = sum(u.get("coins", 0) for u in data_manager.user_data.values())
    total_spent = sum(u.get("total_spent", 0) for u in data_manager.user_data.values())
    total_issued = total_coins + total_spent
    active = len([u for u in data_manager.user_data.values() if u.get("coins", 0) > 0])
    return (
        f"📈 Экономика:\n💰 Выпущено: {format_number(int(total_issued))}\n"
        f"🔥 Потрачено: {format_number(int(total_spent))}\n🪙 В обращении: {format_number(int(total_coins))}\n"
        f"👥 Активных: {active}\n📊 Инфляция: {format_number(int(total_spent / max(1, total_issued) * 100))}%"
    )
