#!/bin/bash
# check-pyjs-quotes.sh — Detect Python-to-JS quoting issues in inline HTML/JS
#
# Checks that backslash-escaped quotes inside Python triple-quoted strings
# survive intact to the JavaScript output.
#
#   PYTHON """  ->  CORRECT?  ->  JS OUTPUT
#   ----------      --------      ---------
#   \\'             YES           \'             (backslash preserved)
#   \'              NO            '              (backslash LOST!)
#   \\"             YES           \"             (backslash preserved)
#   \"              NO            "              (backslash LOST!)
#
# Exit code: 0 if all pass, 1 if any fail.

set -o pipefail
cd "$(dirname "$0")/.." || exit 1

PYDIR="api"
TMPPY=$(mktemp /tmp/check_pyjs_XXXX.py)
trap 'rm -f "$TMPPY"' EXIT

cat > "$TMPPY" << 'PYEOF'
import re, sys, os, subprocess, shutil, tempfile

EVENT_ATTRS = (
    'on(?:click|change|blur|focus|input|load|keydown|keyup|keypress|'
    'mouse(?:down|up|move|over|out|enter|leave)|submit|reset|toggle|'
    'scroll|wheel|contextmenu|dblclick|touch(?:start|end|move)|'
    'cut|copy|paste|select|drag(?:start|end|over|enter|leave|drop))'
)
EVENT_RE = re.compile(
    r'\b(' + EVENT_ATTRS + r')\s*=\s*"((?:[^"\\]|\\.)*?)"',
    re.IGNORECASE
)

SUSPECT_PATTERNS = [
    (r"(?<!\\)\\'", "unescaped \\' -> outputs just '  (use \\\\' )"),
    (r'(?<!\\)\\"', 'unescaped \\" -> outputs just "  (use \\\\" )'),
]


def extract_triple_strings(filepath):
    tdq = '"""'
    tsq = "'''"
    pat = re.compile(
        "(?P<q>" + re.escape(tsq) + "|" + re.escape(tdq) + ")"
        "(.*?)(?P=q)", re.DOTALL
    )
    with open(filepath, 'rb') as fh:
        raw = fh.read()
    text = raw.decode('utf-8')
    for m in pat.finditer(text):
        raw_content = m.group(2)
        line_no = text[:m.start()].count('\n') + 1
        try:
            unescaped = raw_content.encode('utf-8').decode('unicode_escape')
        except Exception:
            unescaped = raw_content
        yield line_no, raw_content, unescaped


def find_js_handlers(html):
    for m in EVENT_RE.finditer(html):
        yield m.group(1), m.group(2)


def check_suspect_quoting(raw, line_offset, filepath):
    issues = []
    for pattern, msg in SUSPECT_PATTERNS:
        for m in re.finditer(pattern, raw):
            inner_line = raw[:m.start()].count('\n') + line_offset
            issues.append((filepath, inner_line, msg))
    return issues


def check_empty_quotes(raw, line_offset, filepath):
    issues = []
    for m in re.finditer(r"onclick\s*=\s*\"[^\"]*?\(\s*''\s*\+", raw):
        inner_line = raw[:m.start()].count('\n') + line_offset
        issues.append((
            filepath, inner_line,
            "empty-string '' in onclick  --  should be \\\\' (escaped quote)"
        ))
    return issues


def is_simple_js(code):
    """Return True if code is a self-contained JS expression (no variable
    references, no template expressions, no backslash-at-expression-level)."""
    if re.search(r"(?<!\$)\$\{", code):
        return False
    if ' + ' in code and re.search(r"'\+|' \+", code):
        return False
    if re.search(r'(?<!\\)\\\'(?!\\)', code):
        return False
    if re.search(r'(?<!\\)\\\"(?!\\)', code):
        return False
    if re.search(r'\bvar\s+|\blet\s+|\bconst\s+', code):
        return False
    if re.search(r'\.(?:replace|match|split|substring|slice|indexOf|map|filter|reduce|forEach)\s*\(', code):
        return False
    return True


def check_with_node(js_code):
    if not shutil.which('node'):
        return None, None
    if not is_simple_js(js_code):
        return None, None
    wrapped = '"use strict";\nvoid function() { ' + js_code + '; };\n'
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False)
    try:
        tmp.write(wrapped)
        tmp.close()
        r = subprocess.run(
            ['node', '--check', tmp.name],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return False, r.stderr.strip()
        return True, None
    except Exception as e:
        return None, str(e)
    finally:
        os.unlink(tmp.name)


def rel(fpath):
    return os.path.relpath(fpath)


def print_fix_guide():
    print()
    print('FIX PATTERNS')
    print('  Inside Python """...""":')
    print('    Wrong: backslash + quote -> outputs just the quote (backslash LOST)')
    print('    Right: double-backslash + quote -> outputs backslash + quote (OK)')
    print()
    print('  Fix with sed (per file):')
    print("    s/\\\\'/\\\\\\\\'/g")
    print('    s/\\\\"/\\\\\\\\"/g')
    print()
    print('  3 patterns to watch for:')
    print('    1. onclick="func(...)" with JS string concatenation')
    print('       where inner quotes use empty-string "" instead of')
    print('       backslash-escaped quotes')
    print("    2. Any backslash-quote inside Python ''' meant to")
    print('       reach JS as backslash-quote (needs double backslash)')
    print('    3. Any JS escape sequence needing a literal backslash')
    print('       in the final browser output')


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else []
    all_errors = []
    files_status = []

    for fpath in targets:
        if not os.path.isfile(fpath):
            continue
        file_errors = []
        js_count = 0
        js_fail = 0
        js_skipped = 0

        for line_offset, raw_content, unescaped in extract_triple_strings(fpath):
            file_errors.extend(check_suspect_quoting(raw_content, line_offset, fpath))
            file_errors.extend(check_empty_quotes(raw_content, line_offset, fpath))
            for attr, js_code in find_js_handlers(unescaped):
                js_count += 1
                ok, err = check_with_node(js_code)
                if ok is None:
                    js_skipped += 1
                elif ok is False:
                    js_fail += 1
                    file_errors.append((
                        fpath, line_offset,
                        attr + '="' + js_code + '"  --  JS syntax error: ' + (err or '')
                    ))

        status = 'FAIL' if file_errors else 'PASS'
        files_status.append((fpath, status, len(file_errors)))
        all_errors.extend(file_errors)

        if js_count > 0 or file_errors:
            for fp, ln, msg in file_errors:
                print('  {}:{}  {}'.format(fp, ln, msg))

        if js_count > 0:
            parts = ['JS handlers: {} checked'.format(js_count)]
            if js_fail:
                parts.append('{} failed'.format(js_fail))
            if js_skipped:
                parts.append('{} skipped (variables)'.format(js_skipped))
            print('  -> {}: {}'.format(rel(fpath), ', '.join(parts)))

    print()
    print('=' * 60)
    print('PYTHON -> JS QUOTING CHECK SUMMARY')
    print('=' * 60)
    if not shutil.which('node'):
        print('NOTE: node not found -- JS syntax checks skipped')
    any_fail = False
    for fpath, status, ecnt in files_status:
        mark = '\u2713' if status == 'PASS' else '\u2717'
        extra = '  ({} issue(s))'.format(ecnt) if ecnt else ''
        print('  {}  {}  {}{}'.format(mark, status, rel(fpath), extra))
        if status != 'PASS':
            any_fail = True

    if all_errors:
        print_fix_guide()
    else:
        print()
        print('  All quoting patterns look correct.')

    sys.exit(1 if any_fail else 0)


if __name__ == '__main__':
    main()
PYEOF

# Use provided files or scan api/ by default
if [[ $# -gt 0 ]]; then
  files=("$@")
else
  files=()
  while IFS= read -r -d '' f; do
    files+=("$f")
  done < <(find "$PYDIR" -name '*.py' -print0 2>/dev/null)
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "PASS  (no .py files to check)"
  exit 0
fi

python3 "$TMPPY" "${files[@]}"
exit $?
