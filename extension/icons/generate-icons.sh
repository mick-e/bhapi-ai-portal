#!/usr/bin/env bash
# generate-icons.sh
# Generates PNG extension icons from the SVG source.
#
# Requirements (install one of these):
#   - ImageMagick 7+  (magick command)
#   - ImageMagick 6.x (convert command)
#   - librsvg         (rsvg-convert command)
#
# Usage:
#   cd extension/icons
#   bash generate-icons.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SVG_SOURCE="${SCRIPT_DIR}/icon.svg"
SIZES=(16 48 128)

if [ ! -f "$SVG_SOURCE" ]; then
  echo "ERROR: SVG source not found at ${SVG_SOURCE}"
  exit 1
fi

echo "Generating PNG icons from ${SVG_SOURCE}..."

# Detect available tool
if command -v magick &>/dev/null; then
  TOOL="magick"
elif command -v convert &>/dev/null; then
  TOOL="convert"
elif command -v rsvg-convert &>/dev/null; then
  TOOL="rsvg-convert"
elif command -v inkscape &>/dev/null; then
  TOOL="inkscape"
else
  echo "ERROR: No SVG-to-PNG converter found."
  echo "Please install one of the following:"
  echo "  - ImageMagick:  https://imagemagick.org/script/download.php"
  echo "  - librsvg:      apt install librsvg2-bin  (Linux)"
  echo "  - Inkscape:     https://inkscape.org/release/"
  exit 1
fi

echo "Using tool: ${TOOL}"

for SIZE in "${SIZES[@]}"; do
  OUTPUT="${SCRIPT_DIR}/icon-${SIZE}.png"
  echo "  Generating icon-${SIZE}.png (${SIZE}x${SIZE})..."

  case "$TOOL" in
    magick)
      magick "$SVG_SOURCE" -resize "${SIZE}x${SIZE}" -background none "$OUTPUT"
      ;;
    convert)
      convert -background none -resize "${SIZE}x${SIZE}" "$SVG_SOURCE" "$OUTPUT"
      ;;
    rsvg-convert)
      rsvg-convert -w "$SIZE" -h "$SIZE" -o "$OUTPUT" "$SVG_SOURCE"
      ;;
    inkscape)
      inkscape "$SVG_SOURCE" --export-type=png --export-filename="$OUTPUT" \
        --export-width="$SIZE" --export-height="$SIZE" 2>/dev/null
      ;;
  esac
done

echo ""
echo "Done. Generated icons:"
for SIZE in "${SIZES[@]}"; do
  FILE="${SCRIPT_DIR}/icon-${SIZE}.png"
  if [ -f "$FILE" ]; then
    FILE_SIZE=$(wc -c < "$FILE")
    echo "  icon-${SIZE}.png  (${FILE_SIZE} bytes)"
  else
    echo "  icon-${SIZE}.png  MISSING (generation may have failed)"
  fi
done
