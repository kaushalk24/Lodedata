/* Training analytics. Pure functions over plain set objects:
 *   { id, exId, ts, reps, weight (kg), label, note, gymId, bw }
 * label: 'warmup' | 'amrap' | 'failure' | 'drop' | 'pr' | null
 * bw: true when `weight` is added load on top of bodyweight (pull-ups, dips). */

import { dayKey, startOfWeek, addDays, daysBetween, round } from './util.js';

export const effWeight = (s, bodyKg = 0) => s.weight + (s.bw ? bodyKg : 0);
export const setVolume = (s, bodyKg = 0) => s.reps * effWeight(s, bodyKg);
const byTs = (a, b) => a.ts - b.ts;

/** Days newest-first, sets oldest-first inside each day (set 1, 2, 3...). */
export function groupByDay(sets) {
  const map = new Map();
  for (const s of [...sets].sort(byTs)) {
    const k = dayKey(s.ts);
    if (!map.has(k)) map.set(k, { key: k, ts: s.ts, sets: [] });
    map.get(k).sets.push(s);
  }
  return [...map.values()].reverse();
}

export function summarize(sets, bodyKg = 0) {
  const reps = sets.reduce((a, s) => a + s.reps, 0);
  const volume = sets.reduce((a, s) => a + setVolume(s, bodyKg), 0);
  return { sets: sets.length, reps: round(reps, 1), volume: round(volume, 2), perRep: reps ? round(volume / reps, 1) : 0 };
}

const delta = (cur, prev) => ({ diff: round(cur - prev, 2), pct: prev ? round(((cur - prev) / prev) * 100, 1) : null });

/** The "COMPARED TO PREVIOUS" card: latest session vs the one before it. */
export function compareToPrevious(sets, bodyKg = 0) {
  const days = groupByDay(sets);
  if (days.length < 2) return null;
  const cur = summarize(days[0].sets, bodyKg), prev = summarize(days[1].sets, bodyKg);
  return {
    cur, prev,
    sets: delta(cur.sets, prev.sets), reps: delta(cur.reps, prev.reps),
    volume: delta(cur.volume, prev.volume), perRep: delta(cur.perRep, prev.perRep),
  };
}

/* ---------- records ---------- */

/** best[r] = heaviest weight lifted for at least r reps. Index 0 unused. */
export function repEnvelope(sets, bodyKg = 0) {
  const maxR = Math.floor(Math.max(0, ...sets.map(s => s.reps)));
  const best = new Array(maxR + 1).fill(null);
  for (const s of sets) {
    const w = effWeight(s, bodyKg);
    for (let r = 1; r <= Math.floor(s.reps); r++) {
      if (best[r] == null || w > best[r].weight) best[r] = { weight: w, setId: s.id, ts: s.ts };
    }
  }
  return best;
}

/** Records table: consecutive rep counts sharing the same best weight merge into a range ("1-6: 95 kg"). */
export function recordRanges(sets, bodyKg = 0) {
  const best = repEnvelope(sets, bodyKg);
  const out = [];
  for (let r = 1; r < best.length; r++) {
    const b = best[r]; if (!b) continue;
    const last = out[out.length - 1];
    if (last && last.weight === b.weight && last.to === r - 1) last.to = r;
    else out.push({ from: r, to: r, weight: b.weight, setId: b.setId, ts: b.ts });
  }
  return out;
}

/**
 * Sets that were personal records when performed: heavier than anything done before for that
 * many reps or more. Bodyweight-only sets (0 kg) count as a PR on reps instead.
 * Nothing on the exercise's first day is a PR (there is nothing to beat yet).
 */
export function prSetIds(sets, bodyKg = 0) {
  const sorted = [...sets].sort(byTs);
  const ids = new Set();
  if (!sorted.length) return ids;
  const firstDay = dayKey(sorted[0].ts);
  const best = []; let maxRepsAtZero = 0;
  for (const s of sorted) {
    const w = effWeight(s, bodyKg), r = Math.floor(s.reps);
    if (dayKey(s.ts) !== firstDay && r >= 1) {
      if (w > 0) {
        let prior = null;
        for (let i = r; i < best.length; i++) if (best[i] != null && (prior == null || best[i] > prior)) prior = best[i];
        if (prior == null || w > prior) ids.add(s.id);
      } else if (s.reps > maxRepsAtZero) ids.add(s.id);
    }
    for (let i = 1; i <= r; i++) if (best[i] == null || w > best[i]) best[i] = w;
    if (w <= 0) maxRepsAtZero = Math.max(maxRepsAtZero, s.reps);
  }
  return ids;
}

/** Would logging (reps, weight) right now beat every earlier set? Used for the live PR badge. */
export function wouldBePR(sets, reps, weight, bodyKg = 0, bw = false) {
  if (!sets.length || !(reps >= 1)) return false;
  const w = weight + (bw ? bodyKg : 0), r = Math.floor(reps);
  if (w <= 0) return reps > Math.max(0, ...sets.filter(s => effWeight(s, bodyKg) <= 0).map(s => s.reps));
  let prior = null;
  for (const s of sets) if (Math.floor(s.reps) >= r) { const sw = effWeight(s, bodyKg); if (prior == null || sw > prior) prior = sw; }
  return prior == null || w > prior;
}

/* ---------- 1RM ---------- */
export const FORMULAS = {
  epley: { name: 'Epley', f: (w, r) => w * (1 + r / 30) },
  brzycki: { name: 'Brzycki', f: (w, r) => r >= 37 ? NaN : w * 36 / (37 - r) },
  lombardi: { name: 'Lombardi', f: (w, r) => w * r ** 0.1 },
  lander: { name: 'Lander', f: (w, r) => (100 * w) / (101.3 - 2.67123 * r) },
  oconner: { name: "O'Conner", f: (w, r) => w * (1 + 0.025 * r) },
};
export function e1rm(weight, reps, formula = 'epley') {
  if (!(reps > 0) || !(weight > 0)) return 0;
  if (reps <= 1) return weight;
  return (FORMULAS[formula] || FORMULAS.epley).f(weight, reps);
}
export function bestE1rm(sets, formula = 'epley', bodyKg = 0) {
  let best = null;
  for (const s of sets) {
    if (s.label === 'warmup' || s.reps > 15) continue; // estimates beyond ~15 reps are noise
    const v = e1rm(effWeight(s, bodyKg), s.reps, formula);
    if (!best || v > best.value) best = { value: v, set: s };
  }
  return best;
}
/** Percent-of-1RM table with approximate reps (inverse Epley). */
export function percentTable(oneRm) {
  return [100, 95, 90, 85, 80, 75, 70, 65, 60, 55, 50].map(p => ({
    pct: p, weight: oneRm * p / 100, reps: p === 100 ? 1 : Math.max(1, Math.round(30 * (100 / p - 1))),
  }));
}

export function bestEfforts(sets, bodyKg = 0) {
  if (!sets.length) return null;
  let setVol = null, maxW = null, maxR = null;
  for (const s of sets) {
    const v = setVolume(s, bodyKg);
    if (!setVol || v > setVol.value) setVol = { value: v, set: s };
    if (!maxW || effWeight(s, bodyKg) > maxW.value) maxW = { value: effWeight(s, bodyKg), set: s };
    if (!maxR || s.reps > maxR.value) maxR = { value: s.reps, set: s };
  }
  let sessVol = null;
  for (const d of groupByDay(sets)) {
    const v = summarize(d.sets, bodyKg).volume;
    if (!sessVol || v > sessVol.value) sessVol = { value: v, day: d };
  }
  return { setVolume: setVol, sessionVolume: sessVol, maxWeight: maxW, maxReps: maxR };
}

/* ---------- progression ---------- */

/**
 * "Beat last time" target, using double progression: add a rep each session until the top of
 * the rep range, then add the smallest weight step and drop back to the bottom of the range.
 * `prevDaySets` is the most recent earlier session; `todayWorkingCount` is how many working sets
 * are already logged today, so set 3 today is compared with set 3 last time.
 */
export function suggestTarget(prevDaySets, todayWorkingCount, { step = 2.5, low = 8, high = 12 } = {}) {
  const working = prevDaySets.filter(s => s.label !== 'warmup');
  if (!working.length) return null;
  const ref = working[Math.min(todayWorkingCount, working.length - 1)];
  const reps = Math.floor(ref.reps);
  if (ref.weight > 0 && reps >= high) return { ref, reps: low, weight: round(ref.weight + step, 3), why: 'weight' };
  return { ref, reps: reps + 1, weight: ref.weight, why: 'rep' };
}

/* ---------- plates ---------- */

/** Greedy plate breakdown for one side. `plates` maps plate size -> total count at the gym. */
export function platesPerSide(total, bar, plates) {
  let rest = round((total - bar) / 2, 4);
  const sizes = Object.keys(plates).map(Number).filter(p => p > 0).sort((a, b) => b - a);
  const side = [];
  if (rest < 0) return { side, remainder: rest };
  for (const p of sizes) {
    let pairs = Math.floor((plates[p] ?? 0) / 2);
    while (pairs > 0 && rest + 1e-9 >= p) { side.push(p); rest = round(rest - p, 4); pairs--; }
  }
  return { side, remainder: rest };
}

/* ---------- day summary (Today tab) ---------- */

/** Rest = gap between consecutive sets of the day; gaps over 20 min are treated as a break, not rest. */
export function daySummary(daySets, prIds, bodyKg = 0) {
  const sorted = [...daySets].sort(byTs);
  const sum = summarize(sorted, bodyKg);
  const gaps = [];
  for (let i = 1; i < sorted.length; i++) {
    const g = (sorted[i].ts - sorted[i - 1].ts) / 1000;
    if (g > 0 && g <= 1200) gaps.push(g);
  }
  const exercises = new Set(sorted.map(s => s.exId)).size;
  const duration = sorted.length > 1 ? (sorted[sorted.length - 1].ts - sorted[0].ts) / 1000 : null;
  return {
    ...sum, exercises, duration,
    avgRest: gaps.length ? gaps.reduce((a, b) => a + b, 0) / gaps.length : null,
    prs: sorted.filter(s => prIds.has(s.id)).length,
    start: sorted[0]?.ts ?? null, end: sorted[sorted.length - 1]?.ts ?? null,
  };
}

/** "Set Details": consecutive identical sets collapse into "3 sets: 9 rep 105 kg". */
export function collapseSets(sets) {
  const out = [];
  for (const s of [...sets].sort(byTs)) {
    const last = out[out.length - 1];
    if (last && last.reps === s.reps && last.weight === s.weight && !!last.bw === !!s.bw) last.count++;
    else out.push({ reps: s.reps, weight: s.weight, bw: s.bw, count: 1 });
  }
  return out;
}

/* ---------- body / muscles ---------- */

/** red < 24 h, orange < 72 h, green after that, grey if never trained. */
export function recoveryState(lastTs, now = Date.now()) {
  if (!lastTs) return 'none';
  const h = (now - lastTs) / 3600000;
  if (h < 24) return 'fresh';
  if (h < 72) return 'recovering';
  return 'rested';
}

/**
 * Per-muscle last-trained time and hard sets this week (primary muscle counts 1, secondary 0.5,
 * warm-ups excluded). `muscleMap(exId)` returns { primary: [], secondary: [] }.
 */
export function muscleReport(sets, muscleMap, now = Date.now()) {
  const weekAgo = now - 7 * 86400000;
  const out = {};
  const touch = m => (out[m] ??= { last: 0, weekSets: 0 });
  for (const s of sets) {
    const mm = muscleMap(s.exId); if (!mm) continue;
    for (const m of mm.primary) { const o = touch(m); o.last = Math.max(o.last, s.ts); if (s.ts >= weekAgo && s.label !== 'warmup') o.weekSets += 1; }
    for (const m of mm.secondary) { const o = touch(m); o.last = Math.max(o.last, s.ts); if (s.ts >= weekAgo && s.label !== 'warmup') o.weekSets += 0.5; }
  }
  return out;
}

/* ---------- streaks ---------- */

/** Consecutive weeks (Sunday start) that met the weekly goal. The current week only adds once met, and never breaks the streak while in progress. */
export function weeklyStreak(sets, goal, now = Date.now()) {
  const days = new Set(sets.map(s => dayKey(s.ts)));
  const countWeek = ws => { let n = 0; for (let i = 0; i < 7; i++) if (days.has(dayKey(addDays(ws, i)))) n++; return n; };
  const thisWeek = startOfWeek(now);
  const thisCount = countWeek(thisWeek);
  let streak = thisCount >= goal ? 1 : 0;
  for (let ws = addDays(thisWeek, -7); ; ws = addDays(ws, -7)) {
    if (countWeek(ws) >= goal) streak++; else break;
    if (streak > 520) break;
  }
  return { streak, thisWeek: thisCount, goal };
}

/** Training days for a GitHub-style heatmap: weeks x 7, oldest week first. */
export function heatmap(sets, weeks = 16, now = Date.now()) {
  const perDay = new Map();
  for (const s of sets) { const k = dayKey(s.ts); perDay.set(k, (perDay.get(k) || 0) + 1); }
  const start = addDays(startOfWeek(now), -7 * (weeks - 1));
  const grid = [];
  for (let w = 0; w < weeks; w++) {
    const col = [];
    for (let d = 0; d < 7; d++) {
      const ts = addDays(start, w * 7 + d);
      col.push({ ts, count: ts > now ? null : perDay.get(dayKey(ts)) || 0 });
    }
    grid.push(col);
  }
  return grid;
}

export const daysSinceLast = (sets, now = Date.now()) => sets.length ? daysBetween(Math.max(...sets.map(s => s.ts)), now) : null;
