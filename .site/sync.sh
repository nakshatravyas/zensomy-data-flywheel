#!/usr/bin/env bash
# Copy the submission documents into the site, rewriting file references into site links.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DST="$(cd "$(dirname "$0")/docs" && pwd)"

rewrite() {
  sed -e 's#`1-TECHNICAL-DESIGN\.md`#[Technical Design](technical-design.md)#g' \
      -e 's#`2-DESIGN-DOCUMENT\.md`#[Design Document](design-document.md)#g' \
      -e 's#`3-implementation/`#[Implementation](implementation.md)#g'
}

rewrite < "$SRC/1-TECHNICAL-DESIGN.md" > "$DST/technical-design.md"
rewrite < "$SRC/2-DESIGN-DOCUMENT.md" > "$DST/design-document.md"
rewrite < "$SRC/3-implementation/README.md" > "$DST/implementation.md"

echo "synced 3 pages"
