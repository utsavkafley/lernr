import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from app.database import SessionLocal
from app.models import Concept, Question, QuestionConcept, Track

PARSED_DIR = Path("data/parsed/spanish")

def load_tracks():
    return [
        json.loads(f.read_text())
        for f in sorted(PARSED_DIR.glob("track_*.json"))
    ]


def upsert_track(session, number):
    track = session.execute(
        select(Track).where(Track.number == number)
    ).scalar_one_or_none()
    if not track:
        track = Track(number=number, title=f"Track {number:02d}")
        session.add(track)
        session.flush()
    return track


def upsert_concept(session, name, first_track_number):
    concept = session.execute(
        select(Concept).where(Concept.name == name)
    ).scalar_one_or_none()
    if not concept:
        concept = Concept(name=name, first_track=first_track_number)
        session.add(concept)
        session.flush()
    return concept


def upsert_question(session, track_id, order, prompt, answer, alternate_answers):
    question = session.execute(
        select(Question).where(
            Question.track_id == track_id,
            Question.order_in_track == order,
        )
    ).scalar_one_or_none()
    if not question:
        question = Question(
            track_id=track_id,
            order_in_track=order,
            prompt=prompt,
            answer=answer,
            alternate_answers=alternate_answers or []
        )
        session.add(question)
    else:
        question.prompt = prompt
        question.answer = answer
        question.alternate_answers = alternate_answers or []
    session.flush()
    return question

def main():
    all_tracks = load_tracks()

    # Determine first_track per concept acorss all fields
    concept_first_track = {}
    for track_data in all_tracks:
        num = track_data["track_number"]
        for q in track_data.get("questions", []):
            for name in q.get("concepts", []):
                if name not in concept_first_track:
                    concept_first_track[name] = num
    
    session = SessionLocal()
    try:
        # Tracks
        print("Seeding tracks...", end=" ")
        track_map = {}
        for track_data in all_tracks:
            num = track_data["track_number"]
            track_map[num] = upsert_track(session, num)
        session.commit()
        print(f"{len(track_map)} tracks")

        # Concepts
        print("Seeding concepts...", end=" ")
        concept_map = {}
        for name, first_num in concept_first_track.items():
            concept_map[name] = upsert_concept(session, name, first_num)
        session.commit()
        print(f"{len(concept_map)} concepts")

        # Questions + concept links
        print("Seeding questions...", end= " ")
        total = 0
        skipped_concepts = set()

        for track_data in all_tracks:
            track = track_map[track_data["track_number"]]
            for q in track_data.get("questions", []):
                question = upsert_question(
                    session,
                    track_id=track.id,
                    order=q["order"],
                    prompt=q["prompt"],
                    answer=q["answer"],
                    alternate_answers=q.get("alternate_answers", []),
                )
                # Delete and re-create concept links so re-runs stay clean
                session.query(QuestionConcept).filter_by(
                    question_id=question.id
                ).delete()
                for name in q.get("concepts", []):
                    if name in concept_map:
                        session.add(
                            QuestionConcept(
                                question_id=question.id,
                                concept_id=concept_map[name].id
                            )
                        )
                    else:
                        skipped_concepts.add(name)
                total += 1

        session.commit()
        print(f"{total} questions")

        if skipped_concepts:
            print("\n⚠ Concepts in JSON not found in DB — run categorize.py first:")

            for name in sorted(skipped_concepts):
                print(f" {name}")
        
        print("\nDone.")
    
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
