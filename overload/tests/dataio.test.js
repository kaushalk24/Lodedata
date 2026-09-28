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
