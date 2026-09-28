import test from 'node:test';
import assert from 'node:assert/strict';
import { parseLog, wordsToDigits } from '../js/parse.js';

const ctx = { fallbackKg: 20, fallbackReps: 8, last: { reps: 8, weight: 20 } };
const p = (text, o = {}) => parseLog(text, { ...ctx, ...o });
const rw = text => p(text).sets.map(s => [s.reps, s.weight]);

test('common gym shorthand', () => {
  assert.deepEqual(rw('8 at 60'), [[8, 60]]);
  assert.deepEqual(rw('8 @ 60'), [[8, 60]]);
  assert.deepEqual(rw('60 for 8'), [[8, 60]]);
  assert.deepEqual(rw('3x10 25'), [[10, 25], [10, 25], [10, 25]]);
  assert.deepEqual(rw('3x8@135'), [[8, 135], [8, 135], [8, 135]]);
  assert.deepEqual(rw('185x5x3'), [[5, 185], [5, 185], [5, 185]]);
  assert.deepEqual(rw('3x10x25'), [[10, 25], [10, 25], [10, 25]]);
  assert.deepEqual(rw('3 sets of 10 at 25'), [[10, 25], [10, 25], [10, 25]]);
  assert.deepEqual(rw('3 times 12 at 40'), [[12, 40], [12, 40], [12, 40]]);
  assert.deepEqual(rw('10 reps at 25 kg'), [[10, 25]]);
  assert.deepEqual(rw('60x8'), [[8, 60]]);
  assert.deepEqual(rw('8x60'), [[8, 60]]);
  assert.deepEqual(rw('8 60'), [[8, 60]]);
});

test('lists and weight carried between sets', () => {
  assert.deepEqual(rw('10, 9, 8 at 25'), [[10, 25], [9, 25], [8, 25]]);
  assert.deepEqual(rw('10 9 8 @ 25'), [[10, 25], [9, 25], [8, 25]]);
  assert.deepEqual(rw('8 at 60, 7'), [[8, 60], [7, 60]]);
  assert.deepEqual(rw('8 at 60 and 7 at 55'), [[8, 60], [7, 55]]);
  assert.deepEqual(rw('8 at 60 then 6 at 70'), [[8, 60], [6, 70]]);
});

test('fills in what the phrase leaves out from the sheet', () => {
  assert.deepEqual(rw('12'), [[12, 20]]);
  assert.deepEqual(rw('3x10'), [[10, 20], [10, 20], [10, 20]]);
  assert.deepEqual(rw('62.5 kg'), [[8, 62.5]]);
});

test('spoken numbers from dictation', () => {
  assert.deepEqual(rw('eight at sixty kilos'), [[8, 60]]);
  assert.deepEqual(rw('one hundred and forty for five'), [[5, 140]]);
  assert.deepEqual(rw('twenty two point five for 10'), [[10, 22.5]]);
  assert.deepEqual(rw('seven and a half at 25'), [[7.5, 25]]);
  assert.equal(wordsToDigits('eight nine ten'), '8 9 10');
  assert.equal(wordsToDigits('one arm row'), 'one arm row');
});

test('units, decimal commas and bodyweight', () => {
  assert.equal(Math.round(p('135 lbs for 5').sets[0].weight * 100) / 100, 61.24);
  assert.equal(Math.round(p('10 at 25', { unit: 'lb' }).sets[0].weight * 100) / 100, 11.34);
  assert.deepEqual(rw('27,5 for 8'), [[8, 27.5]]);
  assert.deepEqual(rw('10,9,8 at 25'), [[10, 25], [9, 25], [8, 25]]);
  assert.deepEqual(rw('bw for 12'), [[12, 0]]);
});

test('labels, RPE and sides', () => {
  const a = p('warm up 10 at 20').sets[0];
  assert.equal(a.label, 'warmup');
  assert.equal(p('8 at 60 to failure').sets[0].label, 'failure');
  assert.equal(p('8 at 60 rpe 8.5').sets[0].rpe, 8.5);
  assert.equal(p('8 at 60 rpe 4').sets[0].rpe, undefined);
  assert.equal(p('left 10 at 12').sets[0].side, 'L');
  assert.equal(p('10 at 12 right side').sets[0].side, 'R');
});

test('same again repeats the last set', () => {
  assert.deepEqual(rw('same again'), [[8, 20]]);
  assert.deepEqual(rw('Same'), [[8, 20]]);
  assert.equal(p('same again to failure').sets[0].label, 'failure');
  // One-sided exercises alternate, so the side is not copied from the last set.
  assert.equal(parseLog('same again', { last: { reps: 10, weight: 12, side: 'L' } }).sets[0].side, undefined);
  assert.equal(parseLog('same again right', { last: { reps: 10, weight: 12, side: 'L' } }).sets[0].side, 'R');
  assert.match(parseLog('same again').error, /no earlier set/);
});

test('timed and distance exercises', () => {
  const t = (text, kind) => parseLog(text, { kind, fallbackKg: 0 }).sets.map(s => [s.sec ?? s.dist, s.weight]);
  assert.deepEqual(t('60', 'time'), [[60, 0]]);
  assert.deepEqual(t('1:30', 'time'), [[90, 0]]);
  assert.deepEqual(t('2 min', 'time'), [[120, 0]]);
  assert.deepEqual(t('3x45s at 10', 'time'), [[45, 10], [45, 10], [45, 10]]);
  assert.deepEqual(t('40m at 32', 'distance'), [[40, 32]]);
  assert.deepEqual(t('3x40 at 30', 'distance'), [[40, 30], [40, 30], [40, 30]]);
  assert.equal(parseLog('60', { kind: 'time' }).sets[0].reps, 0);
});

test('rejects nonsense with a helpful message', () => {
  assert.match(p('hello').error, /Couldn't read that/);
  assert.equal(p('').error, null);
  assert.deepEqual(p('').sets, []);
  assert.match(p('500 at 20').error, /reps doesn't look right/);
  assert.match(p('25x10x25').error || '', /more than 20 sets|reps/);
  assert.match(p('10 at 2000').error, /out of range/);
});
