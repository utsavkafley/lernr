from pydantic_settings import BaseSettings

class Settings(BaseSettings):
        database_url:str
        jwt_secret:str
        jwt_expiry_days: int = 7
        anthropic_api_key: str
        cors_origins: list[str] = ["http://localhost:3000"]

        # Quiz selection constants
        mastery_threshold: float = 0.70
        recent_attempt_window: int = 10
        min_pool_size: int = 3

        class Config:
                env_file = ".env"

settings = Settings()