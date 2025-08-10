import os
from dotenv import load_dotenv

load_dotenv()

# Railway sets DATABASE_URL as environment variable like this:
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("POSTGRES_DATABASE_URL"))

SECRET_KEY = os.getenv("SECRET_KEY", "devsecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")


# If not found, build it from individual PG* vars (Railway provides these by default)
if not DATABASE_URL:
    PGUSER = os.getenv("PGUSER", "postgres")
    PGPASSWORD = os.getenv("PGPASSWORD", "")
    PGHOST = os.getenv("PGHOST", "localhost")
    PGPORT = os.getenv("PGPORT", "5432")
    PGDATABASE = os.getenv("PGDATABASE", "postgres")

    DATABASE_URL = f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
