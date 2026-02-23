"""Configuration management for Ignition MCP server."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file.

    All variables are prefixed with IGNITION_MCP_ in the environment.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="IGNITION_MCP_")

    ignition_gateway_url: str = Field(
        default="http://localhost:8088",
        description="Base URL for the Ignition Gateway (e.g. https://gateway:8043)",
    )

    ignition_username: str = Field(
        default="admin", description="Username for basic auth (used when api_key is empty)"
    )

    ignition_password: str = Field(default="password", description="Password for basic auth")

    ignition_api_key: str = Field(
        default="",
        description="API key for Ignition Gateway REST API auth (preferred over basic auth)",
    )

    webdev_tag_endpoint: str = Field(
        default="",
        description=(
            "WebDev resource path for tag read/write (e.g. Global/GatewayAPI/tags). "
            "Leave empty to disable — tools will return a setup-guidance error."
        ),
    )

    webdev_tag_config_endpoint: str = Field(
        default="",
        description=(
            "WebDev resource path for tag CRUD (e.g. Global/GatewayAPI/tagConfig). "
            "Leave empty to disable — tools will return a setup-guidance error."
        ),
    )

    webdev_alarm_endpoint: str = Field(
        default="",
        description=(
            "WebDev resource path for alarm queries (e.g. Global/GatewayAPI/alarms). "
            "Leave empty to disable — tools will return a setup-guidance error."
        ),
    )

    webdev_tag_history_endpoint: str = Field(
        default="",
        description=(
            "WebDev resource path for tag history (e.g. Global/GatewayAPI/tagHistory). "
            "Leave empty to disable — tools will return a setup-guidance error."
        ),
    )

    webdev_script_exec_endpoint: str = Field(
        default="",
        description=(
            "WebDev resource path for script execution (e.g. Global/GatewayAPI/scriptExec). "
            "Leave empty to disable — tools will return a setup-guidance error."
        ),
    )

    enable_script_execution: bool = Field(
        default=False,
        description=(
            "Enable the run_gateway_script tool. OFF by default for safety. "
            "Set IGNITION_MCP_ENABLE_SCRIPT_EXECUTION=true to enable."
        ),
    )

    ssl_verify: bool = Field(
        default=True,
        description="Verify SSL certificates. Set to false for self-signed certs.",
    )

    server_host: str = Field(default="127.0.0.1", description="Host to bind the MCP server to")

    server_port: int = Field(default=8007, description="Port to bind the MCP server to")


settings = Settings()
