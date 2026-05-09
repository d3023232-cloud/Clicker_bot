"""Основные обработчики бота"""
import time
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

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Топ", callback_data="top"), InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton("🎮 Мини-игры", callback_data="minigames"), InlineKeyboardButton("🎁 Бонус", callback_data="daily")],
        [InlineKeyboardButton("💎 Donat", callback_data="donat_shop"), InlineKeyboardButton("🤝 Рефералка", callback_data="referral")],
        [InlineKeyboardButton("🏅 Достижения", callback_data="achievements"), InlineKeyboardButton("👤 Профиль", callback_data="my_profile")],
        [InlineKeyboardButton("🖱 Клик!", callback_data="click")]
    ])

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    data_manager.update_user_name(user_id, get_user_name(user))

    if data_manager.user_data[user_id].get("banned", False):
        await update.message.reply_text("🚫 Вы забанены.")
        return

    if not await check_subscription(user_id, context):
        kb = [[InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{config.CHANNEL_USERNAME}")]]
        await update.message.reply_text("❗ Для игры подпишитесь на канал.", reply_markup=InlineKeyboardMarkup(kb))
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
        "╔═══════════════════╗\n"
        " 🎮 CLICKER BOT 🎮\n"
        "╚═══════════════════╝\n\n"
        f"👋 Привет, {name}!\n\n"
        "✨ Твой прогресс начинается здесь:\n"
        " 🖱 Кликай → 🔧 Улучшай → 🏆 Будь первым\n\n"
        "🎁 Ежедневный бонус | 🎰 Мини-игры | 💎 Донат\n\n"
        "➡️ Жми «🖱 Клик!» и начни путь к славе! 👇"
    )
    await update.message.reply_text(text, reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data_manager.update_user_name(user_id, get_user_name(query.from_user))

    if data_manager.user_data[user_id].get("banned", False):
        await query.edit_message_text("🚫 Вы забанены.")
        return

    if not await check_subscription(user_id, context):
        await query.edit_message_text(
            "❗ Подпишитесь на канал.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{config.CHANNEL_USERNAME}")]])
        )
        return

    if query.data.startswith("admin_"):
        await _admin_callback(query, context, user_id)
        return

    if query.data == "click":
        res = process_click(user_id)
        ach = ""
        if res.get("new_achievements"):
            names = [config.ACHIEVEMENTS[k]["name"] for k in res["new_achievements"]]
            ach = f"\n\n🎉 Достижение: {', '.join(names)}!"
        await query.edit_message_text(
            f"🖱 Клик!\n💰 +{format_number(int(res['coins_earned']))} (клик)\n🤖 +{format_number(int(res['auto_income']))} (авто)\n🪙 Всего: {format_number(int(res['total_coins']))}\n⚡ Сила: {res['click_power']}{ach}",
            reply_markup=get_main_menu()
        )
    elif query.data == "top":
        await query.edit_message_text(get_top_text(), reply_markup=get_main_menu())
    elif query.data == "shop":
        await query.edit_message_text("🛒 Магазин:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔧 Улучшения", callback_data="shop_upgrades")],
            [InlineKeyboardButton("🏅 Звания", callback_data="shop_titles")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]))
    elif query.data == "shop_upgrades":
        await query.edit_message_text("🔧 Улучшения:", reply_markup=InlineKeyboardMarkup(get_shop_upgrades_keyboard(user_id)))
    elif query.data == "shop_titles":
        await query.edit_message_text("🏅 Звания:", reply_markup=InlineKeyboardMarkup(get_shop_titles_keyboard(user_id)))
    elif query.data == "daily":
        res = process_daily_bonus(user_id)
        msg = f"🎁 +{format_number(res['bonus'])} монет! Возвращайтесь завтра!" if res["success"] else f"🎁 Через {res['hours_left']} ч."
        await query.edit_message_text(msg, reply_markup=get_main_menu())
    elif query.data == "achievements":
        ud = data_manager.user_data[user_id]
        msg = "🏅 Достижения:\n" + "\n".join(f"{'✅' if k in ud['achievements'] else '❌'} {v['name']} — {v['desc']}" for k, v in config.ACHIEVEMENTS.items())
        msg += f"\n\n👑 Звание: {ud['title']}"
        await query.edit_message_text(msg, reply_markup=get_main_menu())
    elif query.data == "my_profile":
        await query.edit_message_text(get_profile_text(user_id), parse_mode="HTML", reply_markup=get_main_menu())
    elif query.data == "referral":
        link = f"https://t.me/{config.YOUR_BOT_USERNAME}?start=ref{user_id}"
        count = len([u for u in data_manager.user_data.values() if u.get("referrer_id") == user_id])
        await query.edit_message_text(f"🤝 Рефералка\n🔗 {link}\n👥 Друзей: {count}\n💎 За каждого: 2 ⭐\n💰 Получено: {data_manager.user_data[user_id]['donate_coins']} ⭐", reply_markup=get_main_menu())
    elif query.data == "donat_shop":
        await query.edit_message_text("💎 Donat-магазин (⭐):", reply_markup=InlineKeyboardMarkup(get_donat_shop_keyboard()))
    elif query.data.startswith("buy_stars_"):
        item = config.DONAT_SHOP.get(query.data[10:])
        if not item:
            return await query.edit_message_text("❌ Товар не найден.", reply_markup=get_main_menu())
        try:
            await context.bot.send_invoice(chat_id=user_id, title=item["name"], description=item["desc"],
                payload=f"donat_{query.data[10:]}", provider_token="", currency="XTR",
                prices=[LabeledPrice(label="Цена", amount=item["stars"])])
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка оплаты: {e}", reply_markup=get_main_menu())
    elif query.data == "minigames":
        await query.edit_message_text("🎮 Мини-игры:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💥 Краш", callback_data="game_crash_start")],
            [InlineKeyboardButton("🎰 Рулетка", callback_data="game_roulette_start")],
            [InlineKeyboardButton("⚔️ Дуэль", callback_data="game_duel_start")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]))
    elif query.data == "game_crash_start":
        res = start_crash_game(user_id)
        if not res["success"]:
            return await query.answer(res["message"], show_alert=True)
        context.user_data.update({"game_state": "crash", "game_user_id": user_id})
        await query.edit_message_text("💥 Краш\n📉 Ставка 20–1 000 000\n\n_Введите число в чат_", parse_mode="HTML")
    elif query.data.startswith("crash_multiplier_"):
        mult = float(query.data.split("_")[2])
        bet = context.user_data.get("crash_bet")
        if not bet or context.user_data.get("game_user_id") != user_id:
            return await query.edit_message_text("❌ Сессия истекла.", reply_markup=get_main_menu())
        res = process_crash_game(user_id, bet, mult)
        await query.edit_message_text(res["message"], parse_mode="HTML", reply_markup=get_main_menu())
        for key in list(context.user_data.keys()):
            if key.startswith(("game_", "crash_", "roulette_", "duel_")):
                context.user_data.pop(key, None)
    elif query.data == "game_roulette_start":
        res = start_roulette_game(user_id)
        if not res["success"]:
            return await query.answer(res["message"], show_alert=True)
        context.user_data.update({"game_state": "roulette", "game_user_id": user_id})
        await query.edit_message_text("🎰 Рулетка\n🔴/⚫ ×1.9 | 🟢 ×9.0\n\n_Введите ставку_", parse_mode="HTML")
    elif query.data.startswith("roulette_color_"):
        color = query.data.split("_")[2]
        bet = context.user_data.get("roulette_bet")
        if not bet or context.user_data.get("game_user_id") != user_id:
            return await query.edit_message_text("❌ Сессия истекла.", reply_markup=get_main_menu())
        res = process_roulette_game(user_id, bet, color)
        await query.edit_message_text(f"🎰 {res['message']}\n🪙 {format_number(int(res['balance']))}", parse_mode="HTML", reply_markup=get_main_menu())
        for key in list(context.user_data.keys()):
            if key.startswith(("game_", "crash_", "roulette_", "duel_")):
                context.user_data.pop(key, None)
    elif query.data == "game_duel_start":
        res = start_duel_game(user_id)
        if not res["success"]:
            return await query.answer(res["message"], show_alert=True)
        context.user_data.update({"game_state": "duel", "game_user_id": user_id})
        await query.edit_message_text("⚔️ Дуэль (48% победа)\n\n_Введите ставку_", parse_mode="HTML")
    elif query.data.startswith("buy_upg_"):
        res = buy_upgrade(user_id, query.data[8:])
        if res.get("new_achievement"):
            await query.answer("🎉 Робо-помощник!", show_alert=True)
        await query.edit_message_text(res["message"], reply_markup=get_main_menu())
    elif query.data.startswith("buy_title_"):
        res = buy_title(user_id, query.data[11:])
        await query.edit_message_text(res["message"], reply_markup=get_main_menu())
    elif query.data in ("back", "noop"):
        await query.edit_message_text("🎮 Главное меню:", reply_markup=get_main_menu())

async def mm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if data_manager.user_data[user_id].get("banned", False):
        await update.message.reply_text("🚫 Вы забанены.")
        return
    if not await check_subscription(user_id, context):
        await update.message.reply_text("❗ Подпишитесь на канал.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{config.CHANNEL_USERNAME}")]]))
        return
    apply_league_tax(user_id)
    await update.message.reply_text(get_profile_text(user_id), parse_mode="HTML")

async def admins_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет доступа.")
        return
    await update.message.reply_text(get_admin_panel_text(), reply_markup=get_admin_main_keyboard())

# ============================================================================
# 🛠 АДМИН: ЛОГИКА
# ============================================================================
async def _admin_callback(query, context, user_id):
    data = query.data
    if data == "admin_main":
        for key in list(context.user_data.keys()):
            if key.startswith(("admin_", "game_", "crash_", "roulette_", "duel_")):
                context.user_data.pop(key, None)
        return await query.edit_message_text("🛠 Админ-панель", reply_markup=get_admin_main_keyboard())
    if data in ("admin_stats", "admin_econ"):
        return await query.edit_message_text(get_econ_stats() if data == "admin_econ" else get_stats(), reply_markup=get_admin_main_keyboard())
    if data == "admin_search_prompt":
        context.user_data.update({"admin_state": "search_input", "admin_action": None})
        return await query.edit_message_text("🔍 Введите @, имя или ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]]))

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
            if key.startswith(("admin_", "game_", "crash_", "roulette_", "duel_")):
                context.user_data.pop(key, None)
        return await query.edit_message_text(res["message"], reply_markup=get_admin_main_keyboard())

    if data == "admin_broadcast":
        context.user_data["admin_state"] = "broadcast_input"
        return await query.edit_message_text("📢 Текст рассылки:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="admin_main")]]))
    if data == "admin_reset_user":
        context.user_data.update({"admin_action":"reset","admin_state":"search_input"})
        return await query.edit_message_text("🔄 Сброс: найдите игрока:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_main")]]))

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        if state == "search_input":
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

        if state == "select_from_list":
            return await update.message.reply_text("👆 Выберите пользователя из списка выше.")

        if state == "input_value":
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

        if state == "broadcast_input":
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
