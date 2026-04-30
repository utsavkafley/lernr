import argparse
import json
import re
import time
from pathlib import Path

import anthropic

TRANSCRIPTS_DIR = Path("data/transcripts/spanish")
RAW_CONCEPTS_CACHE = Path("data/raw_concepts.json")

EXTRACTION_PROMPT = """You are analyzing a Language Transfer Complete Spanish transcript.

List only the Spanish language concepts that are actively practiced in this transcript — meaning the student constructs Spanish answers for them. Do not list concepts that are only explained without practice.

Use short descriptive names. Examples: "conditional tense", "reflexive verbs", "direct object pronouns", "cognate conversion: -tion → -ción"

Return JSON only: {"concepts": ["...", "..."]}"""


def get_track_concepts(client, track_num, text):
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": EXTRACTION_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": f"Track {track_num}:\n\n{text}"}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw).get("concepts", [])


def consolidate(client, all_concepts):
    # Case-insensitive dedup before sending to reduce input size
    seen = set()
    unique = []
    for c in sorted(all_concepts):
        if c.lower() not in seen:
            seen.add(c.lower())
            unique.append(c)

    concepts_text = "\n".join(f"- {c}" for c in unique)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": f"""These are raw concept names collected from 89 tracks of a Spanish language course (Language Transfer Complete Spanish).

Normalize and deduplicate them into a clean canonical taxonomy. Rules:
- Merge near-duplicates into one name ("using the conditional", "conditional tense", "would constructions" → "Conditional tense")
- Consistent formatting: title case for grammar terms, → for conversion rules
- Specific enough to be useful for progress tracking — not so broad as to be meaningless
- Order roughly by when concepts first appear in the course (early tracks first)
- Return ONLY the final list, no explanations

Raw concepts:
{concepts_text}

Return JSON only: {{"taxonomy": ["Concept name", ...]}}""",
            }
        ],
    )

    if response.stop_reason == "max_tokens":
        print("WARNING: consolidation response was truncated — try reducing the concept list")

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw).get("taxonomy", [])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--consolidate-only", action="store_true",
                        help="Skip extraction, load cached concepts and re-run consolidation")
    args = parser.parse_args()

    client = anthropic.Anthropic()

    if args.consolidate_only:
        if not RAW_CONCEPTS_CACHE.exists():
            print("No cache found. Run without --consolidate-only first.")
            return
        all_concepts = json.loads(RAW_CONCEPTS_CACHE.read_text())
        print(f"Loaded {len(all_concepts)} cached concept mentions.")
    else:
        files = sorted(TRANSCRIPTS_DIR.glob("track_*.txt"))
        all_concepts = []

        for txt_file in files:
            m = re.search(r"track_(\d+)", txt_file.name)
            if not m:
                continue
            num = int(m.group(1))
            if num == 1:
                continue

            print(f"Track {num:02d}...", end=" ", flush=True)
            text = txt_file.read_text(encoding="utf-8")

            try:
                concepts = get_track_concepts(client, num, text)
                all_concepts.extend(concepts)
                preview = ", ".join(concepts[:3]) + ("..." if len(concepts) > 3 else "")
                print(preview)
                time.sleep(0.3)
            except Exception as e:
                print(f"ERROR: {e}")

        RAW_CONCEPTS_CACHE.write_text(json.dumps(all_concepts, ensure_ascii=False))
        print(f"\nCollected {len(all_concepts)} raw concept mentions. Saved to {RAW_CONCEPTS_CACHE}")

    print("Consolidating into canonical taxonomy...\n")
    taxonomy = consolidate(client, all_concepts)

    print("CONCEPT_TAXONOMY = [")
    for concept in taxonomy:
        print(f'    "{concept}",')
    print("]")


if __name__ == "__main__":
    main()