"""Main bot entry point"""
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
import data_manager
from handlers import (
    start_handler,
    button_handler,
    mm_handler,
    admins_panel_handler,
    text_message_handler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    # 📥 Загружаем данные игроков
    data_manager.load_data()

    # 🔄 Запускаем автосохранение
    data_manager.start_autosave()

    # 📥 Загружаем промокоды
    try:
        import promocodes
        promocodes.load_promocodes()
        logger.info("🎟 Промокоды загружены")
    except Exception as e:
        logger.warning(f"⚠️ Промокоды не загружены: {e}")

    # Создаём приложение
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # 📜 Команды
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("mm", mm_handler))
    application.add_handler(CommandHandler("admins", admins_panel_handler))

    # 🔘 Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # 💬 Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # 🚀 Запуск
    logger.info("✅ Bot successfully started!")

    try:
        application.run_polling(drop_pending_updates=True)
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")
    finally:
        # 💾 Сохраняем данные при остановке
        data_manager.stop_autosave()
        data_manager.save_data()
        logger.info("💾 Данные сохранены перед остановкой")

if __name__ == '__main__':
    main()
