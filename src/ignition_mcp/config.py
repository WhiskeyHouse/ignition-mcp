"""Runtime settings. Gateway credentials are ign's business, never ours."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IGN_MCP_", extra="ignore", populate_by_name=True)

    ign_bin: str = Field(default="ign", validation_alias="IGN_BIN")
    profile: str | None = Field(default=None, validation_alias="IGNITION_PROFILE")
    host: str = "127.0.0.1"
    port: int = 8765
    min_ign_version: str = "1.2.0"
