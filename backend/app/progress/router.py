from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.concepts import concept_stats
from app.database import get_db
from app.models import Attempt, Track, User, UserTrackProgress
from app.schemas import ConceptStatsResponse, ProgressSummaryResponse

router = APIRouter(prefix="/progress", tags=["progress"])


def _get_or_404(db: Session, number: int) -> Track:
    track = db.execute(select(Track).where(Track.number == number)).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail = "Track not found")
    return track


@router.post("/tracks/{number}/complete", status_code=204)
def mark_complete(
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
        progress.completed_at = None
        db.commit()


def _concept_stats(user_id, db: Session) -> list[ConceptStatsResponse]:
    return [
        ConceptStatsResponse(
            concept_id=s.concept_id,
            name=s.name,
            total_attempts=s.total_attempts,
            correct_attempts=s.correct_attempts,
            quiz_accuracy=s.quiz_accuracy,
            chat_score=s.chat_score,
            blended=s.blended,
            mastered=s.mastered,
        )
        for s in concept_stats(user_id, db)
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
    stats = _concept_stats(current_user.id, db)
    weak = [s for s in stats if not s.mastered]
    return sorted(weak, key=lambda s: s.blended)


