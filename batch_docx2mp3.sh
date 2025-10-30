#!/usr/bin/env bash
# batch_docx2mp3.sh — convert all .docx in a folder to MP3 if missing
# Usage:
#   bash batch_docx2mp3.sh <input_docx_dir> <out_dir>
#   bash batch_docx2mp3.sh docx out
#
# Optional overrides via env vars:
#   ALBUM="My Audiobook" AUTHOR="Your Name" VOICE="fi-FI-SelmaNeural" RATE="-5" VOLUME="+3" \
#   ONLY_COMBINED=1 PREFIX="title" bash batch_docx2mp3.sh docx out
#
# Notes:
# - If PREFIX is set, files will be named: PREFIX_<nn>_<Chapter>.mp3 and PREFIX_<combined>.mp3
# - If PREFIX is NOT set, Python will auto-derive it from DOCX Title → first Heading → filename.
#   We then detect an existing combined file via wildcard "*_<stem>.mp3".

set -euo pipefail

INDIR="${1:-docx}"
OUTDIR="${2:-out}"

# Defaults (can be overridden via env)
ALBUM="${ALBUM:-My Audiobook}"
AUTHOR="${AUTHOR:-Harri J. Salomaa}"
VOICE="${VOICE:-fi-FI-SelmaNeural}"
RATE="${RATE:--5}"           # script adds % automatically
VOLUME="${VOLUME:+$VOLUME}"  # allow empty env var
: "${VOLUME:=+3}"            # default +3%
ONLY_COMBINED="${ONLY_COMBINED:-0}"  # set 1 to skip per-chapter files
PREFIX="${PREFIX:-}"         # optional filename prefix; if empty, Python auto-derives
SCRIPT="${SCRIPT:-docx2mp3.py}"

mkdir -p "$OUTDIR"

# Ensure script is available
if [[ ! -f "$SCRIPT" ]] && ! command -v "$SCRIPT" >/dev/null 2>&1; then
  echo "Error: cannot find $SCRIPT (set SCRIPT=/path/to/docx2mp3.py if needed)" >&2
  exit 1
fi

echo "Input:  $INDIR"
echo "Output: $OUTDIR"
echo "Voice:  $VOICE | Rate: $RATE | Volume: $VOLUME"
echo "Album:  $ALBUM | Author: $AUTHOR"
[[ -n "$PREFIX" ]] && echo "Prefix: $PREFIX (explicit)" || echo "Prefix: auto (DOCX title/heading/filename)"
[[ "$ONLY_COMBINED" == "1" ]] && echo "Mode:   only combined MP3 (no per-chapter files)"

converted_any=0
found_any=0

# Find all .docx (case-insensitive), handle spaces safely
while IFS= read -r -d '' DOCX; do
  found_any=1
  base="$(basename "$DOCX")"
  stem="${base%.*}"  # file name without extension

  # Combined file base name we request from Python
  combined_base="${stem}.mp3"

  # Determine expected combined output path (depends on prefix mode)
  if [[ -n "$PREFIX" ]]; then
    target="$OUTDIR/${PREFIX}_${combined_base}"
    exists_flag=0
    [[ -f "$target" ]] && exists_flag=1
  else
    # Unknown prefix (auto). Detect any "<something>_<stem>.mp3"
    target_glob="$OUTDIR"/*_"$stem".mp3
    exists_flag=0
    # compgen returns non-empty if any file matches
    if compgen -G "$target_glob" > /dev/null; then
      exists_flag=1
      # pick first match for logging
      for f in $target_glob; do target="$f"; break; done
    else
      target="$OUTDIR/_auto_${combined_base}"  # only for log echo after convert
    fi
  fi

  if [[ "$exists_flag" -eq 1 ]]; then
    echo "✓ Exists, skipping: $target"
    continue
  fi

  echo "→ Converting: $DOCX"
  args=(
    "$DOCX"
    --outdir "$OUTDIR"
    --album "$ALBUM"
    --author "$AUTHOR"
    --voice "$VOICE"
    --rate "$RATE"
    --volume "$VOLUME"
    --combined-name "$combined_base"
  )
  if [[ "$ONLY_COMBINED" == "1" ]]; then
    args+=( --no-per-chapter )
  fi
  if [[ -n "$PREFIX" ]]; then
    args+=( --prefix "$PREFIX" )
  fi

  # Prefer local script if present, else rely on PATH
  if [[ -f "$SCRIPT" ]]; then
    python "$SCRIPT" "${args[@]}"
  else
    python "$(command -v "$SCRIPT")" "${args[@]}"
  fi

  echo "✓ Wrote: $target"
  converted_any=1
done < <(find "$INDIR" -type f \( -iname '*.docx' \) -print0)

if [[ "$found_any" -eq 0 ]]; then
  echo "No .docx files found in: $INDIR"
elif [[ "$converted_any" -eq 0 ]]; then
  echo "All targets already exist. Nothing to do."
fi