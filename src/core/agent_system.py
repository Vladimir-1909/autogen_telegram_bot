from __future__ import annotations

import logging
import typing

from autogen import (
    AssistantAgent,
    UserProxyAgent,
    GroupChat,
    GroupChatManager
)
from telegram import Bot

from bot.interface import TelegramInterface
from config import config

logger = logging.getLogger(__name__)


class AgentSystem:
    """System for managing multi-agent team interactions."""

    ROLES = {
        "user_proxy": "👤 User Proxy",
        "analyst": "🧠 Analyst",
        "coder": "👨‍💻 Coder",
        "executor": "⚙️ Executor",
        "manager": "🤖 Manager"
    }

    def __init__(self, chat_id: int, bot: Bot, loop: typing.Any) -> None:
        """
        Initialize agent system.

        Args:
            chat_id: Telegram chat ID
            bot: Telegram bot instance
            loop: Asyncio event loop
        """
        self.chat_id = chat_id
        self.bot = bot
        self.loop = loop
        self.telegram_interface = TelegramInterface(bot, chat_id)
        self.llm_config = config.get_llm_config()
        self.termination_detected = False
        self.last_message = ""
        self._create_agents()
        logger.info(f"✅ Агенты созданы для чата {chat_id}")

    def _create_agents(self) -> None:
        """Create and configure all agents in the system."""
        # User Proxy - interface with user
        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            system_message=(
                "Ты - посредник между пользователем и командой экспертов. "
                "Твоя задача - передать запрос пользователя команде точно и без изменений. "
                "Не добавляй своих комментариев или предположений. "
                "Просто передай исходный запрос команде аналитиков."
            ),
            human_input_mode="NEVER",
            max_consecutive_auto_reply=20,
            code_execution_config={
                "work_dir": str(config.CODE_WORK_DIR),
                "use_docker": False
            },
            llm_config=self.llm_config
        )

        # Analyst - task analysis and planning
        self.analyst = AssistantAgent(
            name="analyst",
            system_message=(
                "Ты - главный аналитик команды. Следуй строго этим правилам:\n\n"

                "🔍 АНАЛИЗ ЗАПРОСА:\n"
                "1. Внимательно изучи запрос пользователя\n"
                "2. Определи, нужны ли для ответа РЕАЛЬНЫЕ данные из внешних источников\n"
                "3. Если нужны реальные данные (погода, курсы валют, новости, статистика и т.д.) - "
                "ОБЯЗАТЕЛЬНО запроси код у Программиста\n"
                "4. НИКОГДА не придумывай данные или не используй устаревшую информацию\n\n"

                "📋 ПЛАНИРОВАНИЕ:\n"
                "5. Если нужны реальные данные:\n"
                "   - Четко опиши задачу для Программиста\n"
                "   - Укажи конкретный публичный API без ключа (например, wttr.in для погоды, "
                "exchangerate-api.com для курсов валют)\n"
                "   - Укажи формат ожидаемого ответа\n"
                "6. Если код не нужен - проанализируй запрос и подготовь ответ на основе "
                "общих знаний\n\n"

                "✅ ЗАВЕРШЕНИЕ:\n"
                "7. После получения результатов от Исполнителя проанализируй их\n"
                "8. Сформулируй ЧЕТКИЙ и ПОЛЕЗНЫЙ ответ для пользователя\n"
                "9. Если ответ готов - напиши TERMINATE\n\n"

                "⚡ ПУБЛИЧНЫЕ API БЕЗ КЛЮЧЕЙ:\n"
                "- Погода: https://wttr.in/Moscow?format=3 или https://wttr.in/Moscow?format=json\n"
                "- Курсы валют: https://api.exchangerate-api.com/v4/latest/USD (бесплатный тариф)\n"
                "- Новости: https://newsapi.org/v2/top-headlines?country=ru (требует ключа, избегай)\n"
                "- Поиск: используй duckduckgo_search библиотеку\n\n"

                "❌ ЗАПРЕЩЕНО:\n"
                "- Придумывать или фантазировать данные\n"
                "- Использовать API, требующие ключи (если ключ не предоставлен)\n"
                "- Отвечать без получения реальных данных, если они нужны\n"
                "- Использовать input() в коде\n\n"
                "При сомнениях - всегда запрашивай выполнение кода для получения реальных данных."
            ),
            llm_config=self.llm_config,
        )

        # Coder - code writing
        self.coder = AssistantAgent(
            name="coder",
            system_message=(
                "Ты - Senior Python разработчик. Следуй строго этим правилам:\n\n"

                "💻 КОДИРОВАНИЕ:\n"
                "1. Пиши ТОЛЬКО рабочий, протестированный Python код\n"
                "2. Для получения данных из интернета используй ТОЛЬКО публичные API без ключей:\n"
                "   • Погода: requests.get('https://wttr.in/{city}?format=json')\n"
                "   • Курсы валют: requests.get('https://api.exchangerate-api.com/v4/latest/USD')\n"
                "   • Поиск: from duckduckgo_search import DDGS; results = DDGS().text(query, max_results=5)\n"
                "3. ВСЕГДА используй print() для вывода результатов\n"
                "4. ВСЕГДА проверяй код на наличие ошибок перед отправкой\n"
                "5. Заключай код ТОЛЬКО в ```python ... ```\n\n"

                "🚫 ЗАПРЕЩЕНО:\n"
                "- Использовать API, требующие ключи (OpenWeatherMap, NewsAPI и т.д.)\n"
                "- Использовать input() или интерактивные функции\n"
                "- Импортировать библиотеки, которых нет в requirements.txt\n"
                "- Писать код, который может повредить систему\n"
                "- Использовать вредоносные или опасные библиотеки\n\n"

                "📋 ФОРМАТ КОДА:\n"
                "```python\n"
                "import requests\n"
                "import json\n"
                "import time\n"
                "\n"
                "def get_real_data():\n"
                "    # Конкретная задача\n"
                "    try:\n"
                "        # Получение данных\n"
                "        response = requests.get('https://публичный-api.без-ключа/endpoint')\n"
                "        data = response.json()\n"
                "        \n"
                "        # Обработка и вывод результатов\n"
                "        result = {\n"
                "            'status': 'success',\n"
                "            'data': data\n"
                "        }\n"
                "        print(json.dumps(result, ensure_ascii=False, indent=2))\n"
                "        return True\n"
                "    except Exception as e:\n"
                "        error_result = {\n"
                "            'status': 'error',\n"
                "            'message': str(e)\n"
                "        }\n"
                "        print(json.dumps(error_result, ensure_ascii=False, indent=2))\n"
                "        return False\n"
                "\n"
                "if __name__ == '__main__':\n"
                "    get_real_data()\n"
                "```\n\n"

                "🎯 ВАЖНО:\n"
                "- Если задача не требует кода - верни 'Код не требуется. Запрос можно обработать без выполнения кода.'\n"
                "- Всегда проверяй доступность API перед использованием\n"
                "- Обрабатывай исключения и выводи понятные ошибки\n\n"
                "При сомнениях - уточни задачу у Аналитика."
            ),
            llm_config=self.llm_config
        )

        # Executor - code execution
        self.executor = UserProxyAgent(
            name="executor",
            system_message=(
                "Ты - исполнитель кода. Следуй этим правилам:\n\n"
                "⚙️ ВЫПОЛНЕНИЕ КОДА:\n"
                "1. Выполняй ВЕСЬ полученный Python код без изменений\n"
                "2. Возвращай ПОЛНЫЙ результат выполнения, включая ошибки\n"
                "3. Если код не запускается - сообщи об ошибке с деталями\n\n"

                "🔍 РЕКОМЕНДАЦИИ:\n"
                "• Всегда проверяй безопасность кода перед выполнением\n"
                "• Обрабатывай сетевые запросы с таймаутами\n"
                "• Используй изолированную среду выполнения\n\n"

                "📋 ФОРМАТ ОТВЕТА:\n"
                ">>>>>>>> EXECUTING CODE BLOCK 1 (inferred language is python)...\n"
                "[результат выполнения кода]\n"
                "exitcode: 0 (execution succeeded)\n"
                "Code output: [полный вывод кода]"
            ),
            human_input_mode="NEVER",
            code_execution_config={
                "work_dir": str(config.CODE_WORK_DIR),
                "use_docker": False
            },
            llm_config=self.llm_config
        )

        # Group chat setup
        allowed_transitions = {
            self.user_proxy: [self.analyst],
            self.analyst: [self.coder, self.user_proxy],
            self.coder: [self.executor],
            self.executor: [self.analyst],
        }

        self.groupchat = GroupChat(
            agents=[self.user_proxy, self.analyst, self.coder, self.executor],
            messages=[],
            max_round=config.MAX_ROUNDS,
            speaker_selection_method="auto",
            allowed_or_disallowed_speaker_transitions=allowed_transitions,
            speaker_transitions_type="allowed"
        )

        # Manager - coordination
        self.manager = GroupChatManager(
            groupchat=self.groupchat,
            llm_config=self.llm_config,
            name="manager",
            system_message=(
                "Ты - менеджер группы. Координируй работу СЛЕДУЮЩИМ ОБРАЗОМ:\n\n"
                "✅ ОБЯЗАТЕЛЬНЫЕ ШАГИ:\n"
                "1. ВСЕГДА направляй запрос сначала к Аналитику\n"
                "2. Если Аналитик определил, что нужны реальные данные - "
                "направляй к Программисту, затем к Исполнителю\n"
                "3. После получения результатов от Исполнителя - направляй к Аналитику "
                "для финальной обработки\n\n"

                "🚫 ЗАПРЕЩЕНО:\n"
                "- Пропускать Исполнителя, если нужны реальные данные\n"
                "- Завершать диалог без TERMINATE от Аналитика\n"
                "- Изменять порядок работы агентов\n\n"

                "⚡ ПРИОРИТЕТЫ:\n"
                "1. Реальные данные > Предположения\n"
                "2. Публичные API без ключей > API с ключами\n"
                "3. Безопасность > Скорость\n\n"
                "🎯 ЦЕЛЬ: Получить МАКСИМАЛЬНО ТОЧНЫЙ ответ с РЕАЛЬНЫМИ данными, "
                "выполнив ВЕСЬ необходимый код."
            ),
        )

        # Register message handlers
        self._register_message_handlers()

    def _register_message_handlers(self) -> None:
        """Register message handlers for all agents."""
        agents = [self.user_proxy, self.analyst, self.coder, self.executor, self.manager]

        def create_handler(agent_name: str):
            async def handler(
                    recipient: typing.Any,
                    messages: list[dict[str, typing.Any]],
                    sender: typing.Any,
                    config: dict[str, typing.Any] | None) -> tuple[bool, typing.Any | None]:
                return await self._handle_message(recipient, messages, sender, agent_name)

            return handler

        for agent in agents:
            agent.register_reply(
                trigger=lambda sender: True,
                reply_func=create_handler(agent.name),
                position=0,
                config=None
            )

    async def _handle_message(
            self,
            recipient: typing.Any,
            messages: list[dict],
            sender: typing.Any,
            agent_name: str
    ) -> tuple[bool, typing.Any | None]:
        """
        Handle messages from all agents.

        Processes messages, filters out service messages, handles TERMINATE,
        and forwards messages to Telegram.

        Args:
            recipient: Message recipient agent
            messages: List of messages in conversation
            sender: Message sender agent
            agent_name: Name of the sending agent

        Returns:
            Tuple[bool, Optional[Any]]: (should_terminate, reply_content)
        """
        if not messages:
            return False, None

        last_msg = messages[-1]
        content = last_msg.get("content", "").strip()
        logger.debug(f"📥 Получено сообщение от {agent_name}: {content[:100]}...")

        # Skip empty messages
        if not content:
            return False, None

        # Skip service messages
        if "Next speaker:" in content or "next speaker" in content.lower() or "##" in content.lower():
            logger.debug(f"⏭️ Пропущено служебное сообщение от {agent_name}")
            return False, None

        # Determine sender role
        role_display = self.ROLES.get(agent_name, f"🤖 {agent_name}")

        # Special handling for executor
        if ">>>>>>>> EXECUTING CODE BLOCK" in content or "exitcode:" in content:
            role_display = "⚙️ Executor (Код)"

        # Handle TERMINATE messages
        if "TERMINATE" in content.upper():
            logger.info(f"✅ TERMINATE обнаружен в сообщении от {agent_name}")
            self.termination_detected = True
            clean_content = content.replace("TERMINATE", "").strip()

            if clean_content:
                # Send final answer
                await self.telegram_interface.send_message(clean_content, "🎯 Финальный ответ")
                self.last_message = clean_content
                logger.info(f"📨 Финальный ответ отправлен: {clean_content[:50]}...")
            else:
                # Send default final message
                default_answer = "✅ Задача успешно выполнена командой экспертов"
                await self.telegram_interface.send_message(default_answer, "🎯 Финальный ответ")
                self.last_message = default_answer
                logger.info("📨 Отправлен стандартный финальный ответ")

            # Return True to terminate the conversation
            return True, None

        # Send regular message to Telegram
        await self.telegram_interface.send_message(content, role_display)
        logger.info(f"📨 [{self.chat_id}] {role_display}: {content[:50]}...")
        return False, None

    async def run_task(self, task: str) -> tuple[bool, str]:
        """
        Run task with multi-agent team.

        Args:
            task: User task description

        Returns:
            Tuple[bool, str]: (termination_detected, last_message)
        """
        logger.info(f"🚀 Запуск задачи для чата {self.chat_id}: {task[:50]}...")

        try:
            # Initiate conversation
            await self.user_proxy.a_initiate_chat(
                self.manager,
                message=task,
                clear_history=True
            )
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении задачи: {e}", exc_info=True)
            raise

        logger.info(
            f"✅ Задача для чата {self.chat_id} завершена. "
            f"TERMINATE: {self.termination_detected}"
        )
        return self.termination_detected, self.last_message
