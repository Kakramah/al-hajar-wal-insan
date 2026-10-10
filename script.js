/* الحجر والإنسان: محرك المشهد.
   كل حركة هنا مربوطة بتقدّم القراءة لا بالوقت: الطريق يُرسم مع قرار العودة، والحجارة تقوم من الركام مع العمل،
   ثم تتشقق الفواصل بين الحجارة لا الحجارة نفسها مع السلوكيات، وينقطع خيط البنّاء مع الوعد،
   ثم يلمع الملاط عند الأمناء وينتشر، ويوضع الحجر الأخير. */
(() => {
  'use strict';
  document.documentElement.classList.add('js');

  const NS = 'http://www.w3.org/2000/svg';
  const mqReduce = matchMedia('(prefers-reduced-motion: reduce)');
  const mqNarrow = matchMedia('(max-width: 767px)');
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const easeOut = t => 1 - Math.pow(1 - t, 3);
  const easeInOut = t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const f1 = n => Math.round(n * 10) / 10;
  const f3 = n => Math.round(n * 1000) / 1000;

  // عشوائية ثابتة البذرة: الركام نفسه في كل زيارة
  function seeded(seed) {
    return () => {
      seed = (seed + 1831565813) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const R = seeded(2026);

  /* ── هندسة الجدار: ستة مداميك برباط متناوب ── */
  const W = { x0: 330, x1: 790, base: 820, N: 6, P: 46, g: 6, L: 115 };
  const yTop = c => W.base - (c + 1) * W.P + W.g;
  const bedY = c => W.base - (c + 1) * W.P + W.g / 2;     // الفاصل فوق المدماك c
  const bounds = c => {
    const xs = [W.x0];
    for (let x = W.x0 + (c % 2 ? W.L / 2 : W.L); x < W.x1 - 1; x += W.L) xs.push(x);
    xs.push(W.x1);
    return xs;
  };
  const inner = c => bounds(c).slice(1, -1);

  const blocks = [];
  for (let c = 0; c < W.N; c++) {
    const b = bounds(c), n = b.length - 1;
    for (let i = 0; i < n; i++) {
      const x = b[i] + (i > 0 ? W.g / 2 : 0);
      const w = b[i + 1] - (i < n - 1 ? W.g / 2 : 0) - x;
      const h = W.P - W.g;
      const rx = 560 + (R() + R() + R() - 1.5) * 200 - w / 2;
      const mound = 70 * Math.exp(-Math.pow((rx + w / 2 - 560) / 160, 2));
      blocks.push({
        c, x, y: yTop(c), w, h, cx: x + w / 2,
        rx, ry: W.base - h - R() * mound, rot: (R() - .5) * 58,
        tone: 1 + Math.floor(R() * 3), last: false, s: 0
      });
    }
  }
  // الحجر الأخير: في وسط المدماك الأعلى، يبقى في الركام حتى آخر القصة
  const lastStone = blocks.filter(b => b.c === W.N - 1)
    .reduce((a, b) => (Math.abs(b.cx - 560) < Math.abs(a.cx - 560) ? b : a));
  lastStone.last = true;
  blocks.forEach(b => { b.s = (b.c / W.N) * .74 + (Math.abs(b.cx - 560) / 230) * .05; });

  /* ── الشقوق: تمشي في الفواصل درجاً، والحجارة سليمة ── */
  const CRACKS = [
    { c: 5, x: 387.5, dir: 1, n: 4 },
    { c: 4, x: 675, dir: 1, n: 3 },
    { c: 2, x: 445, dir: -1, n: 3 },
    { c: 1, x: 617.5, dir: 1, n: 2 }
  ];
  CRACKS.forEach(cr => {
    let x = cr.x, c = cr.c;
    const pts = [[x, c === W.N - 1 ? yTop(c) : bedY(c)]];
    cr.legs = []; cr.beds = [];
    while (c >= 0 && cr.legs.length < cr.n) {
      const yb = c > 0 ? bedY(c - 1) : W.base;
      pts.push([x, yb]); cr.legs.push({ c, x });
      if (c === 0 || cr.legs.length === cr.n) break;
      const cand = inner(c - 1).filter(v => (cr.dir > 0 ? v > x + 1 : v < x - 1));
      const nx = cand.length ? (cr.dir > 0 ? Math.min(...cand) : Math.max(...cand)) : (cr.dir > 0 ? W.x1 : W.x0);
      pts.push([nx, yb]); cr.beds.push({ k: c - 1, xa: Math.min(x, nx), xb: Math.max(x, nx) });
      if (!cand.length) break;
      x = nx; c--;
    }
    // تعرّج خفيف داخل عرض الفاصل
    let d = `M${f1(pts[0][0])} ${f1(pts[0][1])}`;
    for (let k = 1; k < pts.length; k++) {
      const [ax, ay] = pts[k - 1], [bx, by] = pts[k];
      const len = Math.hypot(bx - ax, by - ay), m = Math.max(1, Math.round(len / 7));
      const px = -(by - ay) / len, py = (bx - ax) / len;
      for (let j = 1; j <= m; j++) {
        const t = j / m, off = j === m ? 0 : (R() - .5) * 2.8;
        d += `L${f1(ax + (bx - ax) * t + px * off)} ${f1(ay + (by - ay) * t + py * off)}`;
      }
    }
    cr.d = d;
    // الحجارة التي تنزاح قليلاً على جهة الشق
    cr.moved = blocks.map(b => cr.legs.some(l => l.c === b.c && (b.cx - l.x) * cr.dir > 0));
  });

  /* ── فواصل الملاط: قطع يلمع بعضها عند الأمناء ثم يمتد ── */
  const segs = [];
  for (let c = 0; c < W.N; c++) for (const x of inner(c)) {
    segs.push({ t: 'h', c, x1: x, y1: c < W.N - 1 ? bedY(c) : yTop(c), x2: x, y2: c > 0 ? bedY(c - 1) : W.base });
  }
  for (let k = 0; k < W.N - 1; k++) {
    const xs = [...new Set([W.x0, ...inner(k), ...inner(k + 1), W.x1])].sort((a, b) => a - b);
    for (let j = 0; j < xs.length - 1; j++) segs.push({ t: 'b', c: k, x1: xs[j], y1: bedY(k), x2: xs[j + 1], y2: bedY(k) });
  }
  const lb = lastStone.x - W.g / 2, rb = lastStone.x + lastStone.w + W.g / 2;
  segs.forEach(s => {
    s.crack = CRACKS.some(cr =>
      (s.t === 'h' && cr.legs.some(l => l.c === s.c && Math.abs(l.x - s.x1) < .5)) ||
      (s.t === 'b' && cr.beds.some(bd => bd.k === s.c && s.x1 >= bd.xa - .5 && s.x2 <= bd.xb + .5)));
    s.seal = (s.t === 'h' && s.c === W.N - 1 && (Math.abs(s.x1 - lb) < .5 || Math.abs(s.x1 - rb) < .5)) ||
             (s.t === 'b' && s.c === W.N - 2 && s.x1 >= lb - .5 && s.x2 <= rb + .5);
    s.d = Infinity;
  });
  const findSeg = (t, c, x) => segs.find(s => s.t === t && s.c === c && (t === 'h' ? Math.abs(s.x1 - x) < .5 : s.x1 <= x && s.x2 >= x));
  const seeds = [findSeg('h', 0, 560), findSeg('h', 1, 732.5), findSeg('b', 3, 640), findSeg('h', 4, 560)].filter(Boolean);
  const key = (x, y) => `${f1(x)},${f1(y)}`;
  const at = new Map();
  segs.forEach((s, i) => [key(s.x1, s.y1), key(s.x2, s.y2)].forEach(k => { if (!at.has(k)) at.set(k, []); at.get(k).push(i); }));
  const queue = [];
  seeds.forEach(s => { s.d = 0; queue.push(segs.indexOf(s)); });
  while (queue.length) {
    const i = queue.shift(), s = segs[i];
    [key(s.x1, s.y1), key(s.x2, s.y2)].forEach(k => at.get(k).forEach(j => {
      const o = segs[j];
      if (o.crack || o.seal || o.d <= s.d + 1) return;
      o.d = s.d + 1; queue.push(j);
    }));
  }
  const maxD = Math.max(...segs.filter(s => isFinite(s.d)).map(s => s.d));

  /* ── تعبئة المشهد الأصلي، ثم تُنسخ منه نسخ الفصول ── */
  const stageSvg = document.querySelector('.stage .scene');
  const el = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const gWall = stageSvg.querySelector('.wall');
  blocks.forEach(b => el('rect', { class: `blk t${b.tone}`, width: f1(b.w), height: f1(b.h), rx: 1.5 }, gWall));
  const gCr = stageSvg.querySelector('.cracks');
  CRACKS.forEach(cr => el('path', { class: 'crack', d: cr.d, pathLength: 1 }, gCr));
  const gGold = stageSvg.querySelector('.gold');
  segs.forEach(s => {
    if (s.crack) return;
    const g = el('g', { class: 'seg' }, gGold);
    const a = { x1: f1(s.x1), y1: f1(s.y1), x2: f1(s.x2), y2: f1(s.y2) };
    el('line', Object.assign({ class: 'glow' }, a), g);
    el('line', Object.assign({ class: 'core' }, a), g);
  });
  const goldSegs = segs.filter(s => !s.crack);
  const gCover = el('g', { class: 'cover' });
  gGold.after(gCover);
  el('rect', { class: 'plaster', x: 334, y: 592, width: 106, height: 92, rx: 2 }, gCover);
  let cd = 'M352 590';
  [[362, 606], [358, 620], [374, 634], [370, 646], [392, 660], [400, 676], [418, 688]].forEach(([x, y]) => {
    cd += `L${f1(x + (R() - .5) * 3)} ${f1(y)}`;
  });
  el('path', { class: 'crack crack-cover', d: cd, pathLength: 1 }, gCover);
  stageSvg.querySelectorAll('.string, .string-gold').forEach(p => p.setAttribute('pathLength', 1));
  stageSvg.querySelector('.weight').setAttribute('transform', 'translate(0 -780)');

  function collect(svg) {
    const q = s => svg.querySelector(s), qa = s => [...svg.querySelectorAll(s)];
    return {
      svg, cache: new Map(),
      dawn: q('.tone-dawn'), ash: q('.tone-ash'), goldTone: q('.tone-gold'),
      skyline: q('.skyline'), fixHouse: q('.fix-house'), fixFactory: q('.fix-factory'),
      roadSurface: q('.road-surface'), roadEdges: qa('.road-edge'), lanes: qa('.lanes path'),
      potholes: q('.potholes'), roadNew: q('.road-new'),
      scaffoldG: q('.scaffold'), scaffold: qa('.scaffold path'),
      blks: qa('.blk'), cracks: qa('.cracks .crack'), segs: qa('.seg'),
      plaster: q('.plaster'), coverCrack: q('.crack-cover'),
      mason: q('.mason'), sl: q('.string-l'), sr: q('.string-r'), gl: q('.string-gold.string-gl'), gr: q('.string-gold.string-gr'),
      human: q('.human'), hDash: q('.human-dash'), hSolid: q('.human-solid'),
      weight: q('.weight')
    };
  }
  // يكتب القيمة فقط إن تغيّرت
  const put = (I, node, prop, val) => {
    const k = I.cache.get(node) || {};
    if (k[prop] === val) return;
    k[prop] = val; I.cache.set(node, k);
    if (prop === 'transform' || prop === 'd') node.setAttribute(prop, val);
    else node.style[prop] = val;
  };

  function render(I, B) {
    const ash = easeInOut(B.ash), spread = easeInOut(B.spread), honest = easeOut(B.honest);
    const gold = Math.max(honest * .4, spread);
    const dawn = Math.max(.6, B.dawn);
    put(I, I.dawn, 'opacity', f3(dawn * (1 - ash) * (1 - .5 * gold)));
    put(I, I.ash, 'opacity', f3(ash * (1 - .8 * gold) * .5));
    put(I, I.goldTone, 'opacity', f3(gold * .9));
    put(I, I.skyline, 'opacity', f3(.3 + .06 * B.dawn + .32 * easeOut(B.ruin)));

    [[I.fixHouse, B.house], [I.fixFactory, B.factory]].forEach(([n, v]) => {
      const e = easeOut(v);
      put(I, n, 'opacity', f3(e));
      put(I, n, 'transform', `translate(0 ${f1(820 * (1 - Math.max(e, .02)))}) scale(1 ${f3(Math.max(e, .02))})`);
    });

    const road = Math.max(.24, easeInOut(B.road));
    I.roadEdges.forEach(p => put(I, p, 'strokeDashoffset', f3(1 - road)));
    put(I, I.roadSurface, 'opacity', f3(.45 * road));
    I.lanes.forEach((p, k) => put(I, p, 'opacity', f3(clamp(road * 4 - k) * .9)));
    put(I, I.potholes, 'opacity', f3(easeOut(B.ruin) * (1 - easeOut(B.roadfix))));
    put(I, I.roadNew, 'opacity', f3(.42 * easeOut(B.roadfix)));

    const sc = clamp(B.build / .35);
    I.scaffold.forEach((p, k) => put(I, p, 'strokeDashoffset', f3(1 - clamp(sc * 1.6 - k * .15))));
    put(I, I.scaffoldG, 'opacity', f3(1 - .6 * easeOut(B.stone)));

    // الحجارة: من الركام إلى المداميك، ثم انزياح خفيف حيث تشقّق الفاصل
    const loosen = CRACKS.map((cr, k) => easeOut(B['crack' + (k + 1)]) * (1 - .5 * spread));
    const rubble = easeOut(B.ruin);
    blocks.forEach((b, k) => {
      const e = b.last ? easeInOut(B.stone) : easeOut(clamp((B.build - b.s) / .22));
      const lift = b.last ? 130 : 44;
      let tx = lerp(b.rx, b.x, e), ty = lerp(b.ry, b.y, e) - Math.sin(Math.PI * e) * lift;
      const rot = lerp(b.rot, 0, e);
      CRACKS.forEach((cr, j) => { if (cr.moved[k]) { tx += cr.dir * 2.6 * loosen[j]; ty += 2.4 * loosen[j]; } });
      const n = I.blks[k];
      put(I, n, 'transform', `translate(${f1(tx)} ${f1(ty)}) rotate(${f1(rot)} ${f1(b.w / 2)} ${f1(b.h / 2)})`);
      put(I, n, 'opacity', f3(rubble));
    });
    I.cracks.forEach((p, k) => {
      put(I, p, 'strokeDashoffset', f3(1 - easeInOut(B['crack' + (k + 1)])));
      put(I, p, 'opacity', f3(1 - .6 * spread));
    });

    // الغطاء: سطح نظيف يغطي، ثم يتشقق هو نفسه
    put(I, I.plaster, 'opacity', f3(easeOut(clamp(B.cover * 2))));
    put(I, I.coverCrack, 'strokeDashoffset', f3(1 - easeInOut(clamp(B.cover * 2 - 1))));
    put(I, I.coverCrack, 'opacity', f3(1 - .6 * spread));

    // الأمانة: فواصل تلمع عند الأمناء، ثم تمتد، ثم يُختم الحجر الأخير بملاطه
    const reach = spread * (maxD + 1) * .84;
    goldSegs.forEach((s, k) => {
      let o;
      if (s.seal) o = easeOut(clamp((B.stone - .55) / .45));
      else if (s.d === 0) o = honest;
      else if (isFinite(s.d)) o = clamp(reach - s.d + 1);
      else o = 0;
      put(I, I.segs[k], 'opacity', f3(o));
    });

    // خيط البنّاء: يُشدّ مع العمل، ينقطع مع الوعد، ويُشدّ ذهبياً مع الأمناء
    put(I, I.mason, 'opacity', f3(easeOut(clamp(B.line * 2))));
    const draw = clamp(B.line);
    const s = easeOut(B.snap) * (1 - easeInOut(B.restring));
    const y = 548, mx = 560;
    const dl = `M318 ${y}Q${f1(lerp(439, 323, s))} ${f1(lerp(y, 566, s))} ${f1(lerp(mx, 327, s))} ${f1(lerp(y, 706, s))}`;
    const dr = `M802 ${y}Q${f1(lerp(681, 797, s))} ${f1(lerp(y, 566, s))} ${f1(lerp(mx, 793, s))} ${f1(lerp(y, 706, s))}`;
    const r = easeInOut(B.restring);
    [[I.sl, dl, 1 - r], [I.sr, dr, 1 - r], [I.gl, dl, r], [I.gr, dr, r]].forEach(([n, d, o], k) => {
      put(I, n, 'd', d);
      put(I, n, 'opacity', f3(o));
      put(I, n, 'strokeDashoffset', f3(1 - clamp(draw * 2 - (k % 2))));
    });

    // الإنسان: سؤال بخط متقطع، ثم يكتمل خطه مع المسؤولية
    const hm = easeOut(B.human);
    put(I, I.human, 'opacity', f3(hm));
    put(I, I.human, 'transform', `translate(0 ${f1(10 * (1 - hm))})`);
    const hs = easeInOut(B.humansolid);
    put(I, I.hDash, 'opacity', f3(1 - hs));
    put(I, I.hSolid, 'opacity', f3(hs));

    // ثقل الاستبداد: ينزل على المشهد ثم يرتفع، والشقوق باقية تحته
    const wy = -780 * (1 - easeInOut(B.weightin) * (1 - easeInOut(B.weightout)));
    put(I, I.weight, 'transform', `translate(0 ${f1(wy)})`);
  }

  /* ── الإيقاع: كل نبضة مربوطة بفصل ومدى من تقدّمه، وتتقدّم عليها الفقرة الموسومة بها إن وُجدت ── */
  const BEATS = {
    dawn: [1, 0, .5], road: [1, .1, .75],
    ruin: [2, 0, .35], build: [2, .2, .85], line: [2, .62, .92],
    ash: [3, 0, .15], crack1: [3, .1, .3], crack2: [3, .25, .42], crack3: [3, .38, .55], snap: [3, .5, .65], crack4: [3, .6, .75], cover: [3, .72, .95],
    house: [4, .1, .3], roadfix: [4, .3, .5], factory: [4, .5, .7], human: [4, .7, .9],
    weightin: [5, 0, .4], weightout: [5, .5, .9],
    restring: [6, .05, .35], honest: [6, .5, .9],
    spread: [7, .05, .7], humansolid: [7, .55, .85],
    stone: [8, .2, .7]
  };
  const sections = [...document.querySelectorAll('.ch')];
  const cues = {};
  // الفقرة الموسومة تقود نبضتها حين يحلّ نص الكاتب محلّ السطر المؤقت
  document.querySelectorAll('[data-cue]:not(.pending)').forEach(n => { cues[n.dataset.cue] = n; });

  const beatsForChapter = (ch, local) => {
    const B = {};
    for (const k in BEATS) {
      const [c, a, b] = BEATS[k];
      B[k] = c < ch ? 1 : c > ch ? 0 : clamp((local - a) / (b - a));
    }
    return B;
  };

  const stage = collect(stageSvg);
  const figs = [];
  function ensureFigs() {
    if (figs.length) return;
    sections.forEach((sec, i) => {
      const box = document.createElement('div');
      box.className = 'fig';
      box.setAttribute('aria-hidden', 'true');
      const svg = stageSvg.cloneNode(true);
      svg.setAttribute('viewBox', i === 0 ? '250 225 620 775' : '110 300 900 700');
      box.appendChild(svg);
      sec.insertBefore(box, sec.firstChild);
      figs.push({ i, box, I: collect(svg), visible: false });
    });
    const io = new IntersectionObserver(es => es.forEach(e => {
      const F = figs.find(f => f.box === e.target);
      if (F) F.visible = e.isIntersecting;
    }), { rootMargin: '10% 0px' });
    figs.forEach(F => io.observe(F.box));
  }

  const bar = document.querySelector('.progress');
  let ticking = false;
  function update() {
    ticking = false;
    const vh = innerHeight;
    const max = document.documentElement.scrollHeight - vh;
    if (max > 0) bar.style.transform = `scaleX(${f3(clamp(scrollY / max))})`;
    const reduce = mqReduce.matches;
    if (!document.body.classList.contains('figs')) {
      const probe = vh * .55;
      const pc = sections.map(sec => { const r = sec.getBoundingClientRect(); return clamp((probe - r.top) / r.height); });
      const B = {};
      for (const k in BEATS) {
        const [c, a, b] = BEATS[k];
        const cue = cues[k];
        if (cue) {
          const r = cue.getBoundingClientRect();
          // تبدأ النبضة حين يبلغ أول الفقرة ثلثي الشاشة السفليين، وتكتمل بعد قراءتها
          // data-at يؤخر بداية النبضة إلى خط أعلى في الشاشة، فلا تتزامن مع ما قبلها
          const at = parseFloat(cue.dataset.at) || .78;
          B[k] = clamp((vh * at - r.top) / Math.max(r.height + vh * .12, vh * .22));
        } else B[k] = clamp((pc[c] - a) / (b - a));
      }
      render(stage, B);
    } else {
      figs.forEach(F => {
        if (!reduce && !F.visible && F.drawn) return;
        let local = 1;
        if (!reduce) { const r = F.box.getBoundingClientRect(); local = clamp((vh * .92 - r.top) / (vh * .8)); }
        render(F.I, beatsForChapter(F.i, local));
        F.drawn = true;
      });
    }
  }
  const schedule = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };

  function setMode() {
    const useFigs = mqNarrow.matches || mqReduce.matches;
    document.body.classList.toggle('figs', useFigs);
    if (useFigs) { ensureFigs(); figs.forEach(F => { F.drawn = false; }); }
    schedule();
  }
  [mqNarrow, mqReduce].forEach(m => m.addEventListener('change', setMode));
  addEventListener('scroll', schedule, { passive: true });
  addEventListener('resize', schedule);
  setMode();

  /* ── ظهور النص مع القراءة ── */
  const rv = [...document.querySelectorAll('.rv')];
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    }), { threshold: .15 });
    rv.forEach(n => io.observe(n));
  } else rv.forEach(n => n.classList.add('in'));

  /* ── الإحالة تفتح المصادر ── */
  document.querySelectorAll('.ref').forEach(a => a.addEventListener('click', () => {
    const d = document.getElementById('sources');
    if (d) d.open = true;
  }));

  /* ── المشاركة ── */
  const shareBtn = document.querySelector('.share');
  const alt = document.querySelector('.share-alt');
  const msg = document.querySelector('.share-msg');
  const url = location.href.split('#')[0];
  const line = 'نحنا شو بدنا نعيد إعمار بالضبط؟ رسالة من مغترب رجع على بلده';
  const enc = encodeURIComponent;
  document.querySelector('.sh-wa').href = `https://wa.me/?text=${enc(line + '\n' + url)}`;
  document.querySelector('.sh-tg').href = `https://t.me/share/url?url=${enc(url)}&text=${enc(line)}`;
  document.querySelector('.sh-x').href = `https://x.com/intent/post?text=${enc(line)}&url=${enc(url)}`;
  document.querySelector('.sh-fb').href = `https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`;
  shareBtn.addEventListener('click', async () => {
    if (navigator.share) {
      try { await navigator.share({ title: document.title, text: line, url }); return; }
      catch (err) { if (err && err.name === 'AbortError') return; }
    }
    let copied = false;
    try { await navigator.clipboard.writeText(url); copied = true; } catch (err) { copied = false; }
    msg.textContent = copied ? 'نُسخ الرابط. ويمكنك المشاركة عبر:' : 'شارك الرابط عبر:';
    alt.hidden = false;
  });
})();
