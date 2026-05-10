"""Система промокодов"""
import json
import os
import time

# ── BotHost Shared Storage ──────────────────────────────────────────
SHARED_DIR = os.getenv("SHARED_DIR", "/app/shared")
os.makedirs(SHARED_DIR, exist_ok=True)
PROMO_FILE = os.path.join(SHARED_DIR, "promocodes.json")

def load_promocodes():
    if not os.path.exists(PROMO_FILE):
        return {}
    try:
        with open(PROMO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_promocodes(data):
    with open(PROMO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_promocode(name, coins=0, donate_coins=0, premium_days=0, uses_limit=1):
    promos = load_promocodes()

    if name in promos:
        return {"success": False, "message": f"❌ Промокод '{name}' уже существует!"}

    # Проверка: хотя бы одна награда должна быть > 0
    if coins <= 0 and donate_coins <= 0 and premium_days <= 0:
        return {"success": False, "message": "❌ Промокод должен давать хотя бы одну награду (монеты, донат или премиум)!"}

    if uses_limit <= 0:
        return {"success": False, "message": "❌ Лимит активаций должен быть больше 0!"}

    promos[name] = {
        "coins": coins,
        "donate_coins": donate_coins,
        "premium_days": premium_days,
        "uses_limit": uses_limit,
        "uses_left": uses_limit,
        "used_by": [],
        "created_at": time.time(),
        "active": True
    }

    save_promocodes(promos)
    return {
        "success": True,
        "message": f"✅ Промокод '{name}' создан!\n🪙 {coins} | 💎 {donate_coins} | 👑 {premium_days} дней | Лимит: {uses_limit}"
    }

def delete_promocode(name):
    promos = load_promocodes()

    if name not in promos:
        return {"success": False, "message": f"❌ Промокод '{name}' не найден!"}

    del promos[name]
    save_promocodes(promos)
    return {"success": True, "message": f"🗑 Промокод '{name}' удалён!"}

def check_promocode(name, user_id):
    promos = load_promocodes()

    if name not in promos:
        return {"success": False, "message": "Промокод не найден!"}

    promo = promos[name]

    if not promo.get("active", True):
        return {"success": False, "message": "Промокод неактивен!"}

    if promo["uses_left"] <= 0:
        return {"success": False, "message": "Лимит активаций исчерпан!"}

    if user_id in promo["used_by"]:
        return {"success": False, "message": "Вы уже использовали этот промокод!"}

    return {"success": True, "message": "OK", "promo": promo}

def use_promocode(name, user_id):
    promos = load_promocodes()
    promo = promos[name]

    import data_manager
    ud = data_manager.user_data[user_id]

    rewards_text = []

    if promo["coins"] > 0:
        ud["coins"] += promo["coins"]
        rewards_text.append(f"🪙 +{promo['coins']}")
    if promo["donate_coins"] > 0:
        ud["donate_coins"] += promo["donate_coins"]
        rewards_text.append(f"💎 +{promo['donate_coins']}")
    if promo["premium_days"] > 0:
        ud["premium"] = True
        if promo["premium_days"] == 0:
            ud["premium_until"] = 0
        else:
            current = ud.get("premium_until", 0)
            if current < time.time():
                current = time.time()
            ud["premium_until"] = current + (promo["premium_days"] * 86400)
        rewards_text.append(f"👑 +{promo['premium_days']}д")

    # Обновляем статус промокода
    promo["uses_left"] -= 1
    promo["used_by"].append(user_id)

    if promo["uses_left"] <= 0:
        promo["active"] = False

    save_promocodes(promos)
    data_manager.save_data()

    return {
        "coins": promo["coins"],
        "donate_coins": promo["donate_coins"],
        "premium_days": promo["premium_days"],
        "uses_left": promo["uses_left"],
        "rewards_text": " | ".join(rewards_text) if rewards_text else "Нет наград"
    }

def list_promocodes():
    promos = load_promocodes()

    if not promos:
        return "🎟 <b>Промокоды</b>\n\nПока нет ни одного промокода."

    text = "🎟 <b>Активные промокоды:</b>\n\n"
    active_count = 0

    for name, promo in promos.items():
        if promo.get("active", True) and promo["uses_left"] > 0:
            active_count += 1
            rewards = []
            if promo["coins"] > 0:
                rewards.append(f"🪙 {promo['coins']}")
            if promo["donate_coins"] > 0:
                rewards.append(f"💎 {promo['donate_coins']}")
            if promo["premium_days"] > 0:
                rewards.append(f"👑 {promo['premium_days']}д")

            text += f"<code>{name}</code> — {' | '.join(rewards)}\n"
            text += f"   Осталось: {promo['uses_left']}/{promo['uses_limit']}\n\n"

    if active_count == 0:
        text += "Нет активных промокодов.\n\n"

    text += "<b>История использования:</b>\n"
    for name, promo in promos.items():
        if promo["used_by"]:
            text += f"<code>{name}</code>: {len(promo['used_by'])} акт.\n"

    return text
