\
#!/usr/bin/env python3
"""
    docx2mp3.py — Turn DOCX/TXT into an MP3 audiobook (per-chapter files + combined)
    using Microsoft Edge TTS (edge-tts), with clean chapter detection and robust chunking.

    ──────────────────────────────────────────────────────────────────────────────
    🔹 What this script does
      • Reads a .docx or .txt manuscript
      • Detects chapters from DOCX headings (Heading 1/2 / Otsikko 1/2)
        or heuristically from lines like "Luku", "Osa", "Chapter"
      • Splits chapter text into TTS-safe chunks (~2200 chars) with sentence-aware logic
      • Synthesizes each chunk to MP3 via edge-tts (text mode; no SSML needed)
      • Exports:
          - One MP3 per chapter with ID3 tags (album/artist/title)
          - One combined MP3 (all chapters with small gaps between)

    🔧 Requirements
      pip install edge-tts python-docx pydub tqdm
      FFmpeg must be installed and on your PATH (pydub uses it for MP3 I/O)

    💡 Examples
      doc2mp3.py book.docx --outdir out --album "My Audiobook" --author "Your Name"
      doc2mp3.py book.docx --voice fi-FI-SelmaNeural --rate -5 --volume +3
      doc2mp3.py notes.txt --no-per-chapter  # only export a single combined file

    Author: Harri J. Salomaa
    """

import asyncio
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from tqdm import tqdm
from pydub import AudioSegment

# ===============================
# Small helpers
# ===============================
def slugify(name: str) -> str:
    """Filesystem-safe chapter filename from a title."""
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    safe = re.sub(r"_+", "_", safe).strip("._")
    return safe or "chapter"

def ensure_percent(val: str) -> str:
    """
    Normalize numeric or dB inputs to percentages required by edge-tts:
        - '-5'   → '-5%'
        - '+3dB' → '+3%'
        - '+3'   → '+3%'
    """
    s = str(val).strip()
    if s.lower().endswith("db"):
        s = s[:-2]
    return s if s.endswith("%") else f"{s}%"

# ===============================
# Chapter reading (DOCX / TXT)
# ===============================
@dataclass
class Chapter:
    title: str
    text: str

def read_docx_chapters(path: Path) -> List[Chapter]:
    """
    Read a DOCX file, detect chapters by Heading 1/2 (English: 'Heading 1/2',
    Finnish: 'Otsikko 1/2'). If no headings exist, fall back to heuristic detection.
    """
    from docx import Document

    doc = Document(str(path))
    # Collect (style_name, paragraph_text)
    items: List[Tuple[str, str]] = []
    for p in doc.paragraphs:
        style = getattr(p.style, "name", "") or ""
        text = (p.text or "").strip()
        if text:
            items.append((style, text))

    chapters: List[Chapter] = []
    current_title: Optional[str] = None
    buffer: List[str] = []

    def flush():
        nonlocal current_title, buffer
        content = "\n\n".join(buffer).strip()
        if content:
            chapters.append(Chapter(title=current_title or "Untitled", text=content))
        current_title = None
        buffer = []

    for style, text in items:
        is_heading = any(h in style for h in ("Heading 1", "Heading 2", "Otsikko 1", "Otsikko 2"))
        is_luku_like = bool(re.match(r"^(Luku|Chapter|Osa)\b", text, flags=re.IGNORECASE))
        if is_heading or is_luku_like:
            if buffer:
                flush()
            current_title = text
        else:
            buffer.append(text)
    if buffer:
        flush()

    # Fallback: whole document as one chapter if detection failed
    if not chapters:
        full = "\n\n".join(t for _, t in items)
        chapters = [Chapter(title="Book", text=re.sub(r"\n{3,}", "\n\n", full).strip())]
    return chapters

def read_txt_chapters(path: Path) -> List[Chapter]:
    """
    Heuristic chapter detection for plain text:
        - Splits when a line starts with 'Luku', 'Osa', or 'Chapter' (optionally with numbers).
    If nothing detected, returns a single 'Book' chapter.
    """
    txt = path.read_text(encoding="utf-8", errors="ignore")
    lines = [l.rstrip() for l in txt.splitlines()]

    chapters: List[Chapter] = []
    current_title: Optional[str] = None
    buffer: List[str] = []

    def flush():
        nonlocal current_title, buffer
        content = "\n".join(buffer).strip()
        if content:
            chapters.append(Chapter(title=current_title or f"Chapter {len(chapters)+1}", text=content))
        current_title = None
        buffer = []

    for line in lines:
        if re.match(r"^(Luku\s+\d+|Chapter\s+\d+|Osa\s+\d+|Luku\b|Chapter\b|Osa\b)", line, flags=re.IGNORECASE):
            if buffer:
                flush()
            current_title = line.strip()
        else:
            buffer.append(line)
    if buffer:
        flush()

    if not chapters:
        chapters = [Chapter(title="Book", text=re.sub(r"\n{3,}", "\n\n", txt).strip())]
    return chapters

def read_chapters(path: Path) -> List[Chapter]:
    """Dispatch based on extension."""
    if path.suffix.lower() == ".docx":
        return read_docx_chapters(path)
    return read_txt_chapters(path)

# ===============================
# Chunking for TTS
# ===============================
def split_chunks(text: str, max_chars: int = 2200) -> List[str]:
    """
    Split text into TTS-friendly chunks.
    Prefers paragraph -> sentence boundaries, then hard-splits if necessary.
    """
    parts: List[str] = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            parts.append(para)
            continue

        sentences = re.split(r"(?<=[.!?…])\s+", para)
        buf = ""
        for s in sentences:
            if not s:
                continue
            if len(buf) + 1 + len(s) <= max_chars:
                buf = f"{buf} {s}".strip() if buf else s
            else:
                if buf:
                    parts.append(buf)
                if len(s) <= max_chars:
                    buf = s
                else:
                    for i in range(0, len(s), max_chars):
                        parts.append(s[i : i + max_chars])
                    buf = ""
        if buf:
            parts.append(buf)
    return parts or [text]

# ===============================
# TTS (edge-tts, text mode)
# ===============================
async def synth_to_file(text: str, outfile: Path, voice: str, rate: str, volume: str):
    """
    Synthesize one text chunk to MP3 using edge-tts (text mode).
    """
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
    await communicate.save(str(outfile))

async def synth_chapter(chapter: Chapter, tmpdir: Path, voice: str, rate: str, volume: str) -> AudioSegment:
    """
    Synthesize a whole chapter by chunking it and concatenating the resulting MP3 segments.
    """
    parts = split_chunks(chapter.text, max_chars=2200)
    pause = AudioSegment.silent(duration=800)  # small gap between chunks
    assembled = AudioSegment.empty()
    for idx, part in enumerate(parts):
        part_file = tmpdir / f"{slugify(chapter.title)}_{idx:04d}.mp3"
        await synth_to_file(part, part_file, voice=voice, rate=rate, volume=volume)
        assembled += AudioSegment.from_file(part_file, format="mp3")
        if idx < len(parts) - 1:
            assembled += pause
    return assembled

# ===============================
# Pipeline
# ===============================
async def build(
    src: Path,
    outdir: Path,
    album: str,
    author: str,
    voice: str = "fi-FI-SelmaNeural",
    rate: str = "-5%",
    volume: str = "+0%",
    per_chapter: bool = True,
    combined_name: str = "book_combined.mp3",
    chapter_gap_ms: int = 1200,
    bitrate: str = "192k",
) -> Path:
    """
    Full end-to-end pipeline:
        1) Read chapters
        2) Synthesize each chapter
        3) Export per-chapter MP3s (optional)
        4) Export combined MP3 with gaps between chapters
    """
    chapters = read_chapters(src)
    outdir.mkdir(parents=True, exist_ok=True)

    combined = AudioSegment.empty()
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        for idx, ch in enumerate(tqdm(chapters, desc="Chapters", unit="chapter")):
            seg = await synth_chapter(ch, tdir, voice=voice, rate=rate, volume=volume)

            # Export each chapter with ID3 tags
            if per_chapter:
                fname = f"{idx+1:02d}_{slugify(ch.title)}.mp3"
                fpath = outdir / fname
                seg.export(
                    fpath, format="mp3", bitrate=bitrate,
                    tags={"album": album, "artist": author, "title": ch.title}
                )

            # Append to combined with a chapter gap
            combined += seg
            if idx < len(chapters) - 1:
                combined += AudioSegment.silent(duration=chapter_gap_ms)

    # Export combined file
    combined_path = outdir / combined_name
    combined.export(
        combined_path, format="mp3", bitrate=bitrate,
        tags={"album": album, "artist": author, "title": src.stem}
    )
    return combined_path

# ===============================
# CLI
# ===============================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="DOCX/TXT → per-chapter MP3 files + combined audiobook (Edge TTS)."
    )
    parser.add_argument("source", type=Path, help="Input file (.docx or .txt)")
    parser.add_argument("--outdir", type=Path, default=Path("output_mp3"), help="Output folder (default: output_mp3)")
    parser.add_argument("--album", type=str, default="Audiobook", help="Album tag for MP3 metadata")
    parser.add_argument("--author", type=str, default="Unknown Author", help="Artist/Author tag for MP3 metadata")
    parser.add_argument("--voice", default="fi-FI-SelmaNeural", help="Edge TTS voice (e.g., fi-FI-SelmaNeural)")
    parser.add_argument("--rate", default="-5%", help="Speech rate (accepts -5 or -5%)")
    parser.add_argument("--volume", default="+0%", help="Volume (accepts +3, +3% or +3dB)")
    parser.add_argument("--no-per-chapter", action="store_true", help="Skip per-chapter export; only write combined file")
    parser.add_argument("--combined-name", default="book_combined.mp3", help="Filename for combined audiobook")
    parser.add_argument("--chapter-gap-ms", type=int, default=1200, help="Silence between chapters in combined file (ms)")
    parser.add_argument("--bitrate", default="192k", help="MP3 bitrate (128k–320k)")
    args = parser.parse_args()

    # Normalize percent/dB inputs
    args.rate = ensure_percent(args.rate)
    args.volume = ensure_percent(args.volume)

    # Run
    asyncio.run(
        build(
            src=args.source,
            outdir=args.outdir,
            album=args.album,
            author=args.author,
            voice=args.voice,
            rate=args.rate,
            volume=args.volume,
            per_chapter=not args.no_per_chapter,
            combined_name=args.combined_name,
            chapter_gap_ms=args.chapter_gap_ms,
            bitrate=args.bitrate,
        )
    )
