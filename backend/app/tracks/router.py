from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.concepts import completed_track_ids
from app.database import get_db
from app.models import Question, QuestionConcept, Track, User
from app.schemas import TrackDetailResponse, TrackResponse

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackResponse])
def list_tracks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tracks = db.execute(select(Track).order_by(Track.number)).scalars().all()
    completed = set(completed_track_ids(current_user.id, db))
    result = []
    for track in tracks:
        t = TrackResponse.model_validate(track)
        t.completed = track.id in completed
        result.append(t)
    return result


@router.get("/{number}", response_model=TrackDetailResponse)
def get_track(
    number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    track = db.execute(
        select(Track)
        .where(Track.number == number)
        .options(
            selectinload(Track.questions).selectinload(Question.question_concepts)
                .selectinload(QuestionConcept.concept)
        )
    ).scalar_one_or_none()

    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    completed = set(completed_track_ids(current_user.id, db))
    result = TrackDetailResponse.model_validate(track)
    result.completed = track.id in completed
    return result


