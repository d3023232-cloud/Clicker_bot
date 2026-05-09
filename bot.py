"""Точка входа бота"""
import signal
import os
import sys
import asyncio

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, PreCheckoutQueryHandler
)

import config
import data_manager
from handlers import (
    start_handler, button_handler, mm_handler,
    admins_panel_handler, get_main_menu, text_message_handler
)
from payments import pre_checkout_handler, successful_payment_handler
from reminders import send_reminders
from admin import (
    is_admin, add_coins, give_donate, give_premium,
    get_user_info, reset_user, get_stats, give_daily_reset,
    ban_user, test_achievements, get_debug_info, handle_econ_command
)
from utils import get_user_name, format_number

# ================= ОБРАБОТЧИКИ КОМАНД =================

async def econ_command_handler(update, context):
    """Обработчик команды /econ для управления экономикой"""
    user_id = update.effective_user.id
    args = context.args
    # Передаем управление в admin.py
    result = handle_econ_command(user_id, args)
    # handle_econ_command возвращает текст, отправляем его
    # Если результат содержит markdown/HTML код, используем parse_mode
    await update.message.reply_text(result, parse_mode="HTML")

async def debug_command(update, context):
    """Команда /debug"""
    if not is_admin(update.effective_user.id):
        return
    user_id = update.effective_user.id
    msg = get_debug_info(user_id)
    await update.message.reply_text(msg, parse_mode="HTML")

async def add_coins_command(update, context):
    """Команда /add_coins"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /add_coins <user_id> <amount>")
        return
    result = add_coins(context.args[0], context.args[1])
    await update.message.reply_text(result["message"])

async def give_donate_command(update, context):
    """Команда /give_donate"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /give_donate <user_id> <amount>")
        return
    result = give_donate(context.args[0], context.args[1])
    await update.message.reply_text(result["message"])

async def give_premium_command(update, context):
    """Команда /give_premium"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Используйте: /give_premium <user_id> <days>")
        return
    result = give_premium(context.args[0], context.args[1])
    await update.message.reply_text(result["message"])

async def get_user_command(update, context):
    """Команда /get_user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /get_user <user_id>")
        return
    result = get_user_info(context.args[0])
    await update.message.reply_text(result["message"])

async def reset_user_command(update, context):
    """Команда /reset_user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /reset_user <user_id>")
        return
    result = reset_user(context.args[0])
    await update.message.reply_text(result["message"])

async def stats_command(update, context):
    """Команда /stats"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    result = get_stats()
    await update.message.reply_text(result["message"])

async def give_daily_command(update, context):
    """Команда /give_daily"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /give_daily <user_id>")
        return
    result = give_daily_reset(context.args[0])
    await update.message.reply_text(result["message"])

async def ban_user_command(update, context):
    """Команда /ban_user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /ban_user <user_id>")
        return
    result = ban_user(context.args[0])
    await update.message.reply_text(result["message"])

async def test_achievements_command(update, context):
    """Команда /test_achievements"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Используйте: /test_achievements <user_id>")
        return
    result = test_achievements(context.args[0])
    await update.message.reply_text(result["message"])

async def broadcast_command(update, context):
    """Команда /broadcast"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Доступ запрещён.")
        return
    if not context.args:
        await update.message.reply_text("Используйте: /broadcast <сообщение>")
        return
    
    message = ' '.join(context.args)
    sent_count = 0
    failed_count = 0

    active_users = [
        uid for uid, data in data_manager.user_data.items()
        if data.get("coins", 0) > 0 or data.get("clicks", 0) > 0
    ]

    for uid in active_users:
        try:
            text = "📢 Рассылка от админа:\n\n" + message
            await context.bot.send_message(chat_id=uid, text=text)
            sent_count += 1
        except Exception:
            failed_count += 1

    lines = [
        "✅ Рассылка отправлена!",
        f"📬 Успешно: {sent_count}",
        f"❌ Не доставлено: {failed_count}"
    ]
    await update.message.reply_text("\n".join(lines))

def signal_handler(sig, frame):
    """Обработчик сигналов завершения"""
    print("\n🛑 Получен сигнал завершения. Сохраняем данные...")
    data_manager.save_data()
    exit(0)

def main():
    """Главная функция запуска бота"""
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Загрузка данных
    data_manager.load_data()

    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Получение JobQueue
    job_queue = application.job_queue

    if job_queue is None:
        print("⚠️ JobQueue не доступен. Напоминания отключены.")
        print("💡 Установите: pip install python-telegram-bot[job-queue]")
    else:
        # Фоновая задача напоминаний
        job_queue.run_repeating(send_reminders, interval=1800, first=60)
        print("✅ JobQueue запущен")

    # === РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ===

    # Основные команды
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("mm", mm_handler))
    application.add_handler(CommandHandler("admins", admins_panel_handler))
    
    # 📊 Экономика: команда /econ
    application.add_handler(CommandHandler("econ", econ_command_handler))

    # Админ команды
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("add_coins", add_coins_command))
    application.add_handler(CommandHandler("get_user", get_user_command))
    application.add_handler(CommandHandler("reset_user", reset_user_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("give_daily", give_daily_command))
    application.add_handler(CommandHandler("ban_user", ban_user_command))
    application.add_handler(CommandHandler("test_achievements", test_achievements_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("give_donate", give_donate_command))
    application.add_handler(CommandHandler("give_premium", give_premium_command))

    # 🎮 Обработка ставок и текстовых команд (из handlers.py)
    # Важно: фильтруем команды (~filters.COMMAND), чтобы не мешать /econ и другим
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Callbacks (кнопки)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Платежи
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    print("✅ Бот запущен!")
    print(f"📊 Админы: {config.ADMIN_IDS}")
    print(f"💾 Файл данных: {config.DATA_FILE}")

    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
