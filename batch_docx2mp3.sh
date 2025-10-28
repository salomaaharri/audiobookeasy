#!/usr/bin/env bash
# batch_docx2mp3.sh — convert all .docx in a folder to MP3 if missing
# Usage:
#   bash batch_docx2mp3.sh <input_docx_dir> <out_dir>
#   bash batch_docx2mp3.sh docx out
#
# Optional overrides via env vars:
#   ALBUM="My Audiobook" AUTHOR="Your Name" VOICE="fi-FI-SelmaNeural" RATE="-5" VOLUME="+3" ONLY_COMBINED=1 bash batch_docx2mp3.sh docx out
#
# Requires: docx2mp3.py in repo or on PATH (and its deps installed)

set -euo pipefail

INDIR="${1:-docx}"
OUTDIR="${2:-out}"

# Defaults (can be overridden via env)
ALBUM="${ALBUM:-My Audiobook}"
AUTHOR="${AUTHOR:-Harri J. Salomaa}"
VOICE="${VOICE:-fi-FI-SelmaNeural}"
RATE="${RATE:--5}"          # script will add % automatically
VOLUME="${VOLUME:+$VOLUME}" # allow empty env var
: "${VOLUME:=+3}"           # default +3%
ONLY_COMBINED="${ONLY_COMBINED:-0}"  # set to 1 to skip per-chapter files
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
[[ "$ONLY_COMBINED" == "1" ]] && echo "Mode:   only combined MP3 (no per-chapter files)"

converted_any=0
found_any=0

# Find all .docx (case-insensitive), handle spaces safely
while IFS= read -r -d '' DOCX; do
  found_any=1
  base="$(basename "$DOCX")"
  stem="${base%.*}"                        # file name without extension
  target="$OUTDIR/${stem}.mp3"             # combined output name (custom per file)

  if [[ -f "$target" ]]; then
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
    --combined-name "$(basename "$target")"
  )
  if [[ "$ONLY_COMBINED" == "1" ]]; then
    args+=( --no-per-chapter )
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