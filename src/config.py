from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str

    MONGO_URI: str
    MONGO_DB: str

    RABBIT_HOST: str
    RABBIT_PORT: str
    RABBIT_USER: str
    RABBIT_PASS: str
    QUEUE_NAME: str

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_SES_SENDER: str


settings = Settings()
