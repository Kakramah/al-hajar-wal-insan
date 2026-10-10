#!/bin/bash
# لقطتا الهاتف والحاسوب لصفحة محلية، لتنظر إليهما بالعين قبل التسليم (قواعد الويب 6.2.5).
#   bash لقطات.sh [index.html] [مجلد_المخرجات]
# تحتاج Chrome headless: Google Chrome أو headless_shell الذي ينزّله Playwright.
# أداة مساندة وليست بنداً في البوابة: لا ترسب ولا تحكم، فالحكم للعين.
IN="${1:-index.html}"; OUT="${2:-.}"
[ -f "$IN" ] || { echo "✗ لا أجد $IN: شغّلها من جذر المشروع"; exit 2; }
HS="$(ls -d "$HOME"/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell 2>/dev/null | tail -1)"
[ -x "$HS" ] || HS="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$HS" ] || { echo "✗ لا متصفح headless. ثبّت Google Chrome أو: npx playwright install chromium-headless-shell"; exit 2; }
ABS="$(cd "$(dirname "$IN")" && pwd)/$(basename "$IN")"
snap(){ # العرض الارتفاع الاسم
  rm -f "$OUT/$3"
  "$HS" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=4000 \
        --screenshot="$OUT/$3" --window-size="$1,$2" "file://$ABS" >/dev/null 2>&1 &
  p=$!; for _ in $(seq 1 40); do [ -s "$OUT/$3" ] && break; sleep 1; done; kill $p 2>/dev/null
  [ -s "$OUT/$3" ] && echo "✓ $OUT/$3" || echo "✗ فشلت $3"
}
snap 390 3200 لقطة-390.png
snap 1440 3600 لقطة-1440.png
echo "افتح الصورتين وانظر: هل المعنى يُفهم في خمس ثوانٍ؟ هل لحظة التوقيع في الشاشة الأولى؟ هل شيء مكسور أو متداخل أو فيه تمرير أفقي؟"
