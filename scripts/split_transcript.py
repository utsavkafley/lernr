import re
import pdfplumber
from pathlib import Path

PDF_PATH = Path("data/transcripts/Spanish_Transcript_All_Tracks.pdf")
OUT_DIR = Path("data/transcripts/spanish")

def split():
    tracks = {}
    current_track = None

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.splitlines():
                m = re.match(r'^Track (\d+)$', line.strip())
                if m:
                    num = int(m.group(1))

                    current_track = num
                    if num not in tracks:
                        tracks[num] = []
                elif current_track is not None:
                    tracks[current_track].append(line)
    
    for num, lines in tracks.items():
        filename = OUT_DIR / f"track_{num:02d}.txt"
        filename.write_text("\n".join(lines), encoding="utf-8")
        print(f"Wrote {filename} ({len(lines)} lines)")

    print(f"\Done. {len(tracks)} tracks written.")

if __name__ == "__main__":
    split()