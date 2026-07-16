import os
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./medvest.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "8f9b7c61d5e3a098c76543210fedcba9876543210fedcba9876543210fedcba9")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    PORT: int = int(os.getenv("PORT", "8000"))

settings = Settings()
