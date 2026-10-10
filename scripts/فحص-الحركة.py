#!/usr/bin/env python3
# فحص الحركة لبوابة الويب (6.1.29 إلى 6.1.41 · قواعد الويب 5.14). مكتبة بايثون القياسية وحدها.
# يُشغَّل من جذر المشروع، والبوابة تستدعيه:
#   python3 فحص-الحركة.py ثابت    الطبقتان الأولى والثانية: CSS وJS مقروءان قراءةً، لا بحثاً عن كلمة
#   python3 فحص-الحركة.py متصفح   الطبقة الثالثة: Chrome بلا واجهة بالحركة المخففة على 390 و1440
# يطبع أسطراً تبدأ بـ✓ أو ✗ أو ⚠. GATE_VERBOSE=1 يسرد كل موضع بدل أوله.
# كل فحص هنا أمسك عيباً وقع أو يقع؛ وما يُحتمل أن يكون مقصوداً في موقع سردي تحذير لا رسوب.
import os, re, sys, json, bisect
from html.parser import HTMLParser

VERBOSE = os.environ.get('GATE_VERBOSE') == '1'

# ───────────────────────── المصادر: ما يستدعيه index.html فعلاً ─────────────────────────
def load_sources():
    h = open('index.html', encoding='utf-8', errors='ignore').read()
    loc = lambda u: not re.match(r'(https?:)?//', u)
    line = lambda i: h.count('\n', 0, i) + 1
    css, js = [], []
    for m in re.finditer(r'<link\b[^>]*>', h, re.I):
        t = m.group(0)
        if not re.search(r'rel\s*=\s*["\']?stylesheet', t, re.I): continue
        u = re.search(r'href\s*=\s*["\']([^"\']+)', t, re.I)
        if u and loc(u.group(1)): css.append(('file', u.group(1), m.start()))
    for m in re.finditer(r'<style\b[^>]*>(.*?)</style>', h, re.S | re.I):
        css.append(('inline', m.group(1), m.start(1)))
    css.sort(key=lambda x: x[2])   # ترتيب الوثيقة يحسم التعادل في الأسبقية
    for m in re.finditer(r'<script\b([^>]*)>(.*?)</script>', h, re.S | re.I):
        a = m.group(1)
        u = re.search(r'src\s*=\s*["\']([^"\']+)', a, re.I)
        if u:
            if loc(u.group(1)): js.append(('file', u.group(1), m.start()))
        elif not re.search(r'type\s*=\s*["\'](?!module|text/javascript|application/javascript)', a, re.I):
            js.append(('inline', m.group(2), m.start(2)))
    def read(kind, val, pos):
        if kind == 'inline': return ('index.html', val, line(pos) - 1)
        p = val.split('?')[0].split('#')[0]
        p = p[2:] if p.startswith('./') else p.lstrip('/')
        try: return (p, open(p, encoding='utf-8', errors='ignore').read(), 0)
        except OSError: return None
    seen = set(); out_css = []; out_js = []
    for k, v, p in css:
        if k == 'file' and v in seen: continue
        seen.add(v); r = read(k, v, p)
        if r: out_css.append(r)
    for k, v, p in js:
        if k == 'file' and v in seen: continue
        seen.add(v); r = read(k, v, p)
        if r: out_js.append(r)
    return h, out_css, out_js

# ───────────────────────── قارئ CSS: قواعد بسياقها ونسقها وتعشيشها ─────────────────────────
class Rule:
    __slots__ = ('sels', 'decls', 'ctx', 'src', 'line', 'order')
    def __init__(s, sels, ctx, src, line, order):
        s.sels, s.decls, s.ctx, s.src, s.line, s.order = sels, [], ctx, src, line, order
    def get(s, *props):
        return [d for d in s.decls if d[0] in props]

def mask_comments(t):
    return re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), t, flags=re.S)

def split_top(s, sep=','):
    out, depth, q, cur = [], 0, None, []
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur.append(c)
            if c == '\\' and i + 1 < len(s): cur.append(s[i + 1]); i += 2; continue
            if c == q: q = None
        elif c in '"\'': q = c; cur.append(c)
        elif c in '([': depth += 1; cur.append(c)
        elif c in ')]': depth -= 1; cur.append(c)
        elif depth == 0 and (c == sep if sep != ' ' else c.isspace()):
            out.append(''.join(cur)); cur = []
        else: cur.append(c)
        i += 1
    out.append(''.join(cur))
    return [x.strip() for x in out if x.strip()]

ORDER = [0]
def parse_css(text, src, base):
    rules, kfs = [], {}
    t = mask_comments(text)
    n = len(t)
    nl = [i for i, c in enumerate(t) if c == '\n']
    lineof = lambda i: base + bisect.bisect_right(nl, i) + 1
    def scan(i, end, stop):
        q = None; par = 0
        while i < end:
            c = t[i]
            if q:
                if c == '\\': i += 2; continue
                if c == q: q = None
            elif c in '"\'': q = c
            elif c == '(': par += 1
            elif c == ')': par -= 1
            elif par <= 0 and c in stop: return i
            i += 1
        return end
    def block_end(i):
        d = 0; q = None
        while i < n:
            c = t[i]
            if q:
                if c == '\\': i += 2; continue
                if c == q: q = None
            elif c in '"\'': q = c
            elif c == '{': d += 1
            elif c == '}':
                d -= 1
                if d == 0: return i
            i += 1
        return n
    def decl(pre, pos):
        if ':' not in pre: return None
        p, v = pre.split(':', 1)
        p = p.strip().lower(); v = ' '.join(v.split())
        imp = bool(re.search(r'!\s*important\s*$', v, re.I))
        v = re.sub(r'\s*!\s*important\s*$', '', v, flags=re.I)
        return (p, v, imp, lineof(pos))
    def nest(parents, sels):
        out = []
        for c in sels:
            for p in parents:
                out.append(c.replace('&', p) if '&' in c else p + ' ' + c)
        return out
    def body(i, end, ctx, rule):
        while i < end:
            j = scan(i, end, '{;}')
            pre = t[i:j].strip()
            if j >= end or t[j] in ';}':
                if pre and rule is not None and not pre.startswith('@'):
                    d = decl(pre, i + len(t[i:j]) - len(t[i:j].lstrip()))
                    if d: rule.decls.append(d)
                i = j + 1; continue
            k = block_end(j)
            at = i + len(t[i:j]) - len(t[i:j].lstrip())
            if pre.startswith('@'):
                nm = re.match(r'@([\w-]+)', pre); nm = nm.group(1).lower() if nm else ''
                if nm.endswith('keyframes'):
                    name = pre.split(None, 1)[1].strip().strip('"\'') if len(pre.split(None, 1)) > 1 else ''
                    kfs.setdefault(name, []).append(frames(j + 1, k))
                elif nm in ('media', 'supports', 'layer', 'container', 'document', 'scope', 'starting-style'):
                    body(j + 1, k, ctx + [pre], rule)
            else:
                sels = [x for x in split_top(pre) if '*/' not in x and '/*' not in x]   # محدِّد فاسد يُسقطه المتصفح
                if rule is not None: sels = nest(rule.sels, sels)
                ORDER[0] += 1
                r = Rule(sels, ctx, src, lineof(at), ORDER[0]); rules.append(r)
                body(j + 1, k, ctx, r)
            i = k + 1
    def frames(i, end):
        out = []
        while i < end:
            j = scan(i, end, '{}')
            if j >= end or t[j] == '}': break
            k = block_end(j)
            stops = [s.strip().lower() for s in t[i:j].split(',')]
            r = Rule([], [], src, lineof(i), 0)
            body(j + 1, k, [], r)
            out.append((stops, r.decls))
            i = k + 1
        return out
    body(0, n, [], None)
    return rules, kfs

# ───────────────────────── المحدِّدات: تفكيك وخصوصية ومطابقة على DOM ─────────────────────────
INTERACT = {'hover', 'focus', 'focus-visible', 'focus-within', 'active', 'checked', 'target', 'visited', 'open',
            'popover-open', 'modal', 'fullscreen', 'playing', 'paused', 'indeterminate', 'invalid', 'valid',
            'user-invalid', 'user-valid', 'placeholder-shown', 'target-within', 'current'}
LEGACY_PE = {'before', 'after', 'first-line', 'first-letter'}

def parse_compound(s):
    c = {'tag': None, 'ids': [], 'cls': [], 'attrs': [], 'ps': [], 'pe': None}
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '*': i += 1; continue
        if ch == '&': i += 1; continue
        m = re.match(r'[A-Za-z][\w-]*', s[i:])
        if m and i == 0: c['tag'] = m.group(0).lower(); i += m.end(); continue
        if ch in '.#':
            m = re.match(r'(?:\\.|[\w-])+', s[i + 1:])
            if not m: i += 1; continue
            v = m.group(0).replace('\\', '')
            (c['cls'] if ch == '.' else c['ids']).append(v); i += 1 + m.end(); continue
        if ch == '[':
            j = s.find(']', i)
            j = len(s) if j < 0 else j
            a = s[i + 1:j]
            m = re.match(r'\s*([\w:-]+)\s*(?:([~|^$*]?=)\s*(["\']?)(.*?)\3\s*(?:\s[is])?)?\s*$', a)
            if m: c['attrs'].append((m.group(1).lower(), m.group(2), m.group(4)))
            i = j + 1; continue
        if ch == ':':
            pe = s.startswith('::', i)
            m = re.match(r':{1,2}([\w-]+)', s[i:])
            if not m: i += 1; continue
            nm = m.group(1).lower(); i += m.end(); arg = None
            if i < len(s) and s[i] == '(':
                d = 0; j = i
                while j < len(s):
                    if s[j] == '(': d += 1
                    elif s[j] == ')':
                        d -= 1
                        if d == 0: break
                    j += 1
                arg = s[i + 1:j]; i = j + 1
            if pe or nm in LEGACY_PE: c['pe'] = nm
            else: c['ps'].append((nm, arg))
            continue
        i += 1
    return c

def parse_complex(sel):
    parts, cur, comb = [], [], ' '
    depth = 0; i = 0; s = sel.strip()
    out = []
    while i < len(s):
        ch = s[i]
        if ch in '([': depth += 1
        elif ch in ')]': depth -= 1
        if depth == 0 and (ch.isspace() or ch in '>+~'):
            if cur: out.append((comb, ''.join(cur))); cur = []; comb = ' '
            j = i
            while j < len(s) and (s[j].isspace() or s[j] in '>+~'):
                if s[j] in '>+~': comb = s[j]
                j += 1
            i = j; continue
        cur.append(ch); i += 1
    if cur: out.append((comb, ''.join(cur)))
    return [(cb, parse_compound(cp)) for cb, cp in out]

CX_CACHE = {}
def cx(sel):
    if sel not in CX_CACHE: CX_CACHE[sel] = parse_complex(sel)
    return CX_CACHE[sel]

def specificity(sel):
    a = b = c = 0
    for _, cp in cx(sel):
        a += len(cp['ids']); b += len(cp['cls']) + len(cp['attrs'])
        c += 1 if cp['tag'] else 0
        if cp['pe']: c += 1
        for nm, arg in cp['ps']:
            if nm == 'where': continue
            if nm in ('not', 'is', 'has', 'matches') and arg:
                best = max((specificity(x) for x in split_top(arg)), default=(0, 0, 0))
                a += best[0]; b += best[1]; c += best[2]
            else: b += 1
    return (a, b, c)

class Node:
    __slots__ = ('tag', 'attrs', 'cls', 'id', 'parent', 'kids', 'idx')
    def __init__(s, tag, attrs, parent):
        s.tag = tag; s.attrs = attrs; s.parent = parent; s.kids = []
        s.cls = set((attrs.get('class') or '').split()); s.id = attrs.get('id')
        s.idx = 0

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr', 'param'}
class DOM(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.root = Node('#doc', {}, None); s.stack = [s.root]; s.all = []
    def handle_starttag(s, tag, attrs):
        a = {k.lower(): (v if v is not None else '') for k, v in attrs}
        par = s.stack[-1]; n = Node(tag, a, par); n.idx = len(par.kids); par.kids.append(n); s.all.append(n)
        if tag not in VOID: s.stack.append(n)
    def handle_startendtag(s, tag, attrs):
        s.handle_starttag(tag, attrs)
        if tag not in VOID and s.stack[-1].tag == tag: s.stack.pop()
    def handle_endtag(s, tag):
        for k in range(len(s.stack) - 1, 0, -1):
            if s.stack[k].tag == tag: del s.stack[k:]; break

def descendants(n):
    k = 0; st = list(n.kids)
    while st:
        x = st.pop(); k += 1; st.extend(x.kids)
    return k

class Mode:
    # wild: الأصناف والسمات التي يضيفها JS، وحالات التفاعل، تُعدّ قائمة؛ وإلا فهي غائبة (حالة البداية)
    def __init__(s, root_cls, wild, dyn_cls, dyn_attr, targets=None):
        s.root_cls, s.wild, s.dyn_cls, s.dyn_attr = root_cls, wild, dyn_cls, dyn_attr
        s.targets = targets or {}   # صنفٌ يضيفه JS ← العناصر التي يصيبها فعلاً، إن عُرفت

def n_classes(n, mode):
    if n.tag in ('html', 'body'): return n.cls | mode.root_cls
    return n.cls

def match_compound(n, cp, mode):
    if cp['tag'] and n.tag != cp['tag']: return False
    if cp['ids'] and n.id not in cp['ids']: return False
    cl = n_classes(n, mode)
    for c in cp['cls']:
        if c in cl: continue
        if mode.wild and c in mode.dyn_cls and (mode.targets.get(c) is None or id(n) in mode.targets[c]): continue
        return False
    for name, op, val in cp['attrs']:
        if mode.wild and name in mode.dyn_attr: continue
        if name not in n.attrs: return False
        v = n.attrs[name]
        if op is None: continue
        ok = {'=': v == val, '~=': val in v.split(), '|=': v == val or v.startswith(val + '-'),
              '^=': v.startswith(val), '$=': v.endswith(val), '*=': val in v}.get(op, True)
        if not ok: return False
    for nm, arg in cp['ps']:
        if nm in INTERACT:
            if not mode.wild: return False
            continue
        if nm == 'not' and arg:
            if mode.wild: continue
            if any(match_sel(n, x, mode) for x in split_top(arg)): return False
            continue
        if nm in ('is', 'where', 'matches', 'any') and arg:
            if not any(match_sel(n, x, mode) for x in split_top(arg)): return False
            continue
        if nm == 'root' and n.tag != 'html': return False
        sib = n.parent.kids if n.parent else [n]
        if nm == 'first-child' and n.idx != 0: return False
        if nm == 'last-child' and n.idx != len(sib) - 1: return False
        if nm == 'only-child' and len(sib) != 1: return False
        if nm in ('nth-child', 'nth-last-child') and arg:
            k = n.idx + 1 if nm == 'nth-child' else len(sib) - n.idx
            if not nth(arg, k): return False
        if nm == 'empty' and n.kids: return False
    return True

def nth(arg, k):
    a = arg.strip().lower().split(' of ')[0].replace(' ', '')
    if a == 'odd': return k % 2 == 1
    if a == 'even': return k % 2 == 0
    m = re.fullmatch(r'([+-]?\d*)n([+-]\d+)?', a)
    if m:
        A = m.group(1); A = 1 if A in ('', '+') else -1 if A == '-' else int(A)
        B = int(m.group(2) or 0)
        if A == 0: return k == B
        return (k - B) % A == 0 and (k - B) // A >= 0
    try: return k == int(a)
    except ValueError: return True

def match_sel(n, sel, mode):
    parts = cx(sel)
    if not parts: return False
    def rec(node, i):
        comb, cp = parts[i]
        if not match_compound(node, cp, mode): return False
        if i == 0: return True
        if comb == '>':
            return node.parent is not None and node.parent.tag != '#doc' and rec(node.parent, i - 1)
        if comb == ' ':
            p = node.parent
            while p is not None and p.tag != '#doc':
                if rec(p, i - 1): return True
                p = p.parent
            return False
        sib = node.parent.kids[:node.idx] if node.parent else []
        if comb == '+': return bool(sib) and rec(sib[-1], i - 1)
        return any(rec(x, i - 1) for x in sib)
    return rec(n, len(parts) - 1)

def pe_of(sel):
    p = cx(sel)
    return p[-1][1]['pe'] if p else None

# ───────────────────────── القيم: المدد والمنحنيات والمتغيرات ─────────────────────────
TIME = re.compile(r'^(-?\d*\.?\d+)(ms|s)$', re.I)
KW_T = {'ease', 'ease-in', 'ease-out', 'ease-in-out', 'linear', 'step-start', 'step-end'}
LAYOUT = re.compile(r'^(?:(?:min-|max-)?(?:width|height)|inline-size|block-size|top|right|bottom|left|inset(?:-[\w-]+)?|'
                    r'margin(?:-[\w-]+)?|padding(?:-[\w-]+)?|letter-spacing)$')
MOVE = re.compile(r'^(?:-webkit-)?(?:transform|translate|rotate|scale|offset(?:-[\w-]+)?|clip-path|background-position(?:-[xy])?|'
                  r'mask-position|stroke-dashoffset|perspective)$')
def moves(p): return bool(MOVE.match(p) or LAYOUT.match(p))
def secs(tok):
    m = TIME.match(tok)
    return (float(m.group(1)) / (1000 if m.group(2).lower() == 'ms' else 1)) if m else None

class Vars:
    def __init__(s, rules):
        s.v = {}
        for r in rules:
            for p, val, _, _ in r.decls:
                if p.startswith('--') and (p not in s.v or any(x.strip() in (':root', 'html') for x in r.sels)):
                    s.v[p] = val
    def sub(s, val, depth=0):
        if 'var(' not in val or depth > 6: return val
        def rep(m):
            inner = m.group(1); nm, _, fb = inner.partition(',')
            nm = nm.strip()
            return s.v.get(nm, fb.strip() if fb else 'var(' + nm + ')')
        prev = None
        while prev != val and 'var(' in val and depth < 6:
            prev = val; val = re.sub(r'var\(((?:[^()]|\([^()]*\))*)\)', rep, val); depth += 1
        return val

def parse_trans(val, V):
    """[(prop, duration, delay, timing)] لقائمة transition؛ prop=None تعني all ضمناً"""
    val = V.sub(val)
    if val.strip().lower() in ('none', 'initial', 'unset', 'inherit', 'revert', '0', '0s'): return []
    out = []
    for item in split_top(val):
        prop = None; times = []; timing = None
        for tok in split_top(item, ' '):
            tl = tok.lower()
            s_ = secs(tl)
            if s_ is not None: times.append(s_)
            elif tl in KW_T or tl.startswith(('cubic-bezier(', 'steps(', 'linear(')): timing = tl
            elif tl in ('allow-discrete', 'normal'): pass
            elif tl.startswith('var('): pass
            else: prop = tl
        if prop == 'none': continue
        out.append((prop, times[0] if times else None, times[1] if len(times) > 1 else 0, timing))
    return out

ANIM_KW = {'none', 'infinite', 'normal', 'reverse', 'alternate', 'alternate-reverse', 'forwards', 'backwards', 'both',
           'running', 'paused', 'initial', 'inherit', 'unset'}
def parse_anim(val, V, kfs):
    """[(name, duration, timing)] لقائمة animation"""
    val = V.sub(val); out = []
    for item in split_top(val):
        name = None; times = []; timing = None
        for tok in split_top(item, ' '):
            tl = tok.lower()
            s_ = secs(tl)
            if s_ is not None: times.append(s_)
            elif tl in KW_T or tl.startswith(('cubic-bezier(', 'steps(', 'linear(')): timing = tl
            elif tl in ANIM_KW or re.fullmatch(r'\d*\.?\d+', tl) or tl.startswith('var('): pass
            else: name = tok.strip('"\'')
        if name: out.append((name, times[0] if times else 0, timing))
    return out

def easein_like(t):
    if not t: return False
    if t == 'ease-in': return True
    m = re.match(r'cubic-bezier\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', t)
    if not m: return False
    x1, y1, x2, y2 = map(float, m.groups())
    return y1 < x1 - 0.1 and y2 <= x2 + 0.02

def is_zero_opacity(v):
    return bool(re.fullmatch(r'\s*0*\.?0*%?\s*', v)) and v.strip() not in ('', '.')

def reduce_ctx(ctx):
    for c in ctx:
        cl = c.lower()
        if 'prefers-reduced-motion' in cl and 'no-preference' not in cl and not re.search(r'\bnot\b', cl): return True
    return False
def motion_only_ctx(ctx):
    for c in ctx:
        cl = c.lower()
        if 'prefers-reduced-motion' in cl and ('no-preference' in cl or re.search(r'\bnot\b', cl)): return True
    return False

# ───────────────────────── قارئ JS: الأصناف والحلقات والأهداف ─────────────────────────
JS_KW = {'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'typeof', 'new', 'do', 'else', 'with', 'await', 'yield'}
def mask_js(t):
    """يستبدل محتوى التعليقات والنصوص وتعابير regex بمسافات مع حفظ الأطوال.
    القوالب `…${…}…` تُقرأ بمكدَّس، فالشيفرة داخل ${} تبقى، وقالبٌ داخلها لا يقلب ما بعده نصاً"""
    o = list(t); n = len(t); i = 0; prev = ''
    stack = [0]          # كل عنصر: عمق الأقواس داخل ${ } (0 للمستوى الأعلى)، أو 'tpl' داخل قالب
    def blank(a, b):
        for k in range(a, b):
            if o[k] != '\n': o[k] = ' '
    while i < n:
        c = t[i]
        if stack[-1] == 'tpl':
            if c == '\\': blank(i, min(i + 2, n)); i += 2; continue
            if c == '`': stack.pop(); i += 1; prev = 'x'; continue
            if t.startswith('${', i): stack.append(1); i += 2; prev = '{'; continue
            if c != '\n': o[i] = ' '
            i += 1; continue
        if t.startswith('//', i):
            j = t.find('\n', i); j = n if j < 0 else j; blank(i, j); i = j; continue
        if t.startswith('/*', i):
            j = t.find('*/', i + 2); j = n if j < 0 else j + 2; blank(i, j); i = j; continue
        if c == '`': stack.append('tpl'); i += 1; continue
        if c in '"\'':
            j = i + 1
            while j < n and t[j] != c and t[j] != '\n':
                if t[j] == '\\': j += 1
                j += 1
            blank(i + 1, min(j, n)); i = j + 1; prev = 'x'; continue
        if c == '{' and len(stack) > 1: stack[-1] += 1
        if c == '}' and len(stack) > 1:
            stack[-1] -= 1
            if stack[-1] == 0: stack.pop(); i += 1; continue      # نهاية ${ } والعودة إلى القالب
        if c == '/' and (prev == '' or prev in '(,=:[!&|?{};+-*%<>~^' or re.search(r'\b(return|typeof|case|in|of)\s*$', t[max(0, i - 8):i])):
            j = i + 1; cls = False
            while j < n and t[j] != '\n':
                if t[j] == '\\': j += 2; continue
                if t[j] == '[': cls = True
                elif t[j] == ']': cls = False
                elif t[j] == '/' and not cls: break
                j += 1
            if j < n and t[j] == '/':
                blank(i + 1, j); i = j + 1; prev = 'x'; continue
        if not c.isspace(): prev = c
        i += 1
    return ''.join(o)

def match_close(m, i, o='(', c=')'):
    d = 0
    while i < len(m):
        if m[i] == o: d += 1
        elif m[i] == c:
            d -= 1
            if d == 0: return i
        i += 1
    return len(m) - 1

class JS:
    def __init__(s, sources):
        s.src = sources                      # [(name, raw, base)]
        s.raw = ''.join(r + '\n' for _, r, _ in sources)
        s.m = mask_js(s.raw)
        s.offs = []; o = 0
        for name, r, base in sources: s.offs.append((o, name, base)); o += len(r) + 1
        s.nl = [i for i, c in enumerate(s.raw) if c == '\n']
        s.funcs = {}; s.objs = {}
        s._index()
    def loc(s, i):
        k = bisect.bisect_right([x[0] for x in s.offs], i) - 1
        o, name, base = s.offs[max(k, 0)]
        return f"{name}:{base + s.raw.count(chr(10), o, i) + 1}"
    def _block_after(s, i):
        j = i
        while j < len(s.m) and s.m[j].isspace(): j += 1
        if j < len(s.m) and s.m[j] == '{': return (j, match_close(s.m, j, '{', '}'))
        e = j
        d = 0
        while e < len(s.m):
            ch = s.m[e]
            if ch in '([{': d += 1
            elif ch in ')]}':
                if d == 0: break
                d -= 1
            elif d == 0 and ch in ';,\n': break
            e += 1
        return (j, e)
    def _index(s):
        m = s.m
        for r in re.finditer(r'\bfunction\s*\*?\s*([\w$]+)\s*\(', m):
            pe = match_close(m, r.end() - 1); s.funcs.setdefault(r.group(1), []).append(s._block_after(pe + 1))
        for r in re.finditer(r'([\w$]+)\s*[:=]\s*(?:async\s+)?function\b[^(]*\(', m):
            pe = match_close(m, r.end() - 1); s.funcs.setdefault(r.group(1), []).append(s._block_after(pe + 1))
        for r in re.finditer(r'([\w$]+)\s*[:=]\s*(?:async\s+)?(\([^()]*(?:\([^()]*\)[^()]*)*\)|[\w$]+)\s*=>', m):
            s.funcs.setdefault(r.group(1), []).append(s._block_after(r.end()))
        for r in re.finditer(r'(?:^|[,{;\s])(?:async\s+)?([\w$]+)\s*\(([^()]*)\)\s*\{', m):
            if r.group(1) in JS_KW: continue
            st = m.rfind('{', 0, r.end()); st = r.end() - 1
            s.funcs.setdefault(r.group(1), []).append((st, match_close(m, st, '{', '}')))
        for r in re.finditer(r'\b(?:const|let|var)\s+([\w$]+)\s*=\s*\{', m):
            st = r.end() - 1; s.objs[r.group(1)] = (st, match_close(m, st, '{', '}'))
    def _callback(s, i):
        """امتداد الوسيط الذي يبدأ عند i: اسم دالة أو دالة مضمّنة"""
        m = s.m
        while i < len(m) and m[i].isspace(): i += 1
        r = re.match(r'[\w$.]+', m[i:])
        after = m[i + (r.end() if r else 0):].lstrip()[:2]
        if r and not after.startswith(('=>', '(')) and not r.group(0) in ('function', 'async'):
            return ('name', r.group(0).split('.')[-1])
        # دالة مضمّنة: حتى قوس الاستدعاء المغلق
        d = 0; j = i
        while j < len(m):
            if m[j] in '([{': d += 1
            elif m[j] in ')]}':
                if d == 0: break
                d -= 1
            elif d == 0 and m[j] == ',': break
            j += 1
        return ('span', (i, j))
    def closure(s, roots):
        spans = []; names = set(); todo = list(roots)
        while todo:
            kind, v = todo.pop()
            if kind == 'name':
                if v in names or v not in s.funcs: continue
                names.add(v)
                for sp in s.funcs[v]: todo.append(('span', sp))
                continue
            sp = v
            spans.append(sp)
            txt = s.m[sp[0]:sp[1] + 1]
            for idn in set(re.findall(r'[\w$]+', txt)):
                if idn in s.funcs and idn not in names: todo.append(('name', idn))
            for ob in re.findall(r'([\w$]+)\s*\[', txt):
                if ob in s.objs:
                    a, b = s.objs[ob]
                    for nm, sps in s.funcs.items():
                        for x in sps:
                            if a < x[0] < b and nm not in names: todo.append(('name', nm))
        return spans
    def roots(s, events, raf=True):
        m = s.m; out = []
        ev = '|'.join(events)
        for r in re.finditer(r'addEventListener\(\s*[\'"](?:' + ev + r')[\'"]\s*,', s.raw):
            if m[r.start():r.start() + 16] != 'addEventListener': continue   # داخل تعليق أو نص
            out.append(s._callback(r.end()))
        for r in re.finditer(r'\bon(' + ev + r')\s*=\s*', m):
            out.append(s._callback(r.end()))
        if raf:
            for nm, sps in s.funcs.items():
                for a, b in sps:
                    if re.search(r'requestAnimationFrame\(\s*' + re.escape(nm) + r'\b', m[a:b + 1]): out.append(('name', nm))
        return out
    def io_roots(s):
        return [s._callback(r.end()) for r in re.finditer(r'new\s+IntersectionObserver\(', s.m)]
    def in_spans(s, i, spans):
        return any(a <= i <= b for a, b in spans)

MQARG = r'''((?:'[^']*'|"[^"]*"|`[^`]*`|[\w$.]+))'''   # وسيط matchMedia: نص بين علامتين أو اسم ثابت
QS = r'(?:\$\$?|qsa?|querySelector(?:All)?|getElementById|getElementsByClassName|closest)\(\s*([\'"`])([^\'"`]+)\1'
def to_sel(fn_sel):
    fn, sel = fn_sel
    if 'getElementById' in fn: return '#' + sel
    if 'getElementsByClassName' in fn: return '.' + sel.strip().replace(' ', '.')
    return sel

# ───────────────────────── التحليل ─────────────────────────
class Report:
    def __init__(s): s.items = {}
    def add(s, key, where): s.items.setdefault(key, []).append(where)

def main_static():
    if not os.path.isfile('index.html'):
        print('✗ 6.1.29 لا index.html'); return 1
    html, css_src, js_src = load_sources()
    rules, kfs = [], {}
    for name, text, base in css_src:
        r, k = parse_css(text, name, base); rules += r
        for a, b in k.items(): kfs.setdefault(a, []).extend(b)
    V = Vars(rules)
    dom = DOM(); dom.feed(html)
    nodes = [n for n in dom.all]
    J = JS(js_src)
    raw = J.raw

    # الأصناف التي يضيفها JS، والسمات التي يغيّرها
    dyn_cls = set()
    for a in re.findall(r'classList\.(?:add|toggle|replace|remove)\(([^)]*)\)', raw):
        dyn_cls |= set(x for q in re.findall(r'[\'"`]([^\'"`]+)[\'"`]', a) for x in q.split())
    for a in re.findall(r'className\s*\+?=\s*[\'"`]([^\'"`]*)', raw): dyn_cls |= set(a.split())
    for a in re.findall(r'setAttribute\(\s*[\'"]class[\'"]\s*,\s*[\'"`]([^\'"`]+)', raw): dyn_cls |= set(a.split())
    dyn_attr = set('data-' + re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), x) for x in re.findall(r'dataset\.(\w+)\s*=', raw))
    dyn_attr |= set(x.lower() for x in re.findall(r'(?:setAttribute|toggleAttribute|removeAttribute)\(\s*[\'"]([\w-]+)', raw))
    dyn_attr |= {'hidden'} if re.search(r'\.hidden\s*=', raw) else set()
    dyn_attr |= {'open'} if re.search(r'\.open\s*=|showModal\(|\.show\(\)', raw) else set()
    dyn_attr |= set('aria-' + x.lower() for x in re.findall(r'aria([A-Z]\w+)\s*=', raw))

    # متغيرات الحركة المخففة في JS، وأصناف html/body التي تُضاف بحسبها
    # الاستعلام نصاً حرفياً أو في ثابت، ومتغيره MediaQueryList أو قيمة matches، أو دالة تعيده
    rvars = set(); mvars = set()
    strs = {m.group(1): m.group(3) for m in re.finditer(r'(?:const|let|var)\s+([\w$]+)\s*=\s*([\'"`])([^\'"`]*)\2', raw)}
    def mq_kind(arg):
        arg = arg.strip()
        q = arg[1:-1] if arg[:1] in '\'"`' else strs.get(arg, '')
        if 'prefers-reduced-motion' not in q: return None
        return 'm' if ('no-preference' in q or re.search(r'\bnot\b', q)) else 'r'
    for r in re.finditer(r'(?:(?:const|let|var)\s+)?([\w$]+)\s*=\s*(?:window\.)?matchMedia\(\s*' + MQARG + r'\s*\)', raw):
        k = mq_kind(r.group(2))
        if k: (rvars if k == 'r' else mvars).add(r.group(1))
    for r in re.finditer(r'(?:function\s+([\w$]+)\s*\([^)]*\)\s*\{\s*return|(?:const|let|var)\s+([\w$]+)\s*=\s*\([^)]*\)\s*=>\s*\{?\s*(?:return)?)\s*(?:window\.)?matchMedia\(\s*' + MQARG + r'\s*\)', raw):
        k = mq_kind(r.group(3)); nm = r.group(1) or r.group(2)
        if k and nm: (rvars if k == 'r' else mvars).add(nm)
    for _ in range(2):
        for r in re.finditer(r'(?:(?:const|let|var)\s+)?([\w$]+)\s*=\s*(!?)\s*([\w$]+)(?:\.matches)?(?:\(\))?\s*[;,\n)]', raw):
            if r.group(3) in rvars: (mvars if r.group(2) else rvars).add(r.group(1))
            elif r.group(3) in mvars: (rvars if r.group(2) else mvars).add(r.group(1))
    rootish = {'documentElement', 'body'}
    for r in re.finditer(r'(?:const|let|var)\s+([\w$]+)\s*=\s*document\.(documentElement|body)\b', raw): rootish.add(r.group(1))
    def resolve(recv, at, depth=0):
        """أي محدِّد يصيبه هذا المتغير في JS؟ ('*', None) للصفحة كلها، أو ('sel', محدِّد)، أو None إن لم يُحسم"""
        last = recv.split('.')[-1]
        if last in ('documentElement', 'body') or recv in rootish: return ('*', None)
        if recv.startswith('document.') or depth > 3: return None
        if last == 'target' and '.' in recv and depth < 3:
            # e.target في مراقب: العناصر التي يراقبها
            obs = [resolve(m.group(1), m.start(), depth + 1) for m in re.finditer(r'\.observe\(\s*([\w$.]+)\s*[,)]', raw)]
            sels = [o[1] for o in obs if o and o[0] == 'sel']
            return ('sel', ', '.join(sels)) if sels and len(sels) == len(obs) else None
        cands = []
        pats = [r'(?:const|let|var)\s+' + re.escape(last) + r'\s*=\s*[^;\n]*?' + QS,
                r'\b' + re.escape(last) + r'\s*:\s*[^,\n}]*?' + QS,
                QS + r'[^;\n]*?\)\s*\)*\s*(?:\.\w+\([^)]*\)\s*)*\.(?:forEach|map|filter|find)\(\s*(?:async\s+)?\(?\s*' + re.escape(last) + r'\b',
                r'for\s*\(\s*(?:const|let|var)\s+' + re.escape(last) + r'\s+of\s+[^)]*?' + QS]
        for pt in pats:
            for mm in re.finditer(pt, raw):
                g = [x for x in mm.groups() if x is not None]
                fn = re.search(r'(\$\$?|qsa?|querySelector(?:All)?|getElementById|getElementsByClassName|closest)\(', mm.group(0))
                cands.append((mm.start(), to_sel((fn.group(1) if fn else '', g[-1]))))
        # items.forEach(el => …) أو for (const el of items): يُحسم المتغير الحامل
        for mm in re.finditer(r'([\w$]+)\s*\.(?:forEach|map|filter|find)\(\s*(?:async\s+)?\(?\s*' + re.escape(last) + r'\b|for\s*\(\s*(?:const|let|var)\s+' + re.escape(last) + r'\s+of\s+([\w$]+)\s*\)', raw):
            holder = mm.group(1) or mm.group(2)
            if holder and holder != last:
                rr = resolve(holder, mm.start(), depth + 1)
                if rr and rr[0] == 'sel': cands.append((mm.start(), rr[1]))
        if not cands: return None
        before = [c for c in cands if c[0] <= at]
        return ('sel', (max(before) if before else min(cands))[1])
    env_cls, red_cls, mot_cls = set(), set(), set()
    # صنفٌ على html أو body يُضاف داخل معالج حدث (hovering، menu-open) حالةٌ لا بيئة بدء
    handler_spans = J.closure(J.roots([r'[a-z]+'], raf=False))
    for r in re.finditer(r'([\w$.]+)\.classList\.(add|toggle|replace)\(([^)]*)\)', raw):
        recv = r.group(1).split('.')[-1]
        if recv not in rootish: continue
        if J.in_spans(r.start(), handler_spans) and not re.search(r'prefers-reduced-motion|matches', raw[max(0, r.start() - 200):r.end()]): continue
        names = re.findall(r'[\'"`]([\w-]+)[\'"`]', r.group(3))
        if r.group(2) == 'replace': names = names[1:]
        # الشرط في السطر نفسه، أو في رأس if بلا جسم في السطر السابق؛ لا ما يجاوره مصادفة
        ln_s = raw.rfind('\n', 0, r.start()) + 1; prevl = raw.rfind('\n', 0, max(ln_s - 1, 0)) + 1
        prev = raw[prevl:ln_s]
        ctxt = (prev if re.match(r'\s*(?:if\s*\(.*\)|else)\s*\{?\s*$', prev) else '') + raw[ln_s:r.end()]
        ids = set(re.findall(r'[\w$]+', ctxt))
        neg = bool(re.search(r'!\s*(?:' + '|'.join(map(re.escape, rvars | mvars or {'__'})) + r')\b', ctxt))
        if 'prefers-reduced-motion' in ctxt or ids & (rvars | mvars):
            red = bool(ids & rvars) != neg if ids & (rvars | mvars) else ('no-preference' not in ctxt)
            if r.group(2) == 'toggle' and not ids & (rvars | mvars) and 'reduce' in ctxt: red = True
            (red_cls if red else mot_cls).update(names)
        else:
            env_cls.update(names)
    env_cls -= red_cls | mot_cls
    static_cls = set(c for n in nodes for c in n.cls)
    dyn_only = (dyn_cls - static_cls) - env_cls
    # محدِّد ميت: صنف أو معرّف لا يظهر في الصفحة ولا في JS، فلا يطابق شيئاً أبداً؛ يُسقط كي لا يُحاسَب الموقع على ما لا يقع
    # ما يصنعه JS من أصناف ومعرّفات: class="…" في قوالبه، وclassList وclassName، ومحدِّدات querySelector وclosest
    js_cls = set(dyn_cls)
    for a in re.findall(r'class(?:Name)?\s*[=:]\s*\\?[\'"`]([^\'"`\\]*(?:\$\{[^}]*\}[^\'"`\\]*)*)', raw): js_cls |= set(re.findall(r'[\w-]+', a))
    js_ids = set(re.findall(r'\bid\s*=\s*\\?[\'"`]([\w-]+)', raw)) | set(re.findall(r'getElementById\(\s*[\'"`]([\w-]+)', raw))
    for a in re.findall(r'(?:querySelector(?:All)?|closest|matches|\$\$?|qsa?)\(\s*[\'"`]([^\'"`]+)', raw):
        js_cls |= set(re.findall(r'\.([\w-]+)', a)); js_ids |= set(re.findall(r'#([\w-]+)', a))
    ids_ = set(n.id for n in nodes if n.id)
    def dead(sel):
        for _, cp in cx(sel):
            if any(c not in static_cls and c not in js_cls and c not in env_cls | red_cls | mot_cls for c in cp['cls']): return True
            if any(i not in ids_ and i not in js_ids for i in cp['ids']): return True
        return False
    for r in rules: r.sels = [x for x in r.sels if not dead(x)]
    # قواعد الطباعة لا تُرى على الشاشة
    rules = [r for r in rules if r.sels and not any(re.match(r'@media\s+(?:only\s+)?print\b', c.strip(), re.I) for c in r.ctx)]
    M_START = Mode(env_cls, False, dyn_only, dyn_attr)
    targets = {}
    for r in re.finditer(r'([\w$.\[\]]+)\.classList\.(?:add|toggle)\(\s*[\'"`]([\w-]+)', raw):
        c = r.group(2)
        if c not in dyn_only or (c in targets and targets[c] is None): continue
        res = resolve(r.group(1), r.start())
        es = [n for x in split_top(res[1]) for n in nodes if match_sel(n, x, M_START)] if res and res[0] == 'sel' else []
        targets[c] = None if not es else (targets.get(c) or set()) | set(id(n) for n in es)
    M_WILD = Mode(env_cls, True, dyn_only | red_cls | mot_cls, dyn_attr, targets)
    M_RED = Mode(env_cls | red_cls, True, dyn_only, dyn_attr, targets)

    def sel_ctx(sel):
        """reduce أو motion أو normal بحسب أصناف الجذر في المحدِّد"""
        cls = set(c for _, cp in cx(sel) for c in cp['cls'])
        if cls & red_cls: return 'reduce'
        if cls & mot_cls: return 'motion'
        return 'normal'
    def rctx(r, sel):
        if reduce_ctx(r.ctx): return 'reduce'
        if motion_only_ctx(r.ctx): return 'motion'
        return sel_ctx(sel)

    used = set()
    for r in rules:
        for p, v, _, _ in r.get('animation', 'animation-name', '-webkit-animation', '-webkit-animation-name'):
            for nm, _, _ in parse_anim(v, V, kfs): used.add(nm)
    for k in kfs:
        if re.search(r'animation(?:Name)?\s*[:=]\s*[\'"`][^\'"`]*\b' + re.escape(k) + r'\b', raw): used.add(k)
    def kf_props(name):
        ps = set(); first = {}
        for fl in kfs.get(name, []):
            for stops, decls in fl:
                for d in decls:
                    ps.add(d[0])
                    if any(s_ in ('from', '0%') for s_ in stops): first[d[0]] = d[1]
        return ps, first

    rep = Report()
    short = lambda s_: (s_[:46] + '…') if len(s_) > 47 else s_
    W = lambda r, sel: f"{r.src}:{r.line} {short(sel)}"

    # 5.14.1 transition: all، صريحاً أو ضمناً
    for r in rules:
        for p, v, imp, ln in r.get('transition', '-webkit-transition', 'transition-property'):
            items = parse_trans(v, V) if p != 'transition-property' else [(x.strip().lower(), 1, 0, None) for x in split_top(v)]
            for prop, dur, delay, tm in items:
                if p != 'transition-property' and (dur is None or dur <= 0): continue
                if prop in (None, 'all'):
                    rep.add('all', f"{r.src}:{ln} {short(r.sels[0])} ‹{v}›" if prop else f"{r.src}:{ln} {short(r.sels[0])} ‹{v}› ضمناً")
                    break
    for r in re.finditer(r'\.style\.(?:transition|webkitTransition)\s*=\s*([\'"`])(.*?)\1|transition\s*:\s*([\'"`])(.*?)\3', raw):
        val = r.group(2) if r.group(2) is not None else r.group(4)
        for prop, dur, _, _ in parse_trans(re.sub(r'\$\{[^}]*\}', '1ms', val), V):
            if dur and prop in (None, 'all'): rep.add('all', f"{J.loc(r.start())} ‹{val}›"); break

    # فهرس الانتقالات بحسب العنصر (للمطابقة)
    trans_rules = []   # (rule, sel, props:set|{'*'}, maxdur, items)
    for r in rules:
        for p, v, imp, ln in r.get('transition', '-webkit-transition'):
            items = [it for it in parse_trans(v, V) if it[1]]
            if not items: continue
            props = set('*' if it[0] in (None, 'all') else it[0] for it in items)
            for sel in r.sels: trans_rules.append((r, sel, props, items, ln, imp))
        tp = r.get('transition-property')
        if tp:
            props = set('*' if x.strip().lower() == 'all' else x.strip().lower() for x in split_top(tp[-1][1]))
            durs = [secs(x.strip().lower()) or 0 for x in split_top((r.get('transition-duration') or [(0, '1s')])[-1][1])]
            items = [(x, max(durs or [0]), 0, None) for x in props]
            if max(durs or [0]) > 0:
                for sel in r.sels: trans_rules.append((r, sel, props, items, tp[-1][3], tp[-1][2]))
    anim_rules = []    # (rule, sel, name, dur, timing, ln, imp)
    for r in rules:
        for p, v, imp, ln in r.get('animation', '-webkit-animation', 'animation-name', '-webkit-animation-name'):
            for nm, dur, tm in parse_anim(v, V, kfs):
                if nm in kfs:
                    for sel in r.sels: anim_rules.append((r, sel, nm, dur, tm, ln, imp))

    def els(sel, mode):
        return [n for n in nodes if match_sel(n, sel, mode)]
    def subj_key(sel):
        p = cx(sel)
        if not p: return set()
        cp = p[-1][1]
        return set(('t', cp['tag']) for _ in [0] if cp['tag']) | set(('c', c) for c in cp['cls']) | set(('i', i) for i in cp['ids'])
    def subset_match(gen, spec):
        g = subj_key(gen); s_ = subj_key(spec)
        if pe_of(gen) != pe_of(spec): return False
        return g <= s_

    # أي العناصر يصيبها كل انتقال: مطابقةً على عناصر الصفحة نفسها، لا على آخر جزء من المحدِّد
    tnodes = {}
    def trans_on(sel):
        if sel not in tnodes: tnodes[sel] = set(id(n) for n in els(sel, M_WILD))
        return tnodes[sel]
    def same_el(a, b):
        """هل يصيب المحدِّدان عنصراً واحداً على الأقل؟ وإن لم يطابق أحدهما شيئاً في الصفحة فبالمقارنة اللفظية"""
        if pe_of(a) != pe_of(b): return False
        ea, eb = trans_on(a), trans_on(b)
        if ea and eb: return bool(ea & eb)
        return subset_match(a, b) or subset_match(b, a)
    BG = {'background', 'background-color', 'background-image'}
    BD = {'border', 'border-color'}
    def covers(props, changed):
        if '*' in props or changed & props: return True
        return bool((changed & BG and props & BG) or (changed & BD and props & BD))

    # ما يكتبه JS في style مباشرة يغلب CSS: يُبطل انتقالاً أو حالة hover، أو يحرّك هو
    kebab = lambda x: re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), x)
    inline = {}      # id(عنصر) ← {خاصية: [(موضع، القيمة نصاً)]}
    js_writes = []   # (موضع، خاصية، عناصر أو None إن لم يُحسم الهدف، القيمة)
    for mm in re.finditer(r'([\w$.\[\]]+)\.style\.(?:setProperty\(\s*[\'"]([\w-]+)[\'"]\s*,\s*([^)\n]*)|([A-Za-z]+)\s*=(?!=)\s*([^;\n]*))', raw):
        prop = mm.group(2) or kebab(mm.group(4)); val = (mm.group(3) or mm.group(5) or '').strip()
        if prop == 'css-text': continue
        res = resolve(mm.group(1), mm.start())
        es = None
        if res and res[0] == '*': es = []
        elif res: es = [n for x in split_top(res[1]) for n in els(x, M_START)] or None
        js_writes.append((mm.start(), prop, es, val))
        for n in es or []: inline.setdefault(id(n), {}).setdefault(prop, []).append((mm.start(), val))
    def standing_inline(n):
        """ما يكتبه JS في style خارج معالجات النقر والمفاتيح، فيبقى قائماً ويغلب CSS"""
        return {p_: ws for p_, ws in inline.get(id(n), {}).items() if any(not J.in_spans(i, inter) for i, _ in ws)}
    def lit_props(v):
        v = re.sub(r'\$\{[^}]*\}', '1ms', v.strip().strip('\'"`'))
        return set('*' if it[0] in (None, 'all') else it[0] for it in parse_trans(v, V) if it[1])
    # أصناف يضيفها JS عند التحميل أو التمرير أو المراقب فتبقى؛ وحالات النقر والمفاتيح (aria-pressed، is-active) ليست قائمة دائماً
    # والدوال التي يستدعيها HTML من سمات onclick وonsubmit وأخواتها معالجاتُ تفاعل أيضاً
    html_handlers = set(f for v in re.findall(r'\bon(?:click|submit|change|input|keydown|keyup|pointerdown|mousedown|touchstart)\s*=\s*"([^"]*)"', html, re.I)
                        for f in re.findall(r'(?<![\w$.])([\w$]+)\s*\(', v))
    inter = J.closure(J.roots(['click', 'keydown', 'keyup', 'pointerdown', 'pointerup', 'mousedown', 'touchstart', 'submit',
                               'change', 'input', 'focusin', 'toggle'], raf=False) + [('name', f) for f in html_handlers])
    add_sites = {}
    for mm in re.finditer(r'classList\.(?:add|toggle)\(\s*[\'"`]([\w-]+)', raw): add_sites.setdefault(mm.group(1), []).append(mm.start())
    auto_tok = set(c for c, ss in add_sites.items() if not any(J.in_spans(i, inter) for i in ss))
    def persistent(n, s2):
        if match_sel(n, s2, M_START): return True
        need = set(c for _, cp in cx(s2) for c in cp['cls']) & dyn_only
        needa = set(a for _, cp in cx(s2) for a, _, _ in cp['attrs']) & dyn_attr
        if any(nm in INTERACT for _, cp in cx(s2) for nm, _ in cp['ps']): return False
        return bool(need) and need <= auto_tok and not needa and match_sel(n, s2, M_WILD)
    def winner(n, pe, mode, extra=None):
        """قاعدة transition النافذة على العنصر بالأسبقية: الأهمية ثم الخصوصية ثم الترتيب؛ وقاعدة hover نفسها إن كتبت transition"""
        best = None
        for tr, ts, props, items, ln, imp in trans_rules:
            if rctx(tr, ts) == 'reduce' or pe_of(ts) != pe: continue
            if tr is not extra and any(nm in INTERACT for _, cp in cx(ts) for nm, _ in cp['ps']): continue
            if not (match_sel(n, ts, M_WILD) if tr is extra else persistent(n, ts) if mode is None else match_sel(n, ts, mode)): continue
            key = (imp, specificity(ts), tr.order)
            if best is None or key > best[0]: best = (key, tr, props)
        return best
    def eff_trans(n, pe=None, extra=None):
        il = standing_inline(n)
        if 'transition' in il and pe is None:
            out = set()
            for _, v in il['transition']:
                if re.fullmatch(r'\s*([\'"`])[^\'"`]*\1\s*', v): out |= lit_props(v)
                else: return {'*'}
            return out
        w = winner(n, pe, None, extra)
        return w[2] if w else set()
    TRANSFORMISH = {'transform', 'translate', 'scale', 'rotate', 'animation', 'animation-name', '-webkit-transform'}
    by_prop = {}
    for r2 in rules:
        if reduce_ctx(r2.ctx): continue
        for d in r2.decls:
            for s2 in r2.sels: by_prop.setdefault(d[0], []).append((r2, s2, d[2]))

    # 5.14.2 scale(0) حالةَ بداية
    def is_s0(p, v):
        v = V.sub(v)
        if p in ('transform', '-webkit-transform'): return bool(re.search(r'scale(?:3d)?\(\s*0*\.?0*\s*(?:,\s*0*\.?0*\s*)?(?:,[^)]*)?\)', v)) and not re.search(r'scale(?:3d)?\(\s*0*\.?0*[1-9]', v)
        if p == 'scale': return bool(re.fullmatch(r'\s*0*\.?0*(\s+0*\.?0*)?\s*', v)) and v.strip() not in ('', 'none')
        return False
    for nm in used:
        for fl in kfs.get(nm, []):
            for stops, decls in fl:
                if any(s_ in ('from', '0%') for s_ in stops):
                    for d in decls:
                        if is_s0(d[0], d[1]): rep.add('s0', f"@keyframes {nm} ‹{d[0]}: {d[1]}› سطر {d[3]}")
    for r in rules:
        if reduce_ctx(r.ctx): continue
        for p, v, imp, ln in r.decls:
            if not is_s0(p, v): continue
            for sel in r.sels:
                if any(nm in INTERACT for _, cp in cx(sel) for nm, _ in cp['ps']): continue
                animated = any(same_el(ts, sel) for _, ts, props, _, _, _ in trans_rules
                               if props & {'*', 'transform', '-webkit-transform', 'scale'})
                animated = animated or any(same_el(asel, sel) for _, asel, *_ in anim_rules)
                if animated: rep.add('s0', f"{r.src}:{ln} {short(sel)} ‹{p}: {v}›")
    for r in re.finditer(r'scale\(\s*0\s*\)', raw):
        rep.add('s0', f"{J.loc(r.start())} ‹scale(0)› في JS")

    # 5.14.3 خصائص الترتيب تتحرك
    for r, sel, props, items, ln, imp in trans_rules:
        if reduce_ctx(r.ctx): continue
        bad = sorted(p for p in props if p != '*' and LAYOUT.match(p))
        if bad and sel == r.sels[0]: rep.add('layout', f"{r.src}:{ln} {short(sel)} transition: {' '.join(bad)}")
    for nm in sorted(used):
        ps, _ = kf_props(nm)
        bad = sorted(p for p in ps if LAYOUT.match(p))
        if bad:
            ln = kfs[nm][0][0][1][0][3] if kfs[nm] and kfs[nm][0] and kfs[nm][0][0][1] else 0
            rep.add('layout', f"@keyframes {nm} سطر {ln}: {' '.join(bad)}")
    for r in re.finditer(r'\.animate\(\s*(\[[^\]]*\]|\{[^}]*\})', raw):
        bad = sorted(set(k for k in re.findall(r'([\w-]+)\s*:', r.group(1)) if LAYOUT.match(re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), k))))
        if bad: rep.add('layout', f"{J.loc(r.start())} animate(): {' '.join(bad)}")

    # 5.14.4 و5.14.11 hover
    for r in rules:
        if reduce_ctx(r.ctx): continue
        ctxl = ' '.join(r.ctx).lower()
        g_hover = bool(re.search(r'\(\s*(?:any-)?hover\s*:\s*hover\s*\)', ctxl)); g_fine = bool(re.search(r'\(\s*(?:any-)?pointer\s*:\s*fine\s*\)', ctxl))
        if re.search(r'\(\s*hover\s*:\s*none\s*\)', ctxl): continue
        for sel in r.sels:
            if not re.search(r':hover\b', sel) or re.search(r':not\([^)]*:hover', sel): continue
            base = re.sub(r':hover\b', '', sel)
            # قاعدة تُبطل حركة hover (transform: none على الهاتف مثلاً) علاجٌ لا عَرَض
            if r.decls and all(V.sub(v).strip().lower() in ('none', 'initial', 'unset', 'inherit', 'revert') for _, v, _, _ in r.decls): continue
            changed = set(p for p, *_ in r.decls)
            es_h = els(base, M_WILD)
            if es_h:
                # لكل عنصر: ما يغيّره hover فعلاً بعد ما يغلبه (style من JS، أو قاعدة أخصّ أو لاحقة)، ثم الانتقال النافذ عليه
                mov = False; pe_h = pe_of(sel)
                for n in es_h:
                    il = standing_inline(n) if pe_h is None else {}
                    ch = set(p_ for p_ in changed if not (p_ in il and not any(d[2] for d in r.decls if d[0] == p_)))
                    for p_ in list(ch):
                        if any(d[2] for d in r.decls if d[0] == p_): continue
                        for r2, s2, imp2 in by_prop.get(p_, []):
                            if r2 is r or rctx(r2, s2) == 'reduce' or pe_of(s2) != pe_h: continue
                            if any(nm in INTERACT for _, cp in cx(s2) for nm, _ in cp['ps']): continue
                            if (imp2 or (specificity(s2), r2.order) > (specificity(sel), r.order)) and persistent(n, s2):
                                ch.discard(p_); break
                    if ch & TRANSFORMISH or (ch and covers(eff_trans(n, pe_h, r), ch)): mov = True; break
            else:
                mov = bool(changed & TRANSFORMISH)
                if not mov:
                    for tr, ts, props, items, ln, imp in trans_rules:
                        if reduce_ctx(tr.ctx): continue
                        if ((tr is r) or same_el(ts, base)) and covers(props, changed):
                            mov = True; break
            where = W(r, sel)
            if g_hover and g_fine: continue
            if mov and not g_hover: rep.add('hover', where)
            elif mov: rep.add('hover-half', where + ' (hover:hover بلا pointer:fine)')
            elif not g_hover: rep.add('hover-plain', where)

    # الحالة المخففة: هل قاعدةٌ مخففة تحيّد هذا المصدر على هذا العنصر؟
    red_rules = [(r, sel) for r in rules for sel in r.sels if rctx(r, sel) == 'reduce']
    def neutral(r, kind, props=None):
        for p, v, imp, ln in r.decls:
            vl = V.sub(v).lower()
            if p == 'display' and vl.strip() == 'none': return True
            if kind == 'anim':
                if p in ('animation', '-webkit-animation', 'animation-name', '-webkit-animation-name'):
                    if vl.strip() in ('none', 'unset', 'initial', 'revert') or not parse_anim(v, V, kfs): return True
                    items = parse_anim(v, V, kfs)
                    if all(not any(moves(x) for x in kf_props(nm)[0]) or d <= 0.02 for nm, d, _ in items): return True
                if p in ('animation-duration', '-webkit-animation-duration') and all((secs(x.strip()) or 0) <= 0.02 for x in split_top(vl)): return True
                if p == 'animation-play-state' and 'paused' in vl: return True
            if kind == 'trans':
                if p in ('transition', '-webkit-transition'):
                    its = parse_trans(v, V)
                    if not its or all((d or 0) <= 0.02 or (pp and not moves(pp) and pp != 'all') for pp, d, _, _ in its): return True
                if p == 'transition-duration' and all((secs(x.strip()) or 0) <= 0.02 for x in split_top(vl)): return True
                if p == 'transition-property' and not any(x.strip() == 'all' or moves(x.strip()) for x in split_top(vl)): return True
                if p in ('transform', 'translate', 'scale', 'rotate') and vl.strip() == 'none' and props and all(re.match(r'(-webkit-)?(transform|translate|scale|rotate)$', x) for x in props): return True
        return False
    def wins(rr, rsel, sr, ssel, prop_imp):
        rimp = any(d[2] for d in rr.decls)
        if rimp and not prop_imp: return True
        if prop_imp and not rimp: return False
        a, b = specificity(rsel), specificity(ssel)
        return a > b or (a == b and rr.order >= sr.order)
    def covered(node, pe, kind, sr, ssel, imp, props=None):
        for rr, rsel in red_rules:
            if not neutral(rr, kind, props): continue
            disp = any(d[0] == 'display' and V.sub(d[1]).strip().lower() == 'none' for d in rr.decls)
            rpe = pe_of(rsel)
            # عنصر أو أحد أسلافه يُخفى كله
            if disp and rpe is None:
                x = node
                while x is not None and x.tag != '#doc':
                    if match_sel(x, rsel, M_RED): return True
                    x = x.parent
            if rpe != pe: continue
            if match_sel(node, rsel, M_RED) and (disp or wins(rr, rsel, sr, ssel, imp)): return True
        return False
    def covered_sel(sel, kind, sr, imp, props=None):
        for rr, rsel in red_rules:
            if not neutral(rr, kind, props): continue
            p = cx(rsel)
            if not p: continue
            uni = not (p[-1][1]['tag'] or p[-1][1]['cls'] or p[-1][1]['ids'] or p[-1][1]['attrs'])
            if (uni and pe_of(rsel) == pe_of(sel)) or subset_match(rsel, sel):
                if wins(rr, rsel, sr, sel, imp) or any(d[0] == 'display' for d in rr.decls): return True
            if any(d[0] == 'display' and V.sub(d[1]).strip().lower() == 'none' for d in rr.decls) and pe_of(rsel) is None:
                g = subj_key(rsel)
                if g and any(g <= (set(('t', cp['tag'])) if cp['tag'] else set()) | set(('c', c) for c in cp['cls']) | set(('i', x) for x in cp['ids']) for _, cp in cx(sel)[:-1]): return True
        return False

    # ما لا يعمل من JS في الحركة المخففة: داخل if (!reduce)، أو else لـif (reduce)، أو بعد if (reduce) return،
    # والدالة التي لا تُستدعى إلا من هناك. صنفٌ لا يُضاف إلا من هذه المواضع لا يطلق حركته في الحركة المخففة.
    m_ = J.m
    def split_ops(a, b, op):
        """تقسيم الشرط على && أو || في المستوى الأعلى؛ البنية من النص المقنَّع والمحتوى من الأصل"""
        out = []; d = 0; st = a; i = a
        while i < b:
            ch = m_[i]
            if ch in '([{': d += 1
            elif ch in ')]}': d -= 1
            elif d == 0 and m_.startswith(op, i): out.append((st, i)); i += len(op); st = i; continue
            i += 1
        out.append((st, b))
        return out
    def atom(a, b):
        while True:
            while a < b and m_[a].isspace(): a += 1
            while b > a and m_[b - 1].isspace(): b -= 1
            if a < b and m_[a] == '(' and match_close(m_, a) == b - 1: a += 1; b -= 1; continue
            break
        neg = False
        while a < b and m_[a] == '!' and m_[a + 1:a + 2] != '=':
            neg = not neg; a += 1
            while a < b and m_[a].isspace(): a += 1
            if a < b and m_[a] == '(' and match_close(m_, a) == b - 1: a += 1; b -= 1
        x = raw[a:b].strip()
        mm = re.fullmatch(r'(?:window\.)?([\w$]+)(?:\.matches)?(?:\(\))?', x)
        k = ('r' if mm.group(1) in rvars else 'm' if mm.group(1) in mvars else None) if mm else None
        if not k:
            mm = re.fullmatch(r'(?:window\.)?matchMedia\(\s*' + MQARG + r'\s*\)\.matches', x)
            k = mq_kind(mm.group(1)) if mm else None
        if not k: return None
        return (k == 'r') != neg          # قيمته حين تكون الحركة المخففة مطلوبة
    def cond(a, b):
        ors = split_ops(a, b, '||')
        if len(ors) > 1:
            vs = [cond(x, y) for x, y in ors]
            return True if True in vs else False if all(v is False for v in vs) else None
        ands = split_ops(a, b, '&&')
        if len(ands) > 1:
            vs = [cond(x, y) for x, y in ands]
            return False if False in vs else True if all(v is True for v in vs) else None
        return atom(a, b)
    def stmt_end(i):
        d = 0
        while i < len(m_):
            ch = m_[i]
            if ch in '([{': d += 1
            elif ch in ')]}':
                if d == 0: return i
                d -= 1
            elif d == 0 and ch in ';\n': return i
            i += 1
        return len(m_)
    def extent(i):
        """امتداد العبارة التي تبدأ عند i: كتلة، أو if بفروعها، أو عبارة واحدة"""
        while i < len(m_) and m_[i].isspace(): i += 1
        if m_[i:i + 1] == '{': return (i, match_close(m_, i, '{', '}'))
        mm = re.match(r'if\s*\(', m_[i:])
        if mm:
            q = match_close(m_, i + mm.end() - 1); c = extent(q + 1); e = c[1]
            em = re.match(r'\s*;?\s*else\b', m_[e + 1:])
            if em: e = extent(e + 1 + em.end())[1]
            return (i, e)
        return (i, stmt_end(i))
    def enclosing_end(i):
        st = i
        while st > 0:
            st = m_.rfind('{', 0, st)
            if st < 0: return len(m_)
            en = match_close(m_, st, '{', '}')
            if en > i: return en
        return len(m_)
    # ما لا يعمل من JS في الحركة المخففة: فرع شرطٍ قيمته فيها false، وelse لشرط قيمته true، وما بعد return محروس،
    # و«rm || …» و«!rm && …»، والدالة التي لا تُستدعى إلا من هناك. صنفٌ لا يُضاف إلا من هذه المواضع لا يطلق حركته.
    off = []
    if rvars or mvars:
        for r in re.finditer(r'\bif\s*\(', m_):
            p0 = r.end() - 1; q = match_close(m_, p0)
            v = cond(p0 + 1, q)
            if v is None: continue
            c = extent(q + 1)
            em = re.match(r'\s*;?\s*else\b', m_[c[1] + 1:])
            alt = extent(c[1] + 1 + em.end()) if em else None
            if v is False: off.append(c)
            else:
                if alt: off.append(alt)
                body = m_[c[0]:c[1] + 1]
                top = re.sub(r'\{[^{}]*\}', '', body[1:-1]) if body.startswith('{') else body
                if re.search(r'(?:^|[;\s])(?:return|continue|break)\b', top): off.append((c[1], enclosing_end(r.start())))
        for r in re.finditer(r'(?:^|[;{}\n])[ \t]*(!?\s*\(?\s*(?:window\.)?[\w$.]+(?:\(\))?\s*\)?)\s*(\|\||&&)', m_):
            v = atom(r.start(1), r.end(1))
            if (r.group(2) == '||' and v is True) or (r.group(2) == '&&' and v is False):
                off.append((r.end(), stmt_end(r.end())))
    dead = set()
    def in_off(i):
        return J.in_spans(i, off) or any(J.in_spans(i, J.funcs[f]) for f in dead)
    def sites(name):
        out = []
        for r in re.finditer(r'(?<![\w$.])' + re.escape(name) + r'(?![\w$])', m_):
            head = m_[max(0, r.start() - 12):r.start()]
            if re.match(r'\s*(?:[:=](?!=)|\.(?!call\b|apply\b|bind\b))', m_[r.end():r.end() + 8]) or re.search(r'function\s*\*?\s*$', head): continue
            if any(a <= r.start() <= a + 2 for a, b in J.funcs.get(name, [])): continue
            if any(abs(r.end() - a) < 200 and re.match(r'\s*\([^()]*\)\s*\{', m_[r.end():a + 1] + '{') and m_[r.end():a + 1].strip().endswith('{') for a, b in J.funcs.get(name, [])): continue
            out.append(r.start())
        for ob, (a, b) in J.objs.items():
            if any(a < x[0] < b for x in J.funcs.get(name, [])):
                out += [r.start() for r in re.finditer(r'(?<![\w$.])' + re.escape(ob) + r'\s*\[', m_)]
        return out
    ch = True
    while ch:
        ch = False
        for f in J.funcs:
            if f in dead: continue
            ss = sites(f)
            if ss and all(in_off(i) for i in ss): dead.add(f); ch = True
    def token_sites(kind, tok):
        if kind == 'c':
            pat = r'classList\.(?:add|toggle|replace)\([^)]*[\'"`]' + re.escape(tok) + r'[\'"`]|className\s*\+?=\s*[^;\n]*\b' + re.escape(tok) + r'\b'
        else:
            k = re.sub(r'^data-', '', tok); camel = re.sub(r'-(\w)', lambda m: m.group(1).upper(), k)
            pat = r'dataset\.' + re.escape(camel) + r'\s*=|setAttribute\(\s*[\'"]' + re.escape(tok) + r'[\'"]|toggleAttribute\(\s*[\'"]' + re.escape(tok) + r'[\'"]'
        return [r.start() for r in re.finditer(pat, raw)]
    def never_under_reduce(sel):
        """هل يتطلب المحدِّد صنفاً أو سمة لا يضيفها JS إلا في مسار معطَّل بالحركة المخففة؟"""
        for _, cp in cx(sel):
            for c in cp['cls']:
                if c in dyn_only:
                    ss = token_sites('c', c)
                    if ss and all(in_off(i) for i in ss): return True
            for a, _, _ in cp['attrs']:
                if a in dyn_attr and a.startswith('data-'):
                    ss = token_sites('a', a)
                    if ss and all(in_off(i) for i in ss): return True
        return False
    def path_off(i): return in_off(i)

    # 5.14.5 كل حركة تُلغى أو تُخفف داخل الاستعلام
    seen5 = set()
    def need(kind, r, sel, imp, ln, what, props=None):
        if rctx(r, sel) != 'normal' or never_under_reduce(sel): return
        es = els(sel, M_WILD)
        pe = pe_of(sel)
        ok = all(covered(n, pe, kind, r, sel, imp, props) for n in es) if es else covered_sel(sel, kind, r, imp, props)
        if not ok:
            key = (r.src, ln, sel)
            if key not in seen5: seen5.add(key); rep.add('reduce', f"{r.src}:{ln} {short(sel)} {what}")
    js_vars = set(re.findall(r'setProperty\(\s*[\'"](--[\w-]+)', raw))
    def trans_moves(r, sel, props):
        """انتقال يحرّك فعلاً: نافذ على عنصر واحد على الأقل، وشيءٌ يغيّر خاصيته المتحركة ويعمل في الحركة المخففة
        (قاعدة CSS أخرى على العنصر، أو كتابة JS في style خارج المسار المعطَّل). انتقال لا يغيّر أحدٌ ما يحرّكه ليس حركة."""
        mp = lambda p: moves(p) and ('*' in props or p in props)
        pe = pe_of(sel)
        es = els(sel, M_WILD)
        if not es: return True
        live = []
        for n in es:
            if pe is None and 'transition' in standing_inline(n): continue
            w1, w2 = winner(n, pe, M_START), winner(n, pe, M_WILD)
            if (w1 and w1[1] is r) or (w2 and w2[1] is r): live.append(n)
        if not live: return False
        # خاصية متحركة بمتغير CSS يكتبه JS (setProperty('--x')) تتغير مع كل كتابة
        if any(mp(d[0]) and set(re.findall(r'var\(\s*(--[\w-]+)', d[1])) & js_vars for d in r.decls): return True
        for n in live:
            for p_, lst in by_prop.items():
                if not mp(p_): continue
                for r2, s2, _ in lst:
                    # المغيِّر قاعدةُ حالة (صنف يضيفه JS أو :hover أو سمة)، لا قاعدةٌ تنطبق دائماً فلا تغيّر شيئاً
                    if rctx(r2, s2) == 'reduce' or pe_of(s2) != pe or match_sel(n, s2, M_START): continue
                    if match_sel(n, s2, M_WILD) and not never_under_reduce(s2): return True
            if pe is None:
                for p_, ws in inline.get(id(n), {}).items():
                    if mp(p_) and any(not in_off(i) for i, _ in ws): return True
        return False
    for r, sel, props, items, ln, imp in trans_rules:
        mv = sorted(p for p in props if p == '*' or moves(p))
        if mv and trans_moves(r, sel, props): need('trans', r, sel, imp, ln, 'transition: ' + ' '.join('all' if p == '*' else p for p in mv), set(mv))
    for r, sel, nm, dur, tm, ln, imp in anim_rules:
        ps, _ = kf_props(nm)
        if any(moves(p) for p in ps) and dur > 0.02: need('anim', r, sel, imp, ln, 'animation: ' + nm)
    js_moves = bool(re.search(r'\bgsap\.(?:to|from|fromTo|timeline)\b|ScrollTrigger|\banime\(|\.animate\(\s*[\[{]|behavior\s*:\s*[\'"]smooth', raw)) or (
        bool(re.search(r'requestAnimationFrame|IntersectionObserver|addEventListener\(\s*[\'"]scroll', raw)) and
        bool(re.search(r'\.style\.(?:transform|translate|rotate|scale|top|left|right|bottom)\s*=|\.style\.setProperty\(\s*[\'"](?:--|transform)', raw)))
    js_reads = 'prefers-reduced-motion' in raw
    css_reads = any('prefers-reduced-motion' in t for _, t, _ in css_src)

    # 5.14.6 ما يبدأ مخفياً بـopacity:0 يظهر في الحالة المخففة
    frame = J.closure(J.roots(['scroll']))
    reveal = frame + J.closure(J.io_roots())
    reveal_cls = set(); js_red_cls = set(); cls_sites = {}
    for r in re.finditer(r'classList\.(?:add|toggle)\(\s*[\'"`]([\w-]+)', raw):
        if J.in_spans(r.start(), reveal):
            reveal_cls.add(r.group(1)); cls_sites.setdefault(r.group(1), []).append(r.start())
        ln_s = raw.rfind('\n', 0, r.start()); prevl = raw.rfind('\n', 0, max(ln_s, 0))
        if set(re.findall(r'[\w$]+', raw[max(prevl, 0):r.end()])) & rvars and not re.search(r'!\s*(' + '|'.join(map(re.escape, rvars)) + r')\b', raw[max(prevl, 0):r.end()]):
            js_red_cls.add(r.group(1))
    reveal_attr = set()
    for r in re.finditer(r'dataset\.(\w+)\s*=|setAttribute\(\s*[\'"]([\w-]+)', raw):
        if J.in_spans(r.start(), reveal):
            reveal_attr.add('data-' + re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), r.group(1)) if r.group(1) else r.group(2))
    reveal_nodes = set()
    shown_rules = [(r, sel) for r in rules if rctx(r, '') != 'reduce' for sel in r.sels
                   for p, v, _, _ in r.decls if p == 'opacity' and not is_zero_opacity(V.sub(v))]
    for r in rules:
        for p, v, imp, ln in r.decls:
            if p != 'opacity' or not is_zero_opacity(V.sub(v)): continue
            for sel in r.sels:
                if rctx(r, sel) != 'normal' or pe_of(sel): continue
                es = els(sel, M_START)
                if not es: continue
                bad = []
                for n in es:
                    # يظهر بحركة؟ بحركة تحميل تحرّك opacity، أو بصنف/سمة يضيفها التمرير أو المراقب
                    how = None
                    for ar, asel, nm, dur, tm, aln, aimp in anim_rules:
                        if 'opacity' in kf_props(nm)[0] and match_sel(n, asel, M_WILD): how = 'anim'; break
                    if not how:
                        for sr, ssel in shown_rules:
                            if match_sel(n, ssel, M_START) or not match_sel(n, ssel, M_WILD): continue
                            need_c = set(c for _, cp in cx(ssel) for c in cp['cls']) & dyn_only
                            need_a = set(a for _, cp in cx(ssel) for a, _, _ in cp['attrs']) & dyn_attr
                            if any(nm in INTERACT for _, cp in cx(ssel) for nm, _ in cp['ps']): continue
                            if (need_c & reveal_cls) or (need_a & reveal_attr): how = 'class'; break
                    if not how: continue
                    reveal_nodes.add(id(n))
                    ok = False
                    for rr, rsel in red_rules:
                        if pe_of(rsel): continue
                        disp = any(d[0] == 'display' and V.sub(d[1]).strip().lower() == 'none' for d in rr.decls)
                        op = [d for d in rr.decls if d[0] == 'opacity' and not is_zero_opacity(V.sub(d[1]))]
                        if disp:
                            x = n
                            while x is not None and x.tag != '#doc':
                                if match_sel(x, rsel, M_RED): ok = True; break
                                x = x.parent
                        if not ok and op and match_sel(n, rsel, M_RED) and (op[0][2] or not imp) and \
                                (op[0][2] or specificity(rsel) >= specificity(sel)): ok = True
                        if ok: break
                    if not ok and how == 'anim':
                        # الحالة المخففة لا تلغي حركة الظهور فتكتمل
                        ok = not any(neutral(rr, 'anim') and not any(d[0] == 'animation-duration' for d in rr.decls) and match_sel(n, rsel, M_RED) for rr, rsel in red_rules)
                    if not ok and how == 'class':
                        # فرع JS المخفف يضيف صنف الظهور، أو مسار الظهور نفسه يعمل في الحركة المخففة فيظهر العنصر بلا حركة
                        for sr, ssel in shown_rules:
                            if match_sel(n, ssel, M_WILD) and not match_sel(n, ssel, M_START):
                                need = set(c for _, cp in cx(ssel) for c in cp['cls']) & dyn_only
                                if need & js_red_cls: ok = True; break
                                if any(not path_off(i) for c in need for i in cls_sites.get(c, [])): ok = True; break
                                if set(a for _, cp in cx(ssel) for a, _, _ in cp['attrs']) & reveal_attr: ok = True; break
                    if not ok: bad.append(n)
                if bad: rep.add('reveal', f"{r.src}:{ln} {short(sel)} ‹opacity:0› {len(bad)} عنصراً")

    # 5.14.7 ease-in
    for r in rules:
        if rctx(r, r.sels[0] if r.sels else '') == 'reduce': continue
        for p, v, imp, ln in r.decls:
            tms = []
            if p in ('transition', '-webkit-transition'): tms = [it[3] for it in parse_trans(v, V)]
            elif p in ('animation', '-webkit-animation'): tms = [it[2] for it in parse_anim(v, V, kfs)]
            elif p in ('transition-timing-function', 'animation-timing-function'): tms = [x.strip().lower() for x in split_top(V.sub(v))]
            if any(easein_like(t) for t in tms): rep.add('easein', f"{r.src}:{ln} {short(r.sels[0])} ‹{V.sub(v)[:40]}›")
    for r in re.finditer(r'easing\s*:\s*[\'"](ease-in|cubic-bezier\([^)]*\))[\'"]', raw):
        if easein_like(r.group(1)): rep.add('easein', f"{J.loc(r.start())} ‹easing: {r.group(1)}›")

    # 5.14.8 blur من JS · 5.14.9 setProperty على عنصر ثقيل في حلقة
    blur_vars = set(re.findall(r'blur\(\s*(?:calc\([^)]*?)?var\(\s*(--[\w-]+)', ' '.join(V.sub(d[1]) if False else d[1] for r in rules for d in r.decls)))
    for r in re.finditer(r'\.style\.(?:filter|backdropFilter|webkitBackdropFilter|WebkitBackdropFilter)\s*=([^;\n]*)', raw):
        if 'blur' in r.group(1): rep.add('blurjs', f"{J.loc(r.start())}" + (' في حلقة' if J.in_spans(r.start(), frame) else ''))
    for r in re.finditer(r'setProperty\(\s*[\'"]((?:-webkit-)?(?:backdrop-)?filter|--[\w-]+)[\'"]\s*,([^;\n]*)', raw):
        if r.group(1) in blur_vars or ('filter' in r.group(1) and 'blur' in r.group(2)):
            rep.add('blurjs', f"{J.loc(r.start())} {r.group(1)}" + (' في حلقة' if J.in_spans(r.start(), frame) else ''))
    for r in re.finditer(r'\.animate\(\s*(\[[^\]]*\]|\{[^}]*\})', raw):
        if re.search(r'filter\s*:[^,}\]]*blur', r.group(1)): rep.add('blurjs', f"{J.loc(r.start())} animate()")

    def guarded(i):
        """قيمة ثابتة، أو كتابة لا تقع إلا حين تتغير الحالة (if (a !== b) { … b = a })"""
        arg = raw[i:i + 200].split(',', 1)[1] if ',' in raw[i:i + 200] else ''
        if re.match(r'\s*([\'"])[^\'"`$]*\1\s*\)', arg) or re.match(r'\s*-?\d*\.?\d+\s*\)', arg): return True
        st = J.m.rfind('{', 0, i)
        while st > 0:
            if match_close(J.m, st, '{', '}') >= i:
                head = J.m[max(0, st - 160):st]
                c = re.search(r'if\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$', head)
                if c:
                    mm = re.search(r'([\w$.]+)\s*!==?\s*([\w$.]+)', c.group(1))
                    blk = J.m[st:match_close(J.m, st, '{', '}')]
                    if mm and any(re.search(r'(?<![\w$.])' + re.escape(x) + r'\s*=(?!=)', blk) for x in mm.groups()): return True
                break
            st = J.m.rfind('{', 0, st)
        return False
    unresolved = []
    for r in re.finditer(r'([\w$.\[\]]+)\.style\.setProperty\(\s*[\'"](--[\w-]+)[\'"]', raw):
        if not J.in_spans(r.start(), frame) or guarded(r.start()): continue
        res = resolve(r.group(1), r.start())
        if res is None: unresolved.append(f"{J.loc(r.start())} {r.group(1)}"); continue
        if res[0] == '*': cnt = len(nodes); tgt = 'الصفحة كلها'
        else:
            try: es = [n for s_ in split_top(res[1]) for n in els(s_, M_START)]
            except Exception: es = []
            ds = [descendants(n) for n in es]; cnt = max(ds, default=0); tgt = res[1]
        if cnt >= 10:
            rng = f"{min(ds)} إلى {cnt}" if res[0] != '*' and len(set(ds)) > 1 else str(cnt)
            rep.add('heavy', f"{J.loc(r.start())} {r.group(2)} على {short(tgt)} ({rng} عنصراً داخله)")

    # 5.14.10 انتقال واجهة فوق حدّه (300ms، و500ms للنافذة والدرج) بلا سطر يذكر صنفه في DESIGN.md
    design = open('DESIGN.md', encoding='utf-8', errors='ignore').read() if os.path.isfile('DESIGN.md') else ''
    # انتقال الواجهة: ما يحرّك استجابةً لفعل الزائر، أي خاصيةً تغيّرها قاعدة :hover أو :focus أو :active أو [open]،
    # أو صنفٌ يضيفه JS عند نقرة أو مفتاح. الدخول السردي وتبدّل الألوان مع التمرير ليسا واجهة.
    UI_PS = {'hover', 'focus', 'focus-visible', 'focus-within', 'active', 'checked', 'open', 'popover-open', 'modal', 'target'}
    UI_ATTR = {'open', 'aria-expanded', 'aria-pressed', 'aria-selected', 'aria-checked', 'aria-current', 'hidden'}
    def ui_trigger(tsel):
        for _, cp in cx(tsel):
            if any(nm in UI_PS for nm, _ in cp['ps']): return True
            for a, _, _ in cp['attrs']:
                ss = token_sites('a', a) if a in dyn_attr else []
                if a in UI_ATTR or (ss and all(J.in_spans(i, inter) for i in ss)): return True
            for c in cp['cls']:
                if c in dyn_only:
                    ss = token_sites('c', c)
                    if ss and all(J.in_spans(i, inter) for i in ss): return True
        return False
    def strip_ui(sel):
        return re.sub(r':(?:hover|focus-visible|focus-within|focus|active|checked|open|popover-open|modal|target)\b', '', sel).strip()
    IDENT = re.compile(r'^\s*(?:none|(?:translate[xyz3d]*\(\s*0(?:px|%)?\s*(?:,\s*0(?:px|%)?\s*)*\)|scale[xyz3d]*\(\s*1\s*(?:,\s*1\s*)*\)|rotate[xyz]?\(\s*0(?:deg)?\s*\))(?:\s+(?:translate[xyz3d]*\(\s*0(?:px|%)?\s*(?:,\s*0(?:px|%)?\s*)*\)|scale[xyz3d]*\(\s*1\s*(?:,\s*1\s*)*\)|rotate[xyz]?\(\s*0(?:deg)?\s*\)))*)\s*$', re.I)
    def changed_props(tr, ts):
        """ما تغيّره قاعدة المحفِّز فعلاً: transform بقيمة الهوية (translateY(0)) لا يحرّك شيئاً إلا إن كان العنصر مزاحاً في أصله"""
        out = set()
        for p_, v_, _, _ in tr.decls:
            if p_ in ('transform', 'translate', 'scale', 'rotate') and IDENT.match(V.sub(v_)):
                base = strip_ui(ts)
                moved = any(d[0] == p_ and not IDENT.match(V.sub(d[1])) and same_el(bs, base)
                            for br in rules if br is not tr and rctx(br, '') != 'reduce' for d in br.decls for bs in br.sels
                            if not ui_trigger(bs))
                if not moved: continue
            out.add(p_)
        return out
    # محفِّز عامّ (:focus-visible وحده) يرسم إطار التركيز، ولا يخص عنصراً بعينه
    triggers = [(tr, ts, changed_props(tr, ts)) for tr in rules if rctx(tr, '') != 'reduce' for ts in tr.sels
                if ui_trigger(ts) and strip_ui(ts) not in ('', '*')]
    # والكتابة في style من معالج نقرة أو مفتاح محفِّزٌ أيضاً
    for mm in re.finditer(r'([\w$.\[\]]+)\.style\.(?:setProperty\(\s*[\'"]([\w-]+)|(\w+)\s*=(?!=))', raw):
        if not J.in_spans(mm.start(), inter): continue
        res = resolve(mm.group(1), mm.start())
        if not res or res[0] != 'sel': continue
        prop = mm.group(2) or re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), mm.group(3))
        triggers.append((None, res[1], {prop}))
    def effective(r, sel, lp):
        """هل يبقى هذا الانتقال نافذاً؟ قاعدة أخصّ أو لاحقة تكتب transition على العنصر نفسه في حالته الأولى تُبطله"""
        es = els(sel, M_WILD)
        if not es: return True
        for n in es:
            beaten = False
            for r2, s2, p2, it2, ln2, imp2 in trans_rules:
                if r2 is r or rctx(r2, s2) == 'reduce' or any(nm in INTERACT for _, cp in cx(s2) for nm, _ in cp['ps']): continue
                if pe_of(s2) != pe_of(sel) or not match_sel(n, s2, M_START): continue
                a_, b_ = specificity(s2), specificity(sel)
                if a_ > b_ or (a_ == b_ and r2.order > r.order): beaten = True; break
            if not beaten: return True
        return False
    def why_(names, durs):
        """السبب سطرٌ في DESIGN.md يذكر صنف العنصر أو معرّفه نفسه كلمةً تامة، لا رقمٌ يتصادف ولا جزءُ كلمة"""
        return any(x and re.search(r'(?<![\w-])[.#]?' + re.escape(x) + r'(?![\w-])', design) for x in names)
    MODAL = re.compile(r'(?:^|[-_])(?:modal|drawer|dialog|lightbox|lb|sheet|overlay|popup|panel)(?:[-_]|$)')
    def budget(sel):
        """النوافذ والأدراج 500ms، وسائر الواجهة 300ms (AUDIT.md §2)"""
        p = cx(sel); cp = p[-1][1] if p else {'tag': None, 'cls': [], 'ids': []}
        if cp['tag'] == 'dialog' or any(MODAL.search(x) for x in cp['cls'] + cp['ids']): return 0.5
        if any(n.tag == 'dialog' or n.attrs.get('role') in ('dialog', 'alertdialog') or 'aria-modal' in n.attrs for n in els(sel, M_WILD)): return 0.5
        return 0.3
    for r, sel, props, items, ln, imp in trans_rules:
        if rctx(r, sel) == 'reduce': continue
        long_ = [it for it in items if it[1] and it[1] > budget(sel)]
        if not long_: continue
        lp = set('*' if it[0] in (None, 'all') else it[0] for it in long_)
        if not any(covers(lp, ch) and same_el(ts if tr is None else strip_ui(ts), sel) for tr, ts, ch in triggers): continue
        if not effective(r, sel, lp): continue
        p = cx(sel); cp = p[-1][1] if p else {'cls': [], 'ids': []}
        if not why_(cp['cls'] + cp['ids'], [it[1] for it in long_]):
            rep.add('slow', f"{r.src}:{ln} {short(sel)} {max(it[1] for it in long_) * 1000:.0f}ms")
    # وحركة keyframes يطلقها فعل الزائر نفسه (صنف نقرة أو [open] أو :hover) وتطول فوق 300ms
    for r, sel, nm, dur, tm, ln, imp in anim_rules:
        if rctx(r, sel) == 'reduce' or dur <= budget(sel) or not ui_trigger(sel): continue
        p = cx(sel); cp = p[-1][1] if p else {'cls': [], 'ids': []}
        if not why_(cp['cls'] + cp['ids'], [dur]):
            rep.add('slow', f"{r.src}:{ln} {short(sel)} animation {nm} {dur * 1000:.0f}ms")
    # تكرار المحدد الواحد في قائمة يُذكر مرة
    if 'slow' in rep.items: rep.items['slow'] = list(dict.fromkeys(rep.items['slow']))

    # 5.14.12 blur من 20px فأكثر يتحرك
    def big_blur(v):
        for a, u in re.findall(r'blur\(\s*(\d*\.?\d+)\s*(px|rem|em)?', V.sub(v)):
            px = float(a) * (16 if u in ('rem', 'em') else 1)
            if px >= 20: return px
        return 0
    for nm in used:
        for fl in kfs.get(nm, []):
            for stops, decls in fl:
                for d in decls:
                    if 'filter' in d[0] and big_blur(d[1]): rep.add('bigblur', f"@keyframes {nm} سطر {d[3]} blur({big_blur(d[1]):.0f}px)")
    for r in rules:
        if rctx(r, r.sels[0] if r.sels else '') == 'reduce': continue
        for p, v, imp, ln in r.decls:
            if 'filter' not in p or not big_blur(v): continue
            for sel in r.sels[:1]:
                if any(same_el(ts, sel) for _, ts, props, _, _, _ in trans_rules if props & {'*', 'filter', 'backdrop-filter', '-webkit-backdrop-filter'}):
                    rep.add('bigblur', f"{r.src}:{ln} {short(sel)} blur({big_blur(v):.0f}px)")

    # ───── المخرج ─────
    out = []; fail = 0
    def line(num, rule, key, ok_msg, bad_msg, sev='✗'):
        nonlocal fail
        xs = list(dict.fromkeys(rep.items.get(key, [])))
        if not xs: out.append(f"✓ {num} {ok_msg}"); return
        if sev == '✗': fail = 1
        head = f"{sev} {num} {bad_msg} في {len(xs)} موضعاً ({rule}): {xs[0]}" + (f" ‹و{len(xs) - 1} غيره›" if len(xs) > 1 else '')
        out.append(head)
        if VERBOSE:
            for x in xs: out.append('    ' + x)
    line('6.1.29', '5.14.1', 'all', 'لا transition: all', 'transition: all صريحاً أو ضمناً')
    line('6.1.30', '5.14.2', 's0', 'لا scale(0) بدايةً', 'scale(0) حالةَ بداية')
    line('6.1.31', '5.14.3', 'layout', 'لا خاصية ترتيب تتحرك', 'خاصية ترتيب تتحرك')
    line('6.1.32', '5.14.4', 'hover', 'hover المتحرك محصور بالفأرة', 'hover متحرك بلا (hover:hover) and (pointer:fine)')
    line('6.1.33', '5.14.5', 'reduce', 'كل حركة تُلغى أو تُخفف في الحركة المخففة', 'حركة لا تطالها الحركة المخففة')
    if js_moves and not js_reads:
        if css_reads:
            out.append('⚠ 6.1.33 JS يحرّك (GSAP أو animate أو التمرير الناعم أو rAF) ولا يقرأ prefers-reduced-motion؛ CSS وحده لا يوقفه (5.14.5)')
        else:
            fail = 1
            out.append('✗ 6.1.33 JS يحرّك (GSAP أو animate أو التمرير الناعم أو rAF) ولا ذكر لـprefers-reduced-motion في CSS ولا JS (5.14.5)')
    line('6.1.34', '5.14.6', 'reveal', 'ما يبدأ مخفياً يظهر في الحركة المخففة', 'عنصر يبدأ بـopacity:0 ويبقى مخفياً في الحركة المخففة')
    line('6.1.35', '5.14.7', 'easein', 'لا ease-in', 'ease-in', '⚠')
    line('6.1.36', '5.14.8', 'blurjs', 'لا blur يغيّره JS', 'blur يغيّره JS', '⚠')
    line('6.1.37', '5.14.9', 'heavy', 'لا setProperty على عنصر ثقيل في حلقة التمرير', 'setProperty في حلقة التمرير على عنصر فيه 10 عناصر فأكثر', '⚠')
    line('6.1.38', '5.14.10', 'slow', 'انتقالات الواجهة في حدّها (300ms، و500ms للنافذة) أو معلَّلة في DESIGN.md', 'انتقال واجهة فوق حدّه (300ms، و500ms للنافذة) بلا سطر يذكر صنفه في DESIGN.md', '⚠')
    hp = rep.items.get('hover-half', []) + rep.items.get('hover-plain', [])
    rep.items['hover-w'] = hp
    line('6.1.39', '5.14.11', 'hover-w', 'كل hover محصور بـ(hover:hover) and (pointer:fine)', 'hover غير محصور كاملاً بالفأرة', '⚠')
    line('6.1.40', '5.14.12', 'bigblur', 'لا blur متحرك من 20px', 'blur متحرك من 20px فأكثر', '⚠')
    if VERBOSE and unresolved:
        out.append('    (setProperty في حلقة بهدف لم يُحسم: ' + ' · '.join(unresolved) + ')')
    print('\n'.join(out))
    return fail

# ───────────────────────── الطبقة الثالثة: Chrome بلا واجهة ─────────────────────────
PROBE = r"""
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const frames = () => Promise.race([new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))), sleep(500)]);
  if (document.readyState !== 'complete') await new Promise(r => addEventListener('load', r, {once: true}));
  try { await Promise.race([document.fonts.ready, sleep(3000)]); } catch (e) {}
  await sleep(400);
  const SKIP = new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','TITLE','OPTION']);
  const nodes = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let t; (t = w.nextNode());) {
    const s = t.nodeValue.replace(/\s+/g, ' ').trim();
    if (s.replace(/[\s\d٠-٩.,:%+\-–—/·|()«»"'!؟?،؛]/g, '').length < 2) continue;
    const p = t.parentElement; if (!p || SKIP.has(p.tagName) || p.closest('svg,[hidden],dialog:not([open])')) continue;
    nodes.push({t, p, s, v: false});
  }
  const clipped = cs => {
    const m = /inset\(([^)]*)\)/.exec(cs.clipPath || ''); if (!m) return false;
    const v = m[1].split(/\s+round\s+/)[0].trim().split(/\s+/).map(x => x.endsWith('%') ? parseFloat(x) : NaN);
    const [a, b = a, c = a, d = b] = v; return (a + c >= 99.5) || (b + d >= 99.5);
  };
  // النص ظاهر إن كان له صندوق، وشفافيته المتراكمة فوق 6٪، ولا يقصّه clip-path ولا حاوية overflow:hidden أو clip
  // (سطر مزاح بـtranslateY(110%) داخل حاوية مقصوصة مخفيٌّ وإن بقيت شفافيته 1)
  const range = document.createRange();
  const visible = n => {
    const p = n.p; if (!p.isConnected) return false;
    range.selectNodeContents(n.t);
    const rs = [...range.getClientRects()].filter(x => x.width >= 1 && x.height >= 1);
    if (!rs.length) return false;
    const cs = getComputedStyle(p); if (cs.visibility !== 'visible') return false;
    let op = 1, box = rs;
    for (let e = p; e && e.nodeType === 1; e = e.parentElement) {
      const c = e === p ? cs : getComputedStyle(e);
      op *= parseFloat(c.opacity); if (op < 0.06) return false;
      if (clipped(c)) return false;
      if (/hidden|clip/.test(c.overflowX + ' ' + c.overflowY) && e !== document.documentElement && e !== document.body) {
        const b = e.getBoundingClientRect();
        box = box.map(x => ({l: Math.max(x.left ?? x.l, b.left), r: Math.min(x.right ?? x.r, b.right), t: Math.max(x.top ?? x.t, b.top), b: Math.min(x.bottom ?? x.b, b.bottom)}))
                 .filter(x => x.r - x.l >= 1 && x.b - x.t >= 1);
        if (!box.length) return false;
      }
    }
    return true;
  };
  // في الحركة المخففة: عنصر يتغيّر موضعه أو حجمه مع التمرير (parallax بـJS)، أو حلقة حركة لا تنتهي
  const REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const last = new Map(), moved = new Map();
  const label = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].slice(0, 2).join('.') : '');
  const mat = t => { if (!t || t === 'none') return [1, 0, 0, 1, 0, 0]; const v = t.match(/-?[\d.e]+/g).map(Number); return v.length === 16 ? [v[0], v[1], v[4], v[5], v[12], v[13]] : v; };
  const track = () => {
    if (!REDUCE) return;
    let k = 0;
    for (const e of document.querySelectorAll('body *')) {
      if (++k > 4000) break;
      const t = getComputedStyle(e).transform;
      if (t === 'none' && !last.has(e)) continue;
      const m = mat(t), o = last.get(e);
      if (o && (Math.abs(m[4] - o[4]) > 2 || Math.abs(m[5] - o[5]) > 2 || Math.abs(m[0] - o[0]) > 0.01 || Math.abs(m[3] - o[3]) > 0.01)) moved.set(e, (moved.get(e) || 0) + 1);
      last.set(e, m);
    }
  };
  const finish = () => { for (const a of document.getAnimations()) { try { const t = a.effect && a.effect.getComputedTiming(); if (t && isFinite(t.endTime)) a.finish(); } catch (e) {} } };
  const sample = () => { finish(); for (const n of nodes) if (!n.v && visible(n)) n.v = true; track(); };
  const H = innerHeight, step = Math.max(120, Math.round(H * 0.33));
  sample();
  let y = 0;
  for (let i = 0; i < 600; i++) {
    const max = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight) - H;
    if (y >= max) break;
    y = Math.min(max, y + step); scrollTo(0, y);
    await frames(); await sleep(70); await frames(); sample();
  }
  await sleep(500); sample();
  scrollTo(0, 0); await sleep(300); sample();
  const vis = [...new Set(nodes.filter(n => n.v).map(n => n.s))];
  const all = [...new Set(nodes.map(n => n.s))];
  // ما تحرّك في عيّنتين فأكثر، وحلقات لا تنتهي تحرّك موضعاً، بلا الأبناء الذين يتحركون بحركة آبائهم
  const movers = [...moved].filter(([e, n]) => n >= 2 && ![...moved.keys()].some(a => a !== e && a.contains(e))).map(([e]) => label(e));
  const loops = REDUCE ? document.getAnimations().filter(a => { try { const t = a.effect.getComputedTiming(); const ks = a.effect.getKeyframes ? a.effect.getKeyframes() : [];
      return a.playState === 'running' && t.iterations === Infinity && ks.some(k => k.transform || k.translate || k.rotate || k.scale || k.left || k.top); } catch (e) { return false; } })
      .map(a => (a.effect.target ? label(a.effect.target) : '') + (a.animationName ? ' ' + a.animationName : '')) : [];
  return JSON.stringify({vis, all, rm: REDUCE, w: innerWidth, movers: [...new Set(movers)].slice(0, 12), loops: [...new Set(loops)].slice(0, 12)});
})()
"""

def main_browser():
    import subprocess, tempfile, threading, time, shutil, functools
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
    def warn(msg):
        print(f"⚠ 6.1.41 طبقة المتصفح لم تُفحص: {msg}؛ الحركة المخففة على 390 و1440 لم تُرَ (5.14.13)")
        return 0
    if not os.path.isfile('index.html'): return warn('لا index.html')
    cands = [os.environ.get('CHROME', ''), '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
             shutil.which('google-chrome') or '', shutil.which('chromium') or '', shutil.which('chromium-browser') or '']
    chrome = next((c for c in cands if c and os.path.isfile(c)), None)
    if not chrome: return warn('Chrome غير موجود')

    class Q(SimpleHTTPRequestHandler):
        def log_message(s, *a): pass
    srv = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Q, directory=os.getcwd()))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

    r1, w1 = os.pipe(); r2, w2 = os.pipe()
    hi = [os.dup(r1), os.dup(w2)]; os.close(r1); os.close(w2)
    ud = tempfile.mkdtemp(prefix='gate-chrome-')
    def pre():
        os.dup2(hi[0], 3); os.dup2(hi[1], 4)
    try:
        proc = subprocess.Popen([chrome, '--headless', '--remote-debugging-pipe', '--user-data-dir=' + ud, '--no-first-run',
                                 '--no-default-browser-check', '--disable-extensions', '--mute-audio', '--hide-scrollbars',
                                 '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
                                 '--disable-backgrounding-occluded-windows', 'about:blank'],
                                preexec_fn=pre, pass_fds=(3, 4), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return warn(f'تعذّر تشغيل Chrome ({e.__class__.__name__})')
    finally:
        for f in hi: os.close(f)
    wf = os.fdopen(w1, 'wb', 0); rfd = r2
    lock = threading.Lock(); pend = {}; events = {}; cv = threading.Condition()
    state = {'id': 0, 'dead': False}
    def reader():
        buf = b''
        while True:
            try: ch = os.read(rfd, 1 << 16)
            except OSError: ch = b''
            if not ch: break
            buf += ch
            while b'\0' in buf:
                raw, buf = buf.split(b'\0', 1)
                try: m = json.loads(raw)
                except ValueError: continue
                with cv:
                    if 'id' in m: pend[m['id']] = m
                    elif 'method' in m: events.setdefault((m.get('sessionId'), m['method']), []).append(m)
                    cv.notify_all()
        with cv: state['dead'] = True; cv.notify_all()
    threading.Thread(target=reader, daemon=True).start()
    def send(method, params=None, sid=None, timeout=30):
        with lock:
            state['id'] += 1; i = state['id']
            msg = {'id': i, 'method': method, 'params': params or {}}
            if sid: msg['sessionId'] = sid
            wf.write(json.dumps(msg).encode() + b'\0')
        end = time.time() + timeout
        with cv:
            while i not in pend:
                if state['dead'] or time.time() > end: raise TimeoutError(method)
                cv.wait(0.2)
            m = pend.pop(i)
        if 'error' in m: raise RuntimeError(f"{method}: {m['error'].get('message')}")
        return m.get('result', {})
    def wait_event(sid, name, timeout):
        end = time.time() + timeout
        with cv:
            while not events.get((sid, name)):
                if state['dead'] or time.time() > end: return False
                cv.wait(0.2)
            events[(sid, name)].pop(0); return True

    def run(width, height, mobile, reduce):
        tid = send('Target.createTarget', {'url': 'about:blank'})['targetId']
        sid = send('Target.attachToTarget', {'targetId': tid, 'flatten': True})['sessionId']
        try:
            send('Page.enable', {}, sid)
            # الألسنة الأربعة تعمل معاً، والتركيز المحاكى يمنح كلاً منها إطارات الرسم التي يحتاجها IntersectionObserver
            send('Emulation.setFocusEmulationEnabled', {'enabled': True}, sid)
            send('Emulation.setDeviceMetricsOverride', {'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': mobile}, sid)
            send('Emulation.setTouchEmulationEnabled', {'enabled': mobile, 'maxTouchPoints': 5 if mobile else 1}, sid)
            send('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce' if reduce else 'no-preference'}]}, sid)
            send('Page.navigate', {'url': url}, sid)
            if not wait_event(sid, 'Page.loadEventFired', 40): raise TimeoutError('load')
            res = send('Runtime.evaluate', {'expression': PROBE, 'awaitPromise': True, 'returnByValue': True}, sid, timeout=150)
            if 'exceptionDetails' in res: raise RuntimeError('probe')
            return json.loads(res['result']['value'])
        finally:
            try: send('Target.closeTarget', {'targetId': tid}, timeout=5)
            except Exception: pass

    results = {}; errs = []
    def job(key, *a):
        try: results[key] = run(*a)
        except Exception as e: errs.append(f"{key}: {e}")
    jobs = [('390', 390, 844, True), ('1440', 1440, 900, False)]
    ths = []
    for k, w, h, mob in jobs:
        for red in (False, True):
            t = threading.Thread(target=job, args=((k, red), w, h, mob, red)); t.start(); ths.append(t)
    for t in ths: t.join(200)
    # الأرقام تُسقط من المقارنة: عدّادٌ يُلتقط في منتصف عدّه («9 مليون» ثم «21 مليون») ليس نصاً مخفياً
    norm = lambda x: re.sub(r'[\s\d٠-٩.,،٬٫%+\-]', '', x)
    def lost_of(n, r):
        rv = norm(''.join(r['vis']))
        return [x for x in n['vis'] if norm(x) and norm(x) not in rv]
    # الرسوب يُؤكَّد بإعادة القياس في لسان واحد على التوالي، فلا يُحسب نصٌّ فات أخذَ عيّنته لسانٌ مزدحم
    for k, w, h, mob in jobs:
        if (k, False) in results and (k, True) in results and results[(k, True)].get('rm') and lost_of(results[(k, False)], results[(k, True)]):
            first = set(lost_of(results[(k, False)], results[(k, True)]))
            try:
                n2 = run(w, h, mob, False); r2 = run(w, h, mob, True)
                results[(k, 'confirmed')] = first & set(lost_of(n2, r2))
            except Exception as e: errs.append(f"{k} confirm: {e}")
    try: send('Browser.close', timeout=5)
    except Exception: pass
    try: proc.wait(8)
    except Exception: proc.kill()
    srv.shutdown(); shutil.rmtree(ud, ignore_errors=True)
    if errs or len(results) < 4: return warn('تعذّر إكمال القياس (' + '؛ '.join(errs)[:160] + ')')
    fail = 0; out = []
    for k, _, _, _ in jobs:
        n, r = results[(k, False)], results[(k, True)]
        if not r.get('rm'): out.append(f"⚠ 6.1.41 {k}: لم تُفعَّل الحركة المخففة في Chrome (5.14.13)"); continue
        lost = [s for s in lost_of(n, r) if s in results.get((k, 'confirmed'), set())]
        if lost:
            fail = 1
            ex = ' · '.join((s[:38] + '…') if len(s) > 39 else s for s in lost[:3])
            out.append(f"✗ 6.1.41 {k}: {len(lost)} نصاً ظاهراً في الصفحة العادية يبقى مخفياً بالحركة المخففة (5.14.13): {ex}")
            if VERBOSE:
                for s in lost: out.append('    ' + s[:120])
        else:
            out.append(f"✓ 6.1.41 {k}: كل نص ظاهر ({len(n['vis'])}) يظهر بالحركة المخففة")
        mv = r.get('movers', []) + r.get('loops', [])
        if mv:
            out.append(f"⚠ 6.1.41 {k}: {len(mv)} عنصراً ما زال يتحرك بالحركة المخففة، مع التمرير أو بحلقة لا تنتهي (5.14.13): " + ' · '.join(mv[:4]))
    print('\n'.join(out))
    return fail

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'ثابت'
    try:
        sys.exit(main_browser() if mode == 'متصفح' else main_static())
    except Exception as e:
        if mode == 'متصفح':
            print(f"⚠ 6.1.41 طبقة المتصفح لم تُفحص: خطأ داخلي ({e.__class__.__name__}: {e})"[:240]); sys.exit(0)
        print(f"✗ 6.1.29 تعذّر فحص الحركة: خطأ داخلي في الفاحص ({e.__class__.__name__}: {e})"[:240]); sys.exit(1)
