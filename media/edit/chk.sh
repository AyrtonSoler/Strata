#!/bin/sh
# Syntax-check a bundled edit script with oxlint (parse errors only).
cp "$1" _chk.jsx && ../../frontend/node_modules/.bin/oxlint -A all _chk.jsx 2>&1 | grep -E "x |Error|error" ; rm -f _chk.jsx; echo checked
