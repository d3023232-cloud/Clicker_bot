import random
import config
import data_manager
from game_logic import update_league
from utils import format_number, generate_crash_multiplier, get_econ

def validate_bet(user_id, bet_text):
    """📊 Валидация ставки (влияет: games.min_bet, games.max_bet_pct)"""
    try:
        bet = int(bet_text)
        min_bet = int(get_econ("games.min_bet"))
        max_pct = get_econ("games.max_bet_pct")
        ud = data_manager.user_data[user_id]
        max_allowed = int(ud["coins"] * max_pct)

        if bet < min_bet:
            return {"success": False, "message": f"❌ Минимальная ставка: {min_bet} монет"}
        if bet > max_allowed:
            return {"success": False, "message": f"⚠️ Макс. ставка: {format_number(max_allowed)} монет ({int(max_pct*100)}% от баланса)"}
        if bet > config.MAX_BET:
            return {"success": False, "message": f"❌ Максимальная ставка: {format_number(config.MAX_BET)}"}
        if ud["coins"] < bet:
            return {"success": False, "message": "❌ Недостаточно монет!"}
        return {"success": True, "bet": bet}
    except ValueError:
        return {"success": False, "message": "❌ Введите число (например: 100)"}

def start_crash_game(user_id):
    if data_manager.user_data[user_id]["coins"] < int(get_econ("games.min_bet")):
        return {"success": False, "message": "❌ Нужно минимум 20 монет!"}
    return {"success": True}

def process_crash_game(user_id, bet, multiplier):
    ud = data_manager.user_data[user_id]
    if ud["coins"] < bet:
        return {"success": False, "message": "❌ Недостаточно монет!"}
        
    bot_multiplier = generate_crash_multiplier()
    
    if bot_multiplier >= multiplier:
        win = int(bet * multiplier)
        ud["coins"] += win
        update_league(user_id)
        data_manager.save_data()
        msg = f"✅ УСПЕХ! Ваш коэффициент: {multiplier}x | Краш: {bot_multiplier}x | Выигрыш: +{format_number(win)} монет! 💰"
        return {"success": True, "win": True, "message": msg, "bot_multiplier": bot_multiplier}
    else:
        ud["coins"] -= bet
        update_league(user_id)
        data_manager.save_data()
        msg = f"💥 КРАШ! Ваш коэффициент: {multiplier}x | Краш: {bot_multiplier}x | Потеряно: {format_number(bet)} монет 😢"
        return {"success": True, "win": False, "message": msg, "bot_multiplier": bot_multiplier}

def start_roulette_game(user_id):
    if data_manager.user_data[user_id]["coins"] < int(get_econ("games.min_bet")):
        return {"success": False, "message": "❌ Нужно минимум 20 монет!"}
    return {"success": True}

def process_roulette_game(user_id, bet, color):
    ud = data_manager.user_data[user_id]
    if ud["coins"] < bet:
        return {"success": False, "message": "❌ Недостаточно монет!"}
        
    rand = random.random()
    if rand < 0.45:
        result = "red"
    elif rand < 0.90:
        result = "black"
    else:
        result = "green"
        
    win = 0
    if color == result:
        if color == "green":
            win = int(bet * 9.0)
        else:
            win = int(bet * 1.9)
        ud["coins"] += win
        message = f"🎉 Выпало {result}! Выигрыш: +{format_number(win)} монет! 💰"
    else:
        ud["coins"] -= bet
        message = f"😔 Выпало {result}. Потеряно: {format_number(bet)} монет"
        
    update_league(user_id)
    data_manager.save_data()
    return {"success": True, "win": color == result, "message": message, "result": result, "balance": ud["coins"]}

def start_duel_game(user_id):
    if data_manager.user_data[user_id]["coins"] < 100:
        return {"success": False, "message": "❌ Нужно минимум 100 монет!"}
    return {"success": True}

def process_duel_game(user_id, bet):
    ud = data_manager.user_data[user_id]
    if ud["coins"] < bet:
        return {"success": False, "message": "❌ Недостаточно монет!"}
        
    if random.random() < 0.48:
        win = int(bet * 0.96)
        ud["coins"] += win
        message = f"⚔️ Победа! Получено: +{format_number(win)} монет (с учетом комиссии)"
    else:
        ud["coins"] -= bet
        message = f"⚔️ Поражение. Потеряно: {format_number(bet)} монет"
        
    update_league(user_id)
    data_manager.save_data()
    return {"success": True, "message": message, "balance": ud["coins"]}
