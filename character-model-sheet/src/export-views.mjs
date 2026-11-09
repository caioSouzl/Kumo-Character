// Exports each turnaround view and each expression as a separate SVG in ../views and ../expressions.
import fs from 'node:fs';
import path from 'node:path';
import * as K from './kumo.mjs';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const wrap = (vb, body) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}" width="${vb.split(' ')[2] * 4}" height="${vb.split(' ')[3] * 4}"><defs>${K.defs}</defs>${body}</svg>`;
fs.mkdirSync(path.join(root, 'views'), { recursive: true });
fs.mkdirSync(path.join(root, 'expressions'), { recursive: true });
const views = { front: [K.viewFront(), -75], 'three-quarter': [K.viewThreeQuarter(), -75], side: [K.viewSide(), -115], back: [K.viewBack(), -75] };
for (const [n, [b, x0]] of Object.entries(views)) fs.writeFileSync(path.join(root, 'views', `kumo-${n}.svg`), wrap(`${x0} -250 215 260`, b));
for (const n of Object.keys(K.EXPR)) fs.writeFileSync(path.join(root, 'expressions', `kumo-${n}.svg`), wrap('-66 -250 132 116', K.headFront(n)));
console.log('exported');
