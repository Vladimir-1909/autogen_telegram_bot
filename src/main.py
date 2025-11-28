from __future__ import annotations

import logging
import signal
import sys
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.handlers import handle_message, reset, start
from config import config

logger = logging.getLogger(__name__)


class BotApp:
    """Main bot application with graceful shutdown support."""

    def __init__(self) -> None:
        """Initialize bot application."""
        self.app: Application | None = None

    def setup(self) -> None:
        """Set up bot application with handlers and signal handlers."""
        config.validate()
        logger.info("🚀 Запуск YandexGPT Multi-Agent Bot")

        self.app = Application.builder().token(config.TELEGRAM_TOKEN).build()

        # Register command handlers
        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("reset", reset))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        logger.info("✅ Бот настроен и готов к работе")

    def _shutdown(self, signum: int, frame) -> None:  # pylint: disable=unused-argument
        """
        Handle shutdown signals gracefully.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info("👋 Завершение работы...")
        if self.app:
            try:
                self.app.stop_running()
                logger.info("🛑 Bot application stopped")
            except Exception as e:
                logger.error(f"Error stopping bot application: {e}")
        sys.exit(0)

    def run(self) -> None:
        """Run bot application in appropriate mode."""
        try:
            if config.WEBHOOK_URL:
                logger.info(f"🌐 Режим webhook: {config.WEBHOOK_URL}")
                self.app.run_webhook(
                    listen="0.0.0.0",
                    port=config.PORT,
                    webhook_url=config.WEBHOOK_URL,
                    secret_token=config.WEBHOOK_SECRET_TOKEN if hasattr(config, 'WEBHOOK_SECRET_TOKEN') else None
                )
            else:
                logger.info("📡 Режим polling")
                self.app.run_polling(
                    allowed_updates=Update.ALL_TYPES,
                    close_loop=False,
                    drop_pending_updates=True
                )
        except Exception as e:
            logger.critical(f"🔥 Fatal error during bot execution: {e}", exc_info=True)
            raise


def main() -> None:
    """Main entry point for the application."""
    try:
        # Setup logging early
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=os.getenv("LOG_LEVEL", "INFO"),
            stream=sys.stdout
        )

        bot = BotApp()
        bot.setup()
        bot.run()

    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
