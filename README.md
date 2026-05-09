# LERNR

A text-based practice companion for [Language Transfer's Complete Spanish](https://www.languagetransfer.org/complete-spanish) course.

Language Transfer teaches Spanish through the Socratic method — the teacher asks guiding questions and you pause to construct answers by thinking through patterns. LERNR extends that into a web app where you can drill questions from tracks you've completed, track your mastery across concepts, and get an AI tutor that guides you through your weak spots the same way.

---

## Features

- **Track browser** — mark the 90 LT tracks as completed as you work through the course
- **Practice mode** — quiz questions pulled from your completed tracks, weighted toward concepts you're weakest on
- **Progress dashboard** — per-concept accuracy, overall stats, weak spot identification
- **Socratic AI tutor** — COMING SOON:LangGraph-powered agent that guides you to answers through questions, never by just telling you

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| AI Agent | LangGraph + Claude (Anthropic) |
| Auth | JWT |

---

## Project structure

```
lernr/
├── data/
│   ├── transcripts/     # Raw LT transcript text files
│   └── parsed/          # Structured Q&A JSON per track
├── scripts/
│   ├── categorize.py    # LLM-based Q&A extraction and concept tagging
│   └── seed_db.py       # Seed the database from parsed JSON
├── backend/             # FastAPI app
│   └── app/
│       ├── auth/
│       ├── tracks/
│       ├── progress/
│       ├── quiz/
│       └── agent/
└── frontend/            # Vue 3 app (coming soon)
```

---

## Local setup

### Prerequisites

- Python 3.9+
- PostgreSQL
- Node.js 18+ (for frontend)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```
DATABASE_URL=postgresql://user:password@localhost:5432/lernr
JWT_SECRET=your-secret-here
ANTHROPIC_API_KEY=your-key-here
```

Run migrations and seed the database:

```bash
alembic upgrade head
python ../scripts/seed_db.py
```

Start the server:

```bash
uvicorn app.main:app --reload
```

API docs available at `http://localhost:8000/docs`.

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Data pipeline (transcript parsing + seeding) | ✅ Done |
| 1 | Backend API | ✅ Done |
| 2 | Frontend (Vue) | 🔨 In progress |
| 3 | AI Socratic tutor (LangGraph) | 🔜 Planned |
| 4 | Deployment (AWS ECS + RDS) | 🔜 Planned |

---

## License

MIT
