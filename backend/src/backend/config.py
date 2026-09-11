import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ELSEWHERE_",
    )

    data_dir: Path = Field(
        default_factory=lambda: Path(os.environ["LOCALAPPDATA"]) / "Elsewhere"
    )