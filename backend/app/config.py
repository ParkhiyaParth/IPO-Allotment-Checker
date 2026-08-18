from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    http_timeout_seconds: float = 20.0
    cors_allow_origins: str = "*"
    # Base64-encoded 32-byte AES-256 key for encrypting PANs at rest
    # (device-scoped, opt-in zero-tap allotment discovery). Empty by default
    # -- routes_device_pans.py returns 503 until this is set, rather than
    # silently storing PANs unencrypted or refusing to start.
    pan_encryption_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",")]


settings = Settings()
