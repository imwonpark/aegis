from typing import Optional
from pydantic import BaseModel, Field
from .policy import ActionDecision


class RedisConfig(BaseModel):
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(None, description="Redis password")
    decode_responses: bool = Field(default=True, description="Decode responses as strings")


class LoggingConfig(BaseModel):
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    enable_json: bool = Field(default=False, description="Enable JSON formatted logging")


class EscalationConfig(BaseModel):
    max_retries: int = Field(default=3, description="Maximum webhook retry attempts")
    timeout_seconds: int = Field(default=10, description="Webhook timeout in seconds")
    retry_delay_seconds: int = Field(default=1, description="Delay between retry attempts")


class SecurityConfig(BaseModel):
    api_key_header: str = Field(default="X-API-Key", description="Header name for API key authentication")
    webhook_secret_key: str = Field(default_factory=lambda: "default-webhook-secret-key-change-in-production", description="Secret key for signing webhook payloads")
    enable_rate_limiting: bool = Field(default=True, description="Enable API rate limiting")
    rate_limit_per_minute: int = Field(default=1000, description="Requests per minute per client")


class Config(BaseModel):
    service_name: str = Field(default="aegis-guardrail", description="Service name")
    host: str = Field(default="0.0.0.0", description="Service bind address")
    port: int = Field(default=8000, description="Service port")
    default_decision: ActionDecision = Field(default=ActionDecision.ALLOW, description="Default decision when no policies match")
    log_config: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    redis_config: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    escalation_config: EscalationConfig = Field(default_factory=EscalationConfig, description="Escalation configuration")
    security_config: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")
