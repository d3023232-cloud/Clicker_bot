"""Основные обработчики бота"""
import time
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

import config
import data_manager
from utils import get_user_name, is_premium_active, format_number, check_subscription
from game_logic import process_click, get_profile_text, get_top_text, process_daily_bonus, apply_league_tax
from shop import buy_upgrade, buy_title, get_shop_upgrades_keyboard, get_shop_titles_keyboard, get_donat_shop_keyboard
from minigames import validate_bet, start_crash_game, process_crash_game, start_roulette_game, process_roulette_game, start_duel_game, process_duel_game
from admin import (
    is_admin, get_admin_panel_text, get_admin_keyboard, get_admin_command_description,
    find_user_by_query, get_user_display_name, get_admin_main_keyboard,
    action_add_coins, action_remove_coins, action_add_donate, action_remove_donate,
    action_add_premium, action_remove_premium, action_ban, action_unban, action_reset_user,
    get_stats, get_user_info, get_econ_stats
)


def get_main_menu():
    """Главное меню с кнопками"""
    keyboard = [
        [InlineKeyboardButton("🏆 Топ", callback_data='top'),
         InlineKeyboardButton("🛒 Магазин", callback_data='shop')],
        [InlineKeyboardButton("🎮 Мини-игры", callback_data='minigames'),
         InlineKeyboardButton("🎁 Ежедневный бонус", callback_data='daily')],
        [InlineKeyboardButton("💎 Donat-магазин", callback_data='donat_shop'),
         InlineKeyboardButton("🤝 Рефералка", callback_data='referral')],
        [InlineKeyboardButton("🏅 Достижения", callback_data='achievements'),
         InlineKeyboardButton("👤 Мой профиль", callback_data='my_profile')],
        [InlineKeyboardButton("🖱 Клик!", callback_data='click')]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    # 🔒 Проверка подписки
    if not await check_subscription(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{config.CHANNEL_USERNAME}")]]
        await update.message.reply_text(
            "❗ Для использования бота необходимо подписаться на наш канал:\n"
            f"@{config.CHANNEL_USERNAME}\n\n"
            "После подписки нажмите /start снова.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 🤝 Реферальная система
    if context.args and context.args[0].startswith('ref'):
        try:
            referrer_id = int(context.args[0][3:])
            if referrer_id != user_id and data_manager.user_data[user_id].get("referrer_id") is None:
                data_manager.user_data[user_id]["referrer_id"] = referrer_id
                data_manager.user_data[referrer_id]["donate_coins"] += 2
                data_manager.save_data()
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text="🎁 Вы получили 2 Donat-коина за приглашённого друга!"
                    )
                except Exception:
                    pass
        except ValueError:
            pass

    data_manager.save_data()

    # 📊 Применяем налог при входе
    apply_league_tax(user_id)

    # 🎨 Приветственное сообщение
    user_name = user.first_name or "Игрок"
    welcome_text = (
        "╔═══════════════════╗\n"
        "      🎮 CLICKER BOT 🎮\n"
        "╚═══════════════════╝\n\n"
        f"👋 Привет, {user_name}!\n\n"
        "✨ Твой прогресс начинается здесь:\n"
        "   🖱 Кликай → 🔧 Улучшай → 🏆 Будь первым\n\n"
        "🎁 Не забудь забрать ежедневный бонус!\n"
        "🎰 Испытай удачу в мини-играх!\n\n"
        "➡️ Жми кнопку «🖱 Клик!» и начни путь к славе! 👇"
    )

    await update.message.reply_text(welcome_text, reply_markup=get_main_menu())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    # 🔒 Проверка подписки
    if not await check_subscription(user_id, context):
        await query.edit_message_text(
            "❗ Вы не подписаны на канал! Подпишитесь, чтобы играть.\n"
            f"@{config.CHANNEL_USERNAME}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{config.CHANNEL_USERNAME}")]])
        )
        return

    # === АДМИН: Обработка кнопок панели ===
    if query.data.startswith("admin_"):
        await admin_callback_handler(update, context)
        return

    # === ГЛАВНОЕ МЕНЮ ===
    if query.data == 'click':
        result = process_click(user_id)
        ach_msg = ""
        if result["new_achievements"]:
            ach_names = [config.ACHIEVEMENTS[aid]["name"] for aid in result["new_achievements"]]
            ach_msg = "\n\n🎉 Новое достижение: " + ", ".join(ach_names) + "!"

        lines = [
            "🖱 Вы кликнули!",
            "💰 +" + format_number(int(result['coins_earned'])) + " монет от клика",
            "🤖 +" + format_number(int(result['auto_income'])) + " монет от автокликера",
            "🪙 Всего монет: " + format_number(int(result['total_coins'])),
            "⚡ Сила клика: " + str(result['click_power'])
        ]
        await query.edit_message_text(text="\n".join(lines) + ach_msg, reply_markup=get_main_menu())

    elif query.data == 'top':
        await query.edit_message_text(text=get_top_text(), reply_markup=get_main_menu())

    elif query.data == 'shop':
        keyboard = [
            [InlineKeyboardButton("🔧 Улучшения", callback_data='shop_upgrades')],
            [InlineKeyboardButton("🏅 Звания", callback_data='shop_titles')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
        ]
        await query.edit_message_text("🛒 Магазин:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'shop_upgrades':
        keyboard = get_shop_upgrades_keyboard(user_id)
        await query.edit_message_text("🔧 Улучшения:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'shop_titles':
        keyboard = get_shop_titles_keyboard(user_id)
        await query.edit_message_text("🏅 Звания (покупаются за монеты):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'daily':
        result = process_daily_bonus(user_id)
        if result["success"]:
            await query.edit_message_text(
                "🎁 Получено " + format_number(result['bonus']) + " монет!\nВозвращайтесь завтра!",
                reply_markup=get_main_menu()
            )
        else:
            await query.edit_message_text(
                "🎁 Бонус можно получить через " + str(result['hours_left']) + " ч.",
                reply_markup=get_main_menu()
            )

    elif query.data == 'achievements':
        ud = data_manager.user_data[user_id]
        msg = "🏅 Ваши достижения:\n"
        for key, ach in config.ACHIEVEMENTS.items():
            status = "✅" if key in ud["achievements"] else "❌"
            msg += status + " " + ach['name'] + " — " + ach['desc'] + "\n"
        msg += "\n👑 Ваше звание: " + ud['title']
        await query.edit_message_text(msg, reply_markup=get_main_menu())

    elif query.data == 'my_profile':
        msg = get_profile_text(user_id)
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=get_main_menu())

    elif query.data == 'referral':
        ref_link = f"https://t.me/{config.YOUR_BOT_USERNAME}?start=ref{user_id}"
        ud = data_manager.user_data[user_id]
        ref_count = len([u for u in data_manager.user_data.values() if u.get("referrer_id") == user_id])
        lines = [
            "🤝 **Реферальная система**",
            "",
            "🔗 Ваша ссылка:",
            ref_link,
            "",
            f"👥 Приглашено: **{ref_count}** друзей",
            "💎 За каждого: **2 Donat-коина**",
            f"💰 Всего получено: **{ud['donate_coins']}** Donat-коинов"
        ]
        await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=get_main_menu())

    elif query.data == 'donat_shop':
        keyboard = get_donat_shop_keyboard()
        await query.edit_message_text(
            "💎 **Donat-магазин (оплата звёздами)**\nПокупайте за ⭐:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith('buy_stars_'):
        item_key = query.data[10:]
        if item_key not in config.DONAT_SHOP:
            await query.edit_message_text("❌ Товар не найден.", reply_markup=get_main_menu())
            return

        item = config.DONAT_SHOP[item_key]
        try:
            from telegram import LabeledPrice
            await context.bot.send_invoice(
                chat_id=user_id,
                title=item['name'],
                description=item['desc'],
                payload=f"donat_{item_key}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Цена", amount=item['stars'])],
                max_tip_amount=0,
                suggested_tip_amounts=[],
                start_parameter="buy"
            )
        except Exception as e:
            print("❌ Ошибка при отправке инвойса: " + str(e))
            await query.edit_message_text("❌ Ошибка при создании инвойса.", reply_markup=get_main_menu())

    # === МИНИ-ИГРЫ ===
    elif query.data == 'minigames':
        keyboard = [
            [InlineKeyboardButton("💥 Краш (20–1 000 000 🪙)", callback_data='game_crash_start')],
            [InlineKeyboardButton("🎰 Рулетка (20–1 000 000 🪙)", callback_data='game_roulette_start')],
            [InlineKeyboardButton("⚔️ Дуэль (100–1 000 000 🪙)", callback_data='game_duel_start')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
        ]
        await query.edit_message_text("🎮 Выберите мини-игру:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'game_crash_start':
        result = start_crash_game(user_id)
        if not result["success"]:
            await query.answer(result["message"], show_alert=True)
            return

        lines = [
            "💥 **Краш-игра**",
            "Ставка от 20 до 1 000 000 монет.",
            "",
            "_Введите ставку в чат (например: 100)_"
        ]
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")
        context.user_data["game_state"] = "crash"
        context.user_data["game_user_id"] = user_id

    elif query.data.startswith('crash_multiplier_'):
        try:
            multiplier = float(query.data.split('_')[2])
            bet = context.user_data.get("crash_bet")
            crash_user_id = context.user_data.get("crash_user_id")

            if bet is None or crash_user_id != user_id:
                await query.edit_message_text("❌ Сессия устарела. Начните заново.", reply_markup=get_main_menu())
                return

            result = process_crash_game(user_id, bet, multiplier)
            if not result["success"]:
                await query.edit_message_text(result["message"], reply_markup=get_main_menu())
                return

            await query.edit_message_text(result["message"], parse_mode="HTML", reply_markup=get_main_menu())
            context.user_data.pop("crash_state", None)
            context.user_data.pop("crash_bet", None)
            context.user_data.pop("crash_user_id", None)
        except Exception as e:
            await query.edit_message_text("❌ Ошибка: " + str(e), reply_markup=get_main_menu())

    elif query.data == 'game_roulette_start':
        result = start_roulette_game(user_id)
        if not result["success"]:
            await query.answer(result["message"], show_alert=True)
            return

        lines = [
            "🎰 **Рулетка**",
            "Ставка от 20 до 1 000 000 монет.",
            "Выберите цвет:",
            "• 🔴 Красное (×1.9)",
            "• ⚫ Чёрное (×1.9)",
            "• 🟢 Зелёное (×9.0, шанс 10%)",
            "",
            "_Введите ставку в чат_"
        ]
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")
        context.user_data["game_state"] = "roulette"
        context.user_data["game_user_id"] = user_id

    elif query.data.startswith('roulette_color_'):
        color = query.data.split('_')[2]
        bet = context.user_data.get("roulette_bet")
        roulette_user_id = context.user_data.get("roulette_user_id")

        if bet is None or roulette_user_id != user_id:
            await query.edit_message_text("❌ Сессия устарела. Начните заново.", reply_markup=get_main_menu())
            return

        result = process_roulette_game(user_id, bet, color)
        if not result["success"]:
            await query.edit_message_text(result["message"], reply_markup=get_main_menu())
            return

        lines = [
            "🎰 **Рулетка**",
            result['message'],
            "",
            "🪙 Баланс: " + format_number(int(result['balance']))
        ]
        await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=get_main_menu())
        context.user_data.pop("roulette_state", None)
        context.user_data.pop("roulette_bet", None)
        context.user_data.pop("roulette_user_id", None)

    elif query.data == 'game_duel_start':
        result = start_duel_game(user_id)
        if not result["success"]:
            await query.answer(result["message"], show_alert=True)
            return

        lines = [
            "⚔️ **Дуэль с ботом**",
            "Ставка от 100 до 1 000 000 монет.",
            "Шанс победы: 48% (бот берёт 4% комиссии).",
            "",
            "_Введите ставку в чат_"
        ]
        await query.edit_message_text("\n".join(lines), parse_mode="HTML")
        context.user_data["game_state"] = "duel"
        context.user_data["game_user_id"] = user_id

    # === ПОКУПКИ ===
    elif query.data.startswith('buy_upg_'):
        upg_key = query.data[8:]
        result = buy_upgrade(user_id, upg_key)
        if result["success"]:
            if result.get("new_achievement"):
                await query.answer("🎉 Открыто достижение: Робо-помощник!", show_alert=True)
            await query.edit_message_text(result["message"], reply_markup=get_main_menu())

    elif query.data.startswith('buy_title_'):
        title_key = query.data[11:]
        result = buy_title(user_id, title_key)
        if result["success"]:
            await query.edit_message_text(result["message"], reply_markup=get_main_menu())
        else:
            await query.answer(result["message"], show_alert=True)

    elif query.data == 'back' or query.data == 'noop':
        await query.edit_message_text("🎮 Главное меню:", reply_markup=get_main_menu())


async def mm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /mm (мой профиль)"""
    user_id = update.effective_user.id
    data_manager.update_user_name(user_id, get_user_name(update.effective_user))

    if not await check_subscription(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Подписаться на канал", url=f"https://t.me/{config.CHANNEL_USERNAME}")]]
        await update.message.reply_text(
            "❗ Для использования бота необходимо подписаться на наш канал:\n"
            f"@{config.CHANNEL_USERNAME}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    apply_league_tax(user_id)
    msg = get_profile_text(user_id)
    await update.message.reply_text(msg, parse_mode="HTML")


async def admins_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admins"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return

    keyboard = get_admin_main_keyboard()
    msg = get_admin_panel_text()
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)


# ============================================================================
# 🛠 АДМИН: ИНТЕРАКТИВНЫЕ ОБРАБОТЧИКИ
# ============================================================================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-кнопок админ-панели"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Доступ запрещён")
        return

    data = query.data

    # === ГЛАВНОЕ МЕНЮ АДМИНА ===
    if data == "admin_main":
        context.user_data.clear()
        await query.edit_message_text("🛠 Админ-панель", reply_markup=get_admin_main_keyboard())
        return

    # === ИНФОРМАЦИОННЫЕ КНОПКИ ===
    if data == "admin_stats":
        await query.edit_message_text(get_stats(), reply_markup=get_admin_main_keyboard())
        return

    if data == "admin_econ":
        await query.edit_message_text(get_econ_stats(), reply_markup=get_admin_main_keyboard())
        return

    if data == "admin_search_prompt":
        context.user_data["admin_state"] = "search_input"
        context.user_data["admin_action"] = None
        await query.edit_message_text(
            "🔍 Введите @username, имя или ID игрока:\n"
            "Примеры: @player, Иван, 123456789",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
        )
        return

    # === ВЫБОР ДЕЙСТВИЯ ===
    actions = [
        "add_coins", "remove_coins",
        "add_donate", "remove_donate",
        "add_premium", "remove_premium",
        "ban", "unban", "reset"
    ]

    if any(data.startswith(f"admin_action_{a}") for a in actions):
        action = data.replace("admin_action_", "")
        uid = context.user_data.get("admin_selected_uid")

        if uid and uid in data_manager.user_data:
            context.user_data["admin_action"] = action
            context.user_data["admin_state"] = "input_value"

            prompts = {
                "add_coins": "💰 Введите количество монет для выдачи:",
                "remove_coins": "🔻 Введите количество монет для изъятия:",
                "add_donate": "💎 Введите количество донат-коинов для выдачи:",
                "remove_donate": "💸 Введите количество донат-коинов для изъятия:",
                "add_premium": "⭐ Введите количество дней премиума (0 = навсегда):",
            }

            if action in ["remove_premium", "ban", "unban", "reset"]:
                context.user_data["admin_value"] = 0
                context.user_data["admin_state"] = "confirm"
                user_name = get_user_display_name(uid, data_manager.user_data[uid])
                action_names = {
                    "remove_premium": "❌ Снять премиум",
                    "ban": "🚫 Забанить",
                    "unban": "✅ Разбанить",
                    "reset": "🔄 Полный сброс"
                }
                await query.edit_message_text(
                    f"⚠️ Подтвердите действие:\n"
                    f"👤 Игрок: {user_name}\n"
                    f"🔧 Действие: {action_names[action]}\n\n"
                    f"Нажмите ✅ для выполнения или ❌ для отмены",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{action}_{uid}"),
                         InlineKeyboardButton("❌ Отмена", callback_data="admin_main")]
                    ])
                )
            else:
                await query.edit_message_text(
                    f"👤 Выбран: {get_user_display_name(uid, data_manager.user_data[uid])}\n"
                    f"{prompts[action]}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
                )
        else:
            context.user_data["admin_action"] = action
            context.user_data["admin_state"] = "search_input"
            await query.edit_message_text(
                "🔍 Сначала найдите игрока.\n"
                "Введите @username, имя или ID:",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]])
            )
        return

    # === ВЫБОР ИЗ СПИСКА ПОИСКА ===
    if data.startswith("admin_select_"):
        uid = int(data.replace("admin_select_", ""))
        context.user_data["admin_selected_uid"] = uid

        action = context.user_data.get("admin_action")
        if action:
            context.user_data["admin_state"] = "input_value"
            prompts = {
                "add_coins": "💰 Введите количество монет для выдачи:",
                "remove_coins": "🔻 Введите количество монет для изъятия:",
                "add_donate": "💎 Введите количество донат-коинов для выдачи:",
                "remove_donate": "💸 Введите количество донат-коинов для изъятия:",
                "add_premium": "⭐ Введите количество дней премиума (0 = навсегда):",
            }
            await query.edit_message_text(
                f"👤 Выбран: {get_user_display_name(uid, data_manager.user_data[uid])}\n"
                f"{prompts.get(action, 'Введите значение:')}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
            )
        else:
            await query.edit_message_text(
                get_user_info(uid),
                reply_markup=get_admin_main_keyboard()
            )
        return

    # === ПОДТВЕРЖДЕНИЕ ДЕЙСТВИЯ ===
    if data.startswith("admin_confirm_"):
        parts = data.replace("admin_confirm_", "").split("_")
        action = parts[0]
        uid = int(parts[1])

        if action == "add_coins":
            value = context.user_data.get("admin_value", 0)
            result = action_add_coins(uid, value)
        elif action == "remove_coins":
            value = context.user_data.get("admin_value", 0)
            result = action_remove_coins(uid, value)
        elif action == "add_donate":
            value = context.user_data.get("admin_value", 0)
            result = action_add_donate(uid, value)
        elif action == "remove_donate":
            value = context.user_data.get("admin_value", 0)
            result = action_remove_donate(uid, value)
        elif action == "add_premium":
            value = context.user_data.get("admin_value", 0)
            result = action_add_premium(uid, value)
        elif action == "remove_premium":
            result = action_remove_premium(uid)
        elif action == "ban":
            result = action_ban(uid)
        elif action == "unban":
            result = action_unban(uid)
        elif action == "reset":
            result = action_reset_user(uid)
        else:
            result = {"success": False, "message": "❌ Неизвестное действие"}

        await query.edit_message_text(
            result["message"],
            reply_markup=get_admin_main_keyboard()
        )
        context.user_data.clear()
        return

    # === СИСТЕМНЫЕ ДЕЙСТВИЯ ===
    if data == "admin_broadcast":
        context.user_data["admin_state"] = "broadcast_input"
        await query.edit_message_text(
            "📢 Введите текст рассылки для всех игроков:\n"
            "Поддерживает HTML-разметку",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
        )
        return

    if data == "admin_reset_user":
        context.user_data["admin_action"] = "reset"
        context.user_data["admin_state"] = "search_input"
        await query.edit_message_text(
            "🔄 Сброс данных: найдите игрока.\n"
            "Введите @username, имя или ID:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]])
        )
        return


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений: ставки, админ-ввод, рассылка"""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # === АДМИН: Команда /econ ===
    if text.startswith("/econ"):
        if not is_admin(user_id):
            await update.message.reply_text("❌ Доступ запрещён")
            return
        args = text.split()[1:]
        result = get_econ_stats()
        await update.message.reply_text(result, parse_mode="HTML")
        return

    # === АДМИН: Состояния ввода ===
    if is_admin(user_id):
        admin_state = context.user_data.get("admin_state")

        # Поиск игрока
        if admin_state == "search_input":
            query_text = text.strip()
            found = []
            for uid, data in data_manager.user_data.items():
                name = data.get("name", "").lower()
                username = data.get("username", "").lower().lstrip('@')
                if query_text.lower() in name or (username and query_text.lower() == username) or (query_text.isdigit() and int(query_text) == uid):
                    found.append((uid, data))

            if not found:
                await update.message.reply_text(
                    "❌ Игроки не найдены. Попробуйте другой запрос.",
                    reply_markup=get_admin_main_keyboard()
                )
                context.user_data.pop("admin_state", None)
                return

            if len(found) == 1:
                uid, data = found[0]
                context.user_data["admin_selected_uid"] = uid
                context.user_data["admin_state"] = "action_select"
                await update.message.reply_text(
                    f"👤 Выбран: {get_user_display_name(uid, data)}\n"
                    "Выберите действие:",
                    reply_markup=get_admin_main_keyboard()
                )
            else:
                keyboard = []
                for uid, data in found[:10]:
                    display = get_user_display_name(uid, data)
                    keyboard.append([InlineKeyboardButton(f"👤 {display}", callback_data=f"admin_select_{uid}")])
                keyboard.append([InlineKeyboardButton("🔍 Искать заново", callback_data="admin_search_prompt")])
                keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")])
                await update.message.reply_text(
                    f"🔍 Найдено {len(found)} игроков. Выберите одного:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                context.user_data["admin_state"] = "select_from_list"
                context.user_data["admin_found_users"] = found
            return

        # Ввод значения (сумма, дни)
        if admin_state == "input_value":
            action = context.user_data.get("admin_action")
            uid = context.user_data.get("admin_selected_uid")

            if not action or not uid:
                await update.message.reply_text("❌ Ошибка сессии. Начните заново.", reply_markup=get_admin_main_keyboard())
                context.user_data.pop("admin_state", None)
                return

            try:
                value = int(text)
                if value <= 0 and action not in ["remove_premium", "ban", "unban", "reset"]:
                    await update.message.reply_text("❌ Введите положительное число", reply_markup=get_admin_main_keyboard())
                    return

                context.user_data["admin_value"] = value
                context.user_data["admin_state"] = "confirm"

                action_names = {
                    "add_coins": f"💰 Выдать {format_number(value)} монет",
                    "remove_coins": f"🔻 Забрать {format_number(value)} монет",
                    "add_donate": f"💎 Выдать {value} донат-коинов",
                    "remove_donate": f"💸 Забрать {value} донат-коинов",
                    "add_premium": f"⭐ Премиум на {value} дней" if value > 0 else "⭐ Премиум навсегда",
                }

                user_name = get_user_display_name(uid, data_manager.user_data[uid])
                await update.message.reply_text(
                    f"⚠️ Подтвердите действие:\n"
                    f"👤 Игрок: {user_name}\n"
                    f"🔧 Действие: {action_names.get(action, action)}\n\n"
                    f"Нажмите ✅ для выполнения или ❌ для отмены",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{action}_{uid}"),
                         InlineKeyboardButton("❌ Отмена", callback_data="admin_main")]
                    ])
                )
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число", reply_markup=get_admin_main_keyboard())
                context.user_data.pop("admin_state", None)
            return

        # Рассылка
        if admin_state == "broadcast_input":
            await update.message.reply_text("📢 Рассылка отправляется...")
            sent = 0
            failed = 0
            for uid in data_manager.user_data:
                try:
                    await context.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
                    sent += 1
                except Exception:
                    failed += 1
            await update.message.reply_text(
                f"✅ Рассылка завершена!\n"
                f"📤 Отправлено: {sent}\n"
                f"❌ Ошибок: {failed}",
                reply_markup=get_admin_main_keyboard()
            )
            context.user_data.pop("admin_state", None)
            return

    # === ИГРОК: Ввод ставок в мини-играх ===
    state = context.user_data.get("game_state")
    if state and context.user_data.get("game_user_id") == user_id:
        result = validate_bet(user_id, text, config.MIN_BET, config.MAX_BET)
        if not result["success"]:
            await update.message.reply_text(result["message"])
            return

        bet = result["bet"]

        if state == "crash":
            context.user_data["crash_bet"] = bet
            context.user_data["crash_user_id"] = user_id
            keyboard = [[InlineKeyboardButton(f"×{m}", callback_data=f"crash_multiplier_{m}")] for m in [1.2, 1.5, 2.0, 3.0, 5.0]]
            keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data="back")])
            await update.message.reply_text("💥 Выберите коэффициент для вывода:", reply_markup=InlineKeyboardMarkup(keyboard))

        elif state == "roulette":
            context.user_data["roulette_bet"] = bet
            context.user_data["roulette_user_id"] = user_id
            await update.message.reply_text("🎰 Выберите цвет:", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 Красное", callback_data="roulette_color_red"),
                 InlineKeyboardButton("⚫ Чёрное", callback_data="roulette_color_black")],
                [InlineKeyboardButton("🟢 Зелёное", callback_data="roulette_color_green")]
            ]))

        elif state == "duel":
            context.user_data["duel_bet"] = bet
            result_duel = process_duel_game(user_id, bet)
            await update.message.reply_text(result_duel["message"], reply_markup=get_main_menu())
            context.user_data.pop("game_state", None)
            context.user_data.pop("game_user_id", None)
