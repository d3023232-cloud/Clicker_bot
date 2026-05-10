"""Admin panel with promocode management"""
import time
import config
import data_manager
from utils import format_number, is_premium_active

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

def get_admin_panel_text():
    total_players = len(data_manager.user_data)
    total_coins = sum(d["coins"] for d in data_manager.user_data.values())
    return (
        "🛠 <b>Админ-панель</b>\n\n"
        f"👥 Игроков: {total_players}\n"
        f"🪙 Всего монет: {format_number(int(total_coins))}\n"
        f"💎 Всего донатов: {sum(d['donate_coins'] for d in data_manager.user_data.values())}"
    )

def get_admin_main_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
         InlineKeyboardButton("💰 Экономика", callback_data="admin_econ")],
        [InlineKeyboardButton("🔍 Найти игрока", callback_data="admin_search_prompt"),
         InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promo_menu")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ])

def get_admin_promo_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Создать промокод", callback_data="admin_promo_create")],
        [InlineKeyboardButton("🗑 Удалить промокод", callback_data="admin_promo_delete")],
        [InlineKeyboardButton("📋 Список промокодов", callback_data="admin_promo_list")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]
    ])

def get_user_display_name(user_id, user_data):
    name = user_data.get("name", f"ID{user_id}")
    vip = " 👑" if is_premium_active(user_data) else ""
    return f"{name}{vip}"

def get_user_info(user_id):
    if user_id not in data_manager.user_data:
        return "❌ Пользователь не найден"
    d = data_manager.user_data[user_id]
    return (
        f"👤 {get_user_display_name(user_id, d)}\n"
        f"🪙 {format_number(int(d['coins']))} | 💎 {d['donate_coins']}\n"
        f"⚡ {d['click_power']} | 🤖 {d['auto_clicker']}\n"
        f"🏅 {d['title']} | 🏆 {d['league']}"
    )

def get_stats():
    ud = data_manager.user_data
    if not ud:
        return "📊 Нет данных"
    top = max(((uid, d["coins"]) for uid, d in ud.items()), key=lambda x: x[1], default=(None, 0))
    return (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Игроков: {len(ud)}\n"
        f"🪙 Всего монет: {format_number(int(sum(d['coins'] for d in ud.values())))}\n"
        f"💎 Всего донатов: {sum(d['donate_coins'] for d in ud.values())}\n"
        f"🏆 Топ: {get_user_display_name(top[0], ud[top[0]]) if top[0] else 'Нет'} — {format_number(int(top[1]))}"
    )

def get_econ_stats():
    from utils import get_econ
    return (
        "💰 <b>Экономика</b>\n\n"
        f"Базовый клик: {get_econ('income.click_base')}\n"
        f"Множитель цен: {get_econ('pricing.cost_multiplier')}\n"
        f"Налоги: {get_econ('tax_rates')}"
    )

# ── Action functions ─────────────────────────────────────────────────

def action_add_coins(uid, amount):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["coins"] += amount
    data_manager.save_data()
    return {"success": True, "message": f"✅ +{format_number(amount)} монет для {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_remove_coins(uid, amount):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["coins"] = max(0, data_manager.user_data[uid]["coins"] - amount)
    data_manager.save_data()
    return {"success": True, "message": f"🔻 -{format_number(amount)} монет у {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_add_donate(uid, amount):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["donate_coins"] += amount
    data_manager.save_data()
    return {"success": True, "message": f"💎 +{amount} донат-коинов для {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_remove_donate(uid, amount):
    if uid not in data_manager.user_data or amount <= 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    data_manager.user_data[uid]["donate_coins"] = max(0, data_manager.user_data[uid]["donate_coins"] - amount)
    data_manager.save_data()
    return {"success": True, "message": f"💸 -{amount} донат-коинов у {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_add_premium(uid, days):
    if uid not in data_manager.user_data or days < 0:
        return {"success": False, "message": "❌ Ошибка ввода"}
    ud = data_manager.user_data[uid]
    ud["premium"] = True
    if days == 0:
        ud["premium_until"] = 0
    else:
        current = ud.get("premium_until", 0)
        if current < time.time():
            current = time.time()
        ud["premium_until"] = current + (days * 86400)
    data_manager.save_data()
    return {"success": True, "message": f"⭐ Премиум ({days} дней) выдан {get_user_display_name(uid, ud)}"}

def action_remove_premium(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.user_data[uid]["premium"] = False
    data_manager.user_data[uid]["premium_until"] = 0
    data_manager.save_data()
    return {"success": True, "message": f"❌ Премиум снят у {get_user_display_name(uid, data_manager.user_data[uid])}"}

def action_ban(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.user_data[uid]["banned"] = True
    data_manager.user_data[uid]["auto_clicker"] = 0
    data_manager.save_data()
    return {"success": True, "message": f"🚫 {get_user_display_name(uid, data_manager.user_data[uid])} забанен"}

def action_unban(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.user_data[uid]["banned"] = False
    data_manager.save_data()
    return {"success": True, "message": f"✅ {get_user_display_name(uid, data_manager.user_data[uid])} разбанен"}

def action_reset_user(uid):
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    data_manager.reset_user_data(uid)
    return {"success": True, "message": f"🔄 {get_user_display_name(uid, data_manager.user_data[uid])} сброшен"}
