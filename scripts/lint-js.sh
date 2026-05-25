#!/bin/bash
# Extract JS from Python f-strings and lint with ESLint
# Usage: ./scripts/lint-js.sh [file.py ...]

set -e
cd "$(dirname "$0")/.."

TMPDIR=".lint-tmp"
mkdir -p "$TMPDIR"
trap "rm -rf $TMPDIR" EXIT

FILES="${@:-api/dashboard.py api/strategy_lab.py}"

for f in $FILES; do
  if [ ! -f "$f" ]; then continue; fi
  echo "=== Checking $f ==="
  # Extract content between <script> and </script> tags
  python3 -c "
import re, sys
with open('$f') as fh:
    content = fh.read()
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if not scripts:
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
for i, js in enumerate(scripts):
    js = js.replace('{{', '{').replace('}}', '}')
    out = '$TMPDIR/' + re.sub(r'[/.]', '_', '$f') + f'_script{i}.js'
    with open(out, 'w') as out_fh:
        out_fh.write(js)
    print(f'  Extracted script {i} ({len(js)} bytes) -> {out}')
" 2>&1
done

echo "=== ESLint ==="
HAS_JS=$(ls "$TMPDIR"/*.js 2>/dev/null || true)
if [ -n "$HAS_JS" ]; then
  npx eslint "$TMPDIR"/*.js 2>&1 || true
else
  echo "No JS extracted"
fi
echo "=== Done ==="
