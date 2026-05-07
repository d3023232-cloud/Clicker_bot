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
        "Admin Panel",
        "",
        "/debug - Debug info",
        "/add_coins [id] [amount] - Add coins",
        "/give_donate [id] [amount] - Give donate coins",
        "/give_premium [id] [days] - Give premium",
        "/get_user [id] - User info",
        "/reset_user [id] - Reset user",
        "/stats - Bot stats",
        "/ban_user [id] - Ban user",
        "/broadcast [msg] - Broadcast",
        "/admins - This menu"
    ]
    return chr(10).join(lines)

def get_admin_keyboard():
    from telegram import InlineKeyboardButton
    return [
        [InlineKeyboardButton("Stats (/stats)", callback_data="admin_cmd_stats")],
        [InlineKeyboardButton("Add Coins (/add_coins)", callback_data="admin_cmd_add_coins")],
        [InlineKeyboardButton("Give Donate (/give_donate)", callback_data="admin_cmd_give_donate")],
        [InlineKeyboardButton("Give Premium (/give_premium)", callback_data="admin_cmd_give_premium")],
        [InlineKeyboardButton("User Info (/get_user)", callback_data="admin_cmd_get_user")],
        [InlineKeyboardButton("Ban (/ban_user)", callback_data="admin_cmd_ban_user")],
        [InlineKeyboardButton("Broadcast (/broadcast)", callback_data="admin_cmd_broadcast")],
        [InlineKeyboardButton("Reset (/reset_user)", callback_data="admin_cmd_reset_user")],
        [InlineKeyboardButton("Debug (/debug)", callback_data="admin_cmd_debug")]
    ]

def get_admin_command_description(cmd):
    descriptions = {
        "stats": "/stats - Show bot statistics",
        "add_coins": "/add_coins <id> <amount> - Add coins to user",
        "give_donate": "/give_donate <id> <amount> - Give donate coins",
        "give_premium": "/give_premium <id> <days> - Give premium (0=forever)",
        "get_user": "/get_user <id> - Show user info",
        "ban_user": "/ban_user <id> - Ban user",
        "broadcast": "/broadcast <msg> - Send to all users",
        "reset_user": "/reset_user <id> - Reset all user data",
        "debug": "/debug - Show debug info"
    }
    return descriptions.get(cmd, "Command not found")

def add_coins(target_id, amount):
    try:
        target_id = int(target_id)
        amount = int(amount)
        if amount <= 0:
            return {"success": False, "message": "Amount must be positive"}
        data_manager.user_data[target_id]["coins"] += amount
        update_league(target_id)
        data_manager.save_data()
        return {"success": True, "message": f"Added {format_number(amount)} coins to user {target_id}"}
    except ValueError:
        return {"success": False, "message": "Error: ID and amount must be numbers"}

def give_donate(target_id, amount):
    try:
        target_id = int(target_id)
        amount = int(amount)
        if amount <= 0:
            return {"success": False, "message": "Amount must be positive"}
        data_manager.user_data[target_id]["donate_coins"] += amount
        data_manager.save_data()
        return {"success": True, "message": f"Gave {amount} donate coins to user {target_id}"}
    except ValueError:
        return {"success": False, "message": "Error: ID and amount must be numbers"}

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
        return {"success": True, "message": f"Premium given to {target_id} for {days} days"}
    except ValueError:
        return {"success": False, "message": "Error: ID and days must be numbers"}

def get_user_info(uid):
    try:
        uid = int(uid)
        ud = data_manager.user_data[uid]
        name = data_manager.get_user_name_by_id(uid)
        lines = [
            f"User: {name} (ID: {uid})",
            f"Coins: {format_number(int(ud['coins']))}",
            f"Donate: {ud['donate_coins']}",
            f"Clicks: {format_number(ud['clicks'])}",
            f"Click Power: {ud['click_power']}",
            f"Auto-Clicker: {ud['auto_clicker']} coins/min",
            f"League: {ud['league']}",
            f"Title: {ud['title']}",
            f"Premium: {'Yes' if is_premium_active(ud) else 'No'}",
            f"Achievements: {', '.join(config.ACHIEVEMENTS.get(k, {}).get('name', k) for k in ud['achievements']) or '-'}"
        ]
        return {"success": True, "message": chr(10).join(lines)}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}

def reset_user(uid):
    try:
        uid = int(uid)
        data_manager.reset_user_data(uid)
        return {"success": True, "message": f"User {uid} data reset"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}

def get_stats():
    total_players = len([u for u in data_manager.user_data if data_manager.user_data[u]["coins"] > 0 or data_manager.user_data[u]["clicks"] > 0])
    total_coins = sum(u["coins"] for u in data_manager.user_data.values())
    total_donate = sum(u["donate_coins"] for u in data_manager.user_data.values())
    top_list = [(uid, data["coins"]) for uid, data in data_manager.user_data.items() if data["coins"] > 0]
    if top_list:
        top_player = max(top_list, key=lambda x: x[1])
        top_name = data_manager.get_user_name_by_id(top_player[0])
        top_league = data_manager.user_data[top_player[0]]["league"]
        top_str = f"{top_name} [{top_league}] - {format_number(int(top_player[1]))} coins"
    else:
        top_str = "-"
    lines = [
        "Bot Statistics:",
        f"Active players: {total_players}",
        f"Total coins: {format_number(int(total_coins))}",
        f"Total donate: {int(total_donate)}",
        f"Top player: {top_str}"
    ]
    return {"success": True, "message": chr(10).join(lines)}

def give_daily_reset(uid):
    try:
        uid = int(uid)
        data_manager.user_data[uid]["last_daily"] = 0
        data_manager.save_data()
        return {"success": True, "message": f"Daily bonus reset for {uid}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}

def ban_user(uid):
    try:
        uid = int(uid)
        data_manager.user_data[uid]["auto_clicker"] = 0
        data_manager.user_data[uid]["last_daily"] = time.time() + 10 * 365 * 86400
        data_manager.save_data()
        return {"success": True, "message": f"User {uid} banned"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}

def test_achievements(uid):
    try:
        uid = int(uid)
        data_manager.user_data[uid]["achievements"] = set(config.ACHIEVEMENTS.keys())
        data_manager.save_data()
        return {"success": True, "message": f"All achievements given to {uid}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}

def get_debug_info(user_id):
    ud = data_manager.user_data[user_id]
    lines = [
        "Debug Info:",
        f"Coins: {format_number(int(ud['coins']))}",
        f"Donate: {ud['donate_coins']}",
        f"Clicks: {format_number(ud['clicks'])}",
        f"Click Power: {ud['click_power']}",
        f"Auto-Clicker: {ud['auto_clicker']} coins/min",
        f"League: {ud['league']}",
        f"Title: {ud['title']}",
        f"Premium: {'Yes' if is_premium_active(ud) else 'No'}"
    ]
    return chr(10).join(lines)
