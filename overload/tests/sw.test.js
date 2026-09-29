import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ROOT, assetList, stamped } from '../tools/stamp-sw.mjs';

const sw = readFileSync(`${ROOT}sw.js`, 'utf8');

test('offline cache lists every app file, and its version matches their contents', () => {
  // If this fails after editing the app, run `npm run stamp` in overload/ and commit sw.js.
  assert.equal(sw, stamped(sw), 'sw.js is out of date: run `npm run stamp` in overload/');
});

test('offline cache covers the start page and every module the app imports', () => {
  const assets = assetList();
  for (const f of ['./', 'index.html', 'manifest.webmanifest', 'css/app.css', 'icons/icon-180.png', 'js/app.js', 'js/screens/flow.js']) {
    assert.ok(assets.includes(f), `${f} missing`);
  }
  // Every relative import in the app resolves to a cached file, so a cold start works offline.
  for (const f of assets.filter(a => a.endsWith('.js'))) {
    const dir = f.slice(0, f.lastIndexOf('/') + 1);
    for (const [, spec] of readFileSync(ROOT + f, 'utf8').matchAll(/^import[^'"]*['"](\.[^'"]+)['"]/gm)) {
      const target = new URL(spec, `http://x/${dir}`).pathname.slice(1);
      assert.ok(assets.includes(target), `${f} imports ${spec}, which isn't cached`);
    }
  }
});
