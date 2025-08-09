import os
from dotenv import load_dotenv

load_dotenv()

# Railway sets DATABASE_URL as environment variable like this:
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("POSTGRES_DATABASE_URL", "sqlite:///./kasongo.db"))

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
