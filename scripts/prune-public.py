#!/usr/bin/env python3
"""Prune published files that no built page references.

Since the gallery override processes bundle images at build time
(Hugo emits *_hu_* variants), the raw multi-megabyte originals in
public/projects/*/images/ would only inflate the deploy. Pruning is scoped
strictly to those image directories — RSS index.xml, sitemaps, and other
non-referenced manifests stay. Run after `hugo` builds public/.
"""

import glob
import os
import re
import sys
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
# Hugo URLs include the Pages subpath; files under public/ do not.
BASE_PATH = urlsplit(sys.argv[1]).path.rstrip("/") if len(sys.argv) > 1 else ""

referenced = set()
for html in glob.glob(f"{PUBLIC}/**/*.html", recursive=True):
    text = open(html, encoding="utf-8", errors="replace").read()
    for attr, val in re.findall(r'((?:src|href|srcset|content))="([^"]+)"', text):
        # og/twitter meta and canonical links use absolute URLs; normalize to
        # their site-relative path so they can be matched against public/.
        if attr == "srcset":
            candidates = [c.split()[0] for c in val.split(",")]
        else:
            candidates = [val]
        for u in candidates:
            absurl = re.match(r"https?://[^/]+(/.*)", u)
            path = absurl.group(1) if absurl else u
            if BASE_PATH and (path == BASE_PATH or path.startswith(BASE_PATH + "/")):
                path = path[len(BASE_PATH) :] or "/"
            referenced.add(path)

pruned = 0
for p in glob.glob(f"{PUBLIC}/projects/*/images/*"):
    if os.path.isdir(p) or p.endswith("/index.html"):
        continue
    rel = "/" + os.path.relpath(p, PUBLIC)
    if rel in referenced:
        continue
    os.remove(p)
    pruned += 1
print(f"prune-public: removed {pruned} unreferenced files")
