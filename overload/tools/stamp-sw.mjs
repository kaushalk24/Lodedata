/* Writes the file list and version into sw.js. Run after changing any app file: `npm run stamp`.
   The version is a hash of every cached file, so each change reaches phones as a complete new version. */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = fileURLToPath(new URL('..', import.meta.url));
const SW = `${ROOT}sw.js`;
const TYPES = /\.(js|css|html|webmanifest|png|svg)$/;

function walk(dir) {
  return readdirSync(ROOT + dir, { withFileTypes: true }).filter(d => !d.name.startsWith('.')).flatMap(d =>
    d.isDirectory() ? walk(`${dir}/${d.name}`) : TYPES.test(d.name) ? [`${dir}/${d.name}`] : []);
}

/** Everything the app loads, in a stable order. './' is the start page itself. */
export function assetList() {
  return ['./', 'index.html', 'manifest.webmanifest', ...['css', 'icons', 'js'].flatMap(walk).sort()];
}

/** sw.js as it should be: current file list, and a version that changes when any listed file changes. */
export function stamped(src = readFileSync(SW, 'utf8')) {
  const assets = assetList();
  const hash = createHash('sha256');
  // Line endings are normalised so a Windows checkout gets the same version.
  for (const f of assets.slice(1)) hash.update(`${f}\n`).update(readFileSync(ROOT + f).toString('latin1').replace(/\r\n/g, '\n'));
  const lines = [];
  for (const f of assets.map(a => `'${a}'`)) {
    if (lines.length && `${lines[lines.length - 1]} ${f},`.length <= 118) lines[lines.length - 1] += ` ${f},`;
    else lines.push(`  ${f},`);
  }
  return src
    .replace(/const CACHE = '[^']*';/, `const CACHE = 'overload-${hash.digest('hex').slice(0, 10)}';`)
    .replace(/const ASSETS = \[[\s\S]*?\];/, `const ASSETS = [\n${lines.join('\n')}\n];`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const before = readFileSync(SW, 'utf8'), after = stamped(before);
  if (after === before) console.log('sw.js is up to date');
  else { writeFileSync(SW, after); console.log(`sw.js updated: ${after.match(/const CACHE = '([^']*)'/)[1]}`); }
}
