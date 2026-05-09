#!/usr/bin/env python3
"""
Auto-patcher для Clicker Bot
Исправляет критичные баги без изменения логики игры
"""

import os
import sys
import shutil
from datetime import datetime

BACKUP_DIR = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup_file(filepath):
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    if os.path.exists(filepath):
        shutil.copy2(filepath, os.path.join(BACKUP_DIR, os.path.basename(filepath)))
        print(f"✅ Бэкап: {filepath}")

def patch_handlers():
    """Исправления для handlers.py"""
    filepath = "handlers.py"
    if not os.path.exists(filepath):
        print(f"❌ {filepath} не найден")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Исправляем порядок проверки: game_state ДО is_admin
    old_text_handler = """async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if is_admin(user_id):
        state = context.user_data.get("admin_state")
        if state == "search_input":"""

    new_text_handler = """async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # 🎮 Игровые ставки — проверяем ПЕРВЫМ делом, чтобы админ тоже мог играть
    state = context.user_data.get("game_state")
    if state and context.user_data.get("game_user_id") == user_id:
        res = validate_bet(user_id, text, config.MIN_BET, config.MAX_BET)
        if not res["success"]:
            return await update.message.reply_text(res["message"])
        bet = res["bet"]
        if state == "crash":
            context.user_data.update({"crash_bet":bet,"crash_user_id":user_id})
            kb = [[InlineKeyboardButton(f"×{m}", callback_data=f"crash_multiplier_{m}") for m in [1.2,1.5,2.0,3.0,5.0]]]
            kb.append([InlineKeyboardButton("⬅️ Отмена", callback_data="back")])
            return await update.message.reply_text("💥 Выберите множитель:", reply_markup=InlineKeyboardMarkup(kb))
        elif state == "roulette":
            context.user_data.update({"roulette_bet":bet,"roulette_user_id":user_id})
            return await update.message.reply_text("🎰 Цвет:", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 Красное", callback_data="roulette_color_red"), InlineKeyboardButton("⚫ Чёрное", callback_data="roulette_color_black")],
                [InlineKeyboardButton("🟢 Зелёное", callback_data="roulette_color_green")]]))
        elif state == "duel":
            context.user_data["duel_bet"] = bet
            res_d = process_duel_game(user_id, bet)
            for key in list(context.user_data.keys()):
                if key.startswith(("game_", "crash_", "roulette_", "duel_")):
                    context.user_data.pop(key, None)
            return await update.message.reply_text(res_d["message"], reply_markup=get_main_menu())

    if is_admin(user_id):
        state = context.user_data.get("admin_state")
        if state == "search_input":"""

    content = content.replace(old_text_handler, new_text_handler)

    # 2. Частичная очистка вместо clear() после игр
    content = content.replace(
        "context.user_data.clear()", 
        """for key in list(context.user_data.keys()):
            if key.startswith(("game_", "crash_", "roulette_", "duel_")):
                context.user_data.pop(key, None)""")

    # 3. Частичная очистка в admin_main
    old_admin_main = """if data == "admin_main":
        context.user_data.clear()"""
    new_admin_main = """if data == "admin_main":
        for key in list(context.user_data.keys()):
            if key.startswith(("admin_", "game_", "crash_", "roulette_", "duel_")):
                context.user_data.pop(key, None)"""
    content = content.replace(old_admin_main, new_admin_main)

    # 4. Добавляем проверку banned в start_handler
    old_start = """async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    if not await check_subscription(user_id, context):"""
    new_start = """async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    if data_manager.user_data[user_id].get("banned", False):
        await update.message.reply_text("🚫 Вы забанены.")
        return

    if not await check_subscription(user_id, context):"""
    content = content.replace(old_start, new_start)

    # 5. Добавляем проверку banned в button_handler
    old_button = """async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data_manager.update_user_name(user_id, get_user_name(query.from_user))

    if not await check_subscription(user_id, context):"""
    new_button = """async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data_manager.update_user_name(user_id, get_user_name(query.from_user))

    if data_manager.user_data[user_id].get("banned", False):
        await query.edit_message_text("🚫 Вы забанены.")
        return

    if not await check_subscription(user_id, context):"""
    content = content.replace(old_button, new_button)

    # 6. Добавляем проверку banned в mm_handler
    old_mm = """async def mm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):"""
    new_mm = """async def mm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if data_manager.user_data[user_id].get("banned", False):
        await update.message.reply_text("🚫 Вы забанены.")
        return
    if not await check_subscription(user_id, context):"""
    content = content.replace(old_mm, new_mm)

    # 7. Добавляем обработку select_from_list
    old_input_value = """if state == "input_value":
            act = context.user_data.get("admin_action")"""
    new_input_value = """if state == "select_from_list":
            return await update.message.reply_text("👆 Выберите пользователя из списка выше.")

        if state == "input_value":
            act = context.user_data.get("admin_action")"""
    content = content.replace(old_input_value, new_input_value)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Патч применён: {filepath}")

def patch_data_manager():
    """Исправления для data_manager.py"""
    filepath = "data_manager.py"
    if not os.path.exists(filepath):
        print(f"❌ {filepath} не найден")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Заменяем load_data на версию с восстановлением defaultdict
    old_load = """def load_data():
    global user_data, user_names
    if not os.path.exists(config.DATA_FILE):
        print("Data file not found. Creating new.")
        return
    try:
        with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        loaded = data.get("user_data", {})
        for uid_str, ud in loaded.items():"""

    new_load = """def load_data():
    global user_data, user_names
    if not os.path.exists(config.DATA_FILE):
        print("Data file not found. Creating new.")
        return
    try:
        with open(config.DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        loaded = data.get("user_data", {})
        loaded_names = data.get("user_names", {})

        # Восстанавливаем defaultdict-поведение
        new_user_data = defaultdict(lambda: {
            "clicks": 0, "coins": 0, "click_power": 1.0, "auto_clicker": 0.0,
            "last_click": time.time(), "last_daily": 0, "achievements": set(),
            "title": "Novice", "league": "Bronze", "premium": False,
            "premium_until": 0, "donate_coins": 0, "referrer_id": None,
            "last_reminder": 0, "reminders_enabled": True
        })

        for uid_str, ud in loaded.items():"""

    content = content.replace(old_load, new_load)

    # Заменяем присвоение user_data
    old_assign = """            user_data[uid] = {
                "clicks": ud.get("clicks", 0), "coins": ud.get("coins", 0),
                "click_power": ud.get("click_power", 1.0), "auto_clicker": ud.get("auto_clicker", 0.0),
                "last_click": ud.get("last_click", time.time()), "last_daily": ud.get("last_daily", 0),
                "achievements": set(ud.get("achievements", [])), "title": ud.get("title", "Novice"),
                "league": ud.get("league", "Bronze"), "premium": ud.get("premium", False),
                "premium_until": ud.get("premium_until", 0), "donate_coins": ud.get("donate_coins", 0),
                "referrer_id": ud.get("referrer_id"), "last_reminder": ud.get("last_reminder", 0),
                "reminders_enabled": ud.get("reminders_enabled", True)
            }
        user_names.update(data.get("user_names", {}))"""

    new_assign = """            new_user_data[uid] = {
                "clicks": ud.get("clicks", 0), "coins": ud.get("coins", 0),
                "click_power": ud.get("click_power", 1.0), "auto_clicker": ud.get("auto_clicker", 0.0),
                "last_click": ud.get("last_click", time.time()), "last_daily": ud.get("last_daily", 0),
                "achievements": set(ud.get("achievements", [])), "title": ud.get("title", "Novice"),
                "league": ud.get("league", "Bronze"), "premium": ud.get("premium", False),
                "premium_until": ud.get("premium_until", 0), "donate_coins": ud.get("donate_coins", 0),
                "referrer_id": ud.get("referrer_id"), "last_reminder": ud.get("last_reminder", 0),
                "reminders_enabled": ud.get("reminders_enabled", True)
            }
        user_data = new_user_data
        user_names.update(loaded_names)"""

    content = content.replace(old_assign, new_assign)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Патч применён: {filepath}")

def patch_utils():
    """Исправления для utils.py"""
    filepath = "utils.py"
    if not os.path.exists(filepath):
        print(f"❌ {filepath} не найден")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Добавляем безопасный get_econ
    old_get_econ = """def get_econ(key: str):
    """📊 Безопасно достаёт значение по пути (например: 'income.click_base')"""
    econ = load_economy()
    keys = key.split(".")
    val = econ
    for k in keys:
        val = val[k]
    return val"""

    new_get_econ = """def get_econ(key: str, default=None):
    """📊 Безопасно достаёт значение по пути (например: 'income.click_base')"""
    econ = load_economy()
    keys = key.split(".")
    val = econ
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            print(f"⚠️ Ключ экономики '{key}' не найден, используется дефолт: {default}")
            return default
    return val"""

    content = content.replace(old_get_econ, new_get_econ)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Патч применён: {filepath}")

if __name__ == "__main__":
    print("🔧 Запуск патчера Clicker Bot...")
    print(f"📁 Бэкапы сохраняются в: {BACKUP_DIR}/")
    print()

    patch_handlers()
    patch_data_manager()
    patch_utils()

    print()
    print("✅ Все патчи применены!")
    print(f"📁 Оригинальные файлы сохранены в: {BACKUP_DIR}/")
    print("🔄 Перезапустите бота для применения изменений.")
