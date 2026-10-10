#!/bin/bash
# بوابة تسليم مواقع خلدون · دستور الويب §6.1
# التشغيل من جذر مجلد المشروع:
#   bash ~/khaldoun-projects/khaldoun-web-starter/scripts/بوابة-الويب.sh
# كل فحص هنا أمسك عيباً حقيقياً وقع في مشروع منشور. ما لا يُقاس آلياً مكانه §6.2.
fail=0
say(){ echo "$1"; }
[ -f index.html ] || { echo "✗ لا index.html هنا. شغّل البوابة من جذر المشروع"; exit 2; }

# 6.1.0 البنية ونوع الموقع (2.3.1 · 0.3)
# الأوراق والسكربتات تُقرأ مما يستدعيه index.html فعلاً، فالاسم المخالف لا يُنتج رسوباً كاذباً في بنود تالية.
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
CSS="$TMP/all.css"; JS="$TMP/all.js"; : >"$CSS"; : >"$JS"
python3 - "$CSS" "$JS" <<'PY'
import re,sys,os
h=open('index.html',encoding='utf-8').read()
loc=lambda u: not re.match(r'(https?:)?//',u)
css=[u for u in re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"',h)+re.findall(r'<link\b[^>]*href="([^"]+\.css)"[^>]*rel="stylesheet"',h) if loc(u)]
js=[u for u in re.findall(r'<script\b[^>]*src="([^"]+)"',h) if loc(u)]
inl_css=''.join(re.findall(r'<style[^>]*>(.*?)</style>',h,re.S))
inl_js=''.join(re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>',h,re.S))
def cat(files,inline,out):
    with open(out,'w',encoding='utf-8') as o:
        for f in dict.fromkeys(files):
            p=f.split('?')[0].lstrip('./')
            if os.path.isfile(p): o.write(open(p,encoding='utf-8',errors='ignore').read()+'\n')
        o.write(inline)
cat(css,inl_css,sys.argv[1]); cat(js,inl_js,sys.argv[2])
open(sys.argv[1]+'.names','w').write(' '.join(dict.fromkeys(css)))
open(sys.argv[2]+'.names','w').write(' '.join(dict.fromkeys(js)))
PY
cssn=$(cat "$CSS.names"); jsn=$(cat "$JS.names")
[ -s "$CSS" ] || { say "✗ 6.1.0 لا ورقة أنماط مستدعاة من index.html"; fail=1; }
case " $cssn " in *" style.css "*) : ;; *) say "⚠ 6.1.0 الأنماط في «${cssn:-مضمّنة}» لا style.css (2.3.1)";; esac
[ -n "$jsn" ] && case " $jsn " in *" script.js "*) : ;; *) say "⚠ 6.1.0 السكربت في «$jsn» لا script.js (2.3.1)";; esac
TYPE=$(grep -m1 -oE 'النوع: *(قصة|واجهة|أداة|فهرس)' DESIGN.md 2>/dev/null | sed 's/.*: *//')
[ -n "$TYPE" ] && say "✓ 6.1.0 النوع: $TYPE" || { TYPE="قصة"; say "⚠ 6.1.0 لا «النوع:» في DESIGN.md، يُفحص قصةً (0.3)"; }

# 6.1.1 لا مسارات مطلقة
grep -rn "/Users/\|file:///" --include="*.html" --include="*.css" --include="*.js" . >/dev/null \
  && { say "✗ 6.1.1 مسار مطلق"; fail=1; } || say "✓ 6.1.1 المسارات نسبية"

# 6.1.2 لا ملفات نظام
find . \( -name ".DS_Store" -o -name "._*" -o -name "*.bak" -o -name ".env" \) -not -path "./.git/*" -print | grep -q . \
  && { say "✗ 6.1.2 ملفات نظام"; fail=1; } || say "✓ 6.1.2 لا ملفات نظام"

# 6.1.3 لا صور يتيمة · 6.1.4 لا صور مفقودة
orph=0
for f in images/*; do
  [ -e "$f" ] || continue
  echo "$f" | grep -qiE '\.(jpe?g|png|webp|gif|svg|avif)$' || continue
  grep -qr "$(basename "$f")" --include="*.html" --include="*.css" --include="*.js" --include="*.json" . \
    || { say "✗ 6.1.3 صورة يتيمة: $f"; orph=1; fail=1; }
done
[ "$orph" = 0 ] && say "✓ 6.1.3 لا صور يتيمة"
miss=0
while read -r pth; do
  [ -f "$pth" ] || { say "✗ 6.1.4 صورة مفقودة: $pth"; miss=1; fail=1; }
done < <(grep -oh 'images/[A-Za-z0-9._-]*' -r --include="*.html" --include="*.css" . | sort -u)
[ "$miss" = 0 ] && say "✓ 6.1.4 كل الصور المستدعاة موجودة"

# 6.1.5 سقوف الحجم (5.9.1): 500KB للصورة، 800KB للبطل، 4MB للمجلد
while read -r f; do
  kb=$(du -k "$f" | cut -f1)
  if [ "$kb" -gt 800 ]; then say "✗ 6.1.5 ${kb}KB > 800KB: $f"; fail=1
  else say "⚠ 6.1.5 ${kb}KB > 500KB: $f (مسموح لصورة البطل وحدها)"; fi
done < <(find images -type f -size +500k 2>/dev/null)
tot=$(du -sk images 2>/dev/null | cut -f1)
if [ "${tot:-0}" -gt 4096 ]; then say "✗ 6.1.5 مجلد الصور ${tot}KB > 4MB"; fail=1
else say "✓ 6.1.5 حجم الصور ${tot:-0}KB"; fi

# 6.1.6 الأساسيات والوصولية. الوسوم تُقرأ عبر الأسطر، فوسمٌ موزّع على سطرين سليم
grep -q 'lang="ar"' index.html && grep -q 'dir="rtl"' index.html \
  && say "✓ 6.1.6 lang/dir" || { say "✗ 6.1.6 lang/dir ناقص"; fail=1; }
noalt=$(python3 -c "
import re
h=open('index.html',encoding='utf-8').read()
imgs=re.findall(r'<img\b[^>]*>',h,re.S)
print(sum(1 for i in imgs if not re.search(r'\balt\s*=',i)), len(imgs))" 2>/dev/null || echo "0 0")
set -- $noalt
[ "${1:-0}" -eq 0 ] && say "✓ 6.1.6 alt مكتملة (${2:-0} صورة)" \
  || { say "✗ 6.1.6 صور بلا alt: $1 من $2"; fail=1; }

# 6.1.7 بطاقة المشاركة (5.10)
og=0
for m in "og:title" "og:description" "og:image" "og:url" "twitter:card"; do
  grep -q "$m" index.html || { say "✗ 6.1.7 ناقص: $m"; og=1; fail=1; }
done
[ "$og" = 0 ] && say "✓ 6.1.7 بطاقة المشاركة كاملة"
grep -q 'og:image" content="https://' index.html \
  && say "✓ 6.1.7 og:image مطلق" || say "⚠ 6.1.7 og:image غير مطلق، يُصلَح بعد النشر (2.6.2)"

# 6.1.8 التوقيع والعقاب منسوخان (3.1 · 3.3)
id=0
grep -q "𝓚𝓱𝓪𝓵𝓭𝓸𝓾𝓷𝓐𝓴𝓻𝓪𝓶𝓪𝓱" index.html || { say "✗ 6.1.8 التوقيع مفقود"; id=1; fail=1; }
ls images/eagle-emblem*.svg >/dev/null 2>&1 || { say "✗ 6.1.8 العقاب غير منسوخ إلى images/ (3.3.2)"; id=1; fail=1; }
[ "$id" = 0 ] && say "✓ 6.1.8 التوقيع والعقاب"

# 6.1.9 الخطوط محلية فعلاً (3.6)
grep -q "fonts.googleapis\|fonts.gstatic" index.html "$CSS" 2>/dev/null \
  && { say "✗ 6.1.9 استيراد خط خارجي (3.6.1)"; fail=1; } || say "✓ 6.1.9 لا استيراد خارجي"
nff=$(grep -c "@font-face" "$CSS" 2>/dev/null); nff=${nff:-0}
nwf=$(ls fonts/*.woff2 fonts/*.ttf 2>/dev/null | wc -l | tr -d " ")
if [ "$nff" -gt 0 ] && [ "${nwf:-0}" -gt 0 ]; then
  grep -q "font-display: *swap" "$CSS" \
    && say "✓ 6.1.9 خطوط محلية: $nwf ملفاً · $nff @font-face · swap" \
    || { say "✗ 6.1.9 ينقص font-display: swap (3.6.4)"; fail=1; }
else
  say "✗ 6.1.9 لا خطوط محلية: @font-face:$nff · fonts/:${nwf:-0} (3.6.2)"; fail=1
fi

# 6.1.10 .gitignore
[ -f .gitignore ] && say "✓ 6.1.10 .gitignore" || { say "✗ 6.1.10 .gitignore مفقود"; fail=1; }

# 6.1.11 مشاركة عاملة (8.6): إلزامية للقصة والفهرس
if grep -qE "navigator\.share|clipboard\.writeText|wa\.me/\?text|t\.me/share|twitter\.com/intent|x\.com/intent" index.html "$JS" 2>/dev/null; then
  say "✓ 6.1.11 مشاركة عاملة"
elif [ "$TYPE" = "قصة" ] || [ "$TYPE" = "فهرس" ]; then
  say "✗ 6.1.11 لا كتلة مشاركة عاملة (8.6)"; fail=1
else
  say "⚠ 6.1.11 لا مشاركة، مستحسنة للـ$TYPE (8.6)"
fi

# 6.1.12 النموذج: لوحة نجاح ومصيدة ولا alert (4.10)
if grep -q "web3forms" index.html "$JS" 2>/dev/null; then
  grep -qE "success-message|success-card" index.html "$JS" \
    && say "✓ 6.1.12 لوحة نجاح" || { say "✗ 6.1.12 نموذج بلا لوحة نجاح (8.2.3)"; fail=1; }
  grep -q "botcheck" index.html \
    && say "✓ 6.1.12 مصيدة النموذج" || { say "✗ 6.1.12 لا حقل مصيدة (4.10.4)"; fail=1; }
  sed -E 's://.*::' "$JS" index.html 2>/dev/null | grep -qE '(^|[^.[:alnum:]])alert[[:space:]]*\(' \
    && { say "✗ 6.1.12 استُعمل alert() (4.10.2)"; fail=1; } || say "✓ 6.1.12 لا alert()"
fi

# 6.1.13 DESIGN.md يحمل بطاقة الهوية (5.11 · 10.3)
[ -f DESIGN.md ] && say "✓ 6.1.13 DESIGN.md موجود" || { say "✗ 6.1.13 DESIGN.md مفقود (5.11)"; fail=1; }

# 6.1.14 لا hex حرّ خارج توكنات :root، ولا في JS (10.7.2)
if grep -q ":root" "$CSS"; then
  css_free=$(perl -0pe 's#/\*.*?\*/##gs; s#:root\s*\{[^}]*\}##gs' "$CSS" \
    | grep -oiE "#[0-9a-f]{3,8}\b" | sort -u | wc -l | tr -d " ")
  js_free=$(perl -0pe 's{/\*.*?\*/}{}gs; s{//[^\n]*}{}g' "$JS" 2>/dev/null \
    | grep -oiE "#[0-9a-f]{3,8}\b" | sort -u | wc -l | tr -d " ")
  total=$((css_free + js_free))
  [ "$total" -eq 0 ] && say "✓ 6.1.14 لا hex حرّ" \
    || { say "✗ 6.1.14 $total لوناً خارج التوكنات، css:$css_free js:$js_free (10.7.2)"; fail=1; }
else
  say "✗ 6.1.14 لا كتلة :root للتوكنات (10.7.1)"; fail=1
fi

# 6.1.15 طبقة المجموعة: لكل عنصر عنوان ووصف، وتنقّل بالأسهم (8.3ب) · للقصة والواجهة
if [ "$TYPE" = "قصة" ] || [ "$TYPE" = "واجهة" ]; then
n_img=$(python3 -c "
import re
h=open('index.html',encoding='utf-8').read()
imgs=re.findall(r'<img\b[^>]*>',h,re.S)
skip=('eagle','logo','emblem','favicon','icon')
print(len([i for i in imgs if not any(k in i.lower() for k in skip)]))" 2>/dev/null || echo 0)
ttl=$(grep -o 'data-title=' index.html 2>/dev/null | wc -l | tr -d " ")
dsc=$(grep -o 'data-desc=' index.html 2>/dev/null | wc -l | tr -d " ")
if [ "${n_img:-0}" -gt 3 ] && [ "${ttl:-0}" -eq 0 ]; then
  say "✗ 6.1.15 ${n_img} صورة بلا عنوان ولا وصف (8.3ب.2)"; fail=1
elif [ "${ttl:-0}" -gt 0 ]; then
  [ "$ttl" -eq "$dsc" ] && say "✓ 6.1.15 المجموعة: $ttl عنصراً لكلٍّ عنوان ووصف" \
    || { say "✗ 6.1.15 عناوين:$ttl أوصاف:$dsc (8.3ب.2)"; fail=1; }
  grep -qE "ArrowRight|ArrowLeft" "$JS" 2>/dev/null \
    && say "✓ 6.1.15 تنقّل بالأسهم" || { say "✗ 6.1.15 الـLightbox لا يتنقّل (8.3ب.4)"; fail=1; }
fi
fi

# 6.1.17 لا شَخْطة (— –) في نص يراه الزائر، HTML وJS، والتعليقات مستثناة (4.12)
nd=$(python3 -c "
import re,sys
n=0
try:
    h=open('index.html',encoding='utf-8').read()
    h=re.sub(r'<(script|style)[^>]*>.*?</\1>','',h,flags=re.S); h=re.sub(r'<!--.*?-->','',h,flags=re.S)
    n+=h.count(chr(8212))+h.count(chr(8211))
except Exception: pass
try:
    j=open(sys.argv[1],encoding='utf-8').read()
    j=re.sub(r'/\*.*?\*/','',j,flags=re.S); j=re.sub(r'//[^\n]*','',j)
    n+=j.count(chr(8212))+j.count(chr(8211))
except Exception: pass
print(n)" "$JS" 2>/dev/null || echo 0)
[ "${nd:-0}" -eq 0 ] && say "✓ 6.1.17 لا شَخْطة" \
  || { say "✗ 6.1.17 ${nd} شَخْطة في نص مرئي (4.12)"; fail=1; }

# 6.1.18 الروابط الخارجية آمنة
nrel=$(python3 -c "
import re
h=open('index.html',encoding='utf-8').read()
a=re.findall(r'<a\b[^>]*href=\"https?://[^\"]*\"[^>]*>',h,re.S)
print(len([x for x in a if 'noopener' not in x]))" 2>/dev/null || echo 0)
[ "${nrel:-0}" -eq 0 ] && say "✓ 6.1.18 الروابط الخارجية آمنة" \
  || { say "✗ 6.1.18 ${nrel} رابطاً خارجياً بلا rel=noopener (values.md §1د)"; fail=1; }

# 6.1.19 حسابات خلدون الثلاث، ولا حساب سواها (values.md §1د)
acc=0
for a in "wa.me/966566702030" "instagram.com/khaldounakramah" "mailto:akramahkhaldoun@gmail.com"; do
  grep -q "$a" index.html || { say "✗ 6.1.19 ناقص: $a"; acc=1; fail=1; }
done
bad=$(grep -oE 'mailto:[^"?]+|wa\.me/[0-9]+|instagram\.com/[A-Za-z0-9_.]+' index.html "$JS" 2>/dev/null | sed 's/^[^:]*://' \
  | grep -vxE 'mailto:akramahkhaldoun@gmail\.com|wa\.me/966566702030|instagram\.com/khaldounakramah' | sort -u)
[ -n "$bad" ] && { say "✗ 6.1.19 حساب غير معتمد: $(echo $bad)"; acc=1; fail=1; }
[ "$acc" = 0 ] && say "✓ 6.1.19 الحسابات الثلاث مطابقة"

# 6.1.20 التوقيع المرئي المسبوق بـ@ معزول اتجاهياً (values.md §1هـ)
sigbad=$(python3 -c "
import re
h=open('index.html',encoding='utf-8').read()
body=re.sub(r'<(script|style|head)\b.*?</\1>','',h,flags=re.S|re.I)
n=0
for m in re.finditer(r'@\s*\U0001D4DA\U0001D4F1\U0001D4EA\U0001D4F5\U0001D4ED',body):
    ctx=body[max(0,m.start()-400):m.start()]
    if 'dir=\"ltr\"' not in ctx and 'unicode-bidi' not in ctx: n+=1
print(n)" 2>/dev/null || echo 0)
[ "${sigbad:-0}" -eq 0 ] && say "✓ 6.1.20 التوقيع سليم الاتجاه" \
  || { say "✗ 6.1.20 ${sigbad} توقيعاً بـ@ بلا dir=\"ltr\" (values.md §1هـ)"; fail=1; }

# 6.1.21 صورة الافتتاحية لا تتكرّر (5.12)
dup=$(python3 -c "
import re
h=open('index.html',encoding='utf-8').read()
m=re.search(r'<(header|section)\b[^>]*class=\"[^\"]*hero[^\"]*\".*?</\1>',h,re.S)
if not m: print(0)
else:
    hero=set(re.findall(r'images/([\w.-]+)\.(?:jpg|jpeg|png|webp)',m.group(0)))
    rest=set(re.findall(r'images/([\w.-]+)\.(?:jpg|jpeg|png|webp)',h[m.end():]))
    print(len(hero&rest))" 2>/dev/null || echo 0)
[ "${dup:-0}" -eq 0 ] && say "✓ 6.1.21 الافتتاحية لا تتكرّر" \
  || { say "✗ 6.1.21 صورة الافتتاحية معادة ${dup} مرة (5.12)"; fail=1; }

# 6.1.22 العقاب ظاهر فعلاً، صورةً من ملفه المعدني لا قناع CSS (3.3)
eg=$(python3 -c "
import re,sys
h=open('index.html',encoding='utf-8').read()
try: c=open(sys.argv[1],encoding='utf-8').read()
except Exception: c=''
c=re.sub(r'/\*.*?\*/','',c,flags=re.S)
imgs=re.findall(r'<img\b[^>]*src=\"images/(eagle-emblem[^\"]*\.svg)\"',h,re.S)
if re.search(r'mask(?:-image)?\s*:[^;]*eagle-emblem',c): print('mask')
elif imgs and all(i=='eagle-emblem.svg' for i in imgs): print('flat')
elif any('metal' in i for i in imgs) or re.search(r'background(?:-image)?\s*:[^;]*eagle-emblem-metal',c): print('ok')
else: print('none')" "$CSS" 2>/dev/null || echo none)
case "$eg" in
  ok)   say "✓ 6.1.22 العقاب يُعرض من ملفه المعدني" ;;
  mask) say "✗ 6.1.22 العقاب بقناع CSS يختفي عند الفتح المحلي؛ استعمل <img src=\"images/eagle-emblem-metal.svg\">"; fail=1 ;;
  flat) say "✗ 6.1.22 الملف المسطح يظهر أسود داخل <img>؛ استعمل eagle-emblem-metal.svg"; fail=1 ;;
  *)    say "✗ 6.1.22 لا عقاب معروض من images/ (3.3.2 · 3.5)"; fail=1 ;;
esac

# 6.1.23 توريث الأسلوب (3.4.2): الموقع المبني على أسلوب من البنك يرث خطوطه ولونَي بصمته من صفّه في سجل الهوية،
# ومواصفته محفوظة ومطابقة للسجل. أمسك «الخبز والملح»: بُني على 06 بخط Amiri، وكُتبت مواصفة 06 منه لا من موقعه المرجعي.
STARTER="$(cd "$(dirname "$0")/.." && pwd)"
cat >"$TMP/inherit.py" <<'PY'
import re,sys,glob,os
css,starter,typ=sys.argv[1:4]
if typ=='فهرس': print('skip|الفهرس لا يرث أسلوباً'); sys.exit()
d=open('DESIGN.md',encoding='utf-8').read() if os.path.isfile('DESIGN.md') else ''
m=re.search(r'^\|\s*\**الأسلوب\**\s*\|\s*(\d{2})\b',d,re.M)
if not m: print('skip|لا رقم أسلوب من البنك في DESIGN.md'); sys.exit()
nn=m.group(1)
reg=open(os.path.join(starter,'docs','سجل-الهوية.md'),encoding='utf-8').read()
row=re.search(r'^\|\s*'+nn+r'\s*\|(.*)$',reg,re.M)
if not row: print('fail|الأسلوب '+nn+' غير موجود في بنك سجل الهوية'); sys.exit()
cells=[c.strip() for c in row.group(1).split('|')]
fp=cells[2] if len(cells)>2 else ''
name=r'[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*'
fonts={f for pair in re.findall(r'\b('+name+r')\s*/\s*('+name+r')',fp) for f in pair}
hexes=[h.lower() for h in re.findall(r'#[0-9a-fA-F]{6}\b',fp)]
def prim(text):
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    v=re.findall(r'--font-[\w-]+\s*:\s*([\'"][^;]+);',text)
    if not v: v=[x for x in re.findall(r'font-family\s*:\s*([^;]+);',text) if not x.strip().startswith('var(')]
    return {re.split(r',',x)[0].strip().strip('\'"') for x in v}
c=open(css,encoding='utf-8',errors='ignore').read()
site=prim(c); errs=[]
if fonts and site!=fonts: errs.append('الخطوط ('+'، '.join(sorted(site))+') لا تطابق خطوط الأسلوب '+nn+' ('+'، '.join(sorted(fonts))+')')
miss=[h for h in hexes if h not in c.lower()]
if miss: errs.append('لون البصمة غائب عن التوكنات: '+' '.join(miss))
specs=glob.glob(os.path.join(starter,'docs','site-styles',nn+'-*','STYLE.md'))
if not specs: errs.append('لا مواصفة site-styles/'+nn+'-*/STYLE.md؛ تُستخرج من style.css للموقع المرجعي المنشور')
elif fonts and prim(open(specs[0],encoding='utf-8').read())!=fonts: errs.append('مواصفة الأسلوب '+nn+' تخالف سجل الهوية في الخطوط')
print(('fail|'+' · '.join(errs)) if errs else ('ok|الأسلوب '+nn+' موروث: الخطوط ولونا البصمة والمواصفة مطابقة'))
PY
inh=$(python3 "$TMP/inherit.py" "$CSS" "$STARTER" "$TYPE" 2>/dev/null || echo "fail|تعذّر فحص التوريث")
case "${inh%%|*}" in
  ok)   say "✓ 6.1.23 ${inh#*|}" ;;
  skip) say "✓ 6.1.23 ${inh#*|}" ;;
  *)    say "✗ 6.1.23 ${inh#*|} (3.4.2)"; fail=1 ;;
esac

# 6.1.24 لا علامتا « » في نص يراه الزائر، HTML وJS، والتعليقات مستثناة (4.12.4)
# 6.1.25 الحسابات أيقونات: لا رقم ولا اسم حساب ولا بريد نصاً ظاهراً، والقيم في الروابط وحدها (5.13.3)
cat >"$TMP/marks.py" <<'PY'
import re,sys
h=open('index.html',encoding='utf-8').read()
h=re.sub(r'<(script|style)[^>]*>.*?</\1>','',h,flags=re.S); h=re.sub(r'<!--.*?-->','',h,flags=re.S)
n=h.count(chr(171))+h.count(chr(187))
try:
    j=open(sys.argv[1],encoding='utf-8').read()
    j=re.sub(r'/\*.*?\*/','',j,flags=re.S); j=re.sub(r'(?<![:\'"])//[^\n]*','',j)
    n+=j.count(chr(171))+j.count(chr(187))
except Exception: pass
text=re.sub(r'<[^>]+>',' ',h)
shown=[a for a in ('966566702030','khaldounakramah','akramahkhaldoun@gmail.com') if a in text]
print(str(n)+'|'+' '.join(shown))
PY
mk=$(python3 "$TMP/marks.py" "$JS" 2>/dev/null || echo "0|")
nq=${mk%%|*}; shown=${mk#*|}
[ "${nq:-0}" -eq 0 ] && say "✓ 6.1.24 لا علامتا « »" \
  || { say "✗ 6.1.24 ${nq} علامة « » في نص مرئي (4.12.4)"; fail=1; }
[ -z "$shown" ] && say "✓ 6.1.25 الحسابات أيقونات بلا نص ظاهر" \
  || { say "✗ 6.1.25 الحساب ظاهر نصاً: ${shown} (5.13.3)"; fail=1; }

# 6.1.26 لغة الإنتاج في نص مرئي (4.11.1) · 6.1.27 وظيفة واحدة بزرّين (4.13.3) · 6.1.28 حدّ جانبي لوني فوق 1px (4.12.3)
# تحذيرات تُذكر في تقرير التسليم (6.3) ولا تُسقط المواقع القديمة؛ كل تحذير يُصلَح أو يُعلَّل بسطر.
cat >"$TMP/style.py" <<'PYEOF'
import re,sys
h=open('index.html',encoding='utf-8').read()
h=re.sub(r'<(script|style)[^>]*>.*?</\1>','',h,flags=re.S); h=re.sub(r'<!--.*?-->','',h,flags=re.S)
vis=re.sub(r'<[^>]+>',' ',h)+' '+' '.join(re.findall(r'(?:alt|aria-label|title)="([^"]*)"',h))
prod=re.findall(r'(?:المشهد|مشهد|اللقطة|لقطة)\s+(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|\d+)',vis)
acts=re.findall(r'data-action="([^"]+)"',h)
dup=sorted({k for k in acts if acts.count(k)>1})
try: css=open(sys.argv[1],encoding='utf-8',errors='ignore').read()
except Exception: css=''
css=re.sub(r'/\*.*?\*/','',css,flags=re.S)
bord=len(re.findall(r'border-(?:left|right|inline-start|inline-end)\s*:\s*(?:[2-9]|\d{2,})px\s+solid',css))
print(f"{len(prod)}|{' '.join(dup)}|{bord}")
PYEOF
st=$(python3 "$TMP/style.py" "$CSS" 2>/dev/null || echo "0||0")
n26=${st%%|*}; rest=${st#*|}; d27=${rest%%|*}; n28=${rest#*|}
[ "${n26:-0}" -eq 0 ] && say "✓ 6.1.26 لا لغة إنتاج في نص مرئي" || say "⚠ 6.1.26 ${n26} موضع بلغة إنتاج (مشهد أو لقطة بترقيم) في نص مرئي (4.11.1)"
[ -z "$d27" ] && say "✓ 6.1.27 لا وظيفة بزرّين" || say "⚠ 6.1.27 وظيفة بأكثر من زر: ${d27} (4.13.3)"
[ "${n28:-0}" -eq 0 ] && say "✓ 6.1.28 لا حدّ جانبي لوني" || say "⚠ 6.1.28 ${n28} حدّ جانبي لوني فوق 1px (4.12.3)"

# 6.1.29 إلى 6.1.41 الحركة (5.14): تُقرأ CSS وJS قراءةً (رسوب 6.1.29 إلى 6.1.34، تحذير 6.1.35 إلى 6.1.40)،
# ثم Chrome بلا واجهة بالحركة المخففة على 390 و1440 (6.1.41)، وتعذّره تحذير. حلّت محل البحث عن كلمة prefers-reduced-motion
# بعد «وجهك حلو»: letter-spacing يتحرك، وhover يعلق على الهاتف، ومتغيرات تُكتب على القسم كل إطار، ومرّت الثلاثة من البوابة.
for m in ثابت متصفح; do
  mo=$(python3 "$STARTER/scripts/فحص-الحركة.py" "$m" 2>&1)
  [ -n "$mo" ] || mo="✗ 6.1.29 تعذّر تشغيل فحص الحركة ($m)"
  [ "$m" = متصفح ] && ! echo "$mo" | grep -q '^[✓✗⚠]' && mo="⚠ 6.1.41 طبقة المتصفح لم تُفحص: ${mo:0:120}"
  say "$mo"
  echo "$mo" | grep -q '^✗' && fail=1
done

[ "$fail" = 0 ] && say "══ ✓ البوابة الآلية اجتازت ══" || say "══ ✗ رسبت: لا يُعرض ولا يُنشر ══"
exit $fail
