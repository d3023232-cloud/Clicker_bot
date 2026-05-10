"""Основные обработчики бота — полная версия по ТЗ"""
import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

import config
import data_manager
from utils import get_user_name, is_premium_active, format_number, check_subscription
from game_logic import process_click, get_profile_text, get_top_text, process_daily_bonus, apply_league_tax
from shop import buy_upgrade, buy_title, get_shop_upgrades_keyboard, get_shop_titles_keyboard, get_donat_shop_keyboard
from minigames import validate_bet, start_crash_game, process_crash_game, start_roulette_game, process_roulette_game, start_duel_game, process_duel_game
from admin import (
    is_admin, get_admin_panel_text, get_admin_main_keyboard,
    action_add_coins, action_remove_coins, action_add_donate, action_remove_donate,
    action_add_premium, action_remove_premium, action_ban, action_unban, action_reset_user,
    get_stats, get_user_info, get_econ_stats, get_user_display_name
)

# ============================================================================
# 🎨 КЛАВИАТУРЫ
# ============================================================================

def get_main_menu():
    """Главное меню по ТЗ: Профиль, Топ, Магазин, Донат, Мини-игры, Бонус"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🏆 Топ", callback_data="top")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop"), InlineKeyboardButton("💎 Донат", callback_data="donat")],
        [InlineKeyboardButton("🎮 Мини-игры", callback_data="minigames"), InlineKeyboardButton("🎁 Бонус", callback_data="daily")],
        [InlineKeyboardButton("🖱 Клик!", callback_data="click")]
    ])

def get_profile_submenu():
    """Подменю Профиля: Рефералка, Достижения, Промокод"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Рефералка", callback_data="referral"), InlineKeyboardButton("🏅 Достижения", callback_data="achievements")],
        [InlineKeyboardButton("🎟 Ввести промокод", callback_data="promocode")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ])

def get_shop_submenu():
    """Подменю Магазина: Улучшения, Звания"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Улучшения", callback_data="shop_upgrades")],
        [InlineKeyboardButton("🎖 Звания", callback_data="shop_titles")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ])

def get_donat_submenu():
    """Подменю Доната: Премиум, Монеты, Клики"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Премиум-статус", callback_data="donat_premium")],
        [InlineKeyboardButton("🪙 Монеты", callback_data="donat_coins")],
        [InlineKeyboardButton("👆 Клики", callback_data="donat_clicks")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ])

def get_minigames_menu():
    """Меню мини-игр"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💥 Краш", callback_data="game_crash_start")],
        [InlineKeyboardButton("🎰 Рулетка", callback_data="game_roulette_start")],
        [InlineKeyboardButton("⚔️ Дуэль", callback_data="game_duel_start")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ])

def get_subscription_keyboard():
    """Клавиатура для проверки подписки"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Перейти в канал", url=f"https://t.me/{config.CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ Я подписался — проверить", callback_data="check_subscription")]
    ])

def get_back_button(parent):
    """Универсальная кнопка Назад"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_{parent}")]])

# ============================================================================
# 🚀 СТАРТ
# ============================================================================

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    if data_manager.user_data[user_id].get("banned", False):
        await update.message.reply_text("🚫 Вы забанены.")
        return

    if not await check_subscription(user_id, context):
        text = (
            "🔒 <b>Доступ ограничен</b>\n\n"
            "Чтобы начать игру и получить доступ ко всем функциям, "
            "необходимо подписаться на наш новостной канал.\n\n"
            "📌 Там вы найдёте:\n"
            "• Новости и обновления бота\n"
            "• Промокоды и бонусы\n"
            "• Конкурсы с призами\n\n"
            "👇 Нажмите кнопку ниже, подпишитесь, затем нажмите <b>«Проверить»</b>"
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_subscription_keyboard())
        return

    if context.args and context.args[0].startswith("ref"):
        try:
            ref_id = int(context.args[0][3:])
            if ref_id != user_id and data_manager.user_data[user_id].get("referrer_id") is None:
                data_manager.user_data[user_id]["referrer_id"] = ref_id
                data_manager.user_data[ref_id]["donate_coins"] += 2
                data_manager.save_data()
                try:
                    await context.bot.send_message(ref_id, "🎁 +2 Donat-коина за друга!")
                except:
                    pass
        except:
            pass

    data_manager.save_data()
    apply_league_tax(user_id)

    name = user.first_name or "Игрок"
    text = (
        f"<b>Приветствую, {name}.</b>\n\n"
        "Добро пожаловать в мир, где каждый клик приближает к цели.\n"
        "Здесь терпение вознаграждается, а упорство — уважением.\n\n"
        "<i>— Начните с малого. Достигните большего.</i>\n\n"
        "<b>Что вас ждёт:</b>\n"
        "  ◦ Простая механика с глубоким прогрессом\n"
        "  ◦ Мини-игры для разнообразия\n"
        "  ◦ Система достижений и званий\n"
        "  ◦ Ежедневные бонусы\n\n"
        "<i>Каждый топ начинал с нуля.</i>\n\n"
        "👇 <b>Ваш путь начинается здесь</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_main_menu())

# ============================================================================
# 🔘 ОБРАБОТЧИК КНОПОК
# ============================================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data_manager.update_user_name(user_id, get_user_name(query.from_user))

    # Проверка подписки
    if query.data == "check_subscription":
        if await check_subscription(user_id, context):
            await query.edit_message_text(
                "✅ Подписка подтверждена! Добро пожаловать! 🎉\n\n"
                "Нажмите /start чтобы начать игру.",
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ Вы ещё не подписались на канал!", show_alert=True)
        return

    if data_manager.user_data[user_id].get("banned", False):
        await query.edit_message_text("🚫 Вы забанены.")
        return

    if not await check_subscription(user_id, context):
        text = (
            "🔒 <b>Доступ ограничен</b>\n\n"
            "Для продолжения необходимо подписаться на наш новостной канал.\n\n"
            "👇 Подпишитесь и нажмите <b>«Проверить»</b>"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=get_subscription_keyboard())
        return

    # Админ-панель
    if query.data.startswith("admin_"):
        await _admin_callback(query, context, user_id)
        return

    # === ГЛАВНОЕ МЕНЮ ===
    if query.data == "main_menu" or query.data == "back_to_main":
        await query.edit_message_text("🎮 Главное меню:", reply_markup=get_main_menu())
        return

    # === КЛИК ===
    if query.data == "click":
        res = process_click(user_id)
        ach = ""
        if res.get("new_achievements"):
            names = [config.ACHIEVEMENTS[k]["name"] for k in res["new_achievements"]]
            ach = f"\n\n🎉 Достижение: {', '.join(names)}!"
        vip = " 👑" if is_premium_active(data_manager.user_data[user_id]) else ""
        await query.edit_message_text(
            f"🖱 Клик!{vip}\n💰 +{format_number(int(res['coins_earned']))} (клик)\n"
            f"🤖 +{format_number(int(res['auto_income']))} (авто)\n"
            f"🪙 Всего: {format_number(int(res['total_coins']))}\n"
            f"⚡ Сила: {res['click_power']}{ach}",
            reply_markup=get_main_menu()
        )

    # === ПРОФИЛЬ ===
    elif query.data == "profile":
        await show_profile(query, user_id)
    elif query.data == "back_to_profile":
        await show_profile(query, user_id)

    # === ТОП ===
    elif query.data == "top":
        await show_top(query, user_id)
    elif query.data == "back_to_top":
        await show_top(query, user_id)

    # === МАГАЗИН ===
    elif query.data == "shop":
        await query.edit_message_text("🛒 Магазин:", reply_markup=get_shop_submenu())
    elif query.data == "back_to_shop":
        await query.edit_message_text("🛒 Магазин:", reply_markup=get_shop_submenu())
    elif query.data == "shop_upgrades":
        await show_upgrades(query, user_id)
    elif query.data == "shop_titles":
        await query.edit_message_text("🏅 Звания:", reply_markup=InlineKeyboardMarkup(get_shop_titles_keyboard(user_id)))

    # === ДОНАТ ===
    elif query.data == "donat":
        await query.edit_message_text("💎 Донат-магазин:", reply_markup=get_donat_submenu())
    elif query.data == "back_to_donat":
        await query.edit_message_text("💎 Донат-магазин:", reply_markup=get_donat_submenu())
    elif query.data == "donat_premium":
        await show_premium_info(query, user_id)
    elif query.data == "donat_coins":
        await show_donat_coins(query, user_id)
    elif query.data == "donat_clicks":
        await show_donat_clicks(query, user_id)

    # === МИНИ-ИГРЫ ===
    elif query.data == "minigames":
        await show_minigames(query, user_id)
    elif query.data == "back_to_minigames":
        await show_minigames(query, user_id)
    elif query.data == "game_crash_start":
        await start_crash(query, context, user_id)
    elif query.data == "game_roulette_start":
        await start_roulette(query, context, user_id)
    elif query.data == "game_duel_start":
        await start_duel(query, context, user_id)

    # === БОНУС ===
    elif query.data == "daily":
        await process_daily(query, user_id)

    # === РЕФЕРАЛКА ===
    elif query.data == "referral":
        await show_referral(query, user_id)
    elif query.data == "back_to_referral":
        await show_referral(query, user_id)

    # === ДОСТИЖЕНИЯ ===
    elif query.data == "achievements":
        await show_achievements(query, user_id)

    # === ПРОМОКОД ===
    elif query.data == "promocode":
        context.user_data["promo_state"] = "input"
        await query.edit_message_text(
            "🎟 Введите промокод:\n\n"
            "(или нажмите Назад)",
            reply_markup=get_back_button("profile")
        )

    # === ПОКУПКИ ===
    elif query.data.startswith("buy_upg_"):
        await process_upgrade_buy(query, user_id, query.data[8:])
    elif query.data.startswith("buy_title_"):
        res = buy_title(user_id, query.data[11:])
        await query.edit_message_text(res["message"], reply_markup=get_shop_submenu())
    elif query.data.startswith("buy_stars_"):
        await process_donat_buy(query, context, user_id, query.data[10:])

    # === ИГРОВЫЕ КНОПКИ ===
    elif query.data.startswith("crash_multiplier_"):
        await process_crash_multiplier(query, context, user_id)
    elif query.data.startswith("roulette_color_"):
        await process_roulette_color(query, context, user_id)

    # === НАЗАД (универсальные) ===
    elif query.data in ("back", "noop"):
        await query.edit_message_text("🎮 Главное меню:", reply_markup=get_main_menu())

# ============================================================================
# 👤 ПРОФИЛЬ (по ТЗ)
# ============================================================================

async def show_profile(query, user_id):
    """Экран Профиля по ТЗ: статистика + кнопки Рефералка/Достижения/Промокод"""
    ud = data_manager.user_data[user_id]
    vip = " 👑" if is_premium_active(ud) else ""

    text = (
        f"<b>👤 Профиль{vip}</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Ник: {ud.get('name', 'Игрок')}\n"
        f"🪙 Баланс: {format_number(int(ud['coins']))}\n"
        f"⚡ Сила клика: {ud['click_power']}\n"
        f"🤖 Авто-доход: {ud['auto_clicker']}/сек\n"
        f"🏅 Звание: {ud['title']}\n"
        f"🏆 Лига: {ud['league']}\n"
        f"🖱 Всего кликов: {format_number(ud['clicks'])}\n"
        f"💎 Донат-коины: {ud['donate_coins']}\n"
        f"{('👑 VIP активен!' if vip else '')}"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=get_profile_submenu())

async def show_referral(query, user_id):
    """Рефералка"""
    link = f"https://t.me/{config.YOUR_BOT_USERNAME}?start=ref{user_id}"
    count = len([u for u in data_manager.user_data.values() if u.get("referrer_id") == user_id])
    earned = data_manager.user_data[user_id]['donate_coins']

    text = (
        "🤝 <b>Реферальная программа</b>\n\n"
        f"🔗 Ваша ссылка:\n<code>{link}</code>\n\n"
        f"👥 Приглашено друзей: {count}\n"
        f"💎 Получено донат-коинов: {earned}\n\n"
        "<i>За каждого друга — 2 ⭐</i>"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=get_back_button("profile"))

async def show_achievements(query, user_id):
    """Достижения"""
    ud = data_manager.user_data[user_id]
    text = "🏅 <b>Достижения</b>\n\n"
    for k, v in config.ACHIEVEMENTS.items():
        status = "✅" if k in ud['achievements'] else "❌"
        text += f"{status} {v['name']} — {v['desc']}\n"
    text += f"\n👑 Звание: {ud['title']}"
    await query.edit_message_text(text, reply_markup=get_back_button("profile"))

# ============================================================================
# 🏆 ТОП-10 (по ТЗ)
# ============================================================================

async def show_top(query, user_id):
    """ТОП-10 + личная позиция"""
    sorted_users = sorted(data_manager.user_data.items(), key=lambda x: x[1]["coins"], reverse=True)

    text = "🏆 <b>ТОП-10 игроков</b>\n\n"

    for i, (uid, ud) in enumerate(sorted_users[:10], 1):
        vip = " 👑" if is_premium_active(ud) else ""
        name = ud.get('name', f'ID{uid}')
        marker = " →" if uid == user_id else ""
        text += f"{i}. {name}{vip} — {format_number(int(ud['coins']))}{marker}\n"

    # Личная позиция
    user_position = None
    for i, (uid, _) in enumerate(sorted_users, 1):
        if uid == user_id:
            user_position = i
            break

    if user_position and user_position > 10:
        text += f"\n📍 <b>Ваше место: {user_position}</b>"
    elif user_position and user_position <= 10:
        text += "\n✨ <b>Вы в ТОП-10!</b>"
    else:
        text += "\n📍 <b>Вы ещё не в рейтинге</b>"

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=get_back_button("main"))

# ============================================================================
# 🛒 МАГАЗИН (по ТЗ)
# ============================================================================

async def show_upgrades(query, user_id):
    """Улучшения — список с ценами"""
    ud = data_manager.user_data[user_id]
    text = (
        "⚡ <b>Улучшения</b>\n\n"
        f"🪙 Баланс: {format_number(int(ud['coins']))}\n"
        f"⚡ Текущая сила: {ud['click_power']}\n\n"
        "Выберите улучшение:"
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(get_shop_upgrades_keyboard(user_id)))

async def process_upgrade_buy(query, user_id, upgrade_id):
    """Покупка улучшения с подтверждением"""
    from shop import calc_upgrade_cost, UPGRADES

    ud = data_manager.user_data[user_id]
    current_level = ud.get(f"upgrade_{upgrade_id}", 0)
    cost = calc_upgrade_cost(upgrade_id, current_level)

    if ud["coins"] < cost:
        await query.answer("❌ Недостаточно монет!", show_alert=True)
        return

    # Экран подтверждения
    new_power = UPGRADES[upgrade_id]["effect"](ud["click_power"], current_level + 1)
    increase = new_power - ud["click_power"]

    text = (
        f"⚡ <b>Подтверждение покупки</b>\n\n"
        f"Улучшение: {UPGRADES[upgrade_id]['name']}\n"
        f"Уровень: {current_level + 1}\n\n"
        f"⚡ Сила: {ud['click_power']} → <b>{new_power}</b> (+{increase})\n"
        f"🪙 Стоимость: {format_number(cost)}\n"
        f"💰 Баланс: {format_number(int(ud['coins']))}\n\n"
        f"После покупки: {format_number(int(ud['coins'] - cost))}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Купить за {format_number(cost)}", callback_data=f"confirm_upg_{upgrade_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_shop")]
    ])

    await query.edit_message_text(text, reply_markup=kb)

# ============================================================================
# 💎 ДОНАТ (по ТЗ)
# ============================================================================

async def show_premium_info(query, user_id):
    """Информация о Премиуме"""
    ud = data_manager.user_data[user_id]
    text = (
        "💎 <b>Премиум-статус</b> 👑\n\n"
        "<b>Что даёт премиум:</b>\n"
        "  ◦ x2 сила клика\n"
        "  ◦ x2 авто-доход\n"
        "  ◦ 72 часа авто-дохода бонусом\n"
        "  ◦ x3 ежедневный бонус\n"
        "  ◦ VIP-значок 👑 рядом с ником\n\n"
        "<b>Стоимость (1 месяц):</b>\n"
        "  • 100 ⭐ (Telegram Stars)\n"
        "  • Или 150 донат-коинов\n"
        "  • Или 100 ₽ (скоро)\n\n"
        f"💎 Ваши донат-коины: {ud['donate_coins']}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить за 100 Stars", callback_data="buy_premium_stars")],
        [InlineKeyboardButton("🪙 Купить за 150 донат", callback_data="buy_premium_donate")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_donat")]
    ])

    await query.edit_message_text(text, reply_markup=kb)

async def show_donat_coins(query, user_id):
    """Покупка монет"""
    ud = data_manager.user_data[user_id]
    text = (
        "🪙 <b>Покупка монет</b>\n\n"
        f"💰 Текущий баланс: {format_number(int(ud['coins']))}\n\n"
        "Выберите количество:"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("100 000 🪙 — 25 ⭐", callback_data="buy_coins_100k_stars")],
        [InlineKeyboardButton("100 000 🪙 — 75 донат", callback_data="buy_coins_100k_donate")],
        [InlineKeyboardButton("1 000 000 🪙 — 65 ⭐", callback_data="buy_coins_1m_stars")],
        [InlineKeyboardButton("1 000 000 🪙 — 195 донат", callback_data="buy_coins_1m_donate")],
        [InlineKeyboardButton("10 000 000 🪙 — 250 ⭐", callback_data="buy_coins_10m_stars")],
        [InlineKeyboardButton("10 000 000 🪙 — 750 донат", callback_data="buy_coins_10m_donate")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_donat")]
    ])

    await query.edit_message_text(text, reply_markup=kb)

async def show_donat_clicks(query, user_id):
    """Покупка кликов"""
    ud = data_manager.user_data[user_id]
    text = (
        "👆 <b>Покупка силы клика</b>\n\n"
        f"⚡ Текущая сила: {ud['click_power']}\n"
        f"💎 Донат-коины: {ud['donate_coins']}\n\n"
        "Выберите усиление:"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("+5 клик — 40 ⭐", callback_data="buy_click_5_stars")],
        [InlineKeyboardButton("+5 клик — 120 донат", callback_data="buy_click_5_donate")],
        [InlineKeyboardButton("+10 клик — 90 ⭐", callback_data="buy_click_10_stars")],
        [InlineKeyboardButton("+10 клик — 270 донат", callback_data="buy_click_10_donate")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_donat")]
    ])

    await query.edit_message_text(text, reply_markup=kb)

# ============================================================================
# 🎮 МИНИ-ИГРЫ (по ТЗ — с балансом)
# ============================================================================

async def show_minigames(query, user_id):
    """Мини-игры с отображением баланса"""
    ud = data_manager.user_data[user_id]
    text = (
        "🎮 <b>Мини-игры</b>\n\n"
        f"🪙 Ваш баланс: {format_number(int(ud['coins']))}\n"
        f"📉 Мин. ставка: {format_number(config.MIN_BET)}\n"
        f"📈 Макс. ставка: {format_number(config.MAX_BET)}\n\n"
        "Выберите игру:"
    )
    await query.edit_message_text(text, reply_markup=get_minigames_menu())

async def start_crash(query, context, user_id):
    """Старт Краша"""
    res = start_crash_game(user_id)
    if not res["success"]:
        return await query.answer(res["message"], show_alert=True)
    context.user_data.update({"game_state": "crash", "game_user_id": user_id})
    ud = data_manager.user_data[user_id]
    await query.edit_message_text(
        f"💥 <b>Краш</b>\n\n"
        f"🪙 Баланс: {format_number(int(ud['coins']))}\n"
        f"📉 Ставка: {format_number(config.MIN_BET)} – {format_number(config.MAX_BET)}\n\n"
        "_Введите число в чат_",
        parse_mode="HTML"
    )

async def start_roulette(query, context, user_id):
    """Старт Рулетки"""
    res = start_roulette_game(user_id)
    if not res["success"]:
        return await query.answer(res["message"], show_alert=True)
    context.user_data.update({"game_state": "roulette", "game_user_id": user_id})
    ud = data_manager.user_data[user_id]
    await query.edit_message_text(
        f"🎰 <b>Рулетка</b>\n\n"
        f"🪙 Баланс: {format_number(int(ud['coins']))}\n"
        f"🔴/⚫ ×1.9 | 🟢 ×9.0\n\n"
        "_Введите ставку в чат_",
        parse_mode="HTML"
    )

async def start_duel(query, context, user_id):
    """Старт Дуэли"""
    res = start_duel_game(user_id)
    if not res["success"]:
        return await query.answer(res["message"], show_alert=True)
    context.user_data.update({"game_state": "duel", "game_user_id": user_id})
    ud = data_manager.user_data[user_id]
    await query.edit_message_text(
        f"⚔️ <b>Дуэль</b> (48% победа)\n\n"
        f"🪙 Баланс: {format_number(int(ud['coins']))}\n"
        f"📉 Мин. ставка: {format_number(config.MIN_DUEL_BET)}\n\n"
        "_Введите ставку в чат_",
        parse_mode="HTML"
    )

# ============================================================================
# 🎁 БОНУС (рандом 10-10000 по ТЗ)
# ============================================================================

async def process_daily(query, user_id):
    """Ежедневный бонус — рандом 10-10000"""
    ud = data_manager.user_data[user_id]
    now = time.time()
    last = ud.get("last_daily", 0)

    if now - last < 86400:
        hours_left = int((86400 - (now - last)) / 3600)
        await query.edit_message_text(f"🎁 Бонус доступен через {hours_left} ч.", reply_markup=get_main_menu())
        return

    # Рандомный бонус 10-10000
    bonus = random.randint(10, 10000)
    ud["coins"] += bonus
    ud["last_daily"] = now
    data_manager.save_data()

    await query.edit_message_text(
        f"🍀 <b>Вы испытали сегодняшнюю удачу!</b>\n\n"
        f"🎁 Ваш бонус: {format_number(bonus)} монет!\n"
        f"🪙 Новый баланс: {format_number(int(ud['coins']))}\n\n"
        "Возвращайтесь завтра! 🎰",
        reply_markup=get_main_menu()
    )

# ============================================================================
# 🎟 ПРОМОКОДЫ
# ============================================================================

async def process_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, code):
    """Обработка введённого промокода"""
    from promocodes import check_promocode, use_promocode

    result = check_promocode(code, user_id)
    if not result["success"]:
        await update.message.reply_text(f"❌ {result['message']}")
        return

    rewards = use_promocode(code, user_id)

    text = "🎉 <b>Промокод активирован!</b>\n\n"
    if rewards.get("coins"):
        text += f"🪙 +{format_number(rewards['coins'])} монет\n"
    if rewards.get("donate_coins"):
        text += f"💎 +{rewards['donate_coins']} донат-коинов\n"
    if rewards.get("premium_days"):
        text += f"👑 +{rewards['premium_days']} дней премиума\n"

    text += f"\nОсталось активаций: {rewards['uses_left']}"

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_profile_submenu())
    context.user_data.pop("promo_state", None)

# ============================================================================
# 🛠 АДМИН-ПАНЕЛЬ (расширенная — с промокодами)
# ============================================================================

async def _admin_callback(query, context, user_id):
    data = query.data

    if data == "admin_main":
        for key in list(context.user_data.keys()):
            if key.startswith(("admin_", "game_", "crash_", "roulette_", "duel_", "promo_")):
                context.user_data.pop(key, None)
        return await query.edit_message_text("🛠 Админ-панель", reply_markup=get_admin_main_keyboard())

    if data in ("admin_stats", "admin_econ"):
        return await query.edit_message_text(get_econ_stats() if data == "admin_econ" else get_stats(), reply_markup=get_admin_main_keyboard())

    if data == "admin_search_prompt":
        context.user_data.update({"admin_state": "search_input", "admin_action": None})
        return await query.edit_message_text("🔍 Введите @, имя или ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]]))

    # Промокоды в админке
    if data == "admin_promo_create":
        context.user_data["admin_state"] = "promo_create_name"
        return await query.edit_message_text(
            "🎟 <b>Создание промокода</b>\n\n"
            "Введите название промокода (по которому будут активировать):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
        )

    if data == "admin_promo_delete":
        context.user_data["admin_state"] = "promo_delete"
        return await query.edit_message_text(
            "🗑 Введите название промокода для удаления:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
        )

    if data == "admin_promo_list":
        from promocodes import list_promocodes
        text = list_promocodes()
        return await query.edit_message_text(text, reply_markup=get_admin_main_keyboard())

    # Стандартные действия админа
    actions = ["add_coins", "remove_coins", "add_donate", "remove_donate", "add_premium", "remove_premium", "ban", "unban", "reset"]
    if any(data.startswith(f"admin_action_{a}") for a in actions):
        act = data.replace("admin_action_", "")
        uid = context.user_data.get("admin_selected_uid")
        if uid and uid in data_manager.user_data:
            context.user_data.update({"admin_action": act, "admin_state": "input_value" if act not in ("remove_premium","ban","unban","reset") else "confirm"})
            if act in ("remove_premium","ban","unban","reset"):
                names = {"remove_premium":"❌ Снять премиум","ban":"🚫 Бан","unban":"✅ Разбан","reset":"🔄 Сброс"}
                return await query.edit_message_text(f"⚠️ {names[act]}\n👤 {get_user_display_name(uid, data_manager.user_data[uid])}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ ОК", callback_data=f"admin_confirm_{act}_{uid}"), InlineKeyboardButton("❌ Отмена", callback_data="admin_main")]]))
            prompts = {"add_coins":"💰 Сумма монет:","remove_coins":"🔻 Забрать монет:","add_donate":"💎 Донат-коинов:","remove_donate":"💸 Забрать донат:","add_premium":"⭐ Дней (0=навсегда):"}
            return await query.edit_message_text(f"👤 {get_user_display_name(uid, data_manager.user_data[uid])}\n{prompts[act]}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]]))
        context.user_data.update({"admin_action": act, "admin_state": "search_input"})
        return await query.edit_message_text("🔍 Найдите игрока (@/имя/ID):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]]))

    if data.startswith("admin_select_"):
        uid = int(data.replace("admin_select_", ""))
        context.user_data["admin_selected_uid"] = uid
        if context.user_data.get("admin_action"):
            context.user_data["admin_state"] = "input_value"
            return await query.edit_message_text(f"👤 {get_user_display_name(uid, data_manager.user_data[uid])}\n💬 Введите значение:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]]))
        return await query.edit_message_text(get_user_info(uid), reply_markup=get_admin_main_keyboard())

    if data.startswith("admin_confirm_"):
        rest = data.replace("admin_confirm_", "")
        action, uid_str = rest.rsplit("_", 1)
        uid = int(uid_str)

        funcs = {
            "add_coins": action_add_coins, "remove_coins": action_remove_coins,
            "add_donate": action_add_donate, "remove_donate": action_remove_donate,
            "add_premium": action_add_premium
        }
        val = context.user_data.get("admin_value", 0)
        if action in funcs:
            res = funcs[action](uid, val)
        else:
            res = {"ban": action_ban, "unban": action_unban, "remove_premium": action_remove_premium, "reset": action_reset_user}.get(action, lambda u: {"success": False, "message": "❌ Неизвестное действие"})(uid)

        for key in list(context.user_data.keys()):
            if key.startswith(("admin_", "game_", "crash_", "roulette_", "duel_", "promo_")):
                context.user_data.pop(key, None)
        return await query.edit_message_text(res["message"], reply_markup=get_admin_main_keyboard())

    if data == "admin_broadcast":
        context.user_data["admin_state"] = "broadcast_input"
        return await query.edit_message_text("📢 Текст рассылки:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]]))
    if data == "admin_reset_user":
        context.user_data.update({"admin_action":"reset","admin_state":"search_input"})
        return await query.edit_message_text("🔄 Сброс: найдите игрока:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]]))

# ============================================================================
# 💬 ОБРАБОТЧИК ТЕКСТА
# ============================================================================

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Промокод
    if context.user_data.get("promo_state") == "input":
        await process_promocode(update, context, user_id, text.upper())
        return

    # 🎮 Игровые ставки
    state = context.user_data.get("game_state")
    if state and context.user_data.get("game_user_id") == user_id:
        res = validate_bet(user_id, text)
        if not res["success"]:
            return await update.message.reply_text(res["message"])
        bet = res["bet"]
        if state == "crash":
            context.user_data.update({"crash_bet": bet, "crash_user_id": user_id})
            kb = [[InlineKeyboardButton(f"×{m}", callback_data=f"crash_multiplier_{m}") for m in [1.2, 1.5, 2.0, 3.0, 5.0]]]
            kb.append([InlineKeyboardButton("⬅️ Отмена", callback_data="back_to_minigames")])
            return await update.message.reply_text("💥 Выберите множитель:", reply_markup=InlineKeyboardMarkup(kb))
        elif state == "roulette":
            context.user_data.update({"roulette_bet": bet, "roulette_user_id": user_id})
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

    # Админка
    if is_admin(user_id):
        admin_state = context.user_data.get("admin_state")

        # Промокоды
        if admin_state == "promo_create_name":
            context.user_data["promo_name"] = text.upper()
            context.user_data["admin_state"] = "promo_create_rewards"
            return await update.message.reply_text(
                "🎟 Введите награды (через пробел):\n"
                "1 [монеты] 2 [донат] 3 [дни према]\n"
                "Пример: 1 5000 2 100 3 7\n"
                "(0 если не нужно)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
            )

        if admin_state == "promo_create_rewards":
            parts = text.split()
            try:
                coins = int(parts[1]) if len(parts) > 1 and parts[0] == "1" else 0
                donate = int(parts[3]) if len(parts) > 3 and parts[2] == "2" else 0
                premium = int(parts[5]) if len(parts) > 5 and parts[4] == "3" else 0
                context.user_data["promo_rewards"] = {"coins": coins, "donate_coins": donate, "premium_days": premium}
                context.user_data["admin_state"] = "promo_create_limit"
                return await update.message.reply_text(
                    "🎟 Введите лимит активаций (сколько человек могут использовать):",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]])
                )
            except:
                return await update.message.reply_text("❌ Неверный формат. Пример: 1 5000 2 100 3 7")

        if admin_state == "promo_create_limit":
            try:
                limit = int(text)
                from promocodes import create_promocode
                name = context.user_data.get("promo_name")
                rewards = context.user_data.get("promo_rewards", {})
                result = create_promocode(name, rewards["coins"], rewards["donate_coins"], rewards["premium_days"], limit)
                context.user_data.pop("promo_name", None)
                context.user_data.pop("promo_rewards", None)
                context.user_data.pop("admin_state", None)
                return await update.message.reply_text(result["message"], reply_markup=get_admin_main_keyboard())
            except ValueError:
                return await update.message.reply_text("❌ Введите число.")

        if admin_state == "promo_delete":
            from promocodes import delete_promocode
            result = delete_promocode(text.upper())
            context.user_data.pop("admin_state", None)
            return await update.message.reply_text(result["message"], reply_markup=get_admin_main_keyboard())

        # Стандартная админка
        if admin_state == "search_input":
            q = text.lower().lstrip("@")
            found = [(u, d) for u, d in data_manager.user_data.items() if q in d.get("name","").lower() or (d.get("username","").lower().lstrip("@") == q) or (text.isdigit() and int(text)==u)]
            if not found:
                context.user_data.pop("admin_state", None)
                return await update.message.reply_text("❌ Не найдено.", reply_markup=get_admin_main_keyboard())
            if len(found)==1:
                uid, d = found[0]
                context.user_data["admin_selected_uid"] = uid
                context.user_data["admin_state"] = "action_select"
                return await update.message.reply_text(f"👤 {get_user_display_name(uid,d)}\nВыберите действие:", reply_markup=get_admin_main_keyboard())
            kb = [[InlineKeyboardButton(f"👤 {get_user_display_name(u,d)}", callback_data=f"admin_select_{u}")] for u,d in found[:10]]
            kb.append([InlineKeyboardButton("🔍 Заново", callback_data="admin_search_prompt"), InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")])
            context.user_data.update({"admin_state":"select_from_list","admin_found_users":found})
            return await update.message.reply_text(f"🔍 Найдено {len(found)}:", reply_markup=InlineKeyboardMarkup(kb))

        if admin_state == "select_from_list":
            return await update.message.reply_text("👆 Выберите пользователя из списка выше.")

        if admin_state == "input_value":
            act = context.user_data.get("admin_action")
            uid = context.user_data.get("admin_selected_uid")
            if not act or not uid:
                context.user_data.pop("admin_state", None)
                return await update.message.reply_text("❌ Ошибка сессии.", reply_markup=get_admin_main_keyboard())
            try:
                val = int(text)
                if val <= 0 and act not in ("remove_premium","ban","unban","reset"):
                    return await update.message.reply_text("❌ Введите число > 0")
                context.user_data.update({"admin_value":val,"admin_state":"confirm"})
                names = {"add_coins":f"💰 Выдать {format_number(val)}","remove_coins":f"🔻 Забрать {format_number(val)}","add_donate":f"💎 +{val}","remove_donate":f"💸 -{val}","add_premium":f"⭐ {val} дней" if val>0 else "⭐ Навсегда"}
                return await update.message.reply_text(f"⚠️ Подтвердите:\n👤 {get_user_display_name(uid, data_manager.user_data[uid])}\n🔧 {names.get(act,act)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ ОК", callback_data=f"admin_confirm_{act}_{uid}"), InlineKeyboardButton("❌ Отмена", callback_data="admin_main")]]))
            except ValueError:
                context.user_data.pop("admin_state", None)
                return await update.message.reply_text("❌ Введите число.", reply_markup=get_admin_main_keyboard())

        if admin_state == "broadcast_input":
            await update.message.reply_text("📢 Отправка...")
            sent = failed = 0
            for uid in data_manager.user_data:
                try:
                    await context.bot.send_message(uid, text, parse_mode="HTML")
                    sent += 1
                except:
                    failed += 1
            context.user_data.pop("admin_state", None)
            return await update.message.reply_text(f"✅ Готово: {sent} | ❌ Ошибок: {failed}", reply_markup=get_admin_main_keyboard())

async def mm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if data_manager.user_data[user_id].get("banned", False):
        await update.message.reply_text("🚫 Вы забанены.")
        return
    if not await check_subscription(user_id, context):
        text = (
            "🔒 <b>Доступ ограничен</b>\n\n"
            "Для просмотра профиля необходимо подписаться на наш новостной канал.\n\n"
            "👇 Подпишитесь и нажмите <b>«Проверить»</b>"
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_subscription_keyboard())
        return
    apply_league_tax(user_id)
    await update.message.reply_text(get_profile_text(user_id), parse_mode="HTML")

async def admins_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет доступа.")
        return
    await update.message.reply_text(get_admin_panel_text(), reply_markup=get_admin_main_keyboard())
