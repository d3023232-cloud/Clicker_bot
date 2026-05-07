"""Game logic"""
import time
import config
import data_manager
from utils import get_league, is_premium_active, format_number

def check_achievements(user_id):
    ud = data_manager.user_data[user_id]
    unlocked = []
    if ud["clicks"] >= 1 and "first_click" not in ud["achievements"]:
        ud["achievements"].add("first_click")
        unlocked.append("first_click")
    if ud["clicks"] >= 100 and "click_100" not in ud["achievements"]:
        ud["achievements"].add("click_100")
        unlocked.append("click_100")
    if ud["coins"] >= 100 and "rich_100" not in ud["achievements"]:
        ud["achievements"].add("rich_100")
        unlocked.append("rich_100")
    if unlocked:
        data_manager.save_data()
    return unlocked

def update_league(user_id):
    coins = data_manager.user_data[user_id]["coins"]
    data_manager.user_data[user_id]["league"] = get_league(coins)

def process_click(user_id):
    ud = data_manager.user_data[user_id]
    now = time.time()
    auto_income = 0
    last_click = ud.get("last_click", now)
    seconds_passed = now - last_click
    auto_clicker_rate = ud["auto_clicker"]
    if is_premium_active(ud):
        auto_clicker_rate *= 2
    if seconds_passed >= 1 and auto_clicker_rate > 0:
        minutes_passed = seconds_passed / 60
        auto_income = auto_clicker_rate * minutes_passed
        ud["coins"] += auto_income
    coins_earned = ud["click_power"]
    if is_premium_active(ud):
        coins_earned *= 1.5
    ud["clicks"] += 1
    ud["coins"] += coins_earned
    ud["last_click"] = now
    update_league(user_id)
    data_manager.save_data()
    new_achs = check_achievements(user_id)
    return {
        "coins_earned": coins_earned, "auto_income": auto_income,
        "total_coins": ud["coins"], "click_power": ud["click_power"],
        "new_achievements": new_achs
    }

def get_profile_text(user_id: int) -> str:
    ud = data_manager.user_data[user_id]
    premium_badge = "Premium " if is_premium_active(ud) else ""
    if ud["achievements"]:
        ach_list = [config.ACHIEVEMENTS.get(k, {}).get("name", k) for k in ud["achievements"]]
        achievements_str = ", ".join(ach_list)
    else:
        achievements_str = "-"
    top_list = sorted(
        [(uid, data["coins"]) for uid, data in data_manager.user_data.items() if data["coins"] > 0],
        key=lambda x: x[1], reverse=True
    )
    try:
        rank = next(i for i, (uid, _) in enumerate(top_list, 1) if uid == user_id)
        rank_str = f"#{rank}"
    except StopIteration:
        rank_str = "-"
    current_cost = next((t["cost"] for t in config.TITLES.values() if t["name"] == ud["title"]), 0)
    next_titles = [t for t in config.TITLES.values() if t["cost"] > current_cost]
    if next_titles:
        next_title = min(next_titles, key=lambda x: x["cost"])
        needed = next_title["cost"] - ud["coins"]
        if needed <= 0:
            progress_str = f"Available: {next_title['name']}!"
        else:
            progress_str = f"{format_number(int(needed))} coins to {next_title['name']}"
    else:
        progress_str = "Max title reached!"
    lines = [
        f"Profile {premium_badge}",
        "",
        f"Coins: {format_number(int(ud['coins']))}",
        f"Donate: {ud['donate_coins']}",
        f"Clicks: {format_number(ud['clicks'])}",
        f"Click Power: {ud['click_power']}",
        f"Auto-Clicker: {ud['auto_clicker']} coins/min",
        f"League: {ud['league']}",
        f"Title: {ud['title']}",
        f"Rank: {rank_str}",
        f"Achievements: {achievements_str}",
        "",
        progress_str
    ]
    return chr(10).join(lines)

def get_top_text() -> str:
    top_list = sorted(
        [(uid, data["coins"]) for uid, data in data_manager.user_data.items() if data["coins"] > 0],
        key=lambda x: x[1], reverse=True
    )[:5]
    lines = ["Top-5 Richest:"]
    for i, (uid, coins) in enumerate(top_list, 1):
        name = data_manager.get_user_name_by_id(uid)
        league = data_manager.user_data[uid]["league"]
        premium_badge = "Premium " if is_premium_active(data_manager.user_data[uid]) else ""
        lines.append(f"{i}. {name} {premium_badge}[{league}] - {format_number(int(coins))} coins")
    return chr(10).join(lines)

def process_daily_bonus(user_id):
    now = time.time()
    ud = data_manager.user_data[user_id]
    if now - ud["last_daily"] < 86400:
        hours = int((86400 - (now - ud["last_daily"])) / 3600) + 1
        return {"success": False, "hours_left": hours}
    bonus = config.DAILY_BONUS_PREMIUM if is_premium_active(ud) else config.DAILY_BONUS_BASE
    ud["coins"] += bonus
    ud["last_daily"] = now
    update_league(user_id)
    data_manager.save_data()
    return {"success": True, "bonus": bonus}
