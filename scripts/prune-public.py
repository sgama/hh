#!/usr/bin/env python3
"""Prune published files that no built page references.

Since the gallery/layout overrides process bundle images at build time
(Hugo emits *_hu_* variants), the raw multi-megabyte originals in
public/projects/*/images/ would only inflate the deploy. Any file that
appears in no HTML of public/ is removed. Run after `hugo` builds public/.
"""

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")

referenced = set()
for html in glob.glob(f"{PUBLIC}/**/*.html", recursive=True):
    text = open(html, encoding="utf-8", errors="replace").read()
    for m in re.findall(r'(?:src|href|srcset)="[^"]*"', text):
        referenced.update(re.findall(r"(?:srcset=\"):?([^\" ]+)", m))

pruned = 0
for base in ("css", "js", "projects"):
    for p in glob.glob(f"{PUBLIC}/{base}/**/*", recursive=True):
        if os.path.isdir(p) or p.endswith("/index.html"):
            continue
        rel = "/" + os.path.relpath(p, PUBLIC)
        if rel in referenced:
            continue
        os.remove(p)
        pruned += 1
print(f"prune-public: removed {pruned} unreferenced files")
