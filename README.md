# Kasongo - AI Agent (MVP)
This repo is a starter scaffold for Kasongo — a chat interface for users and an admin dashboard to manage AI agents.

## Quick start (local, development)
1. Copy backend/.env.example -> backend/.env and fill OPENAI_API_KEY and SECRET_KEY as needed.
2. Build and run with Docker Compose:
   ```
   docker-compose up --build
   ```
3. Frontend available at http://localhost:3000 and backend at http://localhost:8000

## Default admin
- username: admin
- password: adminpass

## Notes
- Backend uses SQLModel and will create tables automatically.
- In production, change SECRET_KEY and secure CORS and tokens.
