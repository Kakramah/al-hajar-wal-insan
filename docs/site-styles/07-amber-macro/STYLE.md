# مواصفة الأسلوب 07: احتفاء كهرماني بملمس قريب (`07-amber-macro`)

> **المالك:** `$STARTER/docs/سجل-الهوية.md` §بنك الأساليب (القاعدة 3.4.2 في `docs/قواعد-الويب.md`).  
> **الموقع المرجعي:** `syria-rising-from-rubble` (من تحت الركام تنهض سوريا).  
> **المصدر المقيس:** `:root` في `style.css` للموقع المنشور، منقول كما هو في 2026-09-28. أي قيمة هنا تخالفه تُصحَّح منه.

---

## 1 · البصمة

| الحقل | القيمة |
|---|---|
| **الأرضية** | رمادي دافئ `#1b1b19` وسطح `#22211e`، لا أسود مطلق لأن الصور رمادية دافئة |
| **أسرة لون البطل** | كهرماني الغروب `#d18250` |
| **العائلة الخطية** | عناوين Cairo / متن Tajawal (كما في الموقع المرجعي) |
| **الشبكة** | فصول متناوبة `1fr 1fr` (KHALDOUN-SITE-PATTERN) |
| **الملمس والآلية** | ملمس ماكرو قريب، واللوحة مقيسة من صور الإسمنت والحجر والغروب |

---

## 2 · لوحة التوكنات (:root)

```css
:root {
  /* اللوحة: مقيسة من صور المشروع العشر */
  --bg: #1b1b19;
  --surface: #22211e;
  --stone: #d9c19a;
  --text: #e9e2d6;
  --text-body: #d6cec1;
  --text-muted: #b8b0a3;
  --accent: #d18250;
  --eagle: #c9a557;
  --line: #e9e2d61f;
  --overlay: #1b1b19e0;
  --scrim: #0d0d0bf0;
  --quote-bg: #d1825012;
  --chip-border: #c9a55766;
  --shadow: #0000008c;
  --grain-opacity: 0.05;

  --font-heading: 'Cairo', 'Tajawal', 'Geeza Pro', 'Noto Naskh Arabic', sans-serif;
  --font-body: 'Tajawal', 'Geeza Pro', 'Noto Naskh Arabic', sans-serif;

  --inner-max: 1200px;
  --side-pad: clamp(1.5rem, 5vw, 4rem);
  --section-pad: clamp(5rem, 10vw, 9rem);
  --radius: 12px;
}
```

---

## 3 · يناسب

عودة، بناء، احتفاء هادئ (من صف الأسلوب في سجل الهوية).
