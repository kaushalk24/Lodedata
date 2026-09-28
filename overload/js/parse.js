/* Typed (or dictated) set logging: turns "8 at 60", "3x10 25", "185x5x3", "10, 9, 8 at 25",
 * "eight at sixty kilos" or "same again" into sets. Pure and offline; the set sheet shows a preview
 * before anything is saved, so an ambiguous phrase is never logged blindly. */

import { KG_PER_LB, round } from './util.js';

const ONES = {
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
};
const TENS = { twenty: 20, thirty: 30, forty: 40, fourty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90 };
const isNumWord = w => w in ONES || w in TENS || w === 'hundred';

/** "one hundred and forty" -> "140", "twenty two point five" -> "22.5", "seven and a half" -> "7.5". */
export function wordsToDigits(text) {
  const t = text.split(/\s+/).filter(Boolean);
  const out = [];
  for (let i = 0; i < t.length; i++) {
    const w = t[i];
    if (!isNumWord(w) || (w === 'one' && /^(arm|leg|side|more)$/.test(t[i + 1] || ''))) { out.push(w); continue; }
    // "twenty two" and "one hundred and forty" join; "eight nine" stays two numbers.
    let cur = 0, prev = null, j = i;
    for (; j < t.length; j++) {
      const x = t[j];
      if (x in ONES && (prev === null || prev === 'tens' || prev === 'hundred') && !(prev === 'tens' && ONES[x] >= 10)) { cur += ONES[x]; prev = 'ones'; }
      else if (x in TENS && (prev === null || prev === 'hundred')) { cur += TENS[x]; prev = 'tens'; }
      else if (x === 'hundred' && (prev === null || prev === 'ones') && cur < 10) { cur = (cur || 1) * 100; prev = 'hundred'; }
      else if (x === 'and' && prev === 'hundred' && isNumWord(t[j + 1] || '')) continue;
      else break;
    }
    let num = String(cur);
    if (t[j] === 'point' && (t[j + 1] || '') in ONES) { num += '.' + ONES[t[j + 1]]; j += 2; }
    out.push(num);
    i = j - 1;
  }
  return out.join(' ');
}

const UNIT = {
  kg: ['w', 'kg'], kgs: ['w', 'kg'], kilo: ['w', 'kg'], kilos: ['w', 'kg'], kilogram: ['w', 'kg'], kilograms: ['w', 'kg'],
  lb: ['w', 'lb'], lbs: ['w', 'lb'], pound: ['w', 'lb'], pounds: ['w', 'lb'],
  s: ['t', 1], sec: ['t', 1], secs: ['t', 1], second: ['t', 1], seconds: ['t', 1], min: ['t', 60], mins: ['t', 60], minute: ['t', 60], minutes: ['t', 60],
  m: ['d', 1], meter: ['d', 1], meters: ['d', 1], metre: ['d', 1], metres: ['d', 1], km: ['d', 1000],
  rep: ['r'], reps: ['r'], set: ['s'], sets: ['s'],
};
const OPS = { x: 'x', by: 'x', times: 'x', '@': 'at', at: 'at', with: 'at', for: 'for', of: 'of', plus: 'at' };

function tokenize(seg) {
  const tokens = [];
  const re = /(\d+(?:\.\d+)?)(?::(\d{2}))?|([a-z]+|@)/g;
  let m;
  while ((m = re.exec(seg))) {
    if (m[1] !== undefined) {
      const n = parseFloat(m[1]);
      tokens.push(m[2] !== undefined ? { n: n * 60 + parseInt(m[2], 10), u: 't' } : { n });
    } else {
      const w = m[3];
      const prev = tokens[tokens.length - 1];
      if (UNIT[w] && prev && 'n' in prev && !prev.u) {
        const [u, f] = UNIT[w];
        prev.u = u;
        if (u === 'w') prev.wu = f;
        if ((u === 't' || u === 'd') && f !== 1) prev.n *= f;
      } else if (OPS[w]) tokens.push({ op: OPS[w] });
    }
  }
  return tokens;
}

/**
 * Interpret one segment ("3x10 @ 25"). `metric` is what a bare number means for this exercise:
 * 'r' reps, 't' seconds or 'd' metres.
 */
function interpret(tokens, metric) {
  const res = { count: 1, metrics: [], load: null };
  const used = new Set();
  const nums = tokens.map((t, i) => ('n' in t ? i : -1)).filter(i => i >= 0);
  const next = i => nums.find(j => j > i);
  const take = (i, as) => {
    if (used.has(i)) return; // each number means one thing
    used.add(i);
    const t = tokens[i];
    if (as === 'load') res.load = t;
    else if (as === 'count') res.count = t.n;
    else res.metrics.push(t.n);
  };
  // Explicit units win: "60 kg", "10 reps", "3 sets", "45 s", "40 m".
  for (const i of nums) {
    const u = tokens[i].u;
    if (u === 'w') take(i, 'load');
    else if (u === 's') take(i, 'count');
    else if (u && u === metric) take(i, 'metric');
  }
  // "a x b [x c]" chains.
  for (let i = 0; i < tokens.length; i++) {
    if (!('n' in tokens[i]) || used.has(i) || tokens[i + 1]?.op !== 'x' || !('n' in (tokens[i + 2] || {}))) continue;
    const chain = [i, i + 2];
    if (tokens[i + 3]?.op === 'x' && 'n' in (tokens[i + 4] || {})) chain.push(i + 4);
    const [a, b, c] = chain.map(k => tokens[k]);
    const loadElsewhere = res.load || nums.some(k => !chain.includes(k) && !used.has(k));
    if (c) {
      if (a.u === 'w' || (!c.u && a.n > 20)) { take(chain[0], 'load'); take(chain[1], 'metric'); take(chain[2], 'count'); } // 185x5x3
      else { take(chain[0], 'count'); take(chain[1], 'metric'); take(chain[2], 'load'); } // 3x10x25
    } else if (a.u === 'w') { take(chain[0], 'load'); take(chain[1], 'metric'); } // 60kg x 8
    else if (b.u === 'w') { take(chain[0], 'metric'); take(chain[1], 'load'); } // 8 x 60kg
    else if (b.u === 't' || b.u === 'd' || metric !== 'r' || loadElsewhere || (a.n <= 8 && b.n <= 20)) {
      take(chain[0], 'count'); take(chain[1], 'metric'); // 3x10, 3x60s
    } else if (a.n >= b.n) { take(chain[0], 'load'); take(chain[1], 'metric'); } // 60x8
    else { take(chain[0], 'metric'); take(chain[1], 'load'); } // 8x60
    i = chain[chain.length - 1];
  }
  // Keywords: "8 at 60", "60 for 8", "3 sets of 10".
  tokens.forEach((t, i) => {
    if (!t.op || t.op === 'x') return;
    const j = next(i);
    if (j === undefined || used.has(j)) return;
    if (t.op === 'at') take(j, 'load');
    else if (t.op === 'of') take(j, 'metric');
    else if (t.op === 'for') {
      const prev = [...nums].reverse().find(k => k < i && !used.has(k));
      if (prev !== undefined) take(prev, 'load');
      take(j, 'metric');
    }
  });
  // Whatever is left: bare numbers.
  const bare = nums.filter(i => !used.has(i) && (!tokens[i].u || tokens[i].u === metric));
  if (bare.length === 1) take(bare[0], res.metrics.length && !res.load ? 'load' : 'metric');
  else if (bare.length >= 2) {
    if (res.load || res.metrics.length) bare.forEach(i => take(i, 'metric')); // "10 9 8 @ 25"
    else if (metric === 'r' && tokens[bare[0]].n > 30 && tokens[bare[1]].n <= 30 && bare.length === 2) { take(bare[0], 'load'); take(bare[1], 'metric'); }
    else {
      // "8 60" or "10 9 8 25": a last number bigger than the rest is the weight; "8 9 7" is all reps.
      const lastN = tokens[bare[bare.length - 1]].n;
      const lastIsLoad = metric !== 'r' ? bare.length === 2 : bare.length === 2 || lastN > Math.max(...bare.slice(0, -1).map(i => tokens[i].n));
      bare.slice(0, -1).forEach(i => take(i, 'metric'));
      take(bare[bare.length - 1], lastIsLoad ? 'load' : 'metric');
    }
  }
  return res;
}

const HINT = 'Try "8 at 60", "3x10 25" or "same again".';

/**
 * @param {string} text
 * @param {{kind?:string, unit?:'kg'|'lb', last?:object|null, fallbackKg?:number}} o
 *   fallbackKg / fallbackReps: what the sheet already shows, used when the phrase leaves one out.
 * @returns {{sets: {reps:number, weight:number, sec?:number, dist?:number, label?:string, rpe?:number, side?:string, bw?:boolean}[], error: string|null}}
 */
export function parseLog(text, { kind = 'weight', unit = 'kg', last = null, fallbackKg = 0, fallbackReps = null } = {}) {
  let s = ` ${String(text || '').toLowerCase()} `.replace(/[×*]/g, 'x').replace(/½/g, '.5').replace(/-/g, ' ');
  if (!s.trim()) return { sets: [], error: null };
  // Decimal commas for plate fractions only ("27,5"), so "10,9,8" stays a list.
  s = s.replace(/(^|[^\d,])(\d+),(5|25|75)(?![\d,])/g, '$1$2.$3');
  s = wordsToDigits(s.replace(/([^\s\d.:])(?=\d)|(\d)(?=[^\s\d.:,])/g, '$1$2 '));
  s = ` ${s.replace(/(\d+) and a half/g, (_, n) => `${n}.5`).replace(/(\d+) point (\d)/g, '$1.$2')} `;

  const flags = {};
  const pull = (re, fn) => { s = s.replace(re, (...m) => { fn(...m); return ' '; }); };
  pull(/\brpe\s*(\d+(?:\.5)?)/g, (_, v) => { const r = parseFloat(v); if (r >= 6 && r <= 10) flags.rpe = r; });
  pull(/\bwarm\s*up\b|\bwarmup\b/g, () => { flags.label = 'warmup'; });
  pull(/\b(to )?fail(ure)?\b/g, () => { flags.label = 'failure'; });
  pull(/\bdrop\s*sets?\b|\bdrop\b/g, () => { flags.label = 'drop'; });
  pull(/\bamrap\b/g, () => { flags.label = 'amrap'; });
  pull(/\bleft( side)?\b/g, () => { flags.side = 'L'; });
  pull(/\bright( side)?\b/g, () => { flags.side = 'R'; });
  let bodyOnly = false;
  pull(/\b(bw|body ?weight)\b/g, () => { bodyOnly = true; });

  const withFlags = set => ({ ...set, ...flags });
  if (/^\s*(same( again| as last| as before)?|again|repeat( last| that)?|one more)\s*$/.test(s)) {
    if (!last) return { sets: [], error: 'There is no earlier set to repeat yet.' };
    // The side is left out on purpose: one-sided exercises alternate, so "same again" means the other arm.
    const { reps, weight, sec, dist, bw } = last;
    return { sets: [withFlags({ reps, weight, sec, dist, bw })], error: null };
  }

  const metric = kind === 'time' ? 't' : kind === 'distance' ? 'd' : 'r';
  const segs = s.split(/[,;\n]|\bthen\b|\band\b/).map(x => tokenize(x)).filter(t => t.some(x => 'n' in x));
  if (!segs.length) return { sets: [], error: bodyOnly || Object.keys(flags).length ? `Add the numbers. ${HINT}` : `Couldn't read that. ${HINT}` };

  const parts = segs.map(t => interpret(t, metric));
  const toKg = t => (t ? round((t.wu || unit) === 'lb' ? t.n * KG_PER_LB : t.n, 4) : null);
  const sets = [];
  parts.forEach((p, i) => {
    // A segment without a weight borrows it from the next one ("10, 9, 8 at 25"), then the one before.
    const src = p.load || parts.slice(i + 1).find(q => q.load)?.load || [...parts.slice(0, i)].reverse().find(q => q.load)?.load;
    const weight = bodyOnly && !p.load ? 0 : src ? toKg(src) : fallbackKg;
    const reps = fallbackReps > 0 ? fallbackReps : last?.reps;
    const metrics = p.metrics.length ? p.metrics : (metric === 'r' && reps > 0 ? [reps] : []);
    if (!metrics.length) return;
    const repeat = metrics.length === 1 ? Math.round(p.count) : 1;
    for (const v of metrics) {
      for (let k = 0; k < repeat; k++) {
        const set = metric === 't' ? { reps: 0, sec: Math.round(v), weight } : metric === 'd' ? { reps: 0, dist: round(v, 1), weight } : { reps: v, weight };
        sets.push(withFlags(set));
      }
    }
  });

  if (!sets.length) return { sets: [], error: `Couldn't find the reps. ${HINT}` };
  if (sets.length > 20) return { sets: [], error: 'That is more than 20 sets. Log them in smaller groups.' };
  for (const x of sets) {
    if (metric === 'r' && !(x.reps > 0 && x.reps <= 200)) return { sets: [], error: `${x.reps} reps doesn't look right. ${HINT}` };
    if (metric === 't' && !(x.sec > 0 && x.sec <= 7200)) return { sets: [], error: 'Durations go up to 2 hours.' };
    if (metric === 'd' && !(x.dist > 0 && x.dist <= 100000)) return { sets: [], error: 'Distances go up to 100 km.' };
    if (!(x.weight >= 0 && x.weight <= 1000)) return { sets: [], error: 'That weight is out of range.' };
  }
  return { sets, error: null };
}
