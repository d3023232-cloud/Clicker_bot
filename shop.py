"""Shops"""
import config
import data_manager
from game_logic import update_league
from utils import format_number

def buy_upgrade(user_id, upg_key):
    if upg_key not in config.UPGRADES:
        return {"success": False, "message": "Upgrade not found"}
    ud = data_manager.user_data[user_id]
    upg = config.UPGRADES[upg_key]
    if ud["coins"] < upg["cost"]:
        return {"success": False, "message": "Not enough coins!"}
    ud["coins"] -= upg["cost"]
    if upg["type"] == "click_power":
        old_power = ud["click_power"]
        ud["click_power"] += upg["effect"]
        result = {"success": True, "message": f"Bought: {upg['name']}! Click Power: {old_power} -> {ud['click_power']}"}
    elif upg["type"] == "auto_clicker":
        old_auto = ud["auto_clicker"]
        ud["auto_clicker"] += upg["effect"]
        if "auto_owner" not in ud["achievements"]:
            ud["achievements"].add("auto_owner")
        result = {"success": True, "message": f"Bought: {upg['name']}! Auto-Clicker: {old_auto} -> {ud['auto_clicker']}", "new_achievement": "auto_owner"}
    if "buy_upgrade" not in ud["achievements"]:
        ud["achievements"].add("buy_upgrade")
    update_league(user_id)
    data_manager.save_data()
    return result

def buy_title(user_id, title_key):
    if title_key not in config.TITLES:
        return {"success": False, "message": "Title not found"}
    ud = data_manager.user_data[user_id]
    title = config.TITLES[title_key]
    if ud["coins"] < title["cost"]:
        return {"success": False, "message": "Not enough coins!"}
    ud["coins"] -= title["cost"]
    ud["title"] = title["name"]
    update_league(user_id)
    data_manager.save_data()
    return {"success": True, "message": f"Title '{title['name']}' equipped!"}

def get_shop_upgrades_keyboard(user_id):
    from telegram import InlineKeyboardButton
    ud = data_manager.user_data[user_id]
    coins = ud["coins"]
    keyboard = []
    for key, upg in config.UPGRADES.items():
        if coins >= upg["cost"]:
            btn = InlineKeyboardButton(f"Buy: {upg['name']} ({format_number(upg['cost']})", callback_data=f'buy_upg_{key}')
        else:
            btn = InlineKeyboardButton(f"Locked: {upg['name']} ({format_number(upg['cost'])})", callback_data='noop')
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton("Back", callback_data='shop')])
    return keyboard

def get_shop_titles_keyboard(user_id):
    from telegram import InlineKeyboardButton
    ud = data_manager.user_data[user_id]
    coins = ud["coins"]
    current_title = ud["title"]
    keyboard = []
    for key, title in config.TITLES.items():
        if title["name"] == current_title:
            btn = InlineKeyboardButton(f"Equipped: {title['name']}", callback_data='noop')
        elif coins >= title["cost"]:
            btn = InlineKeyboardButton(f"Buy: {title['name']} ({format_number(title['cost'])})", callback_data=f'buy_title_{key}')
        else:
            btn = InlineKeyboardButton(f"Locked: {title['name']} ({format_number(title['cost'])})", callback_data='noop')
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton("Back", callback_data='shop')])
    return keyboard

def get_donat_shop_keyboard():
    from telegram import InlineKeyboardButton
    keyboard = []
    for key, item in config.DONAT_SHOP.items():
        btn = InlineKeyboardButton(f"{item['name']} ({item['stars']} stars)", callback_data=f'buy_stars_{key}')
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton("Back", callback_data='back')])
    return keyboard
