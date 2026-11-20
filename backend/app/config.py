from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Lee variables de entorno desde .env."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_url: str = "mongodb://mongo:27017"
    mongo_db: str = "staysky"
    rapidapi_key: str = ""
    rapidapi_host: str = "booking-com15.p.rapidapi.com"


settings = Settings()