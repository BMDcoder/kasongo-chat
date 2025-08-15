import os
from dotenv import load_dotenv

load_dotenv()

# Railway typically sets DATABASE_URL as environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")
