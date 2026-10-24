#!/usr/bin/env python3
"""Restore pristine media from originals/ back into the working tree.

Mirrors pre-optimization backups (first-seen-wins copies made by
optimize-media.py) over the repo tree:
- Overwrites every still-existing quantized/converted file with its pristine
  original.
- For files that were deleted by WebP conversion (NN.ext -> NN.webp), removes
  the .webp and restores the original, rewriting `images/NN.webp` references
  in project markdown back to the original extension.
- Skips the disaster-recovery download set (NN_<media-id>~mv2 names) — those
  are Wix-source re-fetches, not repo mirrors — and never adds files that were
  never part of the tree.
"""

import glob
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "originals")


def main():
    restored = overwritten = 0
    for base in ("content", "assets"):
        for f in sorted(glob.glob(f"{ORIG}/{base}/**/*", recursive=True)):
            if not os.path.isfile(f):
                continue
            name = os.path.basename(f)
            if name.startswith("."):
                continue
            stem, ext = os.path.splitext(name)
            if "~mv2" in name:
                continue
            it = os.path.relpath(f, ORIG)
            target = os.path.join(ROOT, it)
            if os.path.isfile(target):
                shutil.copy2(f, target)
                overwritten += 1
            elif ext.lower() in (".png", ".jpg", ".jpeg") and base == "content":
                # deleted by conversion: restore sibling .webp -> original ext
                projdir = os.path.dirname(target)
                webp = os.path.join(projdir, stem + ".webp")
                if os.path.isfile(webp):
                    os.remove(webp)
                    shutil.copy2(f, target)
                    restored += 1
                    rewrite_md(projdir, stem, ext, webp)
                # else: fetch-only differential — do not add
    print(
        f"restore-originals: {overwritten} overwritten, {restored} deleted-by-conversion files restored"
    )


def rewrite_md(projdir, stem, ext, webp):
    for md in glob.glob(f"{projdir}/*.md"):
        t = open(md, encoding="utf-8").read()
        if stem + ".webp" in t:
            open(md, "w", encoding="utf-8").write(t.replace(stem + ".webp", stem + ext))


if __name__ == "__main__":
    main()
