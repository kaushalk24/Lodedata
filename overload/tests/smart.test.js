import test from 'node:test';
import assert from 'node:assert/strict';
import {
  typoCheck, normalizeName, sameName, editDistance, findDuplicates, learnedRest, plateauInfo, projectGoal,
  whatToTrain, warmupRamp, pairKey, unsavedSets,
} from '../js/smart.js';

const DAY = 86400000;
const at = (y, m, d, hh = 7, mm = 0, ss = 0) => new Date(y, m - 1, d, hh, mm, ss).getTime();
let n = 0;
const set = (exId, ts, reps, weight, extra = {}) => ({ id: `s${++n}`, exId, ts, reps, weight, label: null, ...extra });

test('typo guard catches a slipped decimal point and extra digits', () => {
  const hist = [1, 2, 3, 4].map(i => set('x', at(2026, 9, i), 8, 27.5));
  assert.deepEqual(typoCheck(hist, { reps: 8, weight: 275 }), { field: 'weight', value: 275, suggest: 27.5, usual: 27.5, heavier: true });
  assert.equal(typoCheck(hist, { reps: 8, weight: 2.75 }).suggest, 27.5);
  assert.equal(typoCheck(hist, { reps: 8, weight: 30 }), null);
  assert.equal(typoCheck(hist, { reps: 8, weight: 22.5 }), null);  // a normal lighter set
  assert.equal(typoCheck(hist, { reps: 12, weight: 5 }), null);     // very light but no slipped digit explains it
  const noFit = typoCheck(hist, { reps: 8, weight: 90 });
  assert.equal(noFit.suggest, null);
  assert.equal(noFit.field, 'weight');
  assert.deepEqual(typoCheck(hist, { reps: 100, weight: 27.5 }), { field: 'reps', value: 100, suggest: 10, usual: 8, heavier: true });
  assert.equal(typoCheck(hist.slice(0, 2), { reps: 8, weight: 275 }), null); // not enough history
  const warm = [...hist, set('x', at(2026, 9, 5), 10, 5, { label: 'warmup' })];
  assert.equal(typoCheck(warm, { reps: 8, weight: 27.5 }), null);
});

test('name normalisation and matching', () => {
  assert.deepEqual(normalizeName('Forearm curls 2'), ['forearm', 'curl']);
  assert.deepEqual(normalizeName('Dumbell Lateral Raises'), ['dumbbell', 'lateral', 'raise']);
  assert.deepEqual(normalizeName('Lat pull-down'), ['lat', 'pulldown']);
  assert.equal(editDistance('traingle', 'triangle'), 1);
  assert.equal(editDistance('baysian', 'bayesian'), 1);
  const yes = [['Forearm curls 1', 'Forearm curls 2'], ['Jm', 'Jm press'], ['Dumbell Lateral Raise', 'Dumbbell Lateral Raise'],
    ['Traingle rows', 'Triangle row'], ['Baysian curl', 'Bayesian Curl'], ['Leg curl', 'Leg Curls'], ['Lat pulldown', 'Lat Pull Down']];
  for (const [a, b] of yes) assert.ok(sameName(a, b), `${a} ~ ${b}`);
  const no = [['Hack Squat', 'Back Squat'], ['Bench Press', 'Incline Bench Press'], ['Lateral Raise', 'Cable Lateral Raise'],
    ['Seated Row', 'Seated Row (Close)'], ['Shoulder Press', 'Shoulder Press (Smith Machine)'], ['Leg Press', 'Leg Extension'],
    ['Chest Press Machine', 'Incline Chest Press'], ['Hammer Curl', 'Preacher Curl']];
  for (const [a, b] of no) assert.ok(!sameName(a, b), `${a} !~ ${b}`);
});

test('duplicate finder keeps the longer history and respects real differences', () => {
  const ex = [
    { id: 'a', name: 'Forearm curls 1', primary: ['forearms'] },
    { id: 'b', name: 'Forearm curls 2', primary: ['forearms'] },
    { id: 'c', name: 'Leg Press', primary: ['quads'] },
    { id: 'd', name: 'Jm', primary: [] },
    { id: 'e', name: 'Jm press', primary: ['triceps'] },
    { id: 'f', name: 'Shoulder press', primary: ['shoulders'] },
    { id: 'g', name: 'Shoulder press machine', primary: ['shoulders'] },
  ];
  const sets = {
    a: [set('a', at(2026, 9, 1), 10, 10), set('a', at(2026, 9, 3), 10, 10)],
    b: [set('b', at(2026, 9, 5), 10, 10)],
    d: [set('d', at(2026, 9, 1), 10, 20)],
    e: [set('e', at(2026, 9, 2), 10, 20), set('e', at(2026, 9, 4), 10, 20)],
    // f and g were both done on two days: clearly different exercises.
    f: [set('f', at(2026, 9, 1), 8, 20), set('f', at(2026, 9, 8), 8, 20)],
    g: [set('g', at(2026, 9, 1), 8, 40), set('g', at(2026, 9, 8), 8, 40)],
  };
  const setsFor = id => sets[id] || [];
  const pairs = findDuplicates(ex, setsFor).map(p => [p.keep.id, p.drop.id]);
  assert.deepEqual(pairs, [['a', 'b'], ['e', 'd']]);
  const ignored = findDuplicates(ex, setsFor, new Set([pairKey('b', 'a')])).map(p => p.keep.id);
  assert.deepEqual(ignored, ['e']);
});

test('learned rest uses back-to-back sets of one exercise only', () => {
  const s = [];
  const day = at(2026, 9, 20, 7);
  // Squat: warm-up, then 6 working sets 3 minutes apart.
  s.push(set('sq', day, 10, 20, { label: 'warmup' }));
  for (let i = 0; i < 6; i++) s.push(set('sq', day + 60000 + i * 180000, 5, 100));
  // Curls interleaved with rows in a superset: no same-exercise neighbours, so nothing learned.
  for (let i = 0; i < 6; i++) { s.push(set('cu', day + 3600000 + i * 120000, 10, 12)); s.push(set('ro', day + 3660000 + i * 120000, 10, 50)); }
  const r = learnedRest(s);
  assert.deepEqual(r.byEx.get('sq'), { sec: 180, n: 5 });
  assert.equal(r.byEx.has('cu'), false);
  assert.equal(r.overall, 180);
  // A 30-minute break is not rest.
  const r2 = learnedRest([...s, set('sq', day + 60000 + 5 * 180000 + 1800000, 5, 100)]);
  assert.equal(r2.byEx.get('sq').n, 5);
});

test('plateau: 4 sessions without a better estimated 1RM over 2+ weeks', () => {
  const s = [];
  const w = [60, 62.5, 65, 65, 65, 62.5, 65, 65];
  w.forEach((kg, i) => s.push(set('b', at(2026, 7, 1) + i * 4 * DAY, 8, kg)));
  const p = plateauInfo(s);
  assert.equal(p.sessions, 5);
  assert.equal(p.deloadKg, 57.5);
  // Still climbing: no plateau.
  const up = [60, 62.5, 65, 67.5, 70, 72.5].map((kg, i) => set('b', at(2026, 7, 1) + i * 4 * DAY, 8, kg));
  assert.equal(plateauInfo(up), null);
  // A rep gained at the same weight is progress.
  const reps = [8, 8, 8, 8, 8, 9].map((r, i) => set('b', at(2026, 7, 1) + i * 4 * DAY, r, 60));
  assert.equal(plateauInfo(reps), null);
  // Stalled but within 2 weeks: too early to call.
  const quick = [60, 65, 65, 65, 65, 65].map((kg, i) => set('b', at(2026, 7, 1) + i * DAY, 8, kg));
  assert.equal(plateauInfo(quick), null);
  // Timed and assisted exercises are skipped.
  assert.equal(plateauInfo(s, { kind: 'time' }), null);
  assert.equal(plateauInfo(s, { kind: 'assisted' }), null);
});

test('goal projection', () => {
  const now = at(2026, 9, 28, 12);
  const sets = [0, 1, 2, 3, 4, 5, 6, 7].map(i => set('b', now - (56 - i * 7) * DAY, 5, 80 + i)); // +1 kg a week
  // Estimated 1RM (Epley, 5 reps) climbs from 93.3 to 101.5 kg, about 1.17 kg a week.
  const g = projectGoal(sets, 120, { now });
  assert.equal(g.status, 'on-track');
  assert.equal(g.current, 101.5);
  assert.ok(Math.abs(g.perWeek - 1.17) < 0.05, `perWeek ${g.perWeek}`);
  const weeks = (g.eta - now) / DAY / 7;
  assert.ok(weeks > 15 && weeks < 17, `weeks ${weeks}`);
  assert.equal(projectGoal(sets, 100, { now }).status, 'reached');
  assert.equal(projectGoal(sets, 500, { now }).status, 'far');
  const flat = [0, 1, 2, 3].map(i => set('b', now - (28 - i * 7) * DAY, 5, 80));
  assert.equal(projectGoal(flat, 100, { now }).status, 'flat');
  assert.equal(projectGoal(sets.slice(-2), 120, { now }).status, 'data');
});

test('what to train today picks rested muscles, oldest first', () => {
  const now = at(2026, 9, 28, 12);
  const ex = { c: { id: 'c', primary: ['chest'] }, b: { id: 'b', primary: ['back'] }, l: { id: 'l', primary: ['quads'] } };
  const workouts = [{ id: 'W1', exIds: ['c'] }, { id: 'W2', exIds: ['b'] }, { id: 'W3', exIds: ['l'] }];
  const last = { c: now - 5 * DAY, b: now - 4 * DAY, l: now - 1 * DAY };
  const muscles = { chest: last.c, back: last.b, quads: last.l };
  const pick = whatToTrain(workouts, id => ex[id], muscles, id => last[id], now);
  assert.equal(pick.workout.id, 'W1');
  // Done today: skipped.
  const today = { ...last, c: now - 3600000 };
  const pick2 = whatToTrain(workouts, id => ex[id], { ...muscles, chest: today.c }, id => today[id], now);
  assert.equal(pick2.workout.id, 'W2');
  // Everything trained in the last day: suggest rest.
  const sore = { c: now - 20 * 3600000, b: now - 26 * 3600000, l: now - 30 * 3600000 };
  const r = whatToTrain(workouts, id => ex[id], { chest: sore.c, back: sore.b, quads: sore.l }, id => sore[id], now);
  assert.equal(r.rest, true);
  assert.equal(whatToTrain([], id => ex[id], {}, () => 0, now), null);
});

test('warm-up ramp', () => {
  assert.deepEqual(warmupRamp(100, { bar: 20, smallestPlate: 1.25 }).map(r => [r.reps, r.kg]), [[10, 20], [5, 40], [5, 60], [3, 80]]);
  assert.deepEqual(warmupRamp(20, { step: 2.5 }).map(r => [r.reps, r.kg]), [[5, 7.5], [5, 12.5], [3, 15]]);
  assert.deepEqual(warmupRamp(30, { bar: 20, smallestPlate: 1.25 }).map(r => [r.reps, r.kg]), [[3, 25]]);
  assert.deepEqual(warmupRamp(0, { step: 2.5 }), []);
  assert.deepEqual(warmupRamp(2.5, { step: 2.5 }), []);
  // Only loads that exist: 1.25 kg plates make 2.5 kg jumps above the bar.
  for (const r of warmupRamp(87.5, { bar: 20, smallestPlate: 1.25 })) assert.equal(((r.kg - 20) * 100) % 250, 0);
});

test('backup reminder: only once unsaved sets are 30 days old', () => {
  const now = at(2026, 9, 29, 12);
  const log = (days, count = 10) => Array.from({ length: count }, (_, i) => set('a', now - days * DAY + i * 60000, 8, 50));
  assert.equal(unsavedSets([], {}, now), 0);
  assert.equal(unsavedSets(log(3), {}, now), 0, 'a new log is not nagged');
  assert.equal(unsavedSets(log(31, 9), {}, now), 0, 'too few sets to matter');
  assert.equal(unsavedSets(log(31), {}, now), 10, 'never backed up, oldest set a month old');
  assert.equal(unsavedSets([...log(31), ...log(1)], {}, now), 20);
  // After a backup only newer sets count, and their own age starts the clock.
  assert.equal(unsavedSets([...log(40), ...log(5)], { backupAt: now - 20 * DAY }, now), 0);
  assert.equal(unsavedSets([...log(40), ...log(31)], { backupAt: now - 35 * DAY }, now), 10);
  // "Not now" hides it until the snooze ends.
  assert.equal(unsavedSets(log(31), { snoozeUntil: now + DAY }, now), 0);
  assert.equal(unsavedSets(log(31), { snoozeUntil: now - 1 }, now), 10);
});
