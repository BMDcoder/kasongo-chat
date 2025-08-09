# Kasongo - Backend
This is the FastAPI backend for Kasongo.

## Dev
- Copy `backend/.env.example` to `backend/.env` and fill values.
- Start locally with an SQLite fallback:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
