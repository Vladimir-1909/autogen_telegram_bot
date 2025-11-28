from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.interface import TelegramInterface
from core.session_manager import Session, session_manager

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command.

    Sends welcome message with bot description and available features.

    Args:
        update: Incoming update containing message
        context: Context object for the update
    """
    welcome = (
        "🤖 <b>YandexGPT Multi-Agent System</b>\n\n"
        "<b>Команда экспертов:</b>\n"
        "👤 <b>User Proxy</b> - Прием задач\n"
        "🧠 <b>Analyst</b> - Анализ и планирование\n"
        "👨‍💻 <b>Coder</b> - Написание кода\n"
        "⚙️ <b>Executor</b> - Выполнение кода\n"
        "🤖 <b>Manager</b> - Координация\n\n"
        "<b>Вы увидите:</b>\n"
        "✅ Все шаги решения задачи\n"
        "💻 Результаты выполнения кода\n"
        "🎯 Финальный ответ\n\n"
        "Напишите вашу задачу! /reset для очистки памяти."
    )
    await update.message.reply_text(welcome, parse_mode="HTML")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /reset command.

    Clears session memory for current chat.

    Args:
        update: Incoming update containing message
        context: Context object for the update
    """
    chat_id = update.effective_chat.id
    session_manager.clear_session(chat_id)
    await update.message.reply_text("🧹 Память очищена!", parse_mode="HTML")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle incoming text messages from users.

    Processes user requests by initiating multi-agent team work.
    Prevents concurrent task execution and provides status updates.

    Args:
        update: Incoming update containing message
        context: Context object for the update

    Returns:
        None: All responses are sent via Telegram API
    """
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not text:
        return

    session: Session = session_manager.get_session(chat_id)

    # Prevent concurrent task execution
    if session.is_busy:
        await update.message.reply_text(
            "⏳ Задача уже выполняется. Пожалуйста, подождите завершения."
        )
        return

    try:
        session.is_busy = True
        session.set_context(context.bot, asyncio.get_running_loop())

        interface = TelegramInterface(context.bot, chat_id)

        # Confirm message receipt
        await interface.send_message(text, "👤 Пользователь")
        await interface.send_message(
            "🔄 Запускаю команду экспертов...\n\n"
            "Вы увидите полный процесс решения задачи в реальном времени.",
            "ℹ️ Система"
        )
        logger.info(f"📩 Новое сообщение от {chat_id}: {text}")

        # Run multi-agent task
        termination_detected, _ = await session.run_task(text)

        # Send completion status
        if termination_detected:
            await interface.send_message(
                "✅ Работа команды экспертов завершена успешно!",
                "ℹ️ Система"
            )
        else:
            await interface.send_message(
                "⚠️ Диалог завершился без TERMINATE. Возможно, задача не была полностью решена.",
                "ℹ️ Система"
            )

    except Exception as e:
        logger.error(
            f"❌ Ошибка выполнения задачи в чате {chat_id}: {e}",
            exc_info=True
        )
        error_interface = TelegramInterface(context.bot, chat_id)
        await error_interface.send_message(
            f"❌ Критическая ошибка: {str(e)}\n\n"
            "Пожалуйста, попробуйте позже или упростите задачу.",
            "ℹ️ Система"
        )
    finally:
        session.is_busy = False
