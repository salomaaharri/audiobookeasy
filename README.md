# 🎧 AudioBookEasy 🎧 Turn Your Writing into Sound

**audiobookeasy** is a simple, privacy-first tool that converts your `.docx` or `.txt` manuscripts into professional-sounding **MP3 audiobooks** using **Microsoft Edge Neural Voices** 🎧 all **locally** on your own computer (no cloud upload).

This repo includes the script **`docx2mp3.py`** for per-chapter exports **and** a combined audiobook file.

---

## ✨ Features

- ✅ Input: **DOCX** (Word) or **TXT**
- ✅ **Automatic chapter detection** (DOCX headings *Heading 1/2* / *Otsikko 1/2* or lines starting with *Luku / Osa / Chapter*)
- ✅ Output: **one MP3 per chapter** + **one combined MP3**
- ✅ Natural **neural voices** (Finnish & all Edge TTS voices)
- ✅ Adjust **voice**, **rate**, **volume**, **chapter gaps**, **bitrate**
- ✅ Adds **ID3 metadata** (album / author / title)
- ✅ Works almost fully **offline/local** after install

---

## 🧰 Requirements

- **Python 3.9–3.12 recommended.** If you use **Python 3.13**, install the backport: `pip install audioop-lts`.
- **FFmpeg** (for `pydub` MP3 I/O)
- Python packages: `edge-tts`, `python-docx`, `pydub`, `tqdm`

---

## ⚙️ Installation

### 1) Clone
```bash
git clone https://github.com/salomaaharri/audiobookeasy.git
cd audiobookeasy
```

### 2) Create & activate a virtual environment
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

### 3) Install dependencies
```bash
pip install --upgrade pip
pip install edge-tts python-docx pydub tqdm
pip install audioop-lts
```

### 4) Install FFmpeg
- **macOS:** `brew install ffmpeg`  
- **Ubuntu/Debian:** `sudo apt-get install ffmpeg`  
- **Windows:** Download from https://ffmpeg.org/download.html and add `ffmpeg.exe` to PATH

---

## 🚀 Quick Start

### DOCX → per-chapter MP3s + combined audiobook
```bash
python docx2mp3.py demoetxt.docx \ 
  --outdir demo \
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

---

## 🧪 What You’ll Get

```
out/
├── 01_Chapter_1.mp3
├── 02_Chapter_2.mp3
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

---

## 🎙️ Voice Examples

| Language | Voice | Description |
|---|---|---|
| Finnish | `fi-FI-SelmaNeural` | warm, expressive female |
| Finnish | `fi-FI-NooraNeural` | neutral, professional |
| Finnish | `fi-FI-HarriNeural` | calm, male |
| English (US) | `en-US-JennyNeural` | clear, friendly |
| English (GB) | `en-GB-RyanNeural` | British male |

Change with `--voice VOICENAME`.

---

## ⚙️ Command-line Options

| Option | Description | Default |
|---|---|---|
| `source` | Input file (.docx or .txt) | — |
| `--outdir` | Output folder | `output_mp3` |
| `--album` | MP3 album tag | `Audiobook` |
| `--author` | MP3 artist/author tag | `Unknown Author` |
| `--voice` | Edge TTS voice | `fi-FI-SelmaNeural` |
| `--rate` | Speech rate (`-5`, `-5%`, `+10`, …) | `-5%` |
| `--volume` | Volume (`+3`, `+3%`, `+3dB`) | `+0%` |
| `--no-per-chapter` | Only export combined file | `False` |
| `--combined-name` | Filename of combined MP3 | `book_combined.mp3` |
| `--chapter-gap-ms` | Silence between chapters in combined file | `1200` |
| `--bitrate` | MP3 bitrate | `192k` |

---

## 🧯 Troubleshooting

- **`argument --rate: expected one argument`**  
  Add `=` or quote the value: `--rate="-5%"` or just `--rate -5` (script adds the `%`).

- **`Invalid volume '+3dB'`**  
  Use percent: `--volume +3` or `--volume +3%`. This script accepts `+3dB` and converts to `+3%`, but older `edge-tts` may complain if passed through unnormalized.

- **`FFmpeg not found` / export fails**  
  Install FFmpeg and ensure it’s on PATH (see install step 4).

- **Weird chapter splits**  
  Ensure DOCX uses **Heading 1/2** for chapter titles. For TXT, start chapter lines with **Luku / Osa / Chapter**.

---

## 🔐 Privacy

All conversion happens **locally** on your machine. Manuscripts and audio files are never uploaded.

---

## 🧑‍💻 License

**MIT** : free to use, modify, and share.

---

## ✍️ Author

**Harri J. Salomaa** : reflections from 30 years in business, leadership & technology.  
LinkedIn: https://www.linkedin.com/in/hsalomaa

---

## 🌟 Support

If this helped you, please ⭐ the repo and share your audiobook results on LinkedIn with **#audiobookeasy**.
# audiobookeasy
python code to generare simple audiobooks from docx
