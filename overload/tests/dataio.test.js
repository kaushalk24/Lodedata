import test from 'node:test';
import assert from 'node:assert/strict';
import { setsToCSV, buildImport, detectMapping, parseDate, demoState } from '../js/dataio.js';
import { defaultState } from '../js/store.js';

test('export then import round-trips and skips duplicates', () => {
  const s = demoState(defaultState(), new Date(2026, 8, 28, 10, 31).getTime());
  assert.ok(s.sets.length > 300);
  const csv = setsToCSV(s);
  const fresh = buildImport(csv, null, { exercises: [], sets: [] });
  assert.equal(fresh.newSets.length, s.sets.length);
  assert.equal(fresh.newExercises.length, s.exercises.length);
  const again = buildImport(csv, null, { exercises: s.exercises, sets: s.sets });
  assert.equal(again.newSets.length, 0);
  assert.equal(again.skipped, s.sets.length);
});

test('detects Strong and Hevy style columns', () => {
  const strong = detectMapping(['Date', 'Workout Name', 'Duration', 'Exercise Name', 'Set Order', 'Weight', 'Reps', 'Distance', 'Seconds', 'Notes']);
  assert.equal(strong.exercise, 3); assert.equal(strong.date, 0); assert.equal(strong.weight, 5); assert.equal(strong.reps, 6); assert.equal(strong.note, 9);
  const hevy = detectMapping(['title', 'start_time', 'end_time', 'description', 'exercise_title', 'superset_id', 'exercise_notes', 'set_index', 'set_type', 'weight_lbs', 'reps']);
  assert.equal(hevy.exercise, 4); assert.equal(hevy.date, 1); assert.equal(hevy.label, 8); assert.equal(hevy.weight, 9); assert.equal(hevy.unitDefault, 'lb');
});

test('imports warm-up labels and pounds', () => {
  const csv = 'exercise_title,start_time,set_type,weight_lbs,reps\nBench Press,2026-09-01 07:00:00,warmup,95,10\nBench Press,2026-09-01 07:04:00,normal,185,5\n';
  const r = buildImport(csv, null, { exercises: [], sets: [] });
  assert.equal(r.newSets.length, 2);
  assert.equal(r.newSets[0].label, 'warmup');
  assert.equal(Math.round(r.newSets[1].weight * 10) / 10, 83.9);
  assert.equal(r.newExercises[0].primary[0], 'chest');
});

test('date parsing', () => {
  const t = (...a) => new Date(...a).getTime();
  assert.equal(parseDate('2026-09-28 10:31:00'), t(2026, 8, 28, 10, 31));
  assert.equal(parseDate('28/09/2026', '10:31'), t(2026, 8, 28, 10, 31));
  assert.equal(parseDate('09/28/2026 10:31 PM', '', true), t(2026, 8, 28, 22, 31));
  assert.equal(parseDate('03/04/2026', '', true), t(2026, 3, 3));
  assert.equal(parseDate('03/04/2026', '', false), t(2026, 2, 4));
});

test('new set fields survive export and import', () => {
  const base = defaultState();
  const st = { ...base, exercises: [{ id: 'p', name: 'Plank' }, { id: 'c', name: "Farmer's Carry" }, { id: 'a', name: 'Assisted Pull-Up' }, { id: 'r', name: 'Single Arm Dumbbell Row' }], sets: [] };
  const t = new Date(2026, 8, 1, 7).getTime();
  st.sets.push({ id: '1', exId: 'p', ts: t, reps: 0, sec: 75, weight: 0, label: null });
  st.sets.push({ id: '2', exId: 'c', ts: t + 60000, reps: 0, dist: 40, weight: 32, label: null });
  st.sets.push({ id: '3', exId: 'a', ts: t + 120000, reps: 8, weight: -20, bw: true, label: null, rpe: 8.5 });
  st.sets.push({ id: '4', exId: 'r', ts: t + 180000, reps: 10, weight: 22.5, side: 'L', label: null });
  st.sets.push({ id: '5', exId: 'r', ts: t + 190000, reps: 10, weight: 22.5, side: 'R', label: null });
  const r = buildImport(setsToCSV(st), null, { exercises: [], sets: [] });
  assert.equal(r.newSets.length, 5);
  const by = n => r.newSets.find(s => r.newExercises.find(e => e.id === s.exId).name === n);
  assert.equal(by('Plank').sec, 75);
  assert.equal(by("Farmer's Carry").dist, 40);
  assert.deepEqual([by('Assisted Pull-Up').weight, by('Assisted Pull-Up').bw, by('Assisted Pull-Up').rpe], [-20, true, 8.5]);
  assert.deepEqual(r.newSets.filter(s => s.side).map(s => s.side), ['L', 'R']);
  const kinds = Object.fromEntries(r.newExercises.map(e => [e.name, e.kind]));
  assert.deepEqual(kinds, { Plank: 'time', "Farmer's Carry": 'distance', 'Assisted Pull-Up': 'assisted', 'Single Arm Dumbbell Row': undefined });
});

test('identical sets in the same minute import as separate sets, once', () => {
  const csv = 'Date,Exercise,Reps,Weight\n2026-09-01 07:00:00,Curl,10,12\n2026-09-01 07:00:00,Curl,10,12\n2026-09-01 07:00:00,Curl,10,12\n';
  const first = buildImport(csv, null, { exercises: [], sets: [] });
  assert.equal(first.newSets.length, 3);
  const again = buildImport(csv, null, { exercises: first.newExercises, sets: first.newSets });
  assert.equal(again.newSets.length, 0);
  assert.equal(again.skipped, 3);
});

test('Strong-style seconds and distance columns', () => {
  const m = detectMapping(['Date', 'Workout Name', 'Duration', 'Exercise Name', 'Set Order', 'Weight', 'Reps', 'Distance', 'Seconds', 'Notes', 'RPE']);
  assert.equal(m.sec, 8);    // not the workout "Duration"
  assert.equal(m.dist, 7);
  assert.equal(m.rpe, 10);
  const hevy = detectMapping(['title', 'start_time', 'exercise_title', 'weight_kg', 'reps', 'distance_km', 'duration_seconds', 'rpe']);
  assert.equal(hevy.sec, 6);
  assert.equal(hevy.distScale, 1000);
});

test('demo data shows off the smart features', async () => {
  const { plateauInfo, findDuplicates } = await import('../js/smart.js');
  const now = new Date(2026, 8, 28, 10, 31).getTime();
  const s = demoState(defaultState(), now);
  const ex = n => s.exercises.find(e => e.name === n);
  const setsFor = id => s.sets.filter(x => x.exId === id);
  assert.ok(plateauInfo(setsFor(ex('Dumbbell Lateral Raise').id)), 'lateral raise should be stalled');
  assert.equal(plateauInfo(setsFor(ex('Lat Pulldown').id)), null);
  const dups = findDuplicates(s.exercises, setsFor).map(p => [p.keep.name, p.drop.name]);
  assert.deepEqual(dups, [['Seated Calf Raise', 'Seated calf raises']]);
  assert.ok(setsFor(ex('Plank').id).every(x => x.sec > 0 && x.reps === 0));
  assert.ok(setsFor(ex("Farmer's Carry").id).every(x => x.dist === 40));
  const row = setsFor(ex('Single Arm Dumbbell Row').id).filter(x => x.label !== 'warmup');
  assert.equal(row.filter(x => x.side === 'L').length, row.filter(x => x.side === 'R').length);
  assert.equal(s.workouts.find(w => w.name === 'Arms').supersets.length, 1);
  assert.ok(s.measures.length >= 16);
  assert.ok([...s.measures, ...s.body, ...s.sets].every(x => x.ts <= now), 'nothing in the future');
  const early = demoState(defaultState(), new Date(2026, 8, 28, 5, 10).getTime());
  assert.ok([...early.measures, ...early.body, ...early.sets].every(x => x.ts <= new Date(2026, 8, 28, 5, 10).getTime()), 'nothing in the future at 5 am');
});
