"""Configuration management for Ignition MCP server."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    ignition_gateway_url: str = Field(
        default="http://localhost:8088",
        description="Base URL for the Ignition Gateway"
    )
    
    ignition_username: str = Field(
        default="admin",
        description="Username for Ignition Gateway authentication"
    )
    
    ignition_password: str = Field(
        default="password",
        description="Password for Ignition Gateway authentication"
    )
    
    ignition_api_key: str = Field(
        default="",
        description="API key for Ignition Gateway REST API authentication"
    )
    
    server_host: str = Field(
        default="127.0.0.1",
        description="Host to bind the MCP server to"
    )
    
    server_port: int = Field(
        default=8000,
        description="Port to bind the MCP server to"
    )
    
    class Config:
        env_file = ".env"
        env_prefix = "IGNITION_MCP_"


settings = Settings()