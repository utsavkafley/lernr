# LERNR — Technical Specification

A text-based companion app for Language Transfer's Complete Spanish course. LERNR parses LT transcripts into structured Q&A data, tracks user progress through the 90-track course, and provides an AI Socratic tutor that adapts practice sessions to the learner's weak spots.

---

## 1. Project overview

### What is Language Transfer?

Language Transfer (LT) is a free audio course that teaches languages using the Thinking Method — a Socratic approach where the teacher asks guiding questions and the student pauses to construct answers by thinking through patterns, not memorizing. Complete Spanish has 90 audio tracks (~10-15 minutes each) covering the full structural panorama of the language.

The transcripts follow a consistent format: the teacher poses a question (e.g., "How would you say 'I want to explain something to you'?"), there's a pause for the student to think, and then the student answers. The method emphasizes understanding *why* Spanish works the way it does, not rote memorization.

### What is LERNR?

LERNR is a web app that transforms LT's transcript content into an interactive, text-based practice tool. It:

1. **Parses** the 90 LT Spanish transcripts into structured Q&A pairs
2. **Categorizes** each question by the grammatical/linguistic concept it teaches
3. **Tracks** the user's progress — which tracks they've completed, which concepts they've mastered, where they struggle
4. **Quizzes** the user with questions from their completed tracks, weighted toward weak concepts
5. **Provides an AI tutor** that uses the Socratic method (mirroring LT's approach) to guide the user through concepts they're struggling with, rather than just giving answers

### Design philosophy

- **Text-first.** No audio playback — LT already does that. LERNR is for practice and reinforcement.
- **Iterative.** Each phase produces a usable product. Features are additive, not dependent.
- **Honest feedback.** Progress tracking shows real mastery, not gamified streaks. If you're weak on conditional tense, you see that clearly.
- **Socratic AI.** The tutor never gives the answer directly. It guides the user to construct it, the same way Mihalis does in the audio.

---

## 2. Architecture

### Tech stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Vue.js 3 + TypeScript + Vite | Matches resume stack; Composition API for clean state management |
| Backend | Python + FastAPI | Async-native, clean typing, pairs well with LangGraph |
| Database | PostgreSQL | Relational data with clear FK relationships; SQLAlchemy ORM |
| AI Agent | LangGraph (Python) | StateGraph for Socratic conversation flow; tool-calling for progress lookups |
| Auth | JWT (python-jose + passlib) | Stateless, simple, no session management needed |
| Deployment | Docker Compose (dev) → AWS ECS + RDS (prod) | Local parity with production; GitHub Actions CI/CD |

### Project structure

```
lernr/
├── README.md
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── data/
│   ├── transcripts/          # Raw LT transcript files (1 per track)
│   └── parsed/               # Output from parser: structured JSON
├── scripts/
│   ├── parse_transcripts.py  # Phase 0: transcript → structured Q&A JSON
│   ├── categorize.py         # Phase 0: LLM-based concept tagging
│   └── seed_db.py            # Phase 0: load parsed data into PostgreSQL
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── config.py         # Settings, env vars
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── auth/
│   │   │   ├── router.py     # /auth/register, /auth/login
│   │   │   ├── utils.py      # JWT creation, password hashing
│   │   │   └── dependencies.py  # get_current_user dependency
│   │   ├── tracks/
│   │   │   └── router.py     # /tracks, /tracks/{id}/questions
│   │   ├── progress/
│   │   │   └── router.py     # /progress, /progress/concepts
│   │   ├── quiz/
│   │   │   └── router.py     # /quiz/next, /quiz/submit
│   │   └── agent/
│   │       ├── router.py     # /agent/chat (SSE streaming)
│   │       ├── graph.py      # LangGraph StateGraph definition
│   │       └── tools.py      # Agent tools: get_progress, get_weak_concepts, etc.
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_tracks.py
│       ├── test_progress.py
│       ├── test_quiz.py
│       └── test_agent.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── router/
│       │   └── index.ts
│       ├── stores/
│       │   ├── auth.ts       # Pinia store for auth state
│       │   ├── tracks.ts     # Pinia store for track/progress data
│       │   └── quiz.ts       # Pinia store for quiz session state
│       ├── composables/
│       │   ├── useApi.ts     # Axios instance with JWT interceptor
│       │   └── useStream.ts  # SSE streaming composable for agent chat
│       ├── views/
│       │   ├── LoginView.vue
│       │   ├── TracksView.vue
│       │   ├── PracticeView.vue
│       │   ├── ProgressView.vue
│       │   └── TutorView.vue
│       ├── components/
│       │   ├── TrackCard.vue
│       │   ├── QuestionCard.vue
│       │   ├── ConceptBadge.vue
│       │   ├── ProgressChart.vue
│       │   └── ChatMessage.vue
│       └── styles/
│           └── main.css
└── docs/
    └── TECHNICAL_SPEC.md     # This document
```

---

## 3. Data model

### Entity relationship

```
users
  ├── user_track_progress (1:many)
  │     └── tracks (many:1)
  └── attempts (1:many)
        └── questions (many:1)
              ├── tracks (many:1)
              └── question_concepts (many:many)
                    └── concepts (many:1)
```

### Tables

#### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, default uuid4 |
| email | VARCHAR(255) | Unique, indexed |
| username | VARCHAR(100) | Optional display name; used by the AI tutor to address the user |
| password_hash | VARCHAR(255) | bcrypt |
| created_at | TIMESTAMP | Default now() |

#### `tracks`
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| number | INTEGER | 1-90, unique, indexed |
| title | VARCHAR(255) | e.g., "Track 01", "Track 45" |
| description | TEXT | Optional summary of what the track covers |

#### `concepts`
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| name | VARCHAR(255) | e.g., "Cognate conversion: -tion → -ción" |
| description | TEXT | Explanation of the concept |
| first_track | INTEGER | FK → tracks.number. The track where this concept is first introduced |

#### `questions`
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| track_id | INTEGER | FK → tracks.id |
| prompt | TEXT | The teacher's question, in English |
| answer | TEXT | The canonical expected Spanish answer |
| alternate_answers | TEXT[] | Additional accepted forms parsed from transcripts (e.g. "/" delimited variants) |
| order_in_track | INTEGER | Position within the track (1-indexed) |

#### `question_concepts` (join table)
| Column | Type | Notes |
|--------|------|-------|
| question_id | INTEGER | FK → questions.id |
| concept_id | INTEGER | FK → concepts.id |
| | | Composite PK (question_id, concept_id) |

#### `user_track_progress`
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| user_id | UUID | FK → users.id |
| track_id | INTEGER | FK → tracks.id |
| completed | BOOLEAN | Whether the user has listened to/completed this track |
| completed_at | TIMESTAMP | Nullable |
| | | Unique constraint on (user_id, track_id) |

#### `attempts`
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| user_id | UUID | FK → users.id |
| question_id | INTEGER | FK → questions.id |
| user_answer | TEXT | What the user typed |
| evaluation_state | VARCHAR(20) | `correct`, `acceptable`, or `incorrect` (see answer validation spec in §5.4) |
| created_at | TIMESTAMP | Default now(), indexed |
---

## 4. Phase 0 — Data pipeline

### 4.0 Database migrations (Alembic)

Set up Alembic before any other Phase 0 work. All schema changes must go through migration files — never hand-edit a live database.

```
backend/
├── alembic.ini
├── alembic/
│   ├── env.py          # Reads DATABASE_URL from config; uses SQLAlchemy metadata
│   └── versions/       # Auto-generated migration files
```

**Commands:**
- `alembic revision --autogenerate -m "initial schema"` — generate migration from models
- `alembic upgrade head` — apply all pending migrations
- `seed_db.py` always runs *after* `alembic upgrade head`

The Docker Compose backend entrypoint should run `alembic upgrade head` before starting uvicorn so dev and prod environments are always in sync.

### 4.1 Transcript parsing

The LT Spanish transcripts follow a conversational format. The parser needs to extract Q&A pairs from this structure.

**Input:** Raw transcript text files (one per track, stored in `data/transcripts/`)

**Expected transcript patterns to handle:**
```
Teacher: How would you say "I want"?
Student: Quiero.

Teacher: And how would you say "I want to explain"?
Student: Quiero explicar.

Teacher: Good. Now, how would you say "I want to explain something to you"?
Student: Quiero explicarte algo. / Quiero explicar algo a ti.
```

**Output:** Structured JSON per track (stored in `data/parsed/`):
```json
{
  "track_number": 15,
  "questions": [
    {
      "order": 1,
      "prompt": "How would you say \"I want\"?",
      "answer": "Quiero",
      "alternate_answers": []
    },
    {
      "order": 2,
      "prompt": "How would you say \"I want to explain\"?",
      "answer": "Quiero explicar",
      "alternate_answers": []
    },
    {
      "order": 3,
      "prompt": "How would you say \"I want to explain something to you\"?",
      "answer": "Quiero explicarte algo",
      "alternate_answers": ["Quiero explicar algo a ti"]
    }
  ]
}
```

**Parser script:** `scripts/parse_transcripts.py`
- Read each transcript file
- Use regex or structured parsing to identify Q&A pairs
- Handle multiple valid answers (separated by "/" in transcripts)
- Handle teacher explanations between questions (skip these, they're context not Q&A)
- Output clean JSON per track

**Note:** The exact transcript format may vary. The parser should be tolerant of inconsistencies — some tracks may have longer teacher explanations, some may have the student making mistakes before arriving at the correct answer. The parser should extract the *final correct answer* for each question.

**Validation report (`parse_transcripts.py --validate`):**

After parsing, the script must emit a validation report to stdout before exiting. Human review of this report is required before running `seed_db.py`. The report flags:

- Tracks where the extracted question count is below a minimum threshold (flag any track with fewer than 3 questions — likely a parse failure)
- Questions with empty `prompt` or `answer` fields
- Tracks that failed entirely (no questions extracted)
- Total questions per track (so you can spot outliers at a glance)

Example output:
```
Parse summary: 90 tracks, 1,247 questions total
  ⚠ Track 07: 1 question extracted (expected ≥3) — review manually
  ✗ Track 34: 0 questions extracted — parse failure
  OK 88 tracks passed
```

Do not proceed to `categorize.py` until all flagged tracks are resolved (either fixed in the parser or manually corrected in the JSON output).

### 4.2 Concept categorization

Use an LLM to batch-categorize questions into concept groups.

**Script:** `scripts/categorize.py`

**Approach:**
1. Load all parsed Q&A pairs
2. Send batches to the Anthropic API with a prompt like:

```
You are categorizing Spanish language learning questions by grammatical concept.

Given these Q&A pairs from a Spanish course, identify the primary concept(s) each question tests. Use consistent concept names from this taxonomy:

- Cognate conversion (-tion → -ción)
- Cognate conversion (-ly → -mente)
- Present tense: -ar verbs
- Present tense: -er/-ir verbs
- Irregular present tense
- Infinitive constructions (querer + infinitive)
- Reflexive verbs
- Object pronouns (direct)
- Object pronouns (indirect)
- Possessives
- Conditional tense
- Past tense (preterite)
- Past tense (imperfect)
- Subjunctive
- Ser vs estar
- Por vs para
- Prepositions
- Question formation
- Negation
- [Add more as patterns emerge]

For each question, return the concept name(s). If a question tests a concept not in the list, create a new descriptive name for it.

Return JSON only.
```

3. The LLM returns concept tags per question
4. Validate all returned concept names against the canonical taxonomy list (step 2). Any name not in the list is flagged for human review — the script does **not** silently create new concepts.
5. Write back to the parsed JSON files with concept tags added

**Taxonomy governance:** The taxonomy list in the prompt is the canonical source of truth. It is hardcoded in `scripts/categorize.py` as a Python list constant (`CONCEPT_TAXONOMY`). To add a new concept, a developer must edit that constant and re-run categorization for affected tracks. The LLM must never invent concept names autonomously — if a question genuinely tests an unlisted concept, the script logs it and a human decides whether to extend the taxonomy.

**Seeding concepts:** `seed_db.py` upserts concepts by exact `name` string. Concept names are treated as stable identifiers — renaming one requires a data migration, not just an edit to the constant.

**Output:** Updated JSON with concept tags:
```json
{
  "order": 3,
  "prompt": "How would you say \"I want to explain something to you\"?",
  "answer": "Quiero explicarte algo",
  "alternate_answers": ["Quiero explicar algo a ti"],
  "concepts": ["Infinitive constructions", "Object pronouns (indirect)"]
}
```

### 4.3 Database seeding

**Script:** `scripts/seed_db.py`
- Read all parsed + categorized JSON files
- Create track records (1-90)
- Create concept records (deduplicated from all questions)
- Create question records with FK to track
- Create question_concept join records
- Idempotent — can be re-run safely (upsert logic)

---

## 5. Phase 1 — Backend API

### 5.0 Cross-cutting concerns (wire up on Day 1)

**CORS (`main.py`):**
FastAPI does not enable CORS by default. The frontend origin must be explicitly allowlisted, and SSE endpoints require it.

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,   # e.g. ["http://localhost:3000"] in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`CORS_ORIGINS` is an env var (comma-separated list). In production this is the CloudFront distribution URL.

**Rate limiting:**
Use `slowapi` (FastAPI-native). Apply limits to all mutating and expensive endpoints — not just auth:

| Endpoint | Limit |
|----------|-------|
| `POST /auth/register` | 5/minute per IP |
| `POST /auth/login` | 10/minute per IP |
| `POST /quiz/submit` | 60/minute per user |
| `POST /agent/chat` | 20/minute per user |

**JWT security note:**
Tokens are stored in `localStorage` on the frontend (XSS-accessible). This is an accepted MVP tradeoff — document it in the README as a known limitation. The mitigation for a future hardening pass is HttpOnly cookies + CSRF tokens. Do not silently deploy to production without this note visible.

### 5.1 Auth endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create user account. Body: `{ email, password, username? }`. Returns JWT. |
| POST | `/auth/login` | Authenticate. Body: `{ email, password }`. Returns JWT. |
| GET | `/auth/me` | Get current user info. Requires JWT. |

JWT tokens should have a reasonable expiry (e.g., 7 days). Use `python-jose` for encoding/decoding, `passlib[bcrypt]` for password hashing.

### 5.2 Track endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tracks` | List all 90 tracks with user's completion status. Requires JWT. |
| GET | `/tracks/{number}` | Get track details + all questions for that track. |
| GET | `/tracks/{number}/questions` | Get just the questions for a track. |

### 5.3 Progress endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/progress/tracks/{number}/complete` | Mark a track as completed. |
| DELETE | `/progress/tracks/{number}/complete` | Unmark a track as completed. |
| GET | `/progress/summary` | Overall progress: tracks completed, concept accuracy breakdown. |
| GET | `/progress/concepts` | Per-concept accuracy stats (total attempts, correct, accuracy %). |
| GET | `/progress/weak-concepts` | Concepts below `MASTERY_THRESHOLD` (70%), sorted by accuracy ascending. |

### 5.4 Quiz endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/quiz/next` | Get the next question to practice. Weighted toward weak concepts from completed tracks only. |
| POST | `/quiz/submit` | Submit an answer. Body: `{ question_id, user_answer }`. Returns `{ evaluation_state, feedback, expected_answer }`. |

**Answer validation — 3-state result:**

Every quiz submission returns one of three states:

| State | Meaning | Stored as |
|-------|---------|-----------|
| `correct` | Exact match (after normalization) or matches an alternate answer | `correct` |
| `acceptable` | Minor surface error only — missing accent, trivial typo that doesn't change meaning | `acceptable` |
| `incorrect` | Wrong word, wrong tense, wrong structure, or missing key element | `incorrect` |

Progress calculations: `correct` and `acceptable` both count as passing when computing per-concept accuracy. The frontend should visually distinguish them ("✓ Correct" vs "~ Close — watch your accents").

**Validation pipeline (applied in order, stop at first match):**

1. **Normalization:** Lowercase, collapse whitespace, strip leading/trailing punctuation. Apply to user answer and all canonical answers (primary + alternates).
2. **Exact match:** Normalized user answer == any normalized canonical answer → `correct`.
3. **Accent-only difference:** Strip all diacritics from both sides, re-check exact match → `acceptable` (log which accents were missing for the feedback message).
4. **LLM evaluation fallback:** If steps 1–3 produce no match, call Claude Haiku with a structured prompt:

```
You are evaluating a Spanish language learning answer.
Question: {prompt}
Expected answer: {answer}
Alternate accepted answers: {alternate_answers}
Student's answer: {user_answer}

Is the student's answer:
- "correct": semantically equivalent and grammatically correct
- "acceptable": minor surface error only (missing accent, trivial spelling mistake that doesn't change meaning)
- "incorrect": wrong word, wrong tense, wrong structure, or missing a required element

Return JSON only: {"state": "correct"|"acceptable"|"incorrect", "feedback": "<one sentence explaining the result>"}
```

The `feedback` field from the LLM is returned to the frontend alongside the state and shown to the user. For exact/accent matches, generate the feedback string locally (no LLM call needed).

> **Why Haiku, not string matching alone:** Spanish allows significant surface variation in valid answers (pronoun clitic placement, object pronoun ordering). Levenshtein distance ≤ 2 will incorrectly accept "quiero" vs "quiera" (edit distance 1, different tense) — this is a correctness failure, not a typo. The LLM call is ~50ms and inexpensive at Haiku pricing.

**Question selection algorithm:**

Constants (defined in `backend/app/config.py`, not scattered inline):
- `MASTERY_THRESHOLD = 0.70` — concepts below this accuracy are considered weak
- `RECENT_ATTEMPT_WINDOW = 10` — how many recent attempts to exclude from "already seen"
- `MIN_POOL_SIZE = 3` — minimum question pool size before relaxing filters

Steps (applied in order):

1. Filter to questions from the user's completed tracks only.
2. Calculate per-concept accuracy from the user's attempt history. Accuracy = (`correct` + `acceptable` attempts) / total attempts for that concept.
3. Weight concepts inversely by accuracy (weaker concepts get more questions). Concepts with no attempt history are treated as 0% accuracy (highest priority).
4. Within the selected concept, filter out questions answered correctly in the last `RECENT_ATTEMPT_WINDOW` attempts.
5. **Pool size guard:** If the filtered pool has fewer than `MIN_POOL_SIZE` questions, relax the recency filter entirely (show any question from the concept). If the pool is still empty (the concept only has 1 question in completed tracks), fall back to the next weakest concept.
6. Pick randomly from the remaining pool (do not always pick the same question for a given concept).
7. **New user fallback:** If the user has no attempt history at all, serve questions sequentially from their earliest completed track (no weighting needed yet).

### 5.5 Agent endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent/chat` | Start or continue a Socratic tutoring session. Body: `{ message, session_id? }`. Returns SSE stream. |

Detailed in Phase 3 (Section 7).

---

## 6. Phase 2 — Frontend

### 6.1 Views

**Login / Register (`LoginView.vue`)**
- Simple email + password form
- Toggle between login and register modes
- Store JWT in localStorage, redirect to tracks on success

**Track Browser (`TracksView.vue`)**
- Grid or list of all 90 tracks
- Each track shows: number, title, completion status (checkbox or toggle)
- Clicking a track's completion toggle calls `POST /progress/tracks/{number}/complete`
- Visual distinction between completed and uncompleted tracks
- Optional: group tracks by concept cluster or show which concepts each track introduces

**Practice Mode (`PracticeView.vue`)**
- The core learning loop
- Shows one question at a time from `GET /quiz/next`
- Displays the prompt (in English)
- Text input for the user's Spanish answer
- On submit: calls `POST /quiz/submit`, shows result (correct/incorrect + expected answer)
- Shows the concept(s) being tested as small badges
- "Next" button to load the next question
- Running session stats: questions answered, accuracy this session

**Progress Dashboard (`ProgressView.vue`)**
- Overall stats: total tracks completed (X/90), total questions practiced, overall accuracy
- Concept mastery breakdown: list of concepts with accuracy percentages
- Visual indicators: green (≥80%), yellow (50-79%), red (<50%)
- Weak spots section: concepts that need the most work, sorted by accuracy ascending

**Socratic Tutor (`TutorView.vue`)**
- Chat interface for interacting with the AI tutor
- Messages stream in via SSE
- The tutor starts by identifying a weak concept and begins a Socratic dialogue
- User types responses, the tutor guides them through the pattern
- Conversation history persisted in component state (not in DB for MVP)

### 6.2 State management (Pinia)

**`auth` store:** JWT token, user info, login/logout actions

**`tracks` store:** Track list, completion statuses, actions for toggling completion

**`quiz` store:** Current question, session stats (questions answered, correct count), submit action

### 6.3 API layer

**`useApi.ts` composable:**
- Axios instance with `baseURL` pointing to the backend
- Request interceptor that attaches the JWT from the auth store
- Response interceptor that handles 401s (redirect to login)

**`useStream.ts` composable:**
- Wraps `EventSource` or `fetch` with SSE parsing for the agent chat endpoint
- Exposes reactive `messages` array and `isStreaming` boolean
- Handles reconnection and error states

### 6.4 Design direction

- Clean, minimal UI — no gamification, no mascots
- Responsive but desktop-first (this is a study tool, most users will be at a desk)
- Typography-forward: clear hierarchy, readable at a glance
- Color coding for concept mastery (green/yellow/red) should be the main visual accent

---

## 7. Phase 3 — AI Socratic tutor

### 7.0 State persistence (critical — configure before building the graph)

LangGraph's default checkpointer is **in-memory**, which means conversation state is lost on server restart and cannot be shared across multiple ECS instances. Use `langgraph-checkpoint-postgres` from the start:

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def create_graph():
    async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
        await checkpointer.setup()   # Creates checkpoint tables if they don't exist
        graph = workflow.compile(checkpointer=checkpointer)
        return graph
```

The checkpointer uses the same PostgreSQL database as the rest of the app. Alembic does **not** manage the checkpoint tables — `checkpointer.setup()` handles that. This means conversation history is automatically persisted across sessions for free, so "conversation history not persisted in DB for MVP" is no longer a limitation.

### 7.1 Agent design

The agent is a LangGraph `StateGraph` that manages a Socratic tutoring conversation. It mirrors the Language Transfer method: guide the student to construct the answer through a series of smaller questions, never give the answer directly.

**State schema:**
```python
class TutorState(TypedDict):
    messages: list          # Conversation history
    target_concept: str     # The concept being practiced
    target_question: dict   # The full Q&A pair being worked toward
    hint_level: int         # 0 = no hints, 1 = gentle nudge, 2 = strong hint, 3 = reveal
    user_id: str            # For progress lookups
```

**Graph nodes:**

1. **`select_concept`** — Entry node. Calls `get_weak_concepts` tool to find the user's weakest concept. Picks a question from that concept. Sets `target_question` in state.

2. **`ask_question`** — Formulates a Socratic question. If `hint_level` is 0, asks the full question. If higher, breaks it into smaller steps.

3. **`evaluate_response`** — Evaluates the user's answer against the expected answer. Branches:
   - Correct → go to `reinforce` (praise briefly, then ask a harder follow-up from the same concept)
   - Incorrect → increment `hint_level`, go to `give_hint`
   - Close but not exact → acknowledge what's right, point out what's off, stay at same `hint_level`

4. **`give_hint`** — Provides a hint calibrated to `hint_level`:
   - Level 1: Remind them of the relevant pattern ("Remember, for -ar verbs in the conditional, what ending do we add to the infinitive?")
   - Level 2: Give a simpler example first ("Let's start simpler. How do you say 'to speak'?")
   - Level 3: Reveal the answer and explain the pattern, then move to a new question on the same concept

5. **`reinforce`** — The user got it right. Ask a follow-up that tests the same concept at the same or slightly harder difficulty. If they've gotten 3+ correct in a row on this concept, switch to a new weak concept.

**Edges:**
```
select_concept → ask_question
ask_question → (wait for user input)
evaluate_response → reinforce (if correct)
evaluate_response → give_hint (if incorrect)
give_hint → ask_question (loop back with hint context)
reinforce → ask_question (new question, same or new concept)
```

### 7.2 Agent tools

```python
@tool
def get_weak_concepts(user_id: str) -> list[dict]:
    """Returns the user's weakest concepts, sorted by accuracy ascending.
    Each entry has: concept_name, accuracy_pct, total_attempts."""

@tool
def get_concept_questions(concept_name: str, user_id: str) -> list[dict]:
    """Returns questions for a given concept from the user's completed tracks.
    Excludes questions answered correctly in the last 5 attempts."""

@tool
def get_user_progress(user_id: str) -> dict:
    """Returns overall progress summary: tracks_completed, total_attempts,
    overall_accuracy, concepts_mastered, concepts_struggling."""

@tool
def record_attempt(user_id: str, question_id: int, evaluation_state: str) -> None:
    """Records a practice attempt from the tutoring session.
    evaluation_state must be 'correct', 'acceptable', or 'incorrect'."""
```

### 7.3 System prompt for the agent

```
You are a Spanish language tutor that uses the Socratic method — the same approach
used by Language Transfer's Thinking Method. Your role is to guide the student to
construct Spanish sentences by thinking through patterns, never by memorizing.

Core principles:
- NEVER give the answer directly. Ask guiding questions that lead the student to it.
- Build on what the student already knows. Start from simpler forms and build up.
- When the student makes a mistake, don't say "wrong." Ask a question that helps
  them see why their answer doesn't work.
- Keep responses short and focused. One question at a time.
- Celebrate when they get it right, briefly, then move on.
- Use the student's progress data to focus on concepts they struggle with.

You have tools to look up the student's progress, find questions they need practice
on, and record their attempts. Use them to personalize the session.

When starting a session, identify a weak concept and begin with a question from that
concept area. If the student is new with no attempt history, start with early-track
concepts.

Speak in English when explaining or asking questions. The student's answers will be
in Spanish. You may use Spanish words when demonstrating patterns.
```

### 7.4 Streaming integration and session lifecycle

**Session lifecycle:**

| Step | Who | How |
|------|-----|-----|
| Start a new session | Frontend | Sends `POST /agent/chat` with no `session_id`. Backend generates a UUID, returns it in the first SSE event as `{ "type": "session_start", "session_id": "<uuid>" }`. Frontend stores this in the `quiz` Pinia store. |
| Continue a session | Frontend | Sends `POST /agent/chat` with the stored `session_id`. Backend resumes the LangGraph thread from the checkpointed state. |
| Session expiry | N/A | Sessions do not expire automatically — the checkpointer retains state indefinitely. Users can always resume a previous conversation. |
| New session | Frontend | User clicks "New Session" — frontend clears the stored `session_id` and sends the next request without one. |

The `thread_id` passed to LangGraph is `f"{user.id}:{session_id}"` — namespaced by user so one user can never resume another's session even if they guess the UUID.

**SSE implementation:**

```python
@router.post("/agent/chat")
async def chat(request: ChatRequest, user: User = Depends(get_current_user)):
    session_id = request.session_id or str(uuid4())
    thread_id = f"{user.id}:{session_id}"

    async def event_generator():
        if not request.session_id:
            # Signal the frontend to save the new session ID
            yield f"data: {json.dumps({'type': 'session_start', 'session_id': session_id})}\n\n"

        async for event in graph.astream(
            {"messages": request.messages, "user_id": str(user.id)},
            config={"configurable": {"thread_id": thread_id}}
        ):
            yield f"data: {json.dumps(event)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

The frontend's `useStream.ts` composable must handle three event types: `session_start`, regular content chunks, and the `[DONE]` sentinel.

---

## 8. Phase 4 — Polish and deployment

### 8.1 Docker Compose (local dev)

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: lernr
      POSTGRES_USER: lernr
      POSTGRES_PASSWORD: lernr_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://lernr:lernr_dev@db:5432/lernr
      JWT_SECRET: dev-secret-change-in-prod
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      CORS_ORIGINS: http://localhost:3000
    # Entrypoint runs migrations before starting the server:
    # alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000

volumes:
  pgdata:
```

### 8.2 CI/CD (GitHub Actions)

- On push to `main`: run backend tests (pytest), run frontend build (vite build), lint both
- On tag: build Docker images, push to ECR, deploy to ECS

### 8.3 Production deployment

- **AWS ECS** (Fargate) for backend container
- **AWS RDS** (PostgreSQL) for database
- **S3 + CloudFront** for frontend static assets
- **Nginx** as reverse proxy in the backend container
- Environment variables managed via AWS Secrets Manager

### 8.4 Polish checklist

- [ ] Responsive layout (mobile-friendly practice mode)
- [ ] Loading skeletons for async data
- [ ] Error boundaries and user-friendly error messages
- [ ] Input validation (frontend + backend)
- [ ] Rate limiting — already specced in §5.0; verify limits are tuned in prod
- [ ] Clean README with screenshots, setup instructions, architecture diagram
- [ ] README security note: document JWT-in-localStorage as a known MVP limitation; link to future hardening plan (HttpOnly cookies + CSRF)
- [ ] Audit `MASTERY_THRESHOLD`, `RECENT_ATTEMPT_WINDOW`, `MIN_POOL_SIZE` constants in `config.py` before prod — tune based on real usage data