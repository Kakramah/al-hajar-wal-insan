#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""بنك الأساليب — مصغّرات أساليب مواقع خلدون وورقة المقارنة قبل الاختيار.
المالك: docs/سجل-الهوية.md §بنك الأساليب (القاعدة 10.5 في docs/قواعد-الويب.md).

  python3 scripts/بنك-الأساليب.py التقاط <مجلد الموقع> <NN-slug> [--out مجلد]
  python3 scripts/بنك-الأساليب.py ورقة <NN-slug> [<NN-slug> ...] [--out ملف.png]
  python3 scripts/بنك-الأساليب.py بصمة <مجلد الموقع> [...]
"""
import os, re, sys, glob, time, colorsys, subprocess, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

V = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # جذر khaldoun-web-starter
THUMBS = os.path.join(V, "docs", "site-styles")
REGISTRY = os.path.join(V, "docs", "سجل-الهوية.md")


def _chrome():
    """Chrome على الماك، ثم Chromium في الجلسة السحابية (Playwright أو PATH)."""
    for p in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              *sorted(glob.glob("/opt/pw-browsers/chromium*/chrome-linux/chrome")), "/opt/pw-browsers/chromium"]:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    for name in ("chromium", "chromium-browser", "google-chrome"):
        if shutil.which(name):
            return shutil.which(name)
    sys.exit("❌ لا Chrome ولا Chromium على هذا الجهاز")


SHOT_W, SHOT_H = 1440, 900
THUMB_W, THUMB_H = 480, 300


def capture(site_dir, slug, out_dir=THUMBS, wait_ms=4000):
    """يلتقط index.html المحلي عبر Chrome headless ثم يصغّره إلى JPG."""
    index = os.path.join(os.path.abspath(site_dir), "index.html")
    if not os.path.isfile(index):
        sys.exit(f"❌ لا index.html في {site_dir}")
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "shot.png")
        # Chrome على هذا الجهاز يكتب اللقطة ثم لا يخرج؛ ننتظر ثبات حجم الملف ثم نغلقه.
        p = subprocess.Popen([_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                              "--no-first-run", "--disable-extensions", "--disable-sync",
                              f"--window-size={SHOT_W},{SHOT_H}", f"--virtual-time-budget={wait_ms}",
                              f"--user-data-dir={tmp}/profile", f"--screenshot={png}",
                              "file://" + index], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start, last = time.time(), -1
        while time.time() - start < 60:
            size = os.path.getsize(png) if os.path.exists(png) else -1
            if size > 0 and size == last:
                break
            last = size
            time.sleep(1)
        p.kill()
        p.wait()
        if not os.path.exists(png):
            sys.exit(f"❌ لم تُكتب اللقطة خلال 60 ثانية: {site_dir}")
        img = Image.open(png).convert("RGB").resize((THUMB_W, THUMB_H), Image.LANCZOS)
    dst = os.path.join(out_dir, slug + ".jpg")
    img.save(dst, "JPEG", quality=70, optimize=True)
    print(f"✅ {dst} — {os.path.getsize(dst)//1024} ك.ب")
    return dst


def _lum_hue(h):
    h = h.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h[:6]
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b, int(colorsys.rgb_to_hls(r, g, b)[0] * 360)


def fingerprint(site_dir):
    """البصمة الأولية من CSS: الأرضية ولون البطل والخط. الشبكة والملمس تُحسم بالنظر."""
    txt = ""
    for f in glob.glob(site_dir + "/*.css") + glob.glob(site_dir + "/*/*.css") + glob.glob(site_dir + "/index.html"):
        txt += open(f, encoding="utf-8", errors="ignore").read()
    root = re.findall(r"--([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b", txt)
    pick = lambda pat: next((v for k, v in root if re.search(pat, k, re.I)), "")
    bg = pick(r"bg|background|ink|night|base|surface|paper|canvas")
    acc = pick(r"accent|gold|primary|hero|brand|amber|copper|red|blue")
    fonts = []
    for m in re.findall(r"font-family\s*:\s*([^;}{]+)", txt):
        n = m.split(",")[0].strip().strip("'\"")
        if n and not n.startswith("var") and n not in fonts:
            fonts.append(n)
    out = {"bg": bg, "accent": acc, "fonts": "/".join(fonts[:2])}
    if bg:
        out["bg_lum"] = round(_lum_hue(bg)[0], 2)
    if acc:
        out["accent_hue"] = _lum_hue(acc)[1]
    return out


def _font(size):
    # التسميات لاتينية (NN-slug)؛ GeezaPro بلا حروف لاتينية فكانت تخرج مربعات.
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial Unicode.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheet(slugs, out_png):
    """ورقة مقارنة: مصغّرة لكل أسلوب برقمه، وخانة «أسلوب جديد» في الآخر."""
    cols, pad, label_h = 2, 24, 44
    cells = slugs + ["__new__"]
    rows = (len(cells) + cols - 1) // cols
    W = cols * THUMB_W + (cols + 1) * pad
    H = rows * (THUMB_H + label_h) + (rows + 1) * pad
    canvas = Image.new("RGB", (W, H), (246, 244, 239))
    draw, f = ImageDraw.Draw(canvas), _font(22)
    for i, slug in enumerate(cells):
        x = pad + (i % cols) * (THUMB_W + pad)
        y = pad + (i // cols) * (THUMB_H + label_h + pad)
        if slug == "__new__":
            draw.rectangle([x, y, x + THUMB_W, y + THUMB_H], outline=(120, 120, 120), width=3)
            draw.text((x + THUMB_W // 2, y + THUMB_H // 2), "+ new style", fill=(90, 90, 90), font=f, anchor="mm")
            label = "new"
        else:
            p = os.path.join(THUMBS, slug + ".jpg")
            if not os.path.exists(p):
                sys.exit(f"❌ لا مصغّرة: {p}")
            canvas.paste(Image.open(p), (x, y))
            label = slug
        draw.text((x, y + THUMB_H + 10), label, fill=(30, 30, 30), font=f)
    canvas.save(out_png)
    print(f"✅ {out_png}")
    return out_png


def recent_warning(slugs, last=2):
    """القاعدة 2.0.0: تنبيه مرة واحدة إن كان الأسلوب في آخر موقعين من جدول المواقع في سجل الهوية."""
    if not os.path.isfile(REGISTRY):
        return
    rows = [l for l in open(REGISTRY, encoding="utf-8") if re.match(r"^\|\s*\[`[^`]+`\]", l)]
    recent = []
    for l in rows[-last:]:
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        site = re.search(r"`([^`]+)`", cells[0]).group(1)
        style = cells[2] if len(cells) > 2 else ""
        recent.append((site, style))
    for slug in slugs:
        nn = slug[:2]
        used = [site for site, style in recent if style == nn]
        if used:
            print(f"⚠ الأسلوب {nn} استُعمل في آخر موقعين: {'، '.join(used)} (2.0.0). اذكر لماذا يُختار مرة أخرى.")


def _opt(args, name, default):
    if name in args:
        i = args.index(name)
        val = args[i + 1]
        del args[i:i + 2]
        return val
    return default


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a.pop(0)
    if cmd == "التقاط" and len(a) >= 2:
        out = _opt(a, "--out", THUMBS)
        # --wait للمواقع ذات شاشة التحميل: اللقطة الأولى تخرج سوداء إن كان الانتظار قصيراً
        wait = int(_opt(a, "--wait", "4000"))
        capture(a[0], a[1], out, wait)
    elif cmd == "ورقة" and a:
        out = _opt(a, "--out", os.path.join(tempfile.gettempdir(), "style-sheet.png"))
        sheet(a, out)
        recent_warning(a)
    elif cmd == "بصمة" and a:
        for d in a:
            print(os.path.basename(os.path.normpath(d)), fingerprint(d))
    else:
        sys.exit(__doc__)
