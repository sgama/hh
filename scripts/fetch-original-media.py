#!/usr/bin/env python3
"""Fetch every original gallery/image from the original Wix portfolio site.

Safety net for `originals/` (gitignored): reproduces the exact image set of
each project bundle at ORIGINAL Wix quality, ordered and numbered the same way
the build bundles are (01..N from the live project page's gallery order).

- Downloads go ONLY to originals/<path-mirror-of-content/> — repo content is
  never touched. Re-run any time; existing files are skipped.
- Requires: python3 (stdlib) + curl on PATH. Wix pages are fetched live, so an
  unpublished/moved source page will report misses rather than delete anything.

Usage:
    python3 scripts/fetch-original-media.py            # fill originals/
    python3 scripts/fetch-original-media.py --force    # redownload everything
"""

import re
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "originals")
SLUG_TO_DIR = {
    "ai-visual-creation": "ai-visual-creation",
    "brand-identity-social-direction": "brand-identity-social-direction",
    "e-commerce-visual-direction": "e-commerce-visual-direction",
    "email": "email-newsletter-marketing",
    "project-title-1": "photoshoot-and-studio-direction",
    "project-title-2": "ecommerce-operations-specialist",
    "project-title-3": "digital-marketing-campaign",
    "project-title-4": "digital-marketing-photography",
    "project-title-5": "fashion-design-and-pattern-making",
    "project-title-6": "graphic-design-for-banner",
    "untitled-project": "paid-social-advertising",
    "untitled-project-9d03d3": "store-display-merchandising",
}
BASE_URL = (
    "https://hharuna0606.wixsite.com/portfolio/portfolio-collections/my-portfolio/"
)
IMG_EXT = {"png", "jpg", "jpeg", "webp", "gif", "avif"}
MAGIC = (b"\x89PNG", b"\xff\xd8\xff", b"RIFF", b"GIF8")

# Shared image assets (about hero/poster, author photo) mirrored into originals.
ASSETS = [
    "assets/img/about-hero.mp4",
    "assets/img/about-hero-poster.jpg",
    "assets/img/author.jpg",
    "assets/img/cert-1.png",
    "assets/img/cert-2.png",
    "assets/img/cert-3.png",
    "assets/img/cert-4.png",
    "assets/img/tools-brands.png",
]


def curl(url, out=None, quiet=True):
    cmd = ["curl", "-s" if quiet else "-S", "-L", "--max-time", "60"]
    if out:
        cmd += ["-o", out]
    cmd.append(url)
    subprocess.run(cmd, check=True)
    return out


def page(slug):
    f = os.path.join("/tmp/opencode", "wix-%s.html" % slug)
    curl(BASE_URL + slug, out=f)
    with open(f, encoding="utf-8", errors="ignore") as fh:
        return fh.read()


def gallery_media(slug):
    """Distinct wixstatic media of a project page, in document order."""
    p = page(slug)
    seen, seq = set(), []
    for m in re.finditer(r"static\.wixstatic\.com/media/([a-f0-9_]+~mv2)\.([a-z]+)", p):
        base, ext = m.group(1), m.group(2)
        if ext in IMG_EXT and base not in seen:
            seen.add(base)
            seq.append(base + "." + ext)
    return seq


def looks_like_image(path):
    try:
        with open(path, "rb") as fh:
            return fh.read(8).startswith(MAGIC)
    except OSError:
        return False


def fetch(url, dest):
    if looks_like_image(dest) and os.path.getsize(dest) > 0:
        return True
    try:
        curl(url, out=dest, quiet=False)
    except subprocess.CalledProcessError:
        return False
    return looks_like_image(dest) and os.path.getsize(dest) > 0


def mirror_repo_files(out):
    n = 0
    for rel in ASSETS:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            continue
        dest = os.path.join(out, rel)
        if os.path.exists(dest):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        subprocess.run(["cp", src, dest], check=True)
        n += 1
    return n


def main():
    force = "--force" in sys.argv
    out = DEFAULT_OUT
    os.makedirs(out, exist_ok=True)
    assets = mirror_repo_files(out)

    added = missing = False, None
    ok = fail = 0
    for slug, dirn in SLUG_TO_DIR.items():
        prefs = gallery_media(slug)
        if force:
            for i, name in enumerate(prefs, 1):
                dest = os.path.join(
                    out, "content/projects/%s/images/%02d_%s" % (dirn, i, name)
                )
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                url = "https://static.wixstatic.com/media/%s" % name
                if fetch(url, dest):
                    ok += 1
                else:
                    fail += 1
                    print("FAIL: %s/%02d_%s" % (dirn, i, name))
        else:
            # default mode only fills numeric slots that do not exist yet
            have = set()
            d = os.path.join(out, "content/projects/%s/images" % dirn)
            if os.path.isdir(d):
                have = {f for f in os.listdir(d) if re.match(r"^\d{2}_", f)}
            for i, name in enumerate(prefs, 1):
                if "%02d_" % i in " ".join(have):
                    continue
                dest = os.path.join(
                    out, "content/projects/%s/images/%02d_%s" % (dirn, i, name)
                )
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                url = "https://static.wixstatic.com/media/%s" % name
                if fetch(url, dest):
                    ok += 1
                else:
                    fail += 1
                    print("FAIL: %s/%02d_%s" % (dirn, i, name))
    if assets:
        print("asset mirrors copied: %d" % assets)
    print("downloaded %d originals, %d failures; originals/ at %s" % (ok, fail, out))


if __name__ == "__main__":
    main()
