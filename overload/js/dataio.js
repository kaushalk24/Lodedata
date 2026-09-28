/* Getting data in and out: CSV export, CSV import from other apps (column auto-detection),
 * and a realistic demo history. Pure functions over plain objects so they are unit-tested. */

import { uid, norm, dayKey, csvCell, parseCSV, fromDisplay, toDisplay, round, startOfDay, addDays } from './util.js';
import { guessMuscles, libByName } from './library.js';

/* ---------- export ---------- */
export function setsToCSV(state) {
  const unit = state.settings.unit;
  const exName = Object.fromEntries(state.exercises.map(e => [e.id, e.name]));
  const gymName = Object.fromEntries(state.gyms.map(g => [g.id, g.name]));
  const rows = [['Date', 'Time', 'Exercise', 'Reps', 'Weight', 'Unit', 'Label', 'Note', 'Gym', 'Bodyweight']];
  for (const s of [...state.sets].sort((a, b) => a.ts - b.ts)) {
    const d = new Date(s.ts);
    rows.push([dayKey(s.ts), `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`,
      exName[s.exId] || '', s.reps, round(toDisplay(s.weight, unit), 2), unit, s.label || '', s.note || '', gymName[s.gymId] || '', s.bw ? 'yes' : '']);
  }
  return rows.map(r => r.map(csvCell).join(',')).join('\n');
}

/* ---------- import ---------- */
const FIELDS = {
  exercise: [/^exercise( name)?$/, /exercise/, /movement|lift/, /^name$|title/],
  date: [/^date$/, /start.?time|timestamp|datetime/, /date/, /^day$/],
  time: [/^time$/, /clock/],
  reps: [/^reps?$/, /repetitions|reps/],
  weight: [/^weight$/, /weight|load/, /^kg$|^lbs?$/],
  unit: [/^unit|units$/],
  note: [/^notes?$/, /note|comment/],
  label: [/set.?type|^type$|^label$/, /warm/],
};

/** Best guess of which column holds each field. Returns { field: columnIndex | -1 }. */
export function detectMapping(header) {
  const h = header.map(c => norm(c).replace(/ /g, ' '));
  const used = new Set(), map = {};
  for (const [field, patterns] of Object.entries(FIELDS)) {
    map[field] = -1;
    for (const re of patterns) {
      const i = h.findIndex((c, idx) => !used.has(idx) && re.test(c));
      if (i >= 0) { map[field] = i; used.add(i); break; }
    }
  }
  // "exercise_title" / "Exercise Name" must win over a workout "title" column.
  const lbHeader = map.weight >= 0 && /lb/.test(h[map.weight]);
  return { ...map, unitDefault: lbHeader ? 'lb' : 'kg', dayFirst: true };
}

/** Parse "2025-06-22 07:04:00", "22/06/2025 7:04", "Jun 22, 2025, 7:04 AM"... */
export function parseDate(dateStr, timeStr = '', dayFirst = true) {
  let s = String(dateStr || '').trim();
  if (!s) return NaN;
  if (timeStr) s += ' ' + String(timeStr).trim();
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
  if (m) return new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0)).getTime();
  m = s.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})(?:,?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?)?/);
  if (m) {
    let a = +m[1], b = +m[2], y = +m[3];
    if (y < 100) y += 2000;
    if (a > 12) dayFirst = true; else if (b > 12) dayFirst = false;
    const [d, mo] = dayFirst ? [a, b] : [b, a];
    let hh = +(m[4] || 0);
    if (m[7]) { const pm = /p/i.test(m[7]); if (pm && hh < 12) hh += 12; if (!pm && hh === 12) hh = 0; }
    return new Date(y, mo - 1, d, hh, +(m[5] || 0), +(m[6] || 0)).getTime();
  }
  const t = Date.parse(s.replace(/,(?=\s*\d{1,2}:)/, ''));
  return Number.isNaN(t) ? Date.parse(s) : t;
}

const LABELS = [[/warm/, 'warmup'], [/drop/, 'drop'], [/fail/, 'failure'], [/amrap/, 'amrap']];
const toNum = v => { const n = parseFloat(String(v ?? '').replace(',', '.').replace(/[^\d.-]/g, '')); return Number.isFinite(n) ? n : NaN; };

/**
 * Turn CSV rows into new exercises and sets. Existing exercises are matched by name, and a set
 * already present (same exercise, minute, reps and weight) is skipped so re-importing is safe.
 */
export function buildImport(text, mapping, existing, { gymId = null } = {}) {
  const rows = parseCSV(text);
  const header = rows.shift() || [];
  const m = mapping || detectMapping(header);
  const byName = new Map(existing.exercises.map(e => [norm(e.name), e]));
  const seen = new Set(existing.sets.map(s => `${s.exId}|${Math.floor(s.ts / 60000)}|${s.reps}|${round(s.weight, 2)}`));
  const newExercises = [], newSets = [];
  let skipped = 0, bad = 0;
  const get = (r, f) => m[f] >= 0 ? (r[m[f]] ?? '').trim() : '';
  rows.forEach(r => {
    const name = get(r, 'exercise');
    const reps = toNum(get(r, 'reps'));
    const ts = parseDate(get(r, 'date'), m.time >= 0 ? get(r, 'time') : '', m.dayFirst);
    if (!name || !(reps > 0) || !Number.isFinite(ts)) { bad++; return; }
    let w = toNum(get(r, 'weight')); if (!Number.isFinite(w)) w = 0;
    const unitCell = get(r, 'unit').toLowerCase();
    const unit = /lb/.test(unitCell) ? 'lb' : /kg/.test(unitCell) ? 'kg' : m.unitDefault;
    const weight = round(fromDisplay(w, unit), 4);
    let ex = byName.get(norm(name));
    if (!ex) {
      const lib = libByName(name), g = lib ? lib : guessMuscles(name);
      ex = { id: uid(), name, libId: lib?.id || null, primary: [...g.primary], secondary: [...g.secondary], equipment: g.equipment, note: '', restSec: null, created: ts };
      byName.set(norm(name), ex); newExercises.push(ex);
    }
    const key = `${ex.id}|${Math.floor(ts / 60000)}|${reps}|${round(weight, 2)}`;
    if (seen.has(key)) { skipped++; return; }
    seen.add(key);
    const labelCell = get(r, 'label').toLowerCase();
    const label = LABELS.find(([re]) => re.test(labelCell))?.[1] || null;
    newSets.push({ id: uid(), exId: ex.id, ts, reps, weight, label, note: get(r, 'note'), gymId, bw: false });
  });
  return { newExercises, newSets, skipped, bad, header, mapping: m };
}

/* ---------- demo data ---------- */
function rng(seed) { return () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }; }

const DEMO = {
  'Chest shoulders': { color: 'green', ex: [['Shoulder Press', 22.5, 'machine'], ['Dumbbell Lateral Raise', 7.5], ['Incline Dumbbell Bench Press', 20], ['Machine Pec Fly', 40], ['Chest Press Machine', 45], ['Cable Lateral Raises', 5]] },
  Back: { color: 'blue', ex: [['Lat Pulldown', 55], ['Seated Row (Close)', 60], ['Rear Delt Fly Machine', 35], ['Straight Arm Pulldown', 25], ['Pull-Up', 0]] },
  Legs: { color: 'orange', ex: [['Leg Press', 120], ['Lying Leg Curl', 35], ['Leg Extension', 45], ['Hack Squat', 60], ['Seated Calf Raise', 40]] },
  Arms: { color: 'purple', ex: [['Overhead Triceps Extension (Rope)', 20], ['Dumbbell Bicep Curl', 12], ['Tricep Pushdown', 25], ['Hammer Curl', 14], ['Machine Preacher Curl', 25]] },
};
const NOTES = ['Seat 4, pin 3', 'Drop set', 'Slow eccentric', 'Felt strong', 'Grip slipping', 'Standing', 'Paused reps'];

/** ~16 weeks of believable history ending with a Back + shoulders session a few hours before `now`. */
export function demoState(base, now = Date.now()) {
  const r = rng(42);
  const pick = a => a[Math.floor(r() * a.length)];
  const s = JSON.parse(JSON.stringify(base));
  s.gyms = [
    { id: 'gym-a', name: 'Cult Rajajinagar', bar: 20, plates: { 25: 20, 20: 20, 15: 20, 10: 30, 5: 30, 2.5: 30, 1.25: 10 } },
    { id: 'gym-b', name: 'Cult Vijayanagar', bar: 20, plates: { 20: 20, 15: 20, 10: 20, 5: 20, 2.5: 20 } },
  ];
  s.settings.gymId = 'gym-a';
  s.exercises = []; s.workouts = []; s.sets = []; s.sessions = []; s.body = [];
  const exByName = {};
  for (const [wname, def] of Object.entries(DEMO)) {
    const ids = def.ex.map(([name, , eq]) => {
      const lib = libByName(name), g = lib || guessMuscles(name);
      const ex = { id: uid(), name, libId: lib?.id || null, primary: [...g.primary], secondary: [...g.secondary], equipment: eq || g.equipment, note: '', restSec: null, created: now - 200 * 864e5 };
      s.exercises.push(ex); exByName[name] = { ex, base: def.ex.find(d => d[0] === name)[1] };
      return ex.id;
    });
    s.workouts.push({ id: uid(), name: wname, desc: '', color: def.color, group: '', exIds: ids, created: now - 200 * 864e5 });
  }
  exByName['Shoulder Press'].ex.note = 'Seat 3 · back pad upright';
  exByName['Leg Press'].ex.note = 'Sled position 2, feet high and wide';

  const order = ['Chest shoulders', 'Back', 'Legs', 'Arms'];
  const roundW = w => w < 10 ? Math.round(w * 2) / 2 : Math.round(w / 2.5) * 2.5;
  let cycle = 0;
  const today = startOfDay(now);
  const logSession = (dayTs, folder, weekIdx, startMin, only) => {
    let t = dayTs + startMin * 60000;
    const names = only || DEMO[folder].ex.map(e => e[0]).filter(() => r() > 0.25).slice(0, 5);
    const gymId = r() > 0.8 ? 'gym-b' : 'gym-a';
    for (const name of names) {
      const { ex, base } = exByName[name];
      const work = roundW(base * (1 + 0.011 * weekIdx + (r() - 0.5) * 0.04));
      const sets = [];
      if (work > 0) sets.push({ reps: 10 + Math.floor(r() * 3), weight: roundW(work * 0.45), label: 'warmup' });
      let reps = 8 + Math.floor(r() * 5);
      const n = 2 + (r() > 0.5 ? 1 : 0);
      for (let i = 0; i < n; i++) {
        sets.push({ reps: work === 0 ? reps + 2 : reps, weight: work, label: i === n - 1 && r() > 0.85 ? 'failure' : null });
        reps = Math.max(4, reps - Math.floor(r() * 2.2) - (r() > 0.85 ? 0.5 : 0));
      }
      if (r() > 0.9) sets.push({ reps: 10, weight: roundW(work * 0.6), label: 'drop' });
      for (const x of sets) {
        s.sets.push({ id: uid(), exId: ex.id, ts: t, reps: x.reps, weight: x.weight, label: x.label, note: r() > 0.93 ? pick(NOTES) : '', gymId, bw: work === 0 });
        t += (100 + Math.floor(r() * 110)) * 1000;
      }
      t += (60 + Math.floor(r() * 120)) * 1000;
    }
  };
  // History: four sessions a week, rotating through the split, finishing two days ago.
  const weeks = 16;
  for (let d = weeks * 7; d >= 2; d--) {
    const dayTs = addDays(today, -d), dow = new Date(dayTs).getDay();
    if (![1, 2, 4, 6].includes(dow) || r() < 0.12) continue;
    logSession(dayTs, order[cycle++ % 4], weeks - Math.floor(d / 7), 380 + Math.floor(r() * 120));
  }
  // Yesterday legs, today back + shoulder press (mirrors a real split day).
  logSession(addDays(today, -1), 'Legs', weeks, 400, ['Leg Press', 'Lying Leg Curl', 'Leg Extension', 'Seated Calf Raise']);
  const todayStart = Math.max(0, Math.min(Math.floor((now - today) / 60000) - 150, 420));
  logSession(today, 'Back', weeks, todayStart, ['Seated Row (Close)', 'Lat Pulldown', 'Rear Delt Fly Machine']);
  logSession(today, 'Chest shoulders', weeks, todayStart + 38, ['Shoulder Press']);
  s.sets = s.sets.filter(x => x.ts <= now);

  for (let w = weeks; w >= 0; w--) s.body.push({ id: uid(), ts: addDays(today, -w * 7) + 7 * 3600000, kg: round(74.8 - w * 0.12 + (r() - 0.5) * 0.6, 1) });
  for (let w = 1; w <= 6; w++) {
    const st = addDays(today, -w * 7 + 2) + 17 * 3600000;
    s.sessions.push({ id: uid(), activity: 'Tennis', start: st, end: st + (60 + Math.floor(r() * 40)) * 60000 });
  }
  const run = addDays(today, -3) + 6.5 * 3600000;
  s.sessions.push({ id: uid(), activity: 'Running', start: run, end: run + 31 * 60000 });
  s.ui.demo = true;
  return s;
}
