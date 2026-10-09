import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "News Bias Summarizer API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # CORS configuration
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # SerpAPI Key
    SERP_API_KEY: str = os.getenv("SERP_API_KEY", "")

    # Mock Mode (returns static mock response when True)
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "false").lower() == "true"


settings = Settings()
