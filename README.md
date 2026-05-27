# 🎧 AudioBookEasy 🎧 Turn Your Writing into Sound

**audiobookeasy** is a simple, privacy-first tool that converts ...ices** 🎧 all **locally** on your own computer (no cloud upload).

This repo includes the script **`docx2mp3.py`** for per-chapter exports **and** a combined audiobook file.

---

## ✨ Features

- ✅ Input: **DOCX** (Word) or **TXT**
- ✅ **Automatic chapter detection** (DOCX headings *Heading 1/2* / *Otsikko 1/2* or lines starting with *Luku / Osa / Chapter*)
- ✅ Output: **one MP3 per chapter** + **one combined MP3**
- ✅ Natural **neural voices** (Finnish & all Edge TTS voices)
- ✅ Adjust **voice**, **rate**, **volume**, **chapter gaps**, **bitrate**
- ✅ Adds **ID3 metadata** (album / author / title)
...

## 🧰 Requirements

- **Python 3.9–3.12 recommended.** If you use **Python 3.13**, install the backport: `pip install audioop-lts`.
- **FFmpeg** (for `pydub` MP3 I/O)
- Python packages: `edge-tts`, `python-docx`, `pydub`, `tqdm`

---

## ⚙️ Installation

### 1) Clone
```bash
git clone https://github.com/your/repo.git
cd audiobookeasy
```

### 2) Create & activate a virtual environment
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

### 4) Install FFmpeg
- macOS (Homebrew): `brew install ffmpeg`
- Linux (Debian/Ubuntu): `sudo apt-get install ffmpeg`
- Windows: Download from ffmpeg.org and add to PATH

---

## 🚀 Quick Start

### DOCX → per-chapter MP3s + combined audiobook
```bash
python docx2mp3.py demo/demoetxt.docx \ 
  --outdir demo/out \
  --prefix "demotxt" \
  --album "My Audiobook" \
  --author "Harri J. Salomaa" \
  --voice fi-FI-SelmaNeural \
  --rate -5 \
  --volume +3
```

### TXT → audiobook (Finnish Noora)
```bash
python docx2mp3.py notes.txt --outdir out --voice fi-FI-NooraNeural
```

### Only a single combined file (skip per-chapter)
```bash
python docx2mp3.py my_book.docx --no-per-chapter
```

> **Tip:** `--rate` accepts `-5` or `-5%`.  
> **Important:** `edge-tts` expects **percent** for volume → use `+3` or `+3%` (not `+3dB`). This script accepts `+3dB` too; it converts to `+3%`.

> Note: Audio is produced locally on your machine. Depending on the selected voice, the TTS engine may require an internet connection.

---

## 🌍 Translating chapters first (optional)

If you have an English manuscript and want a Finnish audiobook, [translate.py](translate.py) translates a DOCX chapter to Finnish via **Claude Sonnet 4.6** while preserving paragraph structure (so the resulting DOCX feeds straight back into `docx2mp3.py`).

```bash
pip install 'anthropic>=0.92.0'
# Add ANTHROPIC_API_KEY=sk-ant-... to .env.local (auto-loaded)

python translate.py Englanti/Chapter_1.docx --out Suomi/Chapter_1.docx
```

- Keeps English proper names; localizes only labels like *Chapter → Luku*.
- Preserves `Heading 1` / `Heading 2` styles → chapter detection still works in `docx2mp3.py`.
- Cost: ~$0.10–0.15 per ~17k-char chapter (Sonnet 4.6 input + adaptive thinking).

---

## 🔌 Engines

`audiobookeasy` supports three TTS engines. Pick one with `--engine`.

### 🆓 Edge TTS (default, free)

No setup beyond the base install. Decent neural voices, limited emotional control. Finnish: `fi-FI-SelmaNeural`, `fi-FI-NooraNeural`.

```bash
python docx2mp3.py book.docx --engine edge --voice fi-FI-SelmaNeural
```

### 🎭 OpenAI `gpt-4o-mini-tts` (paid, most steerable)

Accepts a **natural-language instruction** per request — the biggest expressiveness win for audiobook narration.

```bash
pip install 'openai>=1.40.0'
export OPENAI_API_KEY=sk-...        # or put it in .env.local (see below)

python docx2mp3.py book.docx \
  --engine openai \
  --voice alloy \
  --instructions "Warm, contemplative narration. Slow on emotional passages. Treat dialogue with quiet intimacy."
```

> **Tip:** instead of `export`, drop your keys into a `.env.local` file next to the script:
> ```
> OPENAI_API_KEY=sk-...
> ELEVENLABS_API_KEY=...
> ```
> The script auto-loads `.env.local` (or `.env`) on startup. `.env*` is gitignored.

Voices: `alloy`, `ash`, `ballad`, `coral`, `echo`, `fable`, `nova`, `onyx`, `sage`, `shimmer`, `verse`. `--rate -5%` maps to OpenAI `speed=0.95`. Supports Finnish and many other languages.

### 🎙️ ElevenLabs (paid, best raw voice quality)

Best for long-form expressive narration and voice cloning. Voice IDs are account-specific — grab them from your ElevenLabs dashboard.

```bash
pip install 'elevenlabs>=1.0.0'
export ELEVENLABS_API_KEY=...

python docx2mp3.py book.docx \
  --engine elevenlabs \
  --voice <your_voice_id> \
  --stability 0.5 --similarity 0.75 --style 0.2
```

Default model: `eleven_multilingual_v2` (Finnish + 29 languages). Override with `--model`.

### Cost & privacy

| Engine | Cost (approx) | Text leaves machine? |
|---|---|---|
| edge | free | yes (sent to MS Edge TTS) |
| openai | ~$0.015 per 1k chars (gpt-4o-mini-tts) | yes (sent to OpenAI) |
| elevenlabs | ~$0.15–0.30 per 1k chars (plan-dependent) | yes (sent to ElevenLabs) |

A 200-page book is roughly 250k–400k characters. Rough totals: OpenAI ~$4–6, ElevenLabs ~$40–120. Audio mixing/export is always local.

---

## 🧪 What You’ll Get

```
out/
├── demotxt_01_Chapter_1.mp3
├── demotxt_02_Chapter_2.mp3
└── book_combined.mp3
```

- Per-chapter files include ID3 tags: **album**, **artist**, **title**  
- `book_combined.mp3` concatenates all chapters with short silence gaps

---

## 🧩 How It Works (high level)

1. Reads DOCX/TXT and **detects chapters**.  
2. Splits text into ~2200-char **chunks** along paragraph/sentence boundaries.  
3. Uses **edge-tts** to synthesize each chunk with the chosen voice, rate, and volume.  
4. **pydub** merges chunks (adding small pauses) and writes MP3s with metadata.

> Small nicety: if the first detected chapter title is literally "Untitled", it is renamed to **"Esipuhe"** for nicer filenames and tags.

---

## 🎙️ Voice Examples

```bash
python docx2mp3.py mybook.docx --voice fi-FI-SelmaNeural
python docx2mp3.py mybook.docx --voice fi-FI-NooraNeural
python docx2mp3.py mybook.docx --voice en-GB-LibbyNeural
```

---

## ⚙️ Command-line Options

| Option | Description | Default |
|---|---|---|
| `source` | Input file (.docx or .txt) | — |
| `--outdir` | Output folder | `output_mp3` |
| `--prefix` | Filename prefix for per-chapter tracks (auto: DOCX title → first heading → input filename) | *(auto)* |
| `--album` | MP3 album tag | `Audiobook` |
| `--author` | MP3 artist/author tag | `Unknown Author` |
| `--engine` | TTS backend: `edge`, `openai`, `elevenlabs` | `edge` |
| `--voice` | Voice (engine-specific) | edge: `fi-FI-SelmaNeural`; openai: `alloy`; elevenlabs: *(required)* |
| `--model` | Engine model override | openai: `gpt-4o-mini-tts`; elevenlabs: `eleven_multilingual_v2` |
| `--rate` | Speech rate (edge: `-5`/`-5%`; openai: mapped to `speed`) | `-5%` |
| `--volume` | Volume (edge only) | `+0%` |
| `--instructions` | OpenAI `gpt-4o-mini-tts` style prompt | *(none)* |
| `--stability` | ElevenLabs stability (0.0–1.0) | `0.5` |
| `--similarity` | ElevenLabs similarity_boost (0.0–1.0) | `0.75` |
| `--style` | ElevenLabs style (0.0–1.0) | `0.0` |
| `--no-per-chapter` | Only export combined file | `False` |
| `--combined-name` | Filename of combined MP3 | `book_combined.mp3` |
| `--chapter-gap-ms` | Silence between chapters in combined file | `1200` |
| `--bitrate` | MP3 bitrate | `192k` |

---

## 🧯 Troubleshooting

- **`argument --rate: expected one argument`**  
  Add `=` or quote the value: `--rate="-5%"` or just `--rate -5` (script adds the `%`).

- **`Invalid volume '+3dB'`**  
  Use percent: `--volume +3` or `--volume +3%`. This script acce...ut older `edge-tts` may complain if passed through unnormalized.

- **`FFmpeg not found` / export fails**  
  Install FFmpeg and ensure it’s on PATH (see install step 4).

- **Weird chapter splits**  
  Ensure DOCX uses **Heading 1/2** for chapter titles. For TXT, start chapter lines with **Luku / Osa / Chapter**.

---

## 🔐 Privacy

Audio processing (splitting/merging, MP3 export) happens **locally** on your machine. Text-to-speech synthesis uses **Edge TTS** and may require an internet connection depending on the voice/engine.

---

## 🧑‍💻 License

MIT — do whatever, attribution appreciated.

---

## ✍️ Author

**Harri J. Salomaa** : reflections from 30 years in business, leadership & technology.  
LinkedIn: https://www.linkedin.com/in/hsalomaa

---

## 🌟 Support

If this helped you, please ⭐ the repo and share your audiobook results on LinkedIn with **#audiobookeasy**.