from pathlib import Path

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings

_env_file = Path(__file__).resolve().parent / ".env"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=_env_file)

    DEBUG: bool = False
    PROJECT_CONTAINERS_DIR: Path = Field(
        default_factory=lambda: _PROJECT_ROOT / "project_containers"
    )
    OPENAI_API_KEY: str
    CURSOR_API_KEY: str

    # Database
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./db.sqlite3"
    DATABASE_ENGINE_POOL_TIMEOUT: int = 30
    DATABASE_ENGINE_POOL_RECYCLE: int = 3600
    DATABASE_ENGINE_POOL_SIZE: int = 5
    DATABASE_ENGINE_MAX_OVERFLOW: int = 10
    DATABASE_ENGINE_POOL_PING: bool = True


settings = Settings()
