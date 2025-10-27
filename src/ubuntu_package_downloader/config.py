from pydantic import Field
from pydantic_settings import (
    SettingsConfigDict,
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    YamlConfigSettingsSource
)
from uuid import uuid4
from pathlib import Path

class ProjectSettings(BaseSettings):
    """Project related settings."""

    model_config = SettingsConfigDict(
        pyproject_toml_depth=2,
        pyproject_toml_table_header=("project",),
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
            init_settings,
        )

    name: str = Field(frozen=True)
    version: str = Field(frozen=True)
    description: str = Field(frozen=True)


class LaunchpadSettings(BaseSettings):
    """Configuration settings for Ubuntu Package Downloader."""

    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "config.yml",
        yaml_config_section="launchpad",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            init_settings,
        )

    consumer_name: str = Field(frozen=True, default=str(uuid4()))
    service_root: str = Field(frozen=True)
    version: str = Field(frozen=True)
    distribution: str = Field(frozen=True)


class Settings(BaseSettings):
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    launchpad: LaunchpadSettings = Field(default_factory=LaunchpadSettings)


if __name__ == "__main__":
    print(Settings.model_validate({}))
