# NLP Project UI

A prescription assistant with a FastAPI backend for medicine lookup and a frontend chatbot UI.

## Project Structure
- `backend/` — FastAPI server for medicine data lookup
- `frontend/` — Static HTML/CSS/JS chatbot UI

## Backend Features
- Fuzzy search for medicine names
- Detailed medicine information (uses, side effects, etc.)
- CORS enabled for frontend integration

## Frontend Features
- Landing page with upload and chat options
- Chat interface that queries backend for medicine info, falls back to OpenAI
- File upload for prescriptions (UI only, not processed)

## Setup
1. Install Python 3.11+ from https://www.python.org/downloads/
2. Place `medicines.xlsx` in the project root next to `backend/` and `frontend/`
3. Set your OpenAI API key in the environment:
   - Windows PowerShell: `setx OPENAI_API_KEY "your_api_key_here"`
   - macOS/Linux: `export OPENAI_API_KEY="your_api_key_here"`
4. Install backend dependencies:
   - `cd backend && python -m pip install -r requirements.txt`
5. Run backend and serve the frontend together:
   - `cd backend && python -m uvicorn main:app --reload --port 8000`
6. Open `http://localhost:8000` in your browser

## API Endpoints
- `GET /health` — Server health
- `GET /medicines` — List medicines
- `GET /search?q=query` — Fuzzy search
- `GET /medicine?name=name` — Get medicine details

## Usage
- In the chat, type a medicine name to get details from backend
- For other questions, it uses OpenAI ChatGPT