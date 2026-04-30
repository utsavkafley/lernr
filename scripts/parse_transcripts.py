import json
import re
from pathlib import Path

TRANSCRIPTS_DIR = Path("data/transcripts/spanish")
PARSED_DIR = Path("data/parsed/spanish")
MIN_QUESTIONS = 3

def parse_turns(text):
    """Return list of [speaker, text] from raw transcript text.
    Lines without a speaker prefix are continuation of the previous turn."""
    turns = []
    for line in text.splitlines():
        teacher = re.match(r'^Teacher:\s*(.*)', line)
        student = re.match(r'^Student:\s*(.*)', line)
        if teacher:
            turns.append(['Teacher', teacher.group(1)])
        elif student:
            turns.append(['Student', student.group(1)])
        elif turns and line.strip():
            turns[-1][1] += ' ' + line.strip()
    return [(s, t.strip()) for s, t in turns]


def extract_qa(turns):
    """Extract Q&A pairs from parsed turns."""
    qa_pairs = []
    order = 1
    i = 0

    while i < len(turns):
        speaker, text = turns[i]

        if speaker == 'Teacher' and '?' in text:
            student_answers = []
            j = i + 1
            while j < len(turns):
                s, t = turns[j]
                if s == 'Teacher':
                    break
                if s == 'Student' and t:
                    student_answers.append(t)
                j += 1

            if student_answers:
                raw = student_answers[-1]
                parts = [p.strip().rstrip('.') for p in raw.split(' / ')]
                qa_pairs.append({
                    "order": order,
                    "prompt": text,
                    "answer": parts[0],
                    "alternate_answers": parts[1:],
                })
                order += 1
            
            i = j
        else:
            i += 1
    
    return qa_pairs


def parse_all():
    PARSED_DIR.mkdir(exist_ok=True)
    results = {}

    for txt_file in sorted(TRANSCRIPTS_DIR.glob("track_*.txt")):
        m = re.search(r'track_(\d+)', txt_file.name)
        if not m:
            continue
        num = int(m.group(1))
        if num == 1:
            continue

        text = txt_file.read_text(encoding="utf-8")
        turns = parse_turns(text)
        questions = extract_qa(turns)

        data = {"track_number": num, "questions": questions}
        out = PARSED_DIR / f"track_{num:02d}.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        results[num] = len(questions)

    return results

def print_report(results):
    total_q = sum(results.values())
    total_t = len(results)
    print(f"\n Parse summary: {total_t} tracks, {total_q:,} questions total")

    warnings = 0
    for num in sorted(results):
        count = results[num]
        if count == 0:
            print(f" ✗ Track {num:02d}: 0 questions - parse failure")
            warnings += 1
        elif count < MIN_QUESTIONS:
            print(f"  ⚠ Track {num:02d}: {count} question(s) (expected ≥{MIN_QUESTIONS}) — review manually")
            warnings += 1
    
    print(f" OK {total_t - warnings} tracks passed")


if __name__ == "__main__":
    results = parse_all()
    print_report(results)
