// Render film.html deterministically: seek(t) per frame in headless Chrome, screenshot each frame.
// usage: node render.mjs stills <outDir> <t1,t2,...>   |   node render.mjs frames <outDir> <from> <to>
import { createRequire } from 'module';
import { mkdirSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_CORE || '/Users/petrinolann/.npm/_npx/e41f203b7505f1fb/node_modules/playwright-core');
const [mode, out, a, b] = process.argv.slice(2);
const here = path.dirname(fileURLToPath(import.meta.url));
const url = 'file://' + path.join(here, 'film.html') + '?frames=' + encodeURIComponent('file://' + process.env.FRAMES_DIR);
const browser = await chromium.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  args: ['--force-color-profile=srgb', '--hide-scrollbars', '--allow-file-access-from-files', '--font-render-hinting=none'],
});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: Number(process.env.SCALE || 1) });  // SCALE=2 renders native 4K
page.on('pageerror', e => console.error('[pageerror]', e.message));
await page.goto(url);
await page.waitForFunction(() => window.ready === true, null, { timeout: 30000 });
mkdirSync(out, { recursive: true });
if (mode === 'stills') {
  for (const t of a.split(',').map(Number)) {
    await page.evaluate(t => window.seek(t), t);
    await page.screenshot({ path: `${out}/t${t.toFixed(2)}.png` });
  }
} else {
  for (let i = +a; i < +b; i++) {
    await page.evaluate(t => window.seek(t), i / 30);
    await page.screenshot({ path: `${out}/${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 94 });
  }
}
await browser.close();
