/* On-device "smart" features. Plain statistics over the log: no network, no AI service.
 * Every function is pure so it can be unit-tested. Weights are kg, times are ms timestamps. */

import { norm, round, dayKey, daysBetween } from './util.js';
import { groupByDay, bestE1rm, isRepKind } from './stats.js';

const DAY = 86400000;
const median = a => { const b = [...a].sort((x, y) => x - y); const m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
const working = sets => sets.filter(s => s.label !== 'warmup');

/* ---------- typo guard ---------- */

/**
 * Catch a slipped decimal point or an extra digit before it reaches the log:
 * 275 kg when you usually lift 27.5, or 100 reps when you usually do 10.
 * Returns { field, value, suggest|null, usual } or null when the numbers look normal.
 */
export function typoCheck(sets, { reps, weight }) {
  const recent = working(sets).slice(-12);
  if (recent.length < 3) return null;
  const weights = recent.map(s => s.weight).filter(w => w > 0);
  if (weight > 0 && weights.length >= 3) {
    const usual = median(weights);
    const ratio = weight / usual;
    if (ratio >= 2.2 || ratio <= 0.22) {
      const fits = [weight / 10, weight / 100, weight * 10]
        .filter(c => c / usual >= 0.5 && c / usual <= 1.6)
        .sort((a, b) => Math.abs(Math.log(a / usual)) - Math.abs(Math.log(b / usual)));
      // Light sets are normal (drop sets, back-off sets), so only flag one when a slipped digit explains it.
      if (ratio < 1 && !fits.length) return null;
      return { field: 'weight', value: weight, suggest: fits.length ? round(fits[0], 2) : null, usual, heavier: ratio > 1 };
    }
  }
  const maxReps = Math.max(0, ...recent.map(s => s.reps));
  if (reps > 30 && maxReps > 0 && reps >= 3 * maxReps) {
    const c = reps / 10;
    return { field: 'reps', value: reps, suggest: c >= 1 && c <= maxReps * 1.5 ? round(c, 1) : null, usual: maxReps, heavier: true };
  }
  return null;
}

/* ---------- duplicate finder ---------- */

const SPELLING = [
  [/\b(dumbell|dumbel|dumbbel)(s?)\b/g, 'dumbbell$2'], [/\bdb\b/g, 'dumbbell'], [/\bbb\b/g, 'barbell'],
  [/\bpull (up|down)\b/g, 'pull$1'], [/\bpush (up|down)\b/g, 'push$1'], [/\bchin up\b/g, 'chinup'],
  [/\b(smithmaskin|smithmachine)\b/g, 'smith machine'], [/\bext\b/g, 'extension'],
];
const STOP = new Set(['the', 'a', 'with', 'on', 'and', 'of']);
const GENERIC = new Set(['press', 'machine', 'exercise']);

/** Lower-case, fix common misspellings, drop trailing numbers ("Forearm curls 2") and plurals. */
export function normalizeName(name) {
  let n = norm(name);
  for (const [re, to] of SPELLING) n = n.replace(re, to);
  const tokens = n.split(' ').filter(t => t && !STOP.has(t))
    .map(t => (t.length > 3 && t.endsWith('s') && !t.endsWith('ss') ? t.slice(0, -1) : t));
  while (tokens.length > 1 && /^\d+$/.test(tokens[tokens.length - 1])) tokens.pop();
  return tokens;
}

/** Edit distance where swapping two neighbouring letters counts once ("traingle" vs "triangle"). */
export function editDistance(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...new Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
    }
  }
  return d[a.length][b.length];
}

const tokenMatch = (x, y) => x === y
  || (Math.min(x.length, y.length) >= 5 && editDistance(x, y) <= 1)
  || (Math.min(x.length, y.length) >= 7 && editDistance(x, y) <= 2);

/** Same exercise under two names? Short words must match exactly, so "Hack squat" and "Back squat" stay apart. */
export function sameName(a, b) {
  const A = normalizeName(a), B = normalizeName(b);
  if (!A.length || !B.length) return false;
  if (A.join(' ') === B.join(' ')) return true;
  const [short, long] = A.length <= B.length ? [A, B] : [B, A];
  const left = [...long];
  for (const t of short) {
    const i = left.findIndex(u => tokenMatch(t, u));
    if (i < 0) return false;
    left.splice(i, 1);
  }
  // Every word matched. Allow at most one extra, generic word: "Jm" / "Jm press".
  return left.length === 0 || (left.length === 1 && GENERIC.has(left[0]));
}

/**
 * Likely duplicate pairs among the user's exercises. Two exercises logged together on two or more
 * days are clearly different movements and are skipped, as are pairs the user dismissed.
 * Returns [{ keep, drop }] where `keep` has the longer history.
 */
export function findDuplicates(exercises, setsFor, ignore = new Set()) {
  const days = new Map(exercises.map(e => [e.id, new Set(setsFor(e.id).map(s => dayKey(s.ts)))]));
  const out = [];
  for (let i = 0; i < exercises.length; i++) {
    for (let j = i + 1; j < exercises.length; j++) {
      const a = exercises[i], b = exercises[j];
      if (ignore.has(pairKey(a.id, b.id)) || !sameName(a.name, b.name)) continue;
      const pa = a.primary || [], pb = b.primary || [];
      if (pa.length && pb.length && !pa.some(m => pb.includes(m))) continue;
      let shared = 0;
      for (const d of days.get(a.id)) if (days.get(b.id).has(d)) shared++;
      if (shared >= 2) continue;
      const na = days.get(a.id).size, nb = days.get(b.id).size;
      out.push(na >= nb ? { keep: a, drop: b } : { keep: b, drop: a });
    }
  }
  return out;
}
export const pairKey = (a, b) => [a, b].sort().join('|');

/* ---------- learned rest ---------- */

/**
 * Your real rest per exercise: the median gap between back-to-back sets of the same exercise on the
 * same day, when no other exercise was done in between. Gaps under 20 s (logged late) or over 15 min
 * (a break) are ignored. Needs 5 gaps. Returns { byEx: Map(exId -> { sec, n }), overall: sec|null }.
 */
export function learnedRest(allSets, { minGaps = 5, recent = 30 } = {}) {
  const sorted = [...allSets].sort((a, b) => a.ts - b.ts);
  const gaps = new Map(), all = [];
  for (let i = 1; i < sorted.length; i++) {
    const a = sorted[i - 1], b = sorted[i];
    if (a.exId !== b.exId || a.label === 'warmup' || b.label === 'warmup' || dayKey(a.ts) !== dayKey(b.ts)) continue;
    const g = (b.ts - a.ts) / 1000;
    if (g < 20 || g > 900) continue;
    if (a.side && b.side && a.side !== b.side && g < 90) continue; // switching arms, not resting
    if (!gaps.has(a.exId)) gaps.set(a.exId, []);
    gaps.get(a.exId).push(g); all.push(g);
  }
  const to15 = s => Math.max(15, Math.round(s / 15) * 15);
  const byEx = new Map();
  for (const [id, g] of gaps) if (g.length >= minGaps) byEx.set(id, { sec: to15(median(g.slice(-recent))), n: g.length });
  return { byEx, overall: all.length >= minGaps ? to15(median(all.slice(-200))) : null };
}

/* ---------- plateau ---------- */

/**
 * Stalled when the best estimated 1RM hasn't improved for 4 sessions spread over at least 2 weeks.
 * Suggests a lighter week at about 90% of the last top set, the usual deload.
 */
export function plateauInfo(sets, { formula = 'epley', bodyKg = 0, kind = 'weight', minSessions = 4, step = 2.5 } = {}) {
  if (!isRepKind(kind) || kind === 'assisted') return null;
  const days = groupByDay(working(sets)).reverse()
    .map(d => ({ ts: d.ts, sets: d.sets, best: bestE1rm(d.sets, formula, bodyKg)?.value || 0 }))
    .filter(d => d.best > 0);
  if (days.length < minSessions + 2) return null;
  let best = 0, prIdx = 0;
  days.forEach((d, i) => { if (d.best > best + 0.01) { best = d.best; prIdx = i; } });
  const since = days.length - 1 - prIdx;
  const last = days[days.length - 1];
  if (since < minSessions || daysBetween(days[prIdx].ts, last.ts) < 14) return null;
  const top = last.sets.reduce((a, s) => (s.weight > a.weight ? s : a), last.sets[0]);
  // Unloaded bodyweight work has no weight to take off; the lighter week is fewer sets instead.
  const deloadKg = top.weight > 0 ? round(Math.max(step, Math.round((top.weight * 0.9) / step) * step), 2) : null;
  return { sessions: since, since: days[prIdx].ts, best, top, deloadKg, total: days.length };
}

/* ---------- goal projection ---------- */

/**
 * When will you hit an estimated 1RM goal? Fits a straight line through the best estimated 1RM of
 * each session in the last 120 days. Returns { current, goal, perWeek, eta|null, status } where
 * status is 'reached' | 'on-track' | 'far' | 'flat' | 'data'.
 */
export function projectGoal(sets, goal, { formula = 'epley', bodyKg = 0, now = Date.now() } = {}) {
  const days = groupByDay(working(sets)).reverse()
    .filter(d => d.ts >= now - 120 * DAY)
    .map(d => ({ t: (d.ts - now) / DAY, y: bestE1rm(d.sets, formula, bodyKg)?.value || 0 }))
    .filter(d => d.y > 0);
  const current = days.length ? Math.max(...days.slice(-3).map(d => d.y)) : 0;
  const base = { current: round(current, 1), goal, perWeek: 0, eta: null };
  if (current >= goal && current > 0) return { ...base, status: 'reached' };
  if (days.length < 3 || days[days.length - 1].t - days[0].t < 14) return { ...base, status: 'data' };
  const n = days.length, mx = days.reduce((a, d) => a + d.t, 0) / n, my = days.reduce((a, d) => a + d.y, 0) / n;
  const sxx = days.reduce((a, d) => a + (d.t - mx) ** 2, 0);
  const slope = sxx ? days.reduce((a, d) => a + (d.t - mx) * (d.y - my), 0) / sxx : 0; // kg per day
  const perWeek = round(slope * 7, 2);
  if (perWeek < 0.1) return { ...base, perWeek, status: 'flat' };
  const daysLeft = (goal - current) / slope;
  if (daysLeft > 730) return { ...base, perWeek, status: 'far' };
  return { ...base, perWeek, eta: now + daysLeft * DAY, status: 'on-track' };
}

/* ---------- what to train today ---------- */

/**
 * Pick the workout folder whose muscles are most recovered, breaking ties by the one done longest
 * ago, the way Fitbod favours fresh muscles. A muscle counts as recovered 72 h after it was trained.
 * `muscleLast` maps muscle -> last trained timestamp. Returns { workout, readiness, lastTs, sore[] },
 * { rest: true, sore[] } when everything is still recovering, or null when there's nothing to pick.
 */
export function whatToTrain(workouts, exercise, muscleLast, lastTs, now = Date.now()) {
  const ready = m => { const t = muscleLast[m]; return t ? Math.min(1, (now - t) / (72 * 3600000)) : 1; };
  const options = [];
  for (const w of workouts) {
    const exs = w.exIds.map(exercise).filter(Boolean);
    const muscles = [...new Set(exs.flatMap(e => e.primary || []))];
    if (!muscles.length) continue;
    const last = Math.max(0, ...exs.map(e => lastTs(e.id)));
    if (last && daysBetween(last, now) === 0) continue; // already done today
    const readiness = muscles.reduce((a, m) => a + ready(m), 0) / muscles.length;
    options.push({ workout: w, readiness, lastTs: last, sore: muscles.filter(m => ready(m) < 1 / 3) });
  }
  if (!options.length) return null;
  options.sort((a, b) => (b.readiness - a.readiness > 0.05 ? 1 : a.readiness - b.readiness > 0.05 ? -1 : 0) || a.lastTs - b.lastTs);
  const top = options[0];
  if (top.readiness < 0.5) return { rest: true, sore: top.sore };
  return top;
}

/* ---------- warm-up ramp ---------- */

/**
 * Warm-up sets for a working weight: Hevy's default ramp (40% x 5, 60% x 5, 80% x 3), plus an
 * empty-bar set first for barbell lifts, as Strong and StrongLifts do. Weights round to what can be
 * loaded: bar plus the smallest plate pair, or `step` for dumbbells and machines.
 */
export function warmupRamp(work, { bar = 0, smallestPlate = 1.25, step = 2.5 } = {}) {
  const inc = bar ? smallestPlate * 2 : step;
  const roundTo = w => bar ? bar + Math.round((w - bar) / inc) * inc : Math.round(w / inc) * inc;
  const rows = [];
  if (bar && work > bar * 1.5) rows.push({ pct: 0, reps: 10, kg: bar });
  for (const [pct, reps] of [[40, 5], [60, 5], [80, 3]]) {
    const kg = round(roundTo((work * pct) / 100), 2);
    if (kg <= 0 || kg >= work || (bar && kg <= bar) || rows.some(r => r.kg >= kg)) continue;
    rows.push({ pct, reps, kg });
  }
  return rows;
}
