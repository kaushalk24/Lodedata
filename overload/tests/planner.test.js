import test from 'node:test';
import assert from 'node:assert/strict';
import { generatePlan } from '../js/planner.js';
import { libByName } from '../js/library.js';

test('split follows days per week and level', () => {
  assert.deepEqual(generatePlan({ days: 3, level: 'beginner' }).days.map(d => d.name), ['Full Body A', 'Full Body B', 'Full Body C']);
  assert.deepEqual(generatePlan({ days: 3, level: 'intermediate' }).days.map(d => d.name), ['Push', 'Pull', 'Legs']);
  assert.deepEqual(generatePlan({ days: 6, level: 'intermediate' }).days.map(d => d.name), ['Push 1', 'Pull 1', 'Legs 1', 'Push 2', 'Pull 2', 'Legs 2']);
});

test('every planned exercise exists in the library, for every equipment option', () => {
  for (const equipment of ['gym', 'dumbbells', 'bodyweight']) {
    for (const goal of ['physique', 'strength', 'athletic', 'general']) {
      for (let days = 2; days <= 6; days++) {
        for (const level of ['beginner', 'intermediate']) {
          const plan = generatePlan({ goal, days, equipment, level });
          for (const d of plan.days) {
            assert.ok(d.exercises.length >= 3, `${goal}/${equipment}/${days}: ${d.name} too short`);
            assert.equal(new Set(d.exercises.map(e => e.name)).size, d.exercises.length);
            for (const e of d.exercises) assert.ok(libByName(e.name), `missing library entry: ${e.name}`);
          }
        }
      }
    }
  }
});

test('strength plans put heavy low-rep work first', () => {
  const d = generatePlan({ goal: 'strength', days: 4, level: 'intermediate' }).days[0];
  assert.deepEqual([d.exercises[0].sets, d.exercises[0].reps, d.exercises[0].rest], [5, '3-5', 180]);
});
