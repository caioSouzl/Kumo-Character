// Kumo — official vector construction.
// Local units: 1 H = 100 units = head height (crest tip to chin).
// Ground line is y = 0, the character faces the viewer, +x = viewer's right.
// Official height: 2.4 H (head 1.0 · torso 0.8 · legs 0.6).

export const C = {
  outline: '#5B3A2E',
  dark: '#1B5E3B',
  mid: '#4CAF6B',
  spot: '#C9D45B',
  belly: '#EAD9B7',
  eye: '#F4B642',
  // working shades derived from the official greens (facet lighting only)
  d1: '#22704A',
  d2: '#2C7A4B',
  d3: '#3A9058',
  m1: '#45A863',
  m2: '#4FB46F',
  m3: '#5DBB79',
  m4: '#68C484',
  edge: '#1F6A40',
  bellyLine: '#D6C29B',
  mouthIn: '#6B3B2E',
  tongue: '#D9826F',
  pupil: '#1A120E',
};

export const SW = 2.2; // outline weight (local units)

const f = (n) => Math.round(n * 100) / 100;
export const P = (pts) => 'M' + pts.map((p) => `${f(p[0])} ${f(p[1])}`).join(' L') + ' Z';
const mx = (pts) => pts.map(([x, y]) => [-x, y]);

let uid = 0;
const id = (p) => `${p}${++uid}`;

/**
 * Outlined part: union outline of all shapes, then fills, then details.
 * shapes: [{d, fill}] ; details: svg string (clipped to the part); over: unclipped svg.
 */
function part(shapes, details = '', over = '', sw = SW) {
  const cid = id('clip');
  const paths = shapes.map((s) => `<path d="${s.d}"/>`).join('');
  return (
    `<clipPath id="${cid}">${paths}</clipPath>` +
    `<g fill="${C.outline}" stroke="${C.outline}" stroke-width="${sw * 2}" stroke-linejoin="round" stroke-linecap="round">${paths}</g>` +
    `<g>${shapes.map((s) => `<path d="${s.d}" fill="${s.fill}"/>`).join('')}</g>` +
    (details ? `<g clip-path="url(#${cid})">${details}</g>` : '') +
    over
  );
}

const poly = (pts, fill, extra = '') => `<path d="${P(pts)}" fill="${fill}" ${extra}/>`;
const patch = (pts, o = 0.9) => poly(pts, C.spot, `opacity="${o}"`);
const line = (d, w = 0.7, col = C.edge, o = 0.55) =>
  `<path d="${d}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" opacity="${o}"/>`;
const ink = (d, w = 1.6) =>
  `<path d="${d}" fill="none" stroke="${C.outline}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/>`;

/* ------------------------------------------------------------------ tail */
// Same spiral glyph in every view: 1.75 turns, counter-clockwise inward,
// outer radius 0.32 H, ending in a rounded tip.
export const SPIRAL = { r0: 32, r1: 5, turns: 1.75, w0: 11, w1: 3.2 };

function bez(p0, p1, p2, p3, t) {
  const u = 1 - t;
  return [
    u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
    u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
  ];
}

export function tailPath(base, c1, c2, center, startDeg, leadW = 15) {
  const { r0, r1, turns, w0, w1 } = SPIRAL;
  const pts = [];
  const ws = [];
  const a0 = (startDeg * Math.PI) / 180;
  const start = [center[0] + r0 * Math.cos(a0), center[1] + r0 * Math.sin(a0)];
  const N1 = 24;
  for (let i = 0; i < N1; i++) {
    const t = i / N1;
    pts.push(bez(base, c1, c2, start, t));
    ws.push(leadW + (w0 - leadW) * t);
  }
  const N2 = 150;
  for (let i = 0; i <= N2; i++) {
    const t = i / N2;
    const a = a0 - t * turns * 2 * Math.PI;
    const r = r0 + (r1 - r0) * Math.pow(t, 0.85);
    pts.push([center[0] + r * Math.cos(a), center[1] + r * Math.sin(a)]);
    ws.push(w0 + (w1 - w0) * t);
  }
  const L = [];
  const R = [];
  const nrm = [];
  for (let i = 0; i < pts.length; i++) {
    const a = pts[Math.max(0, i - 1)];
    const b = pts[Math.min(pts.length - 1, i + 1)];
    let dx = b[0] - a[0];
    let dy = b[1] - a[1];
    const l = Math.hypot(dx, dy) || 1;
    dx /= l;
    dy /= l;
    const n = [-dy, dx];
    nrm.push(n);
    L.push([pts[i][0] + (n[0] * ws[i]) / 2, pts[i][1] + (n[1] * ws[i]) / 2]);
    R.push([pts[i][0] - (n[0] * ws[i]) / 2, pts[i][1] - (n[1] * ws[i]) / 2]);
  }
  const tip = pts[pts.length - 1];
  const d = P([...L, ...R.slice().reverse()]);
  const tr = w1 / 2 + 0.6;
  const tipD = `M${f(tip[0] + tr)} ${f(tip[1])} A${f(tr)} ${f(tr)} 0 1 0 ${f(tip[0] - tr)} ${f(tip[1])} A${f(tr)} ${f(tr)} 0 1 0 ${f(tip[0] + tr)} ${f(tip[1])} Z`;
  // scale bands (spot colour) across the outer half of the tail
  let bands = '';
  for (let i = 4; i < pts.length - 8; i += 11) {
    const j = Math.min(i + 5, pts.length - 1);
    const mid = (k) => [(pts[k][0] + R[k][0]) / 2, (pts[k][1] + R[k][1]) / 2];
    bands += patch([L[i], L[j], mid(j), mid(i)], 0.85);
  }
  // soft shade on the inner edge
  const inner = pts.map((p, i) => [p[0] - nrm[i][0] * ws[i] * 0.15, p[1] - nrm[i][1] * ws[i] * 0.15]);
  const shade = `<path d="${P([...inner, ...R.slice().reverse()])}" fill="${C.d3}" opacity="0.35"/>`;
  return part([{ d, fill: C.mid }, { d: tipD, fill: C.mid }], shade + bands);
}

/* ------------------------------------------------------------------ hands & feet */
// Hand: wrist at origin, pointing down. side = +1 for a hand on the viewer's right
// (thumb points to -x, toward the body). Three fingers + one opposable thumb.
export function hand(x, y, side = 1, rot = 0, s = 1.15) {
  const fing = (ang, len, w) => {
    const a = (ang * Math.PI) / 180;
    const dx = Math.sin(a);
    const dy = Math.cos(a);
    const ex = dx * len;
    const ey = 3 + dy * len;
    const nx = dy * (w / 2);
    const ny = -dx * (w / 2);
    const pts = [[nx, 3 + ny], [ex + nx, ey + ny], [ex - nx, ey - ny], [-nx, 3 - ny]];
    const r = w * 0.66;
    const pad = `M${f(ex + r)} ${f(ey)} A${f(r)} ${f(r)} 0 1 0 ${f(ex - r)} ${f(ey)} A${f(r)} ${f(r)} 0 1 0 ${f(ex + r)} ${f(ey)} Z`;
    return part([{ d: P(pts), fill: C.mid }, { d: pad, fill: C.mid }], '', '', 1.6);
  };
  const palm = 'M-6.5 -4 L6.5 -4 L7.5 5 L3 7.5 L-3 7.5 L-7.5 5 Z';
  const g =
    fing(-side * 68, 9.5, 4) + // opposable thumb, toward the body
    fing(side * 30, 12.5, 4.2) +
    fing(-side * 2, 13.5, 4.2) +
    fing(-side * 32, 12, 4.2) +
    `<path d="${palm}" fill="${C.mid}"/>` +
    `<path d="M-7.5 5 L-6.5 -4 M6.5 -4 L7.5 5" fill="none" stroke="${C.outline}" stroke-width="2.6" stroke-linecap="round"/>` +
    patch([[-3, -3], [2.5, -3], [0, 2]], 0.8);
  return `<g transform="translate(${x} ${y}) rotate(${rot}) scale(${s})">${g}</g>`;
}

// Foot, front view: ankle centred at x, ground y = 0. Three forward toes.
export function footFront(x, tilt = 0) {
  const shapes = [
    { d: 'M-13 -12 L13 -12 L16 -5 L-16 -5 Z', fill: C.mid },
    ...[-10.5, 0, 10.5].map((cx) => ({
      d: `M${cx + 5.6} -4.6 A5.6 5 0 1 1 ${cx - 5.6} -4.6 A5.6 5 0 1 1 ${cx + 5.6} -4.6 Z`,
      fill: C.mid,
    })),
  ];
  const det = ink('M-5.2 -1.5 L-5.2 -6', 1.1) + ink('M5.2 -1.5 L5.2 -6', 1.1) + patch([[-8, -11], [-1, -11], [-4, -6]], 0.8);
  return `<g transform="translate(${x} 0) skewX(${tilt})">${part(shapes, det)}</g>`;
}

// Foot, back view (heel toward the viewer, toe tips peeking out at the sides).
export function footBack(x) {
  const shapes = [
    { d: 'M-13 -12 L13 -12 L16 -3 Q16 0 13 0 L-13 0 Q-16 0 -16 -3 Z', fill: C.mid },
    { d: 'M-19 -3 A3 3 0 1 1 -13 -3 A3 3 0 1 1 -19 -3 Z', fill: C.mid },
    { d: 'M13 -3 A3 3 0 1 1 19 -3 A3 3 0 1 1 13 -3 Z', fill: C.mid },
  ];
  return `<g transform="translate(${x} 0)">${part(shapes, `<path d="M-13 -5 L13 -5 L13 0 L-13 0 Z" fill="${C.d3}" opacity="0.4"/>`)}</g>`;
}

// Foot, side view, toes pointing to +x (or -x when dir = -1).
export function footSide(x, dir = 1, fill = C.mid) {
  const shapes = [
    { d: 'M-14 -12 L4 -12 L10 -7 L-14 -4 Q-15 0 -12 0 L4 0 Z', fill },
    ...[
      [8, -4.5, 5.2],
      [14, -3.6, 4.6],
      [19, -3, 4],
    ].map(([cx, cy, r]) => ({ d: `M${cx + r} ${cy} A${r} ${r * 0.85} 0 1 1 ${cx - r} ${cy} A${r} ${r * 0.85} 0 1 1 ${cx + r} ${cy} Z`, fill })),
    { d: 'M-15 -11 L8 -11 L8 0 L-12 0 Q-15 0 -15 -3 Z', fill },
  ];
  const det = ink('M11 -1 L10 -6', 1) + ink('M16.5 -0.8 L15.5 -5', 1) + patch([[-8, -11], [0, -11], [-4, -6]], 0.8);
  return `<g transform="translate(${x} 0) scale(${dir} 1)">${part(shapes, det)}</g>`;
}

/* ------------------------------------------------------------------ eyes */
// expression parameters for one eye
export function eye(cx, cy, o = {}) {
  const { s = 1, ps = 1, po = [0, 0], lt = 0.1, lb = 0, tilt = 0, side = 1, sparkle = false, rx = 1 } = o;
  const R = 16.5 * s;
  const cid = id('eye');
  const lidTop = cy - R + 2 * R * lt;
  const lidBot = cy + R - 2 * R * lb;
  const tl = tilt * side; // positive tilt lowers the inner corner
  const body =
    `<circle cx="${cx}" cy="${cy}" r="${R}" fill="url(#iris)"/>` +
    `<circle cx="${cx}" cy="${cy}" r="${R * 0.8}" fill="none" stroke="#D9962E" stroke-width="0.8" opacity="0.8"/>` +
    `<circle cx="${cx + po[0]}" cy="${cy + po[1]}" r="${7 * ps * s}" fill="${C.pupil}"/>` +
    `<circle cx="${cx + po[0] - 4.6 * s}" cy="${cy + po[1] - 5 * s}" r="${3.2 * s}" fill="#fff"/>` +
    `<circle cx="${cx + po[0] + 4.4 * s}" cy="${cy + po[1] + 4.2 * s}" r="${1.5 * s}" fill="#fff"/>` +
    (sparkle ? `<circle cx="${cx + po[0] + 1.5 * s}" cy="${cy + po[1] - 6.5 * s}" r="${1.4 * s}" fill="#fff"/>` : '') +
    (lt > 0
      ? `<path d="M${cx - R - 2} ${cy - R - 2} L${cx + R + 2} ${cy - R - 2} L${cx + R + 2} ${lidTop + tl} Q${cx} ${lidTop + 2.5 * s} ${cx - R - 2} ${lidTop - tl} Z" fill="${C.d3}"/>` +
        `<path d="M${cx - R - 2} ${lidTop - tl} Q${cx} ${lidTop + 2.5 * s} ${cx + R + 2} ${lidTop + tl}" fill="none" stroke="${C.outline}" stroke-width="1.6"/>`
      : '') +
    (lb > 0
      ? `<path d="M${cx - R - 2} ${cy + R + 2} L${cx + R + 2} ${cy + R + 2} L${cx + R + 2} ${lidBot} Q${cx} ${lidBot - 5 * s} ${cx - R - 2} ${lidBot} Z" fill="${C.d3}"/>` +
        `<path d="M${cx - R - 2} ${lidBot} Q${cx} ${lidBot - 5 * s} ${cx + R + 2} ${lidBot}" fill="none" stroke="${C.outline}" stroke-width="1.6"/>`
      : '');
  return (
    `<ellipse cx="${cx}" cy="${cy}" rx="${(R + 4.5) * rx}" ry="${R + 4.5}" fill="${C.d2}" stroke="${C.outline}" stroke-width="1.8"/>` +
    `<ellipse cx="${cx}" cy="${cy}" rx="${(R + 2.2) * rx}" ry="${R + 2.2}" fill="none" stroke="${C.edge}" stroke-width="0.7" opacity="0.6"/>` +
    `<clipPath id="${cid}"><ellipse cx="${cx}" cy="${cy}" rx="${R * rx}" ry="${R}"/></clipPath>` +
    `<g clip-path="url(#${cid})"><g transform="translate(${cx} ${cy}) scale(${rx} 1) translate(${-cx} ${-cy})">${body}</g></g>` +
    `<ellipse cx="${cx}" cy="${cy}" rx="${R * rx}" ry="${R}" fill="none" stroke="${C.outline}" stroke-width="1.5"/>`
  );
}

export const defs = `
<radialGradient id="iris" cx="0.45" cy="0.42" r="0.62">
  <stop offset="0" stop-color="#FFE29A"/>
  <stop offset="0.55" stop-color="${C.eye}"/>
  <stop offset="1" stop-color="#D98E25"/>
</radialGradient>`;

/* ------------------------------------------------------------------ head: front */
// Faceted polyhedral head, 14 faces (7 per side). Points are given for the viewer's
// right half and mirrored.
const HP = {
  T: [0, -240], Cc: [0, -212], a: [22, -224], b: [45, -208], c: [57, -186], d: [56, -162],
  e: [42, -145], G: [0, -140], fp: [17, -200], g: [38, -204], h: [14, -171], S: [0, -174],
  m: [37, -157], U: [0, -153],
};
export const HEAD_FACES = (() => {
  const { T, Cc, a, b, c, d, e, G, fp, g, h, S, m, U } = HP;
  const R = [
    ['crest', [T, a, fp, Cc], C.dark, C.d1],
    ['top', [a, b, g, fp], C.d2, C.d3],
    ['temple', [b, c, g], C.d3, C.m1],
    ['cheek', [g, c, d, m, h, fp], C.m1, C.m2],
    ['snout', [Cc, fp, h, S], C.m2, C.m3],
    ['jowl', [d, e, m], C.d3, C.m1],
    ['jaw', [m, e, G, U, S, h], C.m3, C.m4],
  ];
  const out = [];
  for (const [n, pts, rFill, lFill] of R) {
    out.push({ n: n + '-R', pts, fill: rFill });
    out.push({ n: n + '-L', pts: mx(pts), fill: lFill });
  }
  return out;
})();
const HEAD_OUT = (() => {
  const { T, a, b, c, d, e, G } = HP;
  const r = [a, b, c, d, e];
  return [T, ...r, G, ...mx(r).reverse()];
})();
export const HEAD_OUTLINE = HEAD_OUT;

export const EXPR = {
  neutral: { lt: 0.12, mouth: 'neutral' },
  curious: { lt: 0.04, po: [3.5, -2.5], ps: 1.05, brow: { L: [-3, -9], R: [0, -1] }, mouth: 'smallSmile' },
  surprised: { lt: 0, s: 1.1, ps: 0.55, brow: { L: [-9, -8], R: [-9, -8] }, mouth: 'o' },
  happy: { lt: 0.05, lb: 0.3, po: [0, -1.5], brow: { L: [-4, -5], R: [-4, -5] }, mouth: 'grin' },
  confused: { eyes: { L: { lt: 0.04, po: [2, -2] }, R: { lt: 0.28, po: [-2, 1] } }, brow: { L: [-8, -3], R: [3, 2] }, mouth: 'wavy' },
  suspicious: { lt: 0.46, lb: 0.14, tilt: 2.5, po: [5.5, 1.5], brow: { L: [5, -1], R: [5, -1] }, mouth: 'smirk' },
  excited: { lt: 0, s: 1.08, ps: 1.22, sparkle: true, brow: { L: [-8, -10], R: [-8, -10] }, mouth: 'bigOpen' },
  thoughtful: { lt: 0.32, po: [-4.5, -5.5], brow: { L: [-6, -2], R: [1, 1] }, mouth: 'pursed' },
};

function mouth(kind) {
  switch (kind) {
    case 'smallSmile':
      return ink('M-37 -158 Q0 -147 37 -158', 1.9) + ink('M-37 -158 L-39 -161', 1.4) + ink('M37 -158 L39 -161', 1.4);
    case 'o':
      return ink('M-37 -157 Q0 -152 37 -157', 1.4) + `<ellipse cx="0" cy="-150" rx="6" ry="6.5" fill="${C.mouthIn}" stroke="${C.outline}" stroke-width="1.6"/>`;
    case 'grin': {
      const d = 'M-33 -158 Q0 -157 33 -158 Q0 -136 -33 -158 Z';
      return `<path d="${d}" fill="${C.mouthIn}"/><clipPath id="gr"><path d="${d}"/></clipPath><ellipse cx="0" cy="-145" rx="11" ry="5" fill="${C.tongue}" clip-path="url(#gr)"/><path d="${d}" fill="none" stroke="${C.outline}" stroke-width="1.9" stroke-linejoin="round"/>`;
    }
    case 'bigOpen': {
      const d = 'M-36 -160 Q0 -162 36 -160 Q0 -130 -36 -160 Z';
      return `<path d="${d}" fill="${C.mouthIn}"/><clipPath id="bo"><path d="${d}"/></clipPath><ellipse cx="0" cy="-142" rx="13" ry="6" fill="${C.tongue}" clip-path="url(#bo)"/><path d="${d}" fill="none" stroke="${C.outline}" stroke-width="1.9" stroke-linejoin="round"/>`;
    }
    case 'wavy':
      return ink('M-32 -155 C-20 -160 -10 -150 0 -155 S20 -159 32 -153', 1.9);
    case 'smirk':
      return ink('M-30 -155 Q4 -153 34 -161', 1.9) + ink('M34 -161 L36 -164', 1.4);
    case 'pursed':
      return ink('M-37 -157 Q0 -152 37 -157', 0.9) + ink('M6 -152 Q14 -156 23 -152', 1.9);
    default:
      return ink('M-37 -157 Q0 -151 37 -157', 1.9);
  }
}

export function headFront(exprName = 'neutral') {
  const x = EXPR[exprName];
  const faces = HEAD_FACES.map((fc) => poly(fc.pts, fc.fill)).join('');
  const edges = HEAD_FACES.map((fc) => line(P(fc.pts), 0.7)).join('');
  const patches =
    patch([[-30, -220], [-20, -226], [-15, -215], [-25, -211]]) +
    patch([[27, -214], [37, -210], [33, -201], [25, -205]]) +
    patch([[-54, -182], [-47, -190], [-45, -174]]) +
    patch([[49, -170], [55, -178], [54, -160]]) +
    patch([[-6, -230], [-2, -235], [-1, -224]], 0.7) +
    patch([[-10, -190], [-4, -194], [-5, -184]], 0.6) +
    patch([[44, -150], [50, -156], [48, -147]], 0.7);
  const shapes = [{ d: P(HEAD_OUT), fill: C.mid }];
  const e = (side) => {
    const o = { ...x, ...(x.eyes ? x.eyes[side === 1 ? 'R' : 'L'] : {}) };
    return eye(34 * side, -182, { ...o, side });
  };
  const brow = (side) => {
    const b = (x.brow && x.brow[side === 1 ? 'R' : 'L']) || [0, 0];
    const yi = -205 + b[0];
    const yo = -207 + b[1];
    return `<path d="M${17 * side} ${yi} Q${32 * side} ${(yi + yo) / 2 - 4} ${48 * side} ${yo}" fill="none" stroke="${C.dark}" stroke-width="4.2" stroke-linecap="round"/>` +
      `<path d="M${17 * side} ${yi} Q${32 * side} ${(yi + yo) / 2 - 4} ${48 * side} ${yo}" fill="none" stroke="${C.outline}" stroke-width="1" stroke-linecap="round" opacity="0.6" transform="translate(0 -2.6)"/>`;
  };
  const nostrils = ink('M-7 -168 L-5 -166', 1.8) + ink('M7 -168 L5 -166', 1.8);
  return part(shapes, faces + edges + patches, brow(-1) + brow(1) + e(-1) + e(1) + nostrils + mouth(x.mouth));
}

/* ------------------------------------------------------------------ head: back */
export function headBack() {
  const { T, a, b, c, d, e, G } = HP;
  const ridge = [[0, -240], [-13, -205], [0, -168], [13, -205]];
  const faces = [
    poly([T, a, b, [24, -196], [13, -205]], C.d2),
    poly(mx([T, a, b, [24, -196], [13, -205]]), C.d3),
    poly([b, c, d, [26, -170], [24, -196]], C.m1),
    poly(mx([b, c, d, [26, -170], [24, -196]]), C.m2),
    poly([d, e, G, [0, -168], [26, -170]], C.d3),
    poly(mx([d, e, G, [0, -168], [26, -170]]), C.m1),
    poly([[13, -205], [24, -196], [26, -170], [0, -168]], C.m1),
    poly(mx([[13, -205], [24, -196], [26, -170], [0, -168]]), C.m2),
    poly(ridge, C.dark),
  ].join('');
  const edges = [
    [T, a, b, [24, -196], [13, -205]], [b, c, d, [26, -170], [24, -196]], [d, e, G, [0, -168], [26, -170]],
    [[13, -205], [24, -196], [26, -170], [0, -168]],
  ].map((p) => line(P(p)) + line(P(mx(p)))).join('') + line(P(ridge), 0.9);
  const patches = patch([[-34, -212], [-24, -218], [-22, -206]]) + patch([[30, -186], [40, -192], [42, -180], [33, -178]]) +
    patch([[-44, -168], [-36, -174], [-34, -160]]) + patch([[6, -150], [16, -154], [12, -146]], 0.7);
  return part([{ d: P(HEAD_OUT), fill: C.mid }], faces + edges + patches);
}

/* ------------------------------------------------------------------ head: side (faces +x) */
const SIDE_OUT = [[-6, -240], [24, -224], [46, -204], [56, -184], [59, -168], [56, -154], [44, -142], [6, -137],
  [-26, -143], [-46, -158], [-52, -182], [-44, -206], [-26, -224]];
export function headSide() {
  const o = SIDE_OUT;
  const faces = [
    poly([o[0], o[1], [18, -206], [-8, -206], o[12]], C.d1), // crest top
    poly([o[12], [-8, -206], [-30, -188], o[11]], C.dark), // occipital crest
    poly([o[11], [-30, -188], [-28, -160], o[9], o[10]], C.d3),
    poly([o[1], o[2], [40, -196], [18, -206]], C.d2),
    poly([o[2], o[3], [50, -178], [40, -196]], C.m1),
    poly([o[3], o[4], o[5], [44, -158], [50, -178]], C.m3),
    poly([[-8, -206], [18, -206], [40, -196], [50, -178], [44, -158], [-28, -160], [-30, -188]], C.m2),
    poly([o[5], o[6], o[7], o[8], [-28, -160], [44, -158]], C.m4),
    poly([o[8], o[9], [-28, -160]], C.d3),
  ];
  const facePts = [
    [o[0], o[1], [18, -206], [-8, -206], o[12]], [o[12], [-8, -206], [-30, -188], o[11]],
    [o[11], [-30, -188], [-28, -160], o[9], o[10]], [o[1], o[2], [40, -196], [18, -206]],
    [o[2], o[3], [50, -178], [40, -196]], [o[3], o[4], o[5], [44, -158], [50, -178]],
    [o[5], o[6], o[7], o[8], [-28, -160], [44, -158]],
  ];
  const edges = facePts.map((p) => line(P(p))).join('');
  const patches = patch([[-20, -226], [-10, -232], [-8, -220]]) + patch([[-40, -196], [-32, -202], [-32, -186]]) +
    patch([[-40, -168], [-30, -176], [-28, -162]], 0.8) + patch([[30, -218], [38, -212], [30, -206]], 0.8) +
    patch([[0, -150], [10, -152], [6, -144]], 0.6);
  const ex = EXPR.neutral;
  return part([{ d: P(SIDE_OUT), fill: C.mid }], faces.join('') + edges + patches,
    `<path d="M-6 -200 Q12 -212 36 -206" fill="none" stroke="${C.dark}" stroke-width="5" stroke-linecap="round"/>` +
    eye(20, -182, { ...ex, side: 1, po: [3, 0], rx: 0.86 }) +
    ink('M50 -176 L53 -174', 1.8) + ink('M58 -158 Q36 -153 12 -156', 1.9));
}

/* ------------------------------------------------------------------ head: 3/4 (turned to viewer's right) */
const TQ_OUT = [[-4, -240], [20, -223], [42, -207], [55, -188], [60, -170], [55, -155], [40, -144], [4, -139],
  [-30, -142], [-50, -158], [-57, -182], [-48, -207], [-24, -224]];
export function headThreeQuarter() {
  const o = TQ_OUT;
  const k = { Cc: [4, -212], fpL: [-14, -202], fpR: [22, -200], gL: [-36, -205], gR: [38, -198], h: [26, -172], S: [14, -174], mL: [-34, -154], mR: [52, -158], U: [14, -152] };
  const F = [
    [[o[0], o[1], k.fpR, k.Cc], C.dark],
    [[o[0], k.Cc, k.fpL, o[12]], C.d1],
    [[o[1], o[2], k.gR, k.fpR], C.d2],
    [[o[12], k.fpL, k.gL, o[11]], C.d3],
    [[o[2], o[3], k.gR], C.d3],
    [[o[11], k.gL, o[10]], C.m1],
    [[k.gR, o[3], o[4], k.mR, k.h, k.fpR], C.m1],
    [[k.gL, k.fpL, k.S, k.mL, o[9], o[10]], C.m2],
    [[k.Cc, k.fpR, k.h, k.S, k.fpL], C.m3],
    [[k.mR, o[4], o[5], o[6]], C.d3],
    [[k.mL, k.S, k.h, k.mR, o[6], o[7], o[8], o[9]], C.m4],
  ];
  const faces = F.map(([p, c]) => poly(p, c)).join('');
  const edges = F.map(([p]) => line(P(p))).join('');
  const patches = patch([[-26, -220], [-16, -226], [-12, -214], [-22, -210]]) + patch([[26, -214], [36, -208], [30, -200]]) +
    patch([[-54, -186], [-48, -194], [-46, -178]]) + patch([[54, -176], [58, -184], [58, -168]], 0.8) +
    patch([[-46, -160], [-38, -166], [-36, -154]], 0.7);
  return part([{ d: P(TQ_OUT), fill: C.mid }], faces + edges + patches,
    `<path d="M-30 -206 Q-16 -212 -2 -205" fill="none" stroke="${C.dark}" stroke-width="5" stroke-linecap="round"/>` +
    `<path d="M24 -205 Q36 -210 50 -203" fill="none" stroke="${C.dark}" stroke-width="4.4" stroke-linecap="round"/>` +
    eye(-16, -183, { lt: 0.12, side: -1, po: [3, 0] }) +
    eye(41, -183, { lt: 0.12, side: 1, po: [4, 0], rx: 0.62 }) +
    ink('M34 -168 L36 -166', 1.7) + ink('M46 -167 L48 -165', 1.7) + ink('M57 -159 Q16 -148 -34 -154', 1.9));
}

/* ------------------------------------------------------------------ body pieces */
const TORSO = [[-26, -146], [26, -146], [34, -126], [36, -100], [31, -78], [20, -64], [0, -60], [-20, -64], [-31, -78], [-36, -100], [-34, -126]];
const BELLY = 'M-16 -142 C-23 -120 -23 -88 -12 -70 Q0 -64 12 -70 C23 -88 23 -120 16 -142 Z';
const bellyLines = [-128, -114, -100, -86].map((y) => line(`M-15 ${y} Q0 ${y + 3} 15 ${y}`, 0.9, C.bellyLine, 0.9)).join('');
const torsoPatches = patch([[-33, -120], [-27, -126], [-25, -112], [-31, -108]]) + patch([[28, -104], [34, -110], [35, -96]]) +
  patch([[-30, -88], [-25, -94], [-24, -80]], 0.8) + patch([[24, -132], [30, -136], [30, -124]], 0.8);

const ARM_R = [[26, -138], [40, -120], [47, -101], [50, -86], [39, -86], [37, -100], [31, -113], [22, -126]];
const LEG_R = [[6, -72], [30, -72], [32, -48], [28, -18], [28, -10], [10, -10], [10, -40], [6, -56]];
const legDet = (s) => patch([[14 * s, -56], [24 * s, -60], [22 * s, -48]], 0.85) + patch([[20 * s, -34], [27 * s, -38], [26 * s, -26]], 0.8) +
  line(`M${12 * s} -42 Q${19 * s} -38 ${27 * s} -42`, 0.8);
const armDet = (s) => patch([[32 * s, -120], [40 * s, -118], [38 * s, -110]], 0.85) + patch([[42 * s, -100], [47 * s, -98], [44 * s, -92]], 0.8) +
  line(`M${36 * s} -104 Q${42 * s} -102 ${46 * s} -106`, 0.8);

function arm(side, fill = C.mid) {
  const pts = side === 1 ? ARM_R : mx(ARM_R);
  return part([{ d: P(pts), fill }], armDet(side)) + hand(44.5 * side, -88, side);
}
function leg(side, fill = C.mid) {
  const pts = side === 1 ? LEG_R : mx(LEG_R);
  return part([{ d: P(pts), fill }], legDet(side));
}

/* ------------------------------------------------------------------ full views */
export function viewFront() {
  return [
    tailPath([22, -72], [42, -44], [70, -46], [92, -84], 90),
    leg(-1), leg(1), footFront(-19, -3), footFront(19, 3),
    part([{ d: P(TORSO), fill: C.mid }], `<path d="${P([[0, -150], [40, -150], [40, -56], [0, -56]])}" fill="${C.d3}" opacity="0.25"/>` + torsoPatches,
      `<clipPath id="bellyclip"><path d="${BELLY}"/></clipPath><path d="${BELLY}" fill="${C.belly}" stroke="${C.outline}" stroke-width="1.3"/>` + `<g clip-path="url(#bellyclip)">${bellyLines}</g>`),
    arm(-1), arm(1),
    headFront('neutral'),
  ].join('');
}

export function viewBack() {
  const spikes = [];
  for (let y = -140; y < -70; y += 10) spikes.push(poly([[-4.5, y], [0, y - 9], [4.5, y]], C.dark, `stroke="${C.outline}" stroke-width="1.1" stroke-linejoin="round"`));
  return [
    leg(-1), leg(1), footBack(-19), footBack(19),
    part([{ d: P(TORSO), fill: C.mid }], `<path d="${P([[0, -150], [40, -150], [40, -56], [0, -56]])}" fill="${C.d3}" opacity="0.25"/>` + torsoPatches +
      patch([[-14, -120], [-6, -126], [-8, -110]], 0.8) + patch([[8, -96], [16, -100], [14, -88]], 0.8), spikes.join('')),
    arm(-1), arm(1),
    tailPath([0, -70], [2, -40], [60, -36], [92, -84], 90),
    headBack(),
  ].join('');
}

const TORSO_S = [[-24, -146], [20, -146], [26, -122], [27, -98], [22, -76], [11, -62], [-14, -62], [-24, -76], [-29, -100], [-29, -124]];
const ARM_S = [[-12, -136], [6, -134], [10, -110], [12, -88], [2, -88], [-1, -108], [-10, -122]];
const LEG_S = [[-18, -74], [10, -74], [12, -50], [6, -12], [-10, -12], [-12, -40]];
export function viewSide() {
  const spikes = [];
  for (let y = -138; y < -70; y += 10) spikes.push(poly([[-28, y + 4.5], [-37, y], [-28, y - 4.5]], C.dark, `stroke="${C.outline}" stroke-width="1.1" stroke-linejoin="round"`));
  return [
    tailPath([-20, -74], [-24, -50], [-42, -48], [-72, -84], 0),
    // far limbs
    `<g transform="translate(6 -2)">${part([{ d: P(ARM_S), fill: C.d3 }])}${hand(7, -90, -1, -8)}</g>`,
    `<g transform="translate(6 0)">${part([{ d: P(LEG_S), fill: C.d3 }])}${footSide(7, 1, C.d3)}</g>`,
    spikes.join(''),
    part([{ d: P(TORSO_S), fill: C.mid }], patch([[-22, -118], [-14, -124], [-14, -110]]) + patch([[-20, -94], [-12, -98], [-14, -86]], 0.8),
      `<path d="M8 -142 C26 -120 26 -90 13 -66 L3 -66 C14 -90 14 -120 0 -142 Z" fill="${C.belly}" stroke="${C.outline}" stroke-width="1.3"/>`),
    part([{ d: P(LEG_S), fill: C.mid }], patch([[-10, -60], [0, -64], [-2, -50]], 0.85) + patch([[-6, -34], [2, -38], [0, -26]], 0.8)),
    footSide(-2, 1),
    part([{ d: P(ARM_S), fill: C.mid }], patch([[-6, -126], [2, -124], [0, -116]], 0.85) + patch([[2, -104], [8, -102], [6, -96]], 0.8)),
    hand(7, -90, -1, -8),
    headSide(),
  ].join('');
}

export function viewThreeQuarter() {
  const T = [[-22, -146], [28, -146], [36, -126], [37, -100], [32, -78], [21, -64], [2, -60], [-18, -64], [-28, -78], [-32, -100], [-30, -126]];
  const belly = 'M-8 -142 C-14 -120 -14 -88 -4 -70 Q8 -64 18 -70 C27 -88 27 -120 20 -142 Z';
  const ARM_F = ARM_R.map(([x, y]) => [x * 0.9 + 2, y]);
  const LEG_F = LEG_R.map(([x, y]) => [x * 0.9 + 2, y]);
  const ARM_N = mx(ARM_R).map(([x, y]) => [x * 0.95 + 2, y]);
  const LEG_N = mx(LEG_R).map(([x, y]) => [x + 2, y]);
  return [
    tailPath([20, -72], [40, -46], [64, -46], [88, -84], 90),
    part([{ d: P(LEG_F), fill: C.d3 }], legDet(0.9)), `<g transform="translate(22 0) scale(0.95 1)">${footFront(0, 6)}</g>`,
    part([{ d: P(ARM_F), fill: C.d3 }], armDet(0.9)), hand(42, -88, 1, 0, 0.95),
    part([{ d: P(LEG_N), fill: C.mid }], legDet(-1)), footFront(-16, 5),
    part([{ d: P(T), fill: C.mid }], `<path d="${P([[-40, -150], [-10, -150], [-10, -56], [-40, -56]])}" fill="${C.d3}" opacity="0.25"/>` + torsoPatches,
      `<path d="${belly}" fill="${C.belly}" stroke="${C.outline}" stroke-width="1.3"/>`),
    part([{ d: P(ARM_N), fill: C.mid }], armDet(-1)), hand(-40, -88, -1),
    headThreeQuarter(),
  ].join('');
}
