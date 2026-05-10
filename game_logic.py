"""Game logic with VIP effects"""
import time
import random
from utils import get_league, get_econ, is_premium_active
import config
import data_manager

def process_click(user_id):
    ud = data_manager.user_data[user_id]
    now = time.time()

    # Проверяем неактивность
    hours_inactive = (now - ud["last_click"]) / 3600
    inactive_penalty = 1.0
    if hours_inactive > 48:
        inactive_penalty = get_econ("income.inactive_decay_mult", 0.3)

    # Базовые значения
    click_base = get_econ("income.click_base", 1.0)
    auto_cap = get_econ("income.auto_cap_pct", 0.4)

    # VIP-множители
    vip_mult = 2.0 if is_premium_active(ud) else 1.0

    # Расчёт дохода
    coins_earned = click_base * ud["click_power"] * vip_mult
    auto_income = min(ud["auto_clicker"] * click_base, coins_earned * auto_cap) * inactive_penalty * vip_mult

    total = coins_earned + auto_income
    ud["coins"] += total
    ud["clicks"] += 1
    ud["last_click"] = now

    # Достижения
    new_achievements = []
    for key, ach in config.ACHIEVEMENTS.items():
        if key not in ud["achievements"] and ud["clicks"] >= ach["clicks"]:
            ud["achievements"].add(key)
            new_achievements.append(key)

    data_manager.save_data()

    return {
        "coins_earned": coins_earned,
        "auto_income": auto_income,
        "total_coins": ud["coins"],
        "click_power": ud["click_power"],
        "new_achievements": new_achievements
    }

def get_profile_text(user_id):
    ud = data_manager.user_data[user_id]
    vip = " 👑" if is_premium_active(ud) else ""
    name = ud.get("name", f"ID{user_id}")

    text = (
        f"👤 <b>Профиль{name}</b>\n"
        f"├ ID: <code>{user_id}</code>\n"
        f"├ Ник: {name}\n"
        f"├ 🪙 Баланс: {int(ud['coins']):,}\n"
        f"├ ⚡ Сила клика: {ud['click_power']}\n"
        f"├ 🤖 Авто-доход: {ud['auto_clicker']}/сек\n"
        f"├ 🏅 Звание: {ud['title']}\n"
        f"├ 🏆 Лига: {ud['league']}\n"
        f"├ 🖱 Кликов: {ud['clicks']:,}\n"
        f"├ 💎 Донат: {ud['donate_coins']}\n"
        f"└ {('👑 VIP активен!' if vip else '📝 Обычный пользователь')}\n"
    )
    return text

def get_top_text():
    sorted_users = sorted(data_manager.user_data.items(), key=lambda x: x[1]["coins"], reverse=True)
    text = "🏆 <b>Топ игроков</b>\n\n"
    for i, (uid, ud) in enumerate(sorted_users[:10], 1):
        vip = " 👑" if is_premium_active(ud) else ""
        name = ud.get("name", f"ID{uid}")
        text += f"{i}. {name}{vip} — {int(ud['coins']):,}\n"
    return text

def process_daily_bonus(user_id):
    ud = data_manager.user_data[user_id]
    now = time.time()
    last = ud.get("last_daily", 0)

    if now - last < 86400:
        hours_left = int((86400 - (now - last)) / 3600)
        return {"success": False, "hours_left": hours_left}

    # Рандомный бонус 10-10000 (по ТЗ)
    base_bonus = random.randint(10, 10000)

    # VIP x3 бонус
    vip_mult = 3.0 if is_premium_active(ud) else 1.0
    bonus = int(base_bonus * vip_mult)

    ud["coins"] += bonus
    ud["last_daily"] = now
    data_manager.save_data()

    return {"success": True, "bonus": bonus, "base": base_bonus}

def apply_league_tax(user_id):
    ud = data_manager.user_data[user_id]
    rates = get_econ("tax_rates", {})
    tax = rates.get(ud["league"], 0.0)
    if tax > 0:
        tax_amount = int(ud["coins"] * tax)
        ud["coins"] = max(0, ud["coins"] - tax_amount)
        return tax_amount
    return 0

def buy_upgrade(user_id, upgrade_id):
    from shop import calc_upgrade_cost, UPGRADES
    ud = data_manager.user_data[user_id]
    current_level = ud.get(f"upgrade_{upgrade_id}", 0)
    cost = calc_upgrade_cost(upgrade_id, current_level)

    if ud["coins"] < cost:
        return {"success": False, "message": f"❌ Недостаточно монет! Нужно: {cost:,}"}

    ud["coins"] -= cost
    new_level = current_level + 1
    ud[f"upgrade_{upgrade_id}"] = new_level
    ud["click_power"] = UPGRADES[upgrade_id]["effect"](ud["click_power"], new_level)

    new_achievement = False
    if upgrade_id == "auto_clicker" and new_level == 1:
        ud["achievements"].add("buy_upgrade")
        new_achievement = True

    data_manager.save_data()

    return {
        "success": True,
        "message": f"✅ Куплено! Уровень {new_level}. Сила клика: {ud['click_power']}",
        "new_achievement": new_achievement
    }

def buy_title(user_id, title_id):
    from shop import TITLES
    ud = data_manager.user_data[user_id]
    title = TITLES.get(title_id)

    if not title:
        return {"success": False, "message": "❌ Звание не найдено!"}
    if ud["coins"] < title["cost"]:
        return {"success": False, "message": f"❌ Нужно {title['cost']:,} монет!"}
    if ud["clicks"] < title["min_clicks"]:
        return {"success": False, "message": f"❌ Нужно {title['min_clicks']:,} кликов!"}

    ud["coins"] -= title["cost"]
    ud["title"] = title["name"]
    data_manager.save_data()

    return {"success": True, "message": f"🏅 Звание получено: {title['name']}!"}


def update_league(user_id):
    """Обновляет лигу игрока на основе монет"""
    from utils import get_league
    ud = data_manager.user_data[user_id]
    new_league = get_league(ud["coins"])
    if new_league != ud["league"]:
        ud["league"] = new_league
        data_manager.save_data()
        return True
    return False
