from __future__ import annotations

import re
import logging

from telegram import Bot, constants
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramInterface:
    """Interface for sending formatted messages to Telegram."""

    def __init__(self, bot: Bot, chat_id: int) -> None:
        """
        Initialize Telegram interface.

        Args:
            bot: Telegram bot instance
            chat_id: Target chat ID
        """
        self.bot = bot
        self.chat_id = chat_id

    async def send_message(self, text: str, role: str) -> bool:
        """
        Send formatted message to Telegram chat.

        Attempts to send message with HTML formatting, falls back to plain text
        if HTML parsing fails.

        Args:
            text: Message content
            role: Sender role for display

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if not text or not text.strip():
            return False

        try:
            formatted = self._format_message(text, role)

            await self.bot.send_message(
                chat_id=self.chat_id,
                text=formatted,
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
            return True

        except TelegramError as e:
            logger.warning(
                f"⚠️ Ошибка Telegram: {e}. Попытка отправки как plain text."
            )
            try:
                clean_text = re.sub(r'<[^>]+>', '', text)
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=f"{role}\n\n{clean_text}",
                    disable_web_page_preview=True
                )
                return True
            except Exception as e2:
                logger.error(f"❌ Полный провал отправки: {e2}")
                return False

    def _format_message(self, text: str, role: str) -> str:
        """
        Format message content with HTML tags for Telegram.

        Applies special formatting for:
        - Code execution messages
        - Execution results
        - Python code blocks
        - Generic code blocks

        Args:
            text: Raw message content
            role: Sender role for display

        Returns:
            str: HTML-formatted message
        """
        content = text.strip()

        # Format code execution messages
        if ">>>>>>>> EXECUTING CODE BLOCK" in content:
            content = re.sub(
                r'>>>>>>>> EXECUTING CODE BLOCK \d+ \(inferred language is \w+\)\.\.\.',
                '💻 <b>Выполнение кода</b>',
                content
            )

        # Format execution results
        if "exitcode:" in content:
            content = (
                content.replace("exitcode:", "\n<b>Статус:</b>")
                .replace("Code output:", "\n<b>Результат:</b>")
                .replace("execution succeeded", "✅ Успешно")
                .replace("execution failed", "❌ Ошибка")
            )

        # Format code blocks
        if "```python" in content:
            content = content.replace("```python", "<pre><code class='language-python'>")
            content = content.replace("```", "</code></pre>")
        elif "```" in content:
            content = content.replace("```", "<pre><code>")
            content = content.replace("```", "</code></pre>")

        return f"<b>{role}</b>\n\n{content}"
