// Run: cd overload && npm test   (or `node --test` from the repo root)
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  compareToPrevious, recordRanges, prSetIds, wouldBePR, e1rm, platesPerSide, suggestTarget,
  daySummary, collapseSets, weeklyStreak, recoveryState, muscleReport, bestEfforts, groupByDay, summarize,
} from '../js/stats.js';

const at = (y, m, d, hh = 7, mm = 0) => new Date(y, m - 1, d, hh, mm).getTime();
let n = 0;
const set = (ts, reps, weight, extra = {}) => ({ id: `s${++n}`, exId: 'x', ts, reps, weight, label: null, ...extra });

test('compared-to-previous matches the Shoulder Press card in the recording', () => {
  // Thursday 24 Sep 2026 vs Saturday 19 Sep 2026
  const sets = [
    set(at(2026, 9, 19, 7, 16), 10, 5, { label: 'warmup' }), set(at(2026, 9, 19, 7, 16), 8, 27.5), set(at(2026, 9, 19, 7, 22), 7, 27.5),
    set(at(2026, 9, 24, 6, 59), 12, 7.5, { label: 'warmup' }), set(at(2026, 9, 24, 7, 4), 6.5, 27.5), set(at(2026, 9, 24, 7, 10), 6.5, 27.5),
  ];
  const c = compareToPrevious(sets);
  assert.equal(c.cur.sets, 3); assert.equal(c.sets.diff, 0); assert.equal(c.sets.pct, 0);
  assert.equal(c.cur.reps, 25); assert.equal(c.reps.diff, 0);
  assert.equal(c.cur.volume, 447.5); assert.equal(c.volume.diff, -15); assert.equal(c.volume.pct, -3.2);
  assert.equal(c.cur.perRep, 17.9); assert.equal(c.perRep.diff, -0.6); assert.equal(c.perRep.pct, -3.2);
});

test('records table merges rep counts into ranges like 1-6 / 7-9 / 10-14 / 15-16', () => {
  const sets = [set(at(2026, 3, 22), 6, 95), set(at(2026, 3, 1), 9, 85), set(at(2026, 2, 1), 14, 35), set(at(2026, 3, 10), 16, 7.5), set(at(2026, 1, 5), 5, 60)];
  const r = recordRanges(sets).map(x => [x.from, x.to, x.weight]);
  assert.deepEqual(r, [[1, 6, 95], [7, 9, 85], [10, 14, 35], [15, 16, 7.5]]);
});

test('PRs: nothing on day one, heavier-for-reps later, first time at a new rep count', () => {
  const a = set(at(2026, 1, 1), 8, 20), b = set(at(2026, 1, 1, 7, 5), 8, 25);
  const c = set(at(2026, 1, 3), 8, 25);        // ties, not a PR
  const d = set(at(2026, 1, 5), 6, 30);        // heavier than anything for >= 6 reps
  const e = set(at(2026, 1, 7), 16, 7.5);      // first ever 16-rep set
  const f = set(at(2026, 1, 9), 5, 28);        // lighter than 6x30, so not a PR
  const ids = prSetIds([a, b, c, d, e, f]);
  assert.deepEqual([...ids].sort(), [d.id, e.id].sort());
  assert.equal(wouldBePR([a, b, c, d, e, f], { reps: 6, weight: 30.5 }), true);
  assert.equal(wouldBePR([a, b, c, d, e, f], { reps: 6, weight: 30 }), false);
});

test('bodyweight PRs count reps', () => {
  const s1 = set(at(2026, 1, 1), 8, 0), s2 = set(at(2026, 1, 3), 10, 0), s3 = set(at(2026, 1, 5), 9, 0);
  assert.deepEqual([...prSetIds([s1, s2, s3])], [s2.id]);
});

test('1RM formulas', () => {
  assert.equal(Math.round(e1rm(100, 5) * 100) / 100, 116.67);
  assert.equal(e1rm(100, 1), 100);
  assert.equal(Math.round(e1rm(100, 5, 'brzycki') * 10) / 10, 112.5);
});

test('plates per side uses what the gym has', () => {
  const plates = { 25: 30, 20: 30, 15: 30, 10: 30, 5: 30, 2.5: 30 };
  assert.deepEqual(platesPerSide(100, 20, plates), { side: [25, 15], remainder: 0 });
  assert.deepEqual(platesPerSide(62.5, 20, plates).side, [20]);
  assert.equal(platesPerSide(62.5, 20, plates).remainder, 1.25);
  assert.deepEqual(platesPerSide(70, 20, { 25: 1, 10: 4 }).side, [10, 10]); // a single 25 can't be paired
});

test('double progression target', () => {
  const prev = [set(1, 10, 10, { label: 'warmup' }), set(2, 9, 25), set(3, 8, 25)];
  assert.deepEqual(pick(suggestTarget(prev, 0)), { reps: 10, weight: 25, why: 'rep' });
  assert.deepEqual(pick(suggestTarget(prev, 1)), { reps: 9, weight: 25, why: 'rep' });
  assert.deepEqual(pick(suggestTarget(prev, 5)), { reps: 9, weight: 25, why: 'rep' });
  assert.deepEqual(pick(suggestTarget([set(1, 12, 25)], 0)), { reps: 8, weight: 27.5, why: 'weight' });
  assert.equal(suggestTarget([set(1, 10, 5, { label: 'warmup' })], 0), null);
});
const pick = t => ({ reps: t.reps, weight: t.weight, why: t.why });

test('day summary: rest excludes long breaks, collapse identical sets', () => {
  const s = [set(at(2026, 9, 28, 7, 0), 9, 105), set(at(2026, 9, 28, 7, 3), 9, 105), set(at(2026, 9, 28, 7, 7), 9, 105), set(at(2026, 9, 28, 8, 0), 7, 105)];
  const d = daySummary(s, new Set([s[3].id]));
  assert.equal(d.sets, 4); assert.equal(d.reps, 34); assert.equal(d.avgRest, 210); assert.equal(d.prs, 1);
  assert.equal(d.duration, 3600);
  assert.deepEqual(collapseSets(s).map(x => [x.count, x.reps, x.weight]), [[3, 9, 105], [1, 7, 105]]);
});

test('weekly streak counts weeks that met the goal', () => {
  const now = at(2026, 9, 28, 12); // Monday; week started Sunday 27th
  const days = [[9, 27], [9, 22], [9, 24], [9, 25], [9, 14], [9, 16], [9, 18], [9, 9]];
  const s = days.map(([m, d]) => set(at(2026, m, d), 8, 20));
  const r = weeklyStreak(s, 3, now);
  assert.equal(r.thisWeek, 1);
  assert.equal(r.streak, 2); // weeks of 20 and 13 Sep met 3; week of 6 Sep did not
});

test('recovery colours and weekly muscle sets', () => {
  const now = at(2026, 9, 28, 12);
  assert.equal(recoveryState(now - 3 * 3600e3, now), 'fresh');
  assert.equal(recoveryState(now - 30 * 3600e3, now), 'recovering');
  assert.equal(recoveryState(now - 100 * 3600e3, now), 'rested');
  assert.equal(recoveryState(0, now), 'none');
  const rep = muscleReport([set(now - 3600e3, 8, 20), set(now - 3600e3, 8, 20, { label: 'warmup' })], () => ({ primary: ['chest'], secondary: ['triceps'] }), now);
  assert.equal(rep.chest.weekSets, 1); assert.equal(rep.triceps.weekSets, 0.5);
});

test('best efforts and grouping', () => {
  const s = [set(at(2026, 1, 1), 10, 50), set(at(2026, 1, 1, 8), 5, 100), set(at(2026, 1, 2), 12, 40)];
  const b = bestEfforts(s);
  assert.equal(b.setVolume.value, 500); assert.equal(b.sessionVolume.value, 1000); assert.equal(b.maxWeight.value, 100);
  const g = groupByDay(s);
  assert.equal(g.length, 2); assert.equal(g[0].sets[0].reps, 12); assert.equal(g[1].sets[0].reps, 10);
});

test('records for assisted, timed and distance sets', () => {
  // Assisted: less help is progress. Weight is stored as -assistance with bw=true.
  const a1 = set(at(2026, 1, 1), 8, -30, { bw: true }), a2 = set(at(2026, 1, 3), 8, -20, { bw: true }), a3 = set(at(2026, 1, 5), 8, -25, { bw: true });
  assert.deepEqual([...prSetIds([a1, a2, a3], 75, 'assisted')], [a2.id]);
  assert.equal(wouldBePR([a1, a2], { reps: 8, weight: -15, bw: true }, 75, 'assisted'), true);
  // Volume never goes negative when bodyweight is unknown.
  assert.equal(summarize([a1], 0).volume, 0);
  assert.equal(summarize([a1], 80).volume, 400);
  // Timed: longer holds are records; reps are 0.
  const t1 = set(at(2026, 1, 1), 0, 0, { sec: 60 }), t2 = set(at(2026, 1, 3), 0, 0, { sec: 75 }), t3 = set(at(2026, 1, 5), 0, 0, { sec: 70 });
  assert.deepEqual([...prSetIds([t1, t2, t3], 0, 'time')], [t2.id]);
  assert.equal(summarize([t1, t2]).sec, 135);
  // Distance with load: farther at the same weight, or heavier at the same distance.
  const d1 = set(at(2026, 1, 1), 0, 30, { dist: 40 }), d2 = set(at(2026, 1, 3), 0, 32, { dist: 40 }), d3 = set(at(2026, 1, 5), 0, 30, { dist: 50 });
  assert.deepEqual([...prSetIds([d1, d2, d3], 0, 'distance')].sort(), [d2.id, d3.id].sort());
});

test('RPE and failure shape the target', () => {
  const easy = [set(1, 10, 50, { rpe: 7 })];
  assert.deepEqual(pick(suggestTarget(easy, 0)), { reps: 10, weight: 52.5, why: 'easy' });
  const hard = [set(1, 10, 50, { rpe: 10 })];
  assert.deepEqual(pick(suggestTarget(hard, 0)), { reps: 10, weight: 50, why: 'hard' });
  const failed = [set(1, 9, 50, { label: 'failure' })];
  assert.deepEqual(pick(suggestTarget(failed, 0)), { reps: 9, weight: 50, why: 'hard' });
  const mid = [set(1, 9, 50, { rpe: 8 })];
  assert.deepEqual(pick(suggestTarget(mid, 0)), { reps: 10, weight: 50, why: 'rep' });
  // Easy but below the rep range: add reps first.
  assert.deepEqual(pick(suggestTarget([set(1, 6, 50, { rpe: 6 })], 0)), { reps: 7, weight: 50, why: 'rep' });
});

test('collapse keeps timed, distance and sides apart', () => {
  const s1 = set(1, 0, 0, { sec: 60 }), s2 = set(2, 0, 0, { sec: 60 }), s3 = set(3, 0, 0, { sec: 45 });
  assert.deepEqual(collapseSets([s1, s2, s3]).map(x => [x.count, x.sec]), [[2, 60], [1, 45]]);
  const l = set(4, 10, 12, { side: 'L' }), r = set(5, 10, 12, { side: 'R' });
  assert.equal(collapseSets([l, r]).length, 2);
});
