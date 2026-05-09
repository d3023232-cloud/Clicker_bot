import config
import data_manager
import math
from game_logic import update_league
from utils import format_number, is_premium_active, get_econ

def calc_upgrade_cost(base_cost: int, level: int) -> int:
    """📊 Расчет цены улучшения (влияет: pricing.cost_multiplier)"""
    return int(base_cost * (get_econ("pricing.cost_multiplier") ** level))

def buy_upgrade(user_id, upg_key):
    """📊 Покупка улучшения с динамической ценой"""
    if upg_key not in config.UPGRADES:
        return {"success": False, "message": "❌ Улучшение не найдено"}

    ud = data_manager.user_data[user_id]
    upg = config.UPGRADES[upg_key]
    level = ud.get(f"{upg_key}_level", 0)
    current_cost = calc_upgrade_cost(upg["cost"], level)

    if ud["coins"] < current_cost:
        return {"success": False, "message": f"❌ Недостаточно монет! Нужно: {format_number(current_cost)}"}

    ud["coins"] -= current_cost
    ud[f"{upg_key}_level"] = level + 1

    if get_econ("pricing.diminishing_effect"):
        effect_gain = round(upg["effect"] / (1 + 0.5 * level), 2)
    else:
        effect_gain = upg["effect"]

    if upg["type"] == "click_power":
        ud["click_power"] += effect_gain
        msg = f"✅ Куплено: {upg['name']} (Ур. {level+1})! ⚡ Сила клика: +{effect_gain}"
    elif upg["type"] == "auto_clicker":
        ud["auto_clicker"] += effect_gain
        if "auto_owner" not in ud["achievements"]:
            ud["achievements"].add("auto_owner")
        msg = f"✅ Куплено: {upg['name']} (Ур. {level+1})! 🤖 Авто: +{effect_gain}/мин"

    if "buy_upgrade" not in ud["achievements"]:
        ud["achievements"].add("buy_upgrade")

    update_league(user_id)
    data_manager.save_data()
    return {"success": True, "message": msg}

def get_shop_upgrades_keyboard(user_id):
    from telegram import InlineKeyboardButton
    ud = data_manager.user_data[user_id]
    coins = ud["coins"]
    keyboard = []

    for key, upg in config.UPGRADES.items():
        level = ud.get(f"{key}_level", 0)
        cost = calc_upgrade_cost(upg['cost'], level)
        cost_str = format_number(cost)
        if coins >= cost:
            btn_text = f"Купить: {upg['name']} ({cost_str} 🪙)"
            btn = InlineKeyboardButton(btn_text, callback_data='buy_upg_' + key)
        else:
            btn_text = f"🔒 {upg['name']} ({cost_str} 🪙)"
            btn = InlineKeyboardButton(btn_text, callback_data='noop')
        keyboard.append([btn])

    keyboard.append([InlineKeyboardButton("⬅️ Назад в магазин", callback_data='shop')])
    return keyboard

def get_shop_titles_keyboard(user_id):
    from telegram import InlineKeyboardButton
    ud = data_manager.user_data[user_id]
    coins = ud["coins"]
    keyboard = []

    for key, title in config.TITLES.items():
        cost_str = format_number(title['cost'])
        if title['name'] == ud['title']:
            btn_text = f"✅ {title['name']} (Выбрано)"
            btn = InlineKeyboardButton(btn_text, callback_data='noop')
        elif coins >= title['cost']:
            btn_text = f"Купить: {title['name']} ({cost_str} 🪙)"
            btn = InlineKeyboardButton(btn_text, callback_data='buy_title_' + key)
        else:
            btn_text = f"🔒 {title['name']} ({cost_str} 🪙)"
            btn = InlineKeyboardButton(btn_text, callback_data='noop')
        keyboard.append([btn])

    keyboard.append([InlineKeyboardButton("⬅️ Назад в магазин", callback_data='shop')])
    return keyboard

def buy_title(user_id, title_key):
    if title_key not in config.TITLES:
        return {"success": False, "message": "❌ Звание не найдено"}

    ud = data_manager.user_data[user_id]
    title = config.TITLES[title_key]

    if ud["coins"] < title["cost"]:
        return {"success": False, "message": "❌ Недостаточно монет!"}

    ud["coins"] -= title["cost"]
    old_title = ud["title"]
    ud["title"] = title["name"]
    
    update_league(user_id)
    data_manager.save_data()
    
    return {"success": True, "message": f"✅ Звание изменено: {old_title} → {title['name']}"}

def get_donat_shop_keyboard():
    from telegram import InlineKeyboardButton
    keyboard = []
    for key, item in config.DONAT_SHOP.items():
        keyboard.append([InlineKeyboardButton(f"{item['name']} - {item['stars']} ⭐", callback_data=f'buy_stars_{key}')])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back')])
    return keyboard
