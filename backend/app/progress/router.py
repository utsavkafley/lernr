from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import (
    Attempt, Concept, Question, QuestionConcept,
    Track, User, UserTrackProgress
)
from app.schemas import ConceptStatsResponse, ProgressSummaryResponse

router = APIRouter(prefix="/progress", tags=["progress"])


def _get_or_404(db: Session, number: int) -> Track:
    track = db.execute(select(Track).where(Track.number == number)).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail = "Track not found")
    return track


@router.post("/tracks/{number}/complete", status_code=204)
def mark_coomplete(
    number: int,
    db: Session  = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    track = _get_or_404(db, number)
    progress = db.execute(
        select(UserTrackProgress).where(
            UserTrackProgress.user_id == current_user.id,
            UserTrackProgress.track_id == track.id,
        )
    ).scalar_one_or_none()

    if not progress:
        progress = UserTrackProgress(
            user_id=current_user.id,
            track_id=track.id
        )
        db.add(progress)

    progress.completed = True
    progress.completed_at = datetime.now(timezone.utc)
    db.commit()


@router.delete("/tracks/{number}/complete", status_code=204)
def unmark_complete(
    number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    track = _get_or_404(db, number)
    progress = db.execute(
        select(UserTrackProgress).where(
            UserTrackProgress.user_id == current_user.id,
            UserTrackProgress.track_id == track.id,
        )
    ).scalar_one_or_none()

    if progress:
        progress.completed = False
        progress.competed_at = None
        db.commit()


def _concept_stats(user_id, db: Session) -> list[ConceptStatsResponse]:
    rows = db.execute(
        select(
            Concept.id,
            Concept.name,
            func.count(Attempt.id).label("total"),
            func.count(Attempt.id).filter(
                Attempt.evaluation_state.in_(["correct", "acceptable"])
            ).label("correct"),
        )
        .join(QuestionConcept, QuestionConcept.concept_id == Concept.id)
        .join(Attempt, Attempt.question_id == QuestionConcept.question_id)
        .where(Attempt.user_id == user_id)
        .group_by(Concept.id, Concept.name)
    ).all()

    return [
        ConceptStatsResponse(
            concept_id=r.id,
            name=r.name,
            total_attempts=r.total,
            correct_attempts=r.correct or 0,
            accuracy=round((r.correct or 0) / r.total, 2) if r.total else 0.0,
        )
        for r in rows
    ]


@router.get("/summary", response_model=ProgressSummaryResponse)
def summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_tracks = db.execute(select(func.count(Track.id))).scalar()

    tracks_completed = db.execute(
        select(func.count(UserTrackProgress.id)).where(
            UserTrackProgress.user_id == current_user.id,
            UserTrackProgress.completed == True
        )
    ).scalar()

    total_attempts = db.execute(
        select(func.count(Attempt.id)).where(
            Attempt.user_id == current_user.id,
        )
    ).scalar()

    correct_attempts = db.execute(
        select(func.count(Attempt.id)).where(
            Attempt.user_id == current_user.id,
            Attempt.evaluation_state.in_(["correct", "acceptable"])
        )
    ).scalar()

    concept_stats = _concept_stats(current_user.id, db)

    return ProgressSummaryResponse(
        tracks_completed=tracks_completed,
        total_tracks=total_tracks,
        total_attempts=total_attempts,
        overall_accuracy=round(correct_attempts / total_attempts, 2) if total_attempts else 0.00,
        concept_stats=concept_stats
    )


@router.get("/concepts", response_model=list[ConceptStatsResponse])
def concepts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _concept_stats(current_user.id, db)


@router.get("/weak-concepts", response_model=list[ConceptStatsResponse])
def weak_concepts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.config import settings
    stats = _concept_stats(current_user.id, db)
    weak = [s for s in stats if s.accuracy < settings.mastery_threshold]
    return sorted(weak, key=lambda s: s.accuracy)


