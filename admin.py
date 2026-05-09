"""Admin commands"""
import time
import config
import data_manager
from game_logic import update_league
from utils import format_number, is_premium_active

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

def get_admin_panel_text():
    lines = [
        "🛠 Админ-панель",
        "",
        "/debug - Информация отладки",
        "/add_coins [id] [кол-во] - Добавить монеты",
        "/give_donate [id] [кол-во] - Выдать донат-коины",
        "/give_premium [id] [дни] - Выдать премиум",
        "/get_user [id] - Инфо о пользователе",
        "/reset_user [id] - Сбросить пользователя",
        "/stats - Статистика бота",
        "/ban_user [id] - Забанить пользователя",
        "/broadcast [сообщение] - Рассылка",
        "/admins - Это меню"
    ]
    return "\n".join(lines)

def get_admin_keyboard():
    from telegram import InlineKeyboardButton
    return [
        [InlineKeyboardButton("📊 Статистика (/stats)", callback_data="admin_cmd_stats")],
        [InlineKeyboardButton("💰 Добавить монеты (/add_coins)", callback_data="admin_cmd_add_coins")],
        [InlineKeyboardButton("💎 Выдать донат (/give_donate)", callback_data="admin_cmd_give_donate")],
        [InlineKeyboardButton("⭐ Выдать премиум (/give_premium)", callback_data="admin_cmd_give_premium")],
        [InlineKeyboardButton("👤 Инфо юзера (/get_user)", callback_data="admin_cmd_get_user")],
        [InlineKeyboardButton("🚫 Бан (/ban_user)", callback_data="admin_cmd_ban_user")],
        [InlineKeyboardButton("📢 Рассылка (/broadcast)", callback_data="admin_cmd_broadcast")],
        [InlineKeyboardButton("🔄 Сброс (/reset_user)", callback_data="admin_cmd_reset_user")],
        [InlineKeyboardButton("🐞 Отладка (/debug)", callback_data="admin_cmd_debug")]
    ]

def get_admin_command_description(cmd):
    descriptions = {
        "stats": "/stats - Показать статистику бота",
        "add_coins": "/add_coins <id> <кол-во> - Добавить монеты",
        "give_donate": "/give_donate <id> <кол-во> - Выдать донат-коины",
        "give_premium": "/give_premium <id> <дни> - Выдать премиум (0=навсегда)",
        "get_user": "/get_user <id> - Показать инфо юзера",
        "ban_user": "/ban_user <id> - Забанить юзера",
        "broadcast": "/broadcast <текст> - Отправить всем",
        "reset_user": "/reset_user <id> - Полный сброс данных",
        "debug": "/debug - Показать отладочную инфо"
    }
    return descriptions.get(cmd, "Команда не найдена")

def add_coins(target_id, amount):
    try:
        target_id = int(target_id)
        amount = int(amount)
        if amount <= 0:
            return {"success": False, "message": "Количество должно быть положительным"}
        data_manager.user_data[target_id]["coins"] += amount
        update_league(target_id)
        data_manager.save_data()
        return {"success": True, "message": f"✅ Добавлено {format_number(amount)} монет пользователю {target_id}"}
    except ValueError:
        return {"success": False, "message": "❌ Ошибка: ID и количество должны быть числами"}

def give_donate(target_id, amount):
    try:
        target_id = int(target_id)
        amount = int(amount)
        if amount <= 0:
            return {"success": False, "message": "Количество должно быть положительным"}
        data_manager.user_data[target_id]["donate_coins"] += amount
        data_manager.save_data()
        return {"success": True, "message": f"✅ Выдано {amount} донат-коинов пользователю {target_id}"}
    except ValueError:
        return {"success": False, "message": "❌ Ошибка: ID и количество должны быть числами"}

def give_premium(target_id, days):
    try:
        target_id = int(target_id)
        days = int(days)
        if days == 0:
            data_manager.user_data[target_id]["premium"] = True
            data_manager.user_data[target_id]["premium_until"] = 0
        else:
            data_manager.user_data[target_id]["premium"] = True
            data_manager.user_data[target_id]["premium_until"] = time.time() + days * 86400
        data_manager.save_data()
        return {"success": True, "message": f"⭐ Премиум выдан пользователю {target_id} на {days} дней"}
    except ValueError:
        return {"success": False, "message": "❌ Ошибка: ID и дни должны быть числами"}

def get_user_info(uid):
    try:
        uid = int(uid)
        ud = data_manager.user_data[uid]
        name = data_manager.get_user_name_by_id(uid)
        lines = [
            f"👤 Пользователь: {name} (ID: {uid})",
            f"💰 Монеты: {format_number(int(ud['coins']))}",
            f"💎 Донат: {ud['donate_coins']}",
            f"🖱 Клики: {format_number(ud['clicks'])}",
            f"⚡ Сила клика: {ud['click_power']}",
            f"🤖 Авто-кликер: {ud['auto_clicker']} монет/мин",
            f"🏅 Лига: {ud['league']}",
            f"📛 Звание: {ud['title']}",
            f"⭐ Премиум: {'Да' if is_premium_active(ud) else 'Нет'}",
            f"🏆 Достижения: {', '.join(config.ACHIEVEMENTS.get(k, {}).get('name', k) for k in ud['achievements']) or '-'}"
        ]
        return {"success": True, "message": "\n".join(lines)}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def reset_user(uid):
    try:
        uid = int(uid)
        data_manager.reset_user_data(uid)
        return {"success": True, "message": f"🔄 Данные пользователя {uid} сброшены"}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def get_stats():
    total_players = len([u for u in data_manager.user_data if data_manager.user_data[u]["coins"] > 0 or data_manager.user_data[u]["clicks"] > 0])
    total_coins = sum(u["coins"] for u in data_manager.user_data.values())
    total_donate = sum(u["donate_coins"] for u in data_manager.user_data.values())
    
    top_list = [(uid, data["coins"]) for uid, data in data_manager.user_data.items() if data["coins"] > 0]
    if top_list:
        top_player = max(top_list, key=lambda x: x[1])
        top_name = data_manager.get_user_name_by_id(top_player[0])
        top_league = data_manager.user_data[top_player[0]]["league"]
        top_str = f"{top_name} [{top_league}] - {format_number(int(top_player[1]))} 💰"
    else:
        top_str = "-"
        
    lines = [
        "📊 Статистика бота:",
        f"👥 Активных игроков: {total_players}",
        f"💰 Всего монет в игре: {format_number(int(total_coins))}",
        f"💎 Всего донат-коинов: {int(total_donate)}",
        f"🏆 Топ игрок: {top_str}"
    ]
    return {"success": True, "message": "\n".join(lines)}

def give_daily_reset(uid):
    try:
        uid = int(uid)
        data_manager.user_data[uid]["last_daily"] = 0
        data_manager.save_data()
        return {"success": True, "message": f"🔄 Ежедневный бонус сброшен для {uid}"}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def ban_user(uid):
    try:
        uid = int(uid)
        data_manager.user_data[uid]["auto_clicker"] = 0
        data_manager.user_data[uid]["last_daily"] = time.time() + 10 * 365 * 86400
        data_manager.save_data()
        return {"success": True, "message": f"🚫 Пользователь {uid} забанен"}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def test_achievements(uid):
    try:
        uid = int(uid)
        data_manager.user_data[uid]["achievements"] = set(config.ACHIEVEMENTS.keys())
        data_manager.save_data()
        return {"success": True, "message": f"✅ Все достижения выданы пользователю {uid}"}
    except Exception as e:
        return {"success": False, "message": f"❌ Ошибка: {e}"}

def get_debug_info(user_id):
    ud = data_manager.user_data[user_id]
    lines = [
        "🐞 Отладочная информация:",
        f"💰 Монеты: {format_number(int(ud['coins']))}",
        f"💎 Донат: {ud['donate_coins']}",
        f"🖱 Клики: {format_number(ud['clicks'])}",
        f"⚡ Сила клика: {ud['click_power']}",
        f"🤖 Авто-кликер: {ud['auto_clicker']} монет/мин",
        f"🏅 Лига: {ud['league']}",
        f"📛 Звание: {ud['title']}",
        f"⭐ Премиум: {'Да' if is_premium_active(ud) else 'Нет'}"
    ]
    return "\n".join(lines)
