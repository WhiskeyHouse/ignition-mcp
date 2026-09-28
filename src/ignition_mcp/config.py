"""Runtime settings. Gateway credentials are ign's business, never ours."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IGN_MCP_", extra="ignore", populate_by_name=True)

    ign_bin: str = Field(default="ign", validation_alias="IGN_BIN")
    profile: str | None = Field(default=None, validation_alias="IGNITION_PROFILE")
    host: str = "127.0.0.1"
    port: int = 8765
    # 1.4.0 is the first ign whose `rig up` reports `orphaned_modules` and
    # that carries `rig module uninstall`. 1.3.0 predates ALL of the module
    # work, so the old floor admitted a binary missing every module verb.
    min_ign_version: str = "1.4.0"
