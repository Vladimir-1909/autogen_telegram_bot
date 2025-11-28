from __future__ import annotations

import logging
import typing

from telegram import Bot

from core.agent_system import AgentSystem

logger = logging.getLogger(__name__)


class Session:
    """Represents a chat session with agent system."""

    def __init__(self, chat_id: int) -> None:
        """
        Initialize session.

        Args:
            chat_id: Telegram chat ID
        """
        self.chat_id = chat_id
        self.is_busy = False
        self.bot = None
        self.loop = None

    def set_context(self, bot: Bot, loop: typing.Any) -> None:
        """
        Set bot context for session.

        Args:
            bot: Telegram bot instance
            loop: Asyncio event loop
        """
        self.bot = bot
        self.loop = loop

    async def run_task(self, task: str) -> tuple[bool, str]:
        """
        Run task with agent system.

        Args:
            task: User task description

        Returns:
            tuple[bool, str]: (termination_detected, last_message)

        Raises:
            ValueError: If bot context is not set
        """
        if not self.bot or not self.loop:
            raise ValueError("Bot context not set")

        agent_system = AgentSystem(self.chat_id, self.bot, self.loop)
        return await agent_system.run_task(task)


class SessionManager:
    """Singleton manager for chat sessions."""

    _instance = None
    sessions: dict[int, Session] = {}

    def __new__(cls) -> SessionManager:
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(SessionManager, cls).__new__(cls)
            cls._instance.sessions = {}
        return cls._instance

    def get_session(self, chat_id: int) -> Session:
        """
        Get or create session for chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Session: Chat session
        """
        if chat_id not in self.sessions:
            self.sessions[chat_id] = Session(chat_id)
        return self.sessions[chat_id]

    def clear_session(self, chat_id: int) -> None:
        """
        Clear session for chat.

        Args:
            chat_id: Telegram chat ID
        """
        if chat_id in self.sessions:
            del self.sessions[chat_id]
            logger.info(f"🧹 Сессия {chat_id} очищена")


session_manager = SessionManager()
