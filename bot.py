"""Main bot entry point"""
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

import config
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
    # Создаём приложение
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # 📜 Команды
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("mm", mm_handler))
    application.add_handler(CommandHandler("admins", admins_panel_handler))

    # 🔘 Обработчик кнопок (все callback_data)
    application.add_handler(CallbackQueryHandler(button_handler))

    # 💬 Обработчик текстовых сообщений (ставки, админ-ввод, команды)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # 🚀 Запуск
    logger.info("✅ Bot successfully started!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
