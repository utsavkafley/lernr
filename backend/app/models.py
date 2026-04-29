import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    track_progress = relationship("UserTrackProgress", back_populates="user")
    attempts = relationship("Attempt", back_populates="user")


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)
    number = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    questions = relationship("Question", back_populates="track")
    user_progress = relationship("UserTrackProgress", back_populates="track")


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    first_track = Column(Integer, ForeignKey("tracks.number"), nullable=True)

    question_concepts = relationship("QuestionConcept", back_populates="concept")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    alternate_answers = Column(ARRAY(Text), nullable=False, default=list)
    order_in_track = Column(Integer, nullable=False)

    track = relationship("Track", back_populates="questions")
    question_concepts = relationship("QuestionConcept", back_populates="question")
    attempts = relationship("Attempt", back_populates="question")


class QuestionConcept(Base):
    __tablename__ = "question_concepts"

    question_id = Column(Integer, ForeignKey("questions.id"), primary_key=True)
    concept_id = Column(Integer, ForeignKey("concepts.id"), primary_key=True)

    question = relationship("Question", back_populates="question_concepts")
    concept = relationship("Concept", back_populates="question_concepts")


class UserTrackProgress(Base):
    __tablename__ = "user_track_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "track_id"),)

    user = relationship("User", back_populates="track_progress")
    track = relationship("Track", back_populates="user_progress")

class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(Text, nullable=False)
    evaluation_state = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda:
    datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="attempts")
    question = relationship("Question", back_populates="attempts")
