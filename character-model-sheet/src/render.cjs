// Render an SVG file to PNG with Chromium.  node render.cjs <in.svg> <out.png> [scale]
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [inp, out, scale = '1'] = process.argv.slice(2);
  const src = fs.readFileSync(inp, 'utf8');
  const w = +src.match(/width="(\d+)"/)[1];
  const h = +src.match(/height="(\d+)"/)[1];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: Number(scale) });
  await p.goto('file://' + require('path').resolve(inp));
  await p.waitForLoadState('networkidle');
  await p.screenshot({ path: out, clip: { x: 0, y: 0, width: w, height: h } });
  await b.close();
})();
