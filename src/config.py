from __future__ import annotations

import os
import logging
import typing

from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class Config:
    """Simple configuration manager with permission fallbacks."""

    _instance = None

    def __new__(cls) -> "Config":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        """Initialize configuration with simple directory setup."""
        # Telegram configuration
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
        self.WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip() or None
        self.PORT = int(os.getenv("PORT", "8080"))

        # Yandex Cloud configuration
        self.YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
        self.YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
        self.YANDEX_LLM_BASE_URL = os.getenv("YANDEX_LLM_BASE_URL", "https://llm.api.cloud.yandex.net/v1").strip()

        # Model configuration
        model_template = os.getenv(
            "YANDEX_MODEL_URI",
            "gpt://{folder_id}/yandexgpt/latest"
        )
        if "{folder_id}" in model_template:
            self.YANDEX_MODEL_URI = model_template.format(folder_id=self.YANDEX_FOLDER_ID)
        else:
            self.YANDEX_MODEL_URI = model_template

        # LLM parameters
        self.LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.8"))
        self.LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "10000"))
        self.MAX_ROUNDS = int(os.getenv("MAX_ROUNDS", "20"))
        self.API_TIMEOUT = int(os.getenv("API_TIMEOUT", "120"))

        # Simple directory setup - use current directory
        self.CODE_WORK_DIR = Path("workspace")
        self.CACHE_DIR = ".cache"
        self.DISKCACHE_DIR = "cache"

        # Try to create directories, but don't fail if can't
        self._setup_directories()

    def _setup_directories(self) -> None:
        """Simple directory setup that won't fail on permissions."""
        try:
            # Create workspace directory
            self.CODE_WORK_DIR.mkdir(exist_ok=True)
            logger.info(f"✅ Workspace directory: {self.CODE_WORK_DIR}")
        except Exception as e:
            logger.warning(f"⚠️ Workspace setup warning: {e}")
            # Use current directory as fallback
            self.CODE_WORK_DIR = Path.cwd() / "workspace"
            self.CODE_WORK_DIR.mkdir(exist_ok=True)

        try:
            # Create cache directories
            Path(self.CACHE_DIR).mkdir(exist_ok=True)
            Path(self.DISKCACHE_DIR).mkdir(exist_ok=True)
            logger.info(f"✅ Cache directories created")
        except Exception as e:
            logger.warning(f"⚠️ Cache setup warning: {e}")

    def validate(self) -> None:
        """Validate required configuration parameters."""
        errors = []
        if not self.TELEGRAM_TOKEN:
            errors.append("TELEGRAM_TOKEN отсутствует")
        if not self.YANDEX_API_KEY:
            errors.append("YANDEX_API_KEY отсутствует")
        if not self.YANDEX_FOLDER_ID:
            errors.append("YANDEX_FOLDER_ID отсутствует")

        if errors:
            raise ValueError("Ошибки конфигурации: " + ", ".join(errors))
        logger.info("✅ Конфигурация проверена")

    def get_llm_config(self) -> dict[str, typing.Any]:
        """Get LLM configuration for Autogen."""
        return {
            "config_list": [{
                "model": self.YANDEX_MODEL_URI,
                "api_key": self.YANDEX_API_KEY,
                "base_url": self.YANDEX_LLM_BASE_URL,
                "api_type": "yandex",
                "extra_headers": {
                    "Authorization": f"Api-Key {self.YANDEX_API_KEY}",
                    "x-folder-id": self.YANDEX_FOLDER_ID
                },
                "timeout": self.API_TIMEOUT
            }],
            "temperature": self.LLM_TEMPERATURE,
            "max_tokens": self.LLM_MAX_TOKENS,
            "timeout": self.API_TIMEOUT,
            "cache_seed": None
        }


config = Config()
