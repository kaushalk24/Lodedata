import test from 'node:test';
import assert from 'node:assert/strict';
import * as store from '../js/store.js';

const fresh = () => store.replaceState(store.defaultState());

test('supersets stay consistent through remove, merge and delete', () => {
  fresh();
  const a = store.addExercise('Tricep Pushdown'), b = store.addExercise('Hammer Curl'), c = store.addExercise('Cable Curl');
  const w = store.addWorkout({ name: 'Arms', exIds: [a.id, b.id, c.id] });
  store.addSuperset(w.id, [a.id, b.id]);
  assert.deepEqual(store.supersetFor(b.id), { wid: w.id, ids: [a.id, b.id] });
  assert.equal(store.supersetFor(c.id), null);
  // Grouping again moves an exercise out of its old group.
  store.addSuperset(w.id, [b.id, c.id]);
  assert.deepEqual(store.workout(w.id).supersets, [[b.id, c.id]]);
  // Removing an exercise from the workout dissolves a 2-exercise group.
  store.toggleInWorkout(w.id, c.id);
  assert.deepEqual(store.workout(w.id).supersets, []);
  store.toggleInWorkout(w.id, c.id);
  store.addSuperset(w.id, [a.id, b.id, c.id]);
  // Merging keeps the group, pointing at the surviving exercise.
  const d = store.addExercise('Hammer curls');
  store.toggleInWorkout(w.id, d.id);
  store.mergeExercise(b.id, a.id);
  assert.deepEqual(store.workout(w.id).supersets, [[a.id, c.id]]);
  // Delete and undo restore the group exactly.
  const undo = store.deleteExercise(c.id);
  assert.deepEqual(store.workout(w.id).supersets, []);
  undo();
  assert.deepEqual(store.workout(w.id).supersets, [[a.id, c.id]]);
  const undoRemove = store.removeSuperset(w.id, 0);
  assert.equal(store.supersetFor(a.id), null);
  undoRemove();
  assert.ok(store.supersetFor(a.id));
});

test('measurements add and delete with undo', () => {
  fresh();
  store.addMeasures({ waist: 82, bodyfat: 18.5 }, 1000);
  assert.equal(store.getState().measures.length, 2);
  const id = store.getState().measures[0].id;
  const undo = store.deleteMeasure(id);
  assert.equal(store.getState().measures.length, 1);
  undo();
  assert.equal(store.getState().measures.length, 2);
});

test('older saved data without the new fields still loads', () => {
  const old = store.defaultState();
  delete old.measures; delete old.settings.rpeOn; delete old.ui.dupIgnore;
  store.replaceState(old);
  assert.deepEqual(store.getState().measures, []);
  assert.equal(store.settings().rpeOn, false);
  assert.deepEqual(store.getState().ui.dupIgnore, []);
});

test('set type follows history until the user picks one', async () => {
  const { kindFor } = await import('../js/screens/common.js');
  fresh();
  const bridge = store.addExercise('Glute Bridge');          // library says bodyweight
  assert.equal(kindFor(bridge), 'bodyweight');
  store.addSet({ exId: bridge.id, reps: 10, weight: 60, bw: false });
  assert.equal(kindFor(bridge), 'weight');                   // but it has always been loaded
  const custom = store.addExercise('Ring thing');            // guessed as weight
  store.addSet({ exId: custom.id, reps: 8, weight: 0, bw: true });
  assert.equal(kindFor(custom), 'bodyweight');               // logged with the old Bodyweight toggle
  store.updateExercise(custom.id, { kind: 'time' });
  assert.equal(kindFor(custom), 'time');                     // an explicit choice always wins
  assert.equal(kindFor(store.addExercise('Plank')), 'time');
});
