import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    JWT_SECRET: str = os.getenv("JWT_SECRET", "8f9b7c61d5e3a098c76543210fedcba9876543210fedcba9876543210fedcba9")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    PORT: int = int(os.getenv("PORT", "8000"))

    @property
    def DATABASE_URL(self) -> str:
        url = os.getenv("DATABASE_URL", "")
        if url and not url.startswith("${{"):
            return url
        host = os.getenv("PGHOST", "localhost")
        port = os.getenv("PGPORT", "5432")
        user = os.getenv("PGUSER", "postgres")
        password = os.getenv("PGPASSWORD", "")
        database = os.getenv("PGDATABASE", "medvest")
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"


settings = Settings()
