#!/usr/bin/env python3
"""Media optimization pipeline for content/ + assets/ images.

Behavior (idempotent — re-running does nothing for already-processed files):
1. Backup: untouched copies of every matched file go to originals/<mirror-path>
   (gitignored) BEFORE any modification — the reprocessing safety net. Files
   already in originals/ at that path are never overwritten, so the very
   first-seen state of a file wins.
2. Convert: PNG/JPG larger than 1 MB are re-encoded as WebP (quality 78) via
   cwebp when that yields < 60% of the original size; the source file is then
   replaced and every reference (front matter `images:` / `featureimage:`,
   gallery `<img>`, og lists, layout partials for shared assets) is rewritten.
3. Quantize: remaining PNGs via pngquant (quality 70-95, skip-if-larger),
   JPEGs via jpegoptim (max 85, strip metadata).

Requires on PATH: cwebp, pngquant, jpegoptim (brew install webp pngquant jpegoptim).
"""

import glob
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONVERT_MIN = 1_000_000  # bytes; smaller files skip conversion
WEBP_Q = 78
GUARD = 0.60  # conversion must shrink below this ratio to be accepted

PNG_QUANT = [
    "pngquant",
    "--strip",
    "--skip-if-larger",
    "--quality",
    "70-95",
    "--force",
    "--ext",
    ".png",
]
JPG_OPTIM = ["jpegoptim", "--strip-all", "--max=85", "--quiet"]
MAX_WIDTH = 1600  # 2x max display width; anything wider gets resized on convert


def image_dims(src):
    """Width/height of a PNG or JPEG byte-wise (no Pillow dependency)."""
    with open(src, "rb") as f:
        data = f.read(26)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] == b"\xff\xd8":  # JPEG: scan for SOF0..SOF15 (skip DHT/DAC/RST)
        data = open(src, "rb").read(256 * 1024)
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            ):
                return (
                    int.from_bytes(data[i + 9 : i + 11], "big"),
                    int.from_bytes(data[i + 7 : i + 9], "big"),
                )
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
            else:
                i += 2 + int.from_bytes(data[i + 2 : i + 4], "big")
    return None, None


def sh(cmd, paths):
    subprocess.run([*cmd, paths], check=False, stdout=subprocess.DEVNULL)


def main():
    converted = failed = quantized = 0
    total_before = total_after = 0
    for src in sorted(
        glob.glob(f"{ROOT}/content/**/*.png", recursive=True)
        + glob.glob(f"{ROOT}/content/**/*.jp*g", recursive=True)
        + glob.glob(f"{ROOT}/assets/**/*.png", recursive=True)
        + glob.glob(f"{ROOT}/assets/**/*.jp*g", recursive=True)
    ):
        rel = os.path.relpath(src, ROOT)
        size = os.path.getsize(src)
        total_before += size

        # 1) untouched backup, first-seen-wins
        backup = os.path.join(ROOT, "originals", rel)
        if not os.path.exists(backup):
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            shutil.copy2(src, backup)

        # 2) oversize -> WebP. Strategy: dimension-cap wide images to MAX_WIDTH
        #    (2x max display size) first, which beats plain re-encoding for
        #    photographic PNGs; only fall back to the strict ratio-gated plain
        #    conversion when no ratio requirement.
        conv_accepted = False
        if size > CONVERT_MIN:
            attempts = []
            width, height = image_dims(src)
            if width and width > MAX_WIDTH:
                attempts.append(
                    (
                        ["cwebp", "-q", str(WEBP_Q), "-resize", str(MAX_WIDTH), "0"],
                        size * 0.95,
                    )
                )
            attempts.append((["cwebp", "-q", str(WEBP_Q)], size * GUARD))
            for cmd, gate in attempts:
                tmp = src + ".webp-tmp"
                cmd = [*cmd, src, "-o", tmp]
                if subprocess.run(cmd, capture_output=True).returncode != 0:
                    continue
                wsize = os.path.getsize(tmp)
                if wsize < gate:
                    webp = src.rsplit(".", 1)[0] + ".webp"
                    os.replace(tmp, webp)
                    os.remove(src)
                    rewrite_refs(rel, webp, src)
                    converted += 1
                    conv_accepted = True
                    total_after += wsize
                    break
                else:
                    os.remove(tmp)
            if conv_accepted:
                continue
            else:
                failed += 1

        # 3) in-place quantize/optimize
        if src.lower().endswith(".png"):
            sh(PNG_QUANT, src)
        else:
            sh(JPG_OPTIM, src)
        total_after += os.path.getsize(src)
        quantized += 1

    print(
        "optimize-media: %d converted to WebP, %d WebP attempts rejected (kept original),"
        " %d quantized; %d MB -> %.1f MB"
        % (
            converted,
            failed,
            quantized,
            total_before // (1024 * 1024),
            total_after / (1024 * 1024),
        )
    )


def rewrite_refs(old_rel, new_rel, src):
    """Rewrite every textual reference from old file to new one.

    - Content-bundle assets: referenced as `images/<name>.<ext>` inside *.md
      under the same project directory (EN and JA share the bundle).
    - Shared assets: referenced by asset-relative path (img/…) anywhere.
    """
    name = os.path.basename(src)
    new_name = os.path.basename(new_rel)
    targets = []
    rel_dir = os.path.dirname(old_rel)
    if rel_dir.startswith("content/"):
        # md files live at the bundle root (parent of images/), never inside images/
        targets += glob.glob(f"{ROOT}/{rel_dir}/*.md") + glob.glob(
            f"{ROOT}/{rel_dir}/../*.md"
        )
        old_needle, new_needle = (
            name,
            new_name,
        )  # `images/01.png` etc.; unique inside its bundle
    else:  # assets/img/… shared
        targets += (
            glob.glob(f"{ROOT}/content/**/*.md", recursive=True)
            + glob.glob(f"{ROOT}/layouts/**/*.html", recursive=True)
            + glob.glob(f"{ROOT}/config/**/*.toml", recursive=True)
        )
        old_needle, new_needle = old_rel, new_rel
    for t in targets:
        text = open(t, encoding="utf-8").read()
        if old_needle in text:
            open(t, "w", encoding="utf-8").write(text.replace(old_needle, new_needle))


def repair_dangling_refs():
    """Self-heal: rewrite images/NN.<ext> refs whose target was already
    converted to NNN.webp (covers prior runs of the buggy rewriter)."""
    fixed = 0
    for md in glob.glob(f"{ROOT}/content/projects/*/index*.md"):
        text = open(md, encoding="utf-8").read()
        orig = text
        for m in set(re.findall(r"images/(\d+\.(?:png|jpe?g))", text)):
            if os.path.exists(os.path.join(ROOT, os.path.dirname(md), "images", m)):
                continue
            webp = m.rsplit(".", 1)[0] + ".webp"
            if os.path.exists(
                os.path.join(
                    ROOT, os.path.dirname(md), "images", webp.rsplit("/", 1)[1]
                )
            ):
                text = text.replace(m, webp)
        if text != orig:
            open(md, "w", encoding="utf-8").write(text)
            fixed += 1
    return fixed


if __name__ == "__main__":
    sys.exit(main())
