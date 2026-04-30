# LERNR — Technical Specification

A text-based companion app for Language Transfer's Complete Spanish course. Parses LT transcripts into structured Q&A data, tracks user progress through 90 tracks, and provides an AI Socratic tutor that adapts practice to weak spots.

---

## 1. Project overview

LERNR is a web app that transforms LT's transcript content into an interactive practice tool:

1. **Parses** the 90 LT Spanish transcripts into structured Q&A pairs
2. **Categorizes** each question by grammatical/linguistic concept
3. **Tracks** the user's progress — completed tracks, mastered concepts, weak spots
4. **Quizzes** the user with questions weighted toward weak concepts
5. **Provides an AI tutor** that uses the Socratic method to guide users through struggling concepts

**Design philosophy:** Text-first, iterative, honest feedback (real mastery not streaks), Socratic AI that never gives answers directly.

---

## 2. Architecture

### Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue.js 3 + TypeScript + Vite |
| Backend | Python + FastAPI |
| Database | PostgreSQL (SQLAlchemy ORM) |
| AI Agent | LangGraph (Python) |
| Auth | JWT (python-jose + passlib) |
| Deployment | Docker Compose (dev) → AWS ECS + RDS (prod) |

### Project structure

```
lernr/
├── data/
│   ├── transcripts/          # Raw LT transcript files
│   └── parsed/               # Structured JSON per track
├── scripts/
│   ├── parse_transcripts.py  # Transcript splitting (done)
│   ├── categorize.py         # LLM-based Q&A extraction + concept tagging (done)
│   └── seed_db.py            # Load parsed data into PostgreSQL (done)
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth/             # /auth/register, /auth/login, /auth/me
│   │   ├── tracks/           # /tracks, /tracks/{number}
│   │   ├── progress/         # /progress/summary, /progress/concepts
│   │   ├── quiz/             # /quiz/next, /quiz/submit
│   │   └── agent/            # /agent/chat (SSE) — Phase 3
│   └── tests/
└── frontend/                 # Phase 2
```

---

## 3. Data model

```
users
  ├── user_track_progress (1:many) → tracks
  └── attempts (1:many) → questions
        ├── tracks
        └── question_concepts (many:many) → concepts
```

| Table | Key columns |
|-------|------------|
| `users` | id (UUID), email, username, password_hash |
| `tracks` | id, number (1-90), title, description |
| `concepts` | id, name, description, first_track |
| `questions` | id, track_id, prompt, answer, alternate_answers (TEXT[]), order_in_track |
| `question_concepts` | question_id, concept_id (composite PK) |
| `user_track_progress` | user_id, track_id, completed, completed_at |
| `attempts` | id, user_id, question_id, user_answer, evaluation_state, created_at |

`evaluation_state`: `correct`, `acceptable`, or `incorrect`. Both `correct` and `acceptable` count as passing in accuracy calculations.

---

## 4. Phase 0 — Data pipeline ✅

- **`categorize.py`** — One Claude Sonnet call per track. Extracts clean Q&A pairs and tags concepts in a single pass. Validates all concept names against `CONCEPT_TAXONOMY` hardcoded in the script.
- **`seed_db.py`** — Idempotent upsert of 89 tracks, 331 concepts, 2171 questions.

---

## 5. Phase 1 — Backend API ✅

### Endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/auth/register` | — |
| POST | `/auth/login` | — |
| GET | `/auth/me` | JWT |
| GET | `/tracks` | JWT |
| GET | `/tracks/{number}` | JWT |
| POST | `/progress/tracks/{number}/complete` | JWT |
| DELETE | `/progress/tracks/{number}/complete` | JWT |
| GET | `/progress/summary` | JWT |
| GET | `/progress/concepts` | JWT |
| GET | `/progress/weak-concepts` | JWT |
| GET | `/quiz/next` | JWT |
| POST | `/quiz/submit` | JWT |

### Quiz constants (`config.py`)

| Constant | Default | Purpose |
|----------|---------|---------|
| `mastery_threshold` | 0.70 | Below this = weak concept |
| `recent_attempt_window` | 10 | Questions to exclude as "recently seen" |
| `min_pool_size` | 3 | Minimum pool before relaxing recency filter |

### Answer validation pipeline

1. Normalize (lowercase, strip whitespace)
2. Exact match → `correct`
3. Accent-strip both sides → match → `acceptable`
4. Claude Haiku fallback → `correct` / `acceptable` / `incorrect`

---

## 6. Phase 2 — Frontend

### Views

| View | Purpose |
|------|---------|
| `LoginView.vue` | Email/password, toggle register/login, JWT to localStorage |
| `TracksView.vue` | Grid of 90 tracks with completion toggles |
| `PracticeView.vue` | Quiz loop: question → answer input → result → next |
| `ProgressView.vue` | Overall stats + concept mastery breakdown (green/yellow/red) |
| `TutorView.vue` | SSE chat interface for Socratic tutor |

### State (Pinia stores)

- **`auth`** — JWT token, user info
- **`tracks`** — track list + completion statuses
- **`quiz`** — current question, session stats

### API layer

- **`useApi.ts`** — Axios instance with JWT interceptor, 401 → redirect to login
- **`useStream.ts`** — SSE composable for agent chat (reactive `messages`, `isStreaming`)

---

## 7. Phase 3 — AI Socratic tutor

LangGraph `StateGraph` with Postgres checkpointer (`langgraph-checkpoint-postgres`) for persistent conversation state across sessions.

### State

```python
class TutorState(TypedDict):
    messages: list
    target_concept: str
    target_question: dict
    hint_level: int          # 0–3; 3 = reveal answer
    user_id: str
```

### Graph nodes

1. **`select_concept`** — picks weakest concept via `get_weak_concepts` tool
2. **`ask_question`** — Socratic question, broken into sub-steps if hint_level > 0
3. **`evaluate_response`** — correct → `reinforce`, incorrect → `give_hint`
4. **`give_hint`** — calibrated to hint_level (nudge → simpler example → reveal)
5. **`reinforce`** — follow-up on same concept; after 3+ correct, switch concept

### Tools

- `get_weak_concepts(user_id)` — concepts sorted by accuracy ascending
- `get_concept_questions(concept_name, user_id)` — questions from completed tracks
- `get_user_progress(user_id)` — overall summary
- `record_attempt(user_id, question_id, evaluation_state)` — persist session attempts

### Endpoint

`POST /agent/chat` — SSE stream. `session_id` in body; generated on first call, stored by frontend. Thread ID namespaced as `{user_id}:{session_id}`.

---

## 8. Phase 4 — Deployment

- **Dev:** Docker Compose (postgres + backend + frontend). Backend entrypoint runs `alembic upgrade head` before uvicorn.
- **Prod:** AWS ECS (Fargate) + RDS (PostgreSQL) + S3/CloudFront (frontend). Secrets via AWS Secrets Manager.

### Checklist

- [ ] Rate limiting (slowapi): register 5/min, login 10/min, quiz submit 60/min, agent 20/min
- [ ] Responsive layout
- [ ] Error boundaries + user-friendly messages
- [ ] README with setup instructions + security note (JWT in localStorage = known MVP limitation)
- [ ] Tune `mastery_threshold`, `recent_attempt_window`, `min_pool_size` based on usage data
