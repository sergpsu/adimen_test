import logging
from typing import Optional

from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    DB_URL: str = "sqlite+aiosqlite:///adimen_test_db"

    SQS_QUEUE_URL: Optional[AnyUrl]

    # user created on start
    USER_EMAIL: Optional[str] = None
    USER_PASSWORD: Optional[str] = None


settings = Settings()

logger = logging.getLogger()


def setup_logger():
    logger.setLevel(logging.getLevelName(settings.LOG_LEVEL.upper()))
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-5s] %(message)s"))
    logger.addHandler(handler)
