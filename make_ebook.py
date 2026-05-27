#!/usr/bin/env python3
"""
make_ebook.py — Build an EPUB from a folder of DOCX chapters.

Walks a directory of DOCX files (sorted by chapter number), extracts paragraphs
preserving Heading 1/2 vs body, and writes a single EPUB 3 file with TOC,
metadata, and an optional cover image. The result opens in Apple Books (Mac/iOS),
Google Play Books / Moon+ Reader (Android), Edge / Calibre / Thorium (PC), Kobo,
and any other modern EPUB reader.

Example:
    python make_ebook.py Englanti --out Englanti/the_guardian_of_syntax.epub \\
        --title "The Guardian of Syntax" --author "Harri J. Salomaa" \\
        --lang en --cover cover.png
"""

import argparse
import re
import sys
from html import escape
from pathlib import Path
from typing import List, Optional, Tuple

from docx import Document
from ebooklib import epub


CHAPTER_FILENAME_RE = re.compile(r"[Cc]hapter[_ ]*(\d+)")


def natural_chapter_num(p: Path) -> int:
    """Extract chapter number from filename like 'Foo_Chapter_12.docx' for natural sort."""
    m = CHAPTER_FILENAME_RE.search(p.stem)
    return int(m.group(1)) if m else 0


def is_chapter_file(p: Path) -> bool:
    """Match files whose basename contains 'Chapter_<N>' or 'Chapter <N>' — keeps stray DOCX (descriptions, reader guides, full-book bundles) out of the EPUB."""
    return bool(CHAPTER_FILENAME_RE.search(p.stem))


def read_paragraphs(src: Path) -> List[Tuple[str, str]]:
    """Read non-empty paragraphs as (style_name, text) tuples."""
    doc = Document(str(src))
    items: List[Tuple[str, str]] = []
    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if text:
            style = getattr(p.style, "name", "") or "Normal"
            items.append((style, text))
    return items


def is_heading_1(style: str) -> bool:
    return "Heading 1" in style or "Otsikko 1" in style


def is_heading_2(style: str) -> bool:
    return "Heading 2" in style or "Otsikko 2" in style


def is_chapter_line(text: str) -> bool:
    return bool(re.match(r"^(Luku|Chapter|Osa)\b", text, flags=re.IGNORECASE))


def chapter_to_html(paragraphs: List[Tuple[str, str]], fallback_title: str) -> Tuple[str, str]:
    """
    Convert paragraphs to a chapter title + HTML body.
    Skips preamble before the first Heading 1 / Luku / Chapter line so per-file
    boilerplate (book title, author note) doesn't repeat in every chapter.
    """
    start_idx = None
    for i, (style, text) in enumerate(paragraphs):
        if is_heading_1(style) or is_chapter_line(text):
            start_idx = i
            break

    if start_idx is None:
        # No heading detected — keep whole content
        chapter_title = fallback_title
        body_paragraphs = paragraphs
    else:
        chapter_title = paragraphs[start_idx][1]
        body_paragraphs = paragraphs[start_idx:]

    parts = []
    for i, (style, text) in enumerate(body_paragraphs):
        e = escape(text)
        if i == 0:
            parts.append(f"<h1>{e}</h1>")
        elif is_heading_1(style) or is_chapter_line(text):
            parts.append(f"<h1>{e}</h1>")
        elif is_heading_2(style):
            parts.append(f"<h2>{e}</h2>")
        else:
            parts.append(f"<p>{e}</p>")

    return chapter_title, "\n".join(parts)


CSS_TEXT = """body { font-family: Georgia, "Times New Roman", serif; line-height: 1.55; }
h1 { font-size: 1.5em; margin-top: 2.5em; margin-bottom: 1.2em; text-align: center; }
h2 { font-size: 1.2em; margin-top: 1.5em; }
p { text-indent: 1.5em; margin: 0.3em 0; text-align: justify; }
h1 + p, h2 + p { text-indent: 0; }
"""


def build_epub(
    docx_dir: Path,
    out_path: Path,
    title: str,
    author: str,
    language: str,
    cover: Optional[Path] = None,
    book_id: Optional[str] = None,
) -> None:
    book = epub.EpubBook()
    book.set_identifier(book_id or f"audiobookeasy-{language}-{out_path.stem}")
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    if cover is not None:
        book.set_cover(cover.name, cover.read_bytes())

    css = epub.EpubItem(
        uid="style",
        file_name="style/style.css",
        media_type="text/css",
        content=CSS_TEXT.encode("utf-8"),
    )
    book.add_item(css)

    all_docx = sorted(docx_dir.glob("*.docx"))
    docx_files = sorted([p for p in all_docx if is_chapter_file(p)], key=natural_chapter_num)
    skipped = [p.name for p in all_docx if not is_chapter_file(p)]
    if skipped:
        print(f"  skipping non-chapter files: {', '.join(skipped)}")
    if not docx_files:
        sys.exit(f"✖ No chapter .docx files in {docx_dir}")

    chapters = []
    for i, src in enumerate(docx_files, 1):
        paras = read_paragraphs(src)
        if not paras:
            print(f"  ! ch {i:2d}: empty — skipping ({src.name})", file=sys.stderr)
            continue

        fallback = f"Chapter {i}"
        ch_title, body_html = chapter_to_html(paras, fallback_title=fallback)

        c = epub.EpubHtml(
            title=ch_title,
            file_name=f"chap_{i:02d}.xhtml",
            lang=language,
        )
        c.content = body_html  # ebooklib wraps with its own <html><head><body> template
        c.add_item(css)
        book.add_item(c)
        chapters.append(c)
        print(f"  ch {i:2d}: {ch_title}")

    if not chapters:
        sys.exit("✖ No chapters built — aborting.")

    book.toc = chapters
    book.spine = ["nav"] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(out_path), book)
    print(f"✓ {out_path}  ({len(chapters)} chapters)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an EPUB from a folder of DOCX chapters.")
    parser.add_argument("docx_dir", type=Path, help="Directory containing chapter DOCX files")
    parser.add_argument("--out", type=Path, required=True, help="Output .epub path")
    parser.add_argument("--title", required=True, help="Book title")
    parser.add_argument("--author", default="Unknown Author", help="Author name")
    parser.add_argument("--lang", default="en", help="ISO 639-1 language code (en, fi, ...)")
    parser.add_argument("--cover", type=Path, default=None, help="Path to cover image (PNG / JPG)")
    parser.add_argument("--book-id", default=None, help="EPUB book identifier (default: auto)")
    args = parser.parse_args()

    if not args.docx_dir.is_dir():
        sys.exit(f"✖ Not a directory: {args.docx_dir}")
    if args.cover is not None and not args.cover.is_file():
        sys.exit(f"✖ Cover not found: {args.cover}")

    build_epub(
        docx_dir=args.docx_dir,
        out_path=args.out,
        title=args.title,
        author=args.author,
        language=args.lang,
        cover=args.cover,
        book_id=args.book_id,
    )


if __name__ == "__main__":
    main()
