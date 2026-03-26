"""Application configuration loaded from environment variables."""

import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    """
    Application settings resolved from environment variables or .env file.

    :param database_url: SQLAlchemy connection URL for MySQL
    :param debug: enable debug mode
    """

    database_url: str = "mysql+pymysql://root:root@localhost:3306/transfer_bookings"
    debug: bool = False

    model_config = pydantic_settings.SettingsConfigDict(env_file=".env")


settings = Settings()
