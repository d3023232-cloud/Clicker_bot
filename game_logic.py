"""Game logic"""
import time
import config
import data_manager
from utils import get_league, is_premium_active, format_number, get_econ

def apply_league_tax(user_id):
    """📊 Ежедневный налог по лиге (влияет: tax_rates, заставляет тратить монеты)"""
    ud = data_manager.user_data[user_id]
    now = int(time.time())
    if now - ud.get("last_tax", 0) < 86400:
        return 0
    
    rates = get_econ("tax_rates")
    rate = rates.get(ud["league"], 0.0)
    tax = int(ud["coins"] * rate)
    
    if tax > 0:
        ud["coins"] = max(0, ud["coins"] - tax)
        ud["last_tax"] = now
        data_manager.save_data()
    return tax

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
    """📊 Основной процесс клика (влияет: income.click_base, auto_cap_pct, inactive_decay_mult)"""
    ud = data_manager.user_data[user_id]
    now = time.time()

    # 1. Доход за клик
    base_click = get_econ("income.click_base")
    click_power = ud["click_power"]
    premium_mult = 1.5 if is_premium_active(ud) else 1.0
    coins_earned = round((base_click + click_power) * premium_mult, 2)

    # 2. Автодоход с ограничениями
    auto_income = 0.0
    seconds_passed = now - ud.get("last_click", now)
    if seconds_passed >= 1 and ud["auto_clicker"] > 0:
        max_auto = ud["click_power"] * get_econ("income.auto_cap_pct")
        auto_rate = min(ud["auto_clicker"], max_auto)
        
        if seconds_passed > 172800:
            auto_rate *= get_econ("income.inactive_decay_mult")
            
        auto_income = round(auto_rate * (seconds_passed / 60), 2)

    ud["coins"] += coins_earned + auto_income
    ud["clicks"] += 1
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
    premium_badge = "⭐ Premium " if is_premium_active(ud) else ""
    
    if ud["achievements"]:
        ach_list = [config.ACHIEVEMENTS.get(k, {}).get("name", k) for k in ud["achievements"]]
        achievements_str = ", ".join(ach_list)
    else:
        achievements_str = "Нет достижений"

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
            progress_str = f"✅ Доступно: {next_title['name']}!"
        else:
            progress_str = f"📈 Нужно еще {format_number(int(needed))} монет до звания {next_title['name']}"
    else:
        progress_str = "🏆 Максимальное звание достигнуто!"

    lines = [
        f"👤 Профиль {premium_badge}",
        "",
        f"💰 Монеты: {format_number(int(ud['coins']))}",
        f"💎 Донат-коины: {ud['donate_coins']}",
        f"🖱 Клики: {format_number(ud['clicks'])}",
        f"⚡ Сила клика: {ud['click_power']}",
        f"🤖 Авто-кликер: {ud['auto_clicker']} монет/мин",
        f"🏅 Лига: {ud['league']}",
        f"📛 Звание: {ud['title']}",
        f"📊 Место в топе: {rank_str}",
        f"🏆 Достижения: {achievements_str}",
        "",
        progress_str
    ]
    return "\n".join(lines)

def get_top_text() -> str:
    top_list = sorted(
        [(uid, data["coins"]) for uid, data in data_manager.user_data.items() if data["coins"] > 0],
        key=lambda x: x[1], reverse=True
    )[:5]
    
    lines = ["🏆 Топ-5 богачей:"]
    for i, (uid, coins) in enumerate(top_list, 1):
        name = data_manager.get_user_name_by_id(uid)
        league = data_manager.user_data[uid]["league"]
        premium_badge = "⭐ " if is_premium_active(data_manager.user_data[uid]) else ""
        lines.append(f"{i}. {name} {premium_badge}[{league}] - {format_number(int(coins))} 💰")
        
    if not top_list:
        lines.append("Пока никого нет. Будь первым!")
        
    return "\n".join(lines)

def process_daily_bonus(user_id):
    now = time.time()
    ud = data_manager.user_data[user_id]
    if now - ud["last_daily"] < 86400:
        hours = int((86400 - (now - ud["last_daily"])) / 3600) + 1
        return {"success": False, "hours_left": hours}
    
    bonus = int(get_econ("income.daily_base"))
    if is_premium_active(ud):
        bonus = int(bonus * 1.5)
        
    ud["coins"] += bonus
    ud["last_daily"] = now
    update_league(user_id)
    data_manager.save_data()
    return {"success": True, "bonus": bonus}
