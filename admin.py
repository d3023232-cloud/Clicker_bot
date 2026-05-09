"""Admin commands — интерактивная панель"""
import time
import re
import config
import data_manager
from game_logic import update_league
from utils import format_number, is_premium_active

# === УТИЛИТЫ ===

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

def find_user_by_query(query: str):
    """Поиск пользователя по @username, ID или части имени"""
    query = query.strip().lower().lstrip('@')
    
    # Попытка найти по ID
    if query.isdigit():
        uid = int(query)
        if uid in data_manager.user_data:
            return uid, data_manager.user_data[uid]
        return None, None
    
    # Поиск по username (если есть в данных)
    for uid, data in data_manager.user_data.items():
        # Проверяем сохранённое имя
        name = data.get("name", "").lower()
        if query in name:
            return uid, data
        # Проверяем username (если бот его сохраняет)
        username = data.get("username", "").lower().lstrip('@')
        if username and query == username:
            return uid, data
    return None, None

def get_user_display_name(uid, data):
    name = data.get("name", f"ID{uid}")
    username = data.get("username")
    if username:
        return f"{name} (@{username})"
    return name

# === КЛАВИШАТУРЫ ===

def get_admin_main_keyboard():
    """Главная админ-панель с логическими группами"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Группа 1: Информация (отдельный блок)
    info_row = [
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("🔍 Поиск игрока", callback_data="admin_search_prompt")
    ]
    
    # Группа 2: Работа с игроком (парные кнопки)
    # Левая колонка — выдача/добавление
    # Правая колонка — изъятие/ограничение
    player_rows = [
        [
            InlineKeyboardButton("💰 Выдать монеты", callback_data="admin_action_add_coins"),
            InlineKeyboardButton("🔻 Забрать монеты", callback_data="admin_action_remove_coins")
        ],
        [
            InlineKeyboardButton("💎 Донат+", callback_data="admin_action_add_donate"),
            InlineKeyboardButton("💸 Донат-", callback_data="admin_action_remove_donate")
        ],
        [
            InlineKeyboardButton("⭐ Премиум+", callback_data="admin_action_add_premium"),
            InlineKeyboardButton("❌ Премиум-", callback_data="admin_action_remove_premium")
        ],
        [
            InlineKeyboardButton("🚫 Забанить", callback_data="admin_action_ban"),
            InlineKeyboardButton("✅ Разбанить", callback_data="admin_action_unban")
        ],
    ]
    
    # Группа 3: Системные (отдельный блок)
    system_row = [
        InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("🔄 Сброс игрока", callback_data="admin_reset_user")
    ]
    
    # Кнопка назад / отмены
    back_row = [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
    
    keyboard = [info_row, *player_rows, system_row, back_row]
    return InlineKeyboardMarkup(keyboard)

def get_player_select_keyboard(found_users: list):
    """Клавиатура выбора игрока из поиска"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = []
    for uid, data in found_users[:10]:  # макс 10 результатов
        display = get_user_display_name(uid, data)
        keyboard.append([InlineKeyboardButton(f"👤 {display}", callback_data=f"admin_select_{uid}")])
    keyboard.append([InlineKeyboardButton("🔍 Искать заново", callback_data="admin_search_prompt")])
    keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")])
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(action: str, uid: int):
    """Клавиатура подтверждения действия"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{action}_{uid}"),
            InlineKeyboardButton("❌ Отмена", callback_data="admin_main")
        ]
    ])

# === ОБРАБОТЧИКИ ДЕЙСТВИЙ ===

def action_add_coins(uid, amount: int):
    """Выдать монеты"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    if amount <= 0:
        return {"success": False, "message": "❌ Сумма должна быть положительной"}
    
    data_manager.user_data[uid]["coins"] += amount
    update_league(uid)
    data_manager.save_data()
    return {
        "success": True,
        "message": f"✅ Выдано {format_number(amount)} монет пользователю {get_user_display_name(uid, data_manager.user_data[uid])}"
    }

def action_remove_coins(uid, amount: int):
    """Забрать монеты"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    if amount <= 0:
        return {"success": False, "message": "❌ Сумма должна быть положительной"}
    
    current = data_manager.user_data[uid]["coins"]
    data_manager.user_data[uid]["coins"] = max(0, current - amount)
    update_league(uid)
    data_manager.save_data()
    return {
        "success": True,
        "message": f"✅ Забрано {format_number(amount)} монет у {get_user_display_name(uid, data_manager.user_data[uid])}"
    }

def action_add_donate(uid, amount: int):
    """Выдать донат-коины"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    if amount <= 0:
        return {"success": False, "message": "❌ Сумма должна быть положительной"}
    
    data_manager.user_data[uid]["donate_coins"] += amount
    data_manager.save_data()
    return {
        "success": True,
        "message": f"✅ Выдано {amount} донат-коинов пользователю {get_user_display_name(uid, data_manager.user_data[uid])}"
    }

def action_remove_donate(uid, amount: int):
    """Забрать донат-коины"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    if amount <= 0:
        return {"success": False, "message": "❌ Сумма должна быть положительной"}
    
    current = data_manager.user_data[uid]["donate_coins"]
    data_manager.user_data[uid]["donate_coins"] = max(0, current - amount)
    data_manager.save_data()
    return {
        "success": True,
        "message": f"✅ Забрано {amount} донат-коинов у {get_user_display_name(uid, data_manager.user_data[uid])}"
    }

def action_add_premium(uid, days: int):
    """Выдать премиум"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    
    if days == 0:
        data_manager.user_data[uid]["premium"] = True
        data_manager.user_data[uid]["premium_until"] = 0
        desc = "навсегда"
    else:
        data_manager.user_data[uid]["premium"] = True
        data_manager.user_data[uid]["premium_until"] = time.time() + days * 86400
        desc = f"на {days} дней"
    
    data_manager.save_data()
    return {
        "success": True,
        "message": f"⭐ Премиум выдан {get_user_display_name(uid, data_manager.user_data[uid])} {desc}"
    }

def action_remove_premium(uid):
    """Забрать премиум"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    
    data_manager.user_data[uid]["premium"] = False
    data_manager.user_data[uid]["premium_until"] = 0
    data_manager.save_data()
    return {
        "success": True,
        "message": f"❌ Премиум снят с {get_user_display_name(uid, data_manager.user_data[uid])}"
    }

def action_ban(uid):
    """Забанить пользователя"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    
    data_manager.user_data[uid]["banned"] = True
    data_manager.user_data[uid]["auto_clicker"] = 0
    data_manager.save_data()
    return {
        "success": True,
        "message": f"🚫 Пользователь {get_user_display_name(uid, data_manager.user_data[uid])} забанен"
    }

def action_unban(uid):
    """Разбанить пользователя"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    
    data_manager.user_data[uid]["banned"] = False
    data_manager.save_data()
    return {
        "success": True,
        "message": f"✅ Пользователь {get_user_display_name(uid, data_manager.user_data[uid])} разбанен"
    }

def action_reset_user(uid):
    """Полный сброс данных игрока"""
    if uid not in data_manager.user_data:
        return {"success": False, "message": "❌ Пользователь не найден"}
    
    data_manager.reset_user_data(uid)
    return {
        "success": True,
        "message": f"🔄 Данные пользователя {get_user_display_name(uid, data_manager.user_data[uid])} сброшены"
    }

# === ИНФОРМАЦИОННЫЕ ФУНКЦИИ ===

def get_stats():
    """Статистика бота"""
    total_players = len([u for u in data_manager.user_data if data_manager.user_data[u].get("coins", 0) > 0 or data_manager.user_data[u].get("clicks", 0) > 0])
    total_coins = sum(u.get("coins", 0) for u in data_manager.user_data.values())
    total_donate = sum(u.get("donate_coins", 0) for u in data_manager.user_data.values())
    
    top_list = [(uid, data["coins"]) for uid, data in data_manager.user_data.items() if data.get("coins", 0) > 0]
    if top_list:
        top_player = max(top_list, key=lambda x: x[1])
        top_name = get_user_display_name(top_player[0], data_manager.user_data[top_player[0]])
        top_league = data_manager.user_data[top_player[0]].get("league", "-")
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
    return "\n".join(lines)

def get_user_info(uid):
    """Детальная информация о пользователе"""
    if uid not in data_manager.user_data:
        return "❌ Пользователь не найден"
    
    ud = data_manager.user_data[uid]
    name = get_user_display_name(uid, ud)
    
    lines = [
        f"👤 {name} (ID: {uid})",
        f"💰 Монеты: {format_number(int(ud.get('coins', 0)))}",
        f"💎 Донат: {ud.get('donate_coins', 0)}",
        f"🖱 Клики: {format_number(ud.get('clicks', 0))}",
        f"⚡ Сила клика: {ud.get('click_power', 1)}",
        f"🤖 Авто-кликер: {ud.get('auto_clicker', 0)} монет/мин",
        f"🏅 Лига: {ud.get('league', '🥉 Бронза')}",
        f"📛 Звание: {ud.get('title', 'Новичок')}",
        f"⭐ Премиум: {'Да' if is_premium_active(ud) else 'Нет'}",
        f"🚫 Забанен: {'Да' if ud.get('banned', False) else 'Нет'}",
        f"🏆 Достижения: {', '.join(config.ACHIEVEMENTS.get(k, {}).get('name', k) for k in ud.get('achievements', set())) or '-'}"
    ]
    return "\n".join(lines)

def get_econ_stats():
    """Статистика экономики"""
    total_coins = sum(u.get("coins", 0) for u in data_manager.user_data.values())
    total_spent = sum(u.get("total_spent", 0) for u in data_manager.user_data.values())
    total_issued = total_coins + total_spent
    active_players = len([u for u in data_manager.user_data.values() if u.get("coins", 0) > 0 or u.get("clicks", 0) > 0])
    
    lines = [
        "📈 Экономика бота:",
        f"💰 Всего выпущено: {format_number(int(total_issued))}",
        f"🔥 Всего потрачено: {format_number(int(total_spent))}",
        f"🪙 В обращении: {format_number(int(total_coins))}",
        f"👥 Активных игроков: {active_players}",
        "",
        f"📊 Инфляция: {format_number(int(total_spent / max(1, total_issued) * 100))}% монет уже потрачено"
    ]
    return "\n".join(lines)
