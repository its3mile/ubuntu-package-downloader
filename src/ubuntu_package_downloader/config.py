from pydantic import Field
from pydantic_settings import SettingsConfigDict, BaseSettings
from uuid import uuid4


class Settings(BaseSettings):
    """Configuration settings for Ubuntu Package Downloader."""

    model_config = SettingsConfigDict(
        pyproject_toml_depth=2,
        pyproject_toml_table_header=("tool", "settings"),
    )
    launchpad_consumer_name: str = Field(frozen=True, default=str(uuid4()))
    launchpad_service_root: str = Field(frozen=True, default="production")
    launchpad_version: str = Field(frozen=True, default="devel")
    launchpad_distribution: str = Field(frozen=True, default="ubuntu")
