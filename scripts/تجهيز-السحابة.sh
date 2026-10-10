#!/usr/bin/env bash
# تجهيز جلسة سحابية (claude.ai/code) لبناء أي موقع بقواعد الويب.
# الجلسة السحابية لا ترى جهاز خلدون، فهذا الملف يضع ما تحتاجه القواعد في أماكنها:
#   قواعد الويب وبوابتها ← ~/khaldoun-projects/khaldoun-web-starter
#   بيت خلدون (القيم والعقاب) ← ~/khaldoun، والعقاب ← ~/khaldoun-brand
#   المشروع المفتوح في الجلسة ← ~/khaldoun-projects/<اسمه>
# يُشغَّل من جذر مستودع المشروع، ويُعاد تشغيله بلا ضرر:
#   bash ~/khaldoun-projects/khaldoun-web-starter/scripts/تجهيز-السحابة.sh

set -u
say() { printf '%s\n' "$*"; }
fail=0
P="$HOME/khaldoun-projects"
mkdir -p "$P"

clone() { # clone <owner/repo> <dest>
  [ -d "$2/.git" ] && { git -C "$2" pull -q --ff-only 2>/dev/null; say "✓ $1 موجود ومحدَّث"; return 0; }
  if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
    gh repo clone "$1" "$2" -- -q --depth 1 && { say "✓ استُنسخ $1"; return 0; }
  fi
  git clone -q --depth 1 "https://github.com/$1.git" "$2" && { say "✓ استُنسخ $1"; return 0; }
  say "✗ تعذّر استنساخ $1: أعطِ Claude على GitHub صلاحية هذا المستودع ثم أعد التشغيل"; fail=1; return 1
}

# ١ قواعد الويب
clone Kakramah/khaldoun-web-starter "$P/khaldoun-web-starter"

# ٢ بيت خلدون، والعقاب منه
clone Kakramah/khaldoun "$HOME/khaldoun"
if [ -d "$HOME/khaldoun/assets/brand" ] && [ ! -e "$HOME/khaldoun-brand" ]; then
  ln -s "$HOME/khaldoun/assets/brand" "$HOME/khaldoun-brand"
fi

# ٣ المشروع المفتوح في الجلسة يعيش في ~/khaldoun-projects/<اسمه> (قواعد الويب 0.1)
root=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -n "$root" ] && [ "$(basename "$root")" != "khaldoun-web-starter" ]; then
  name=$(basename "$root")
  case "$root" in
    "$P"/*) say "✓ المشروع في مكانه: $root" ;;
    *) [ -e "$P/$name" ] || ln -s "$root" "$P/$name"; say "✓ المشروع مربوط: $P/$name ← $root" ;;
  esac
else
  say "⚠ لم يُشغَّل من جذر مستودع مشروع؛ اربطه بنفسك في $P/<اسمه>"
fi

# ٤ فحص التهيئة (قواعد الويب 0.2)
for f in eagle-emblem-metal.svg eagle-emblem.svg; do
  [ -f "$HOME/khaldoun-brand/eagle/$f" ] || { say "✗ أصل العقاب مفقود: $f"; fail=1; }
done
[ -f "$HOME/khaldoun/identity/values.md" ] || { say "✗ values.md مفقود"; fail=1; }
command -v gh >/dev/null && gh auth status >/dev/null 2>&1 \
  || say "⚠ gh غير جاهز: طلبات الدمج تُفتح من أداة الجلسة نفسها"

# ٥ بنوك الصور خارج git فلا تصل إلى السحابة (3.4.1)
say "⚠ بنوك الصور الحقيقية على جهاز خلدون وحده: اطلب منه الصور، أو اكتب برومبتات التوليد ليولّدها ويرفعها"

[ $fail -eq 0 ] && say "══ ✓ الجلسة جاهزة: اقرأ قواعد الويب وابدأ ══" || say "══ ✗ التجهيز ناقص: أصلح ما سبق قبل أي كود ══"
exit $fail
