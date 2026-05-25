from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


# --- Auth ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: Optional[str]

    class Config:
        from_attributes = True


# --- Tracks ---

class ConceptResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
    
class QuestionResponse(BaseModel):
    id: int
    order_in_track: int
    prompt: str
    answer: str
    alternate_answers: list[str]
    concepts: list[ConceptResponse]

    class Config:
        from_attributes = True

class TrackResponse(BaseModel):
    id: int
    number: int
    title: str
    description: Optional[str]
    completed: bool = False

    class Config:
        from_attributes = True

class TrackDetailResponse(TrackResponse):
    questions: list[QuestionResponse]


# --- Progress ---

class TrackCompleteRequest(BaseModel):
    pass

class ConceptStatsResponse(BaseModel):
    concept_id: int
    name: str
    total_attempts: int
    correct_attempts: int
    quiz_accuracy: float
    chat_score: float
    blended: float
    mastered: bool

class ProgressSummaryResponse(BaseModel):
    tracks_completed: int
    total_tracks: int
    total_attempts: int
    overall_accuracy: float
    concept_stats: list[ConceptStatsResponse]


# --- Quiz ---

class QuizQuestionResponse(BaseModel):
    question_id: int
    prompt: str
    concepts: list[ConceptResponse]

class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: str

class SubmitAnswerResponse(BaseModel):
    evaluation_state: str
    feedback: str
    expected_answer: str
    alternate_answers: list[str]

