"""Validate the starter site's basic structure and local references."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


class PageCheck(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.direction = None
        self.title = False
        self.h1 = False
        self.errors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
            self.direction = attrs.get("dir")
        if tag == "title":
            self.title = True
        if tag == "h1":
            self.h1 = True
        if tag == "img" and not attrs.get("alt"):
            self.errors.append("صورة بلا وصف alt")
        for key in ("src", "href"):
            value = attrs.get(key, "")
            if not value or value.startswith(("#", "//")):
                continue
            parsed = urlsplit(value)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = (ROOT / parsed.path.lstrip("/")).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                self.errors.append(f"مرجع محلي مفقود: {value}")


def main():
    page = ROOT / "index.html"
    check = PageCheck()
    check.feed(page.read_text(encoding="utf-8"))
    if check.lang != "ar" or check.direction != "rtl":
        check.errors.append("يجب تحديد lang=ar و dir=rtl")
    if not check.title or not check.h1:
        check.errors.append("الصفحة تحتاج title و h1")
    if check.errors:
        raise SystemExit("\n".join(check.errors))
    print("فحص البنية والملفات المحلية: ناجح")


if __name__ == "__main__":
    main()
