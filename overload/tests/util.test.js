import test from 'node:test';
import assert from 'node:assert/strict';
import { relTime, dayHeader, fmtNum, fmtDuration, matches, parseCSV, html, raw, fmtW } from '../js/util.js';
import { guessMuscles } from '../js/library.js';

const now = new Date(2026, 8, 28, 10, 31).getTime(); // Mon 28 Sep 2026, 10:31
const ago = (d, h = 0, m = 0) => now - ((d * 24 + h) * 60 + m) * 60000;

test('relative times match the exercise list', () => {
  assert.equal(relTime(now - 11000, now), '11 secs ago');
  assert.equal(relTime(now - 400, now), '1 sec ago');
  assert.equal(relTime(ago(0, 3), now), '3h ago');
  assert.equal(relTime(ago(1), now), 'Yesterday');
  assert.equal(relTime(ago(2), now), '2d ago');
  assert.equal(relTime(ago(8), now), '1w ago');
  assert.equal(relTime(ago(40), now), '1mo ago');
  assert.equal(relTime(ago(335), now), '11mo ago');
  assert.equal(relTime(new Date(2025, 8, 17).getTime(), now), '17/09/25');
  assert.equal(relTime(0, now), '');
});

test('day headers', () => {
  assert.equal(dayHeader(ago(0, 1), now), 'Today');
  assert.equal(dayHeader(ago(4), now), 'Thursday');
  assert.equal(dayHeader(new Date(2026, 8, 19, 7).getTime(), now), 'Sat, 19 Sep 2026');
});

test('number and duration formatting', () => {
  assert.equal(fmtNum(5080.75), '5,080.75');
  assert.equal(fmtNum(27.5), '27.5');
  assert.equal(fmtDuration(322), '5m 22s');
  assert.equal(fmtDuration(3900), '1h 5m');
  assert.equal(fmtW(25, 'lb'), '55.1');
});

test('search matches word prefixes', () => {
  assert.ok(matches('Incline Dumbbell Bench Press', 'inc dumb'));
  assert.ok(matches('Cable Chest Fly (High To Low)', 'chest'));
  assert.ok(!matches('Leg Press', 'chest'));
});

test('csv parsing handles quotes and commas', () => {
  assert.deepEqual(parseCSV('a,b\n"x, y","say ""hi"""\n'), [['a', 'b'], ['x, y', 'say "hi"']]);
});

test('html template escapes user text', () => {
  assert.equal(String(html`<b>${'<i>'}</b>${raw('<br>')}`), '<b>&lt;i&gt;</b><br>');
  assert.equal(String(html`${['<a>', raw('<b>')]}`), '&lt;a&gt;<b>');
});

test('muscle guesses for real exercise names from the recording', () => {
  const p = n => guessMuscles(n).primary[0];
  assert.equal(p('Jm press'), 'triceps');
  assert.equal(p('Rare Delts'), 'shoulders');
  assert.equal(p('Cross body cable extension'), 'triceps');
  assert.equal(p('Standing leg curl'), 'hamstrings');
  assert.equal(p('Chest press rajajinagar'), 'chest');
  assert.equal(p('Forearm curls 1'), 'forearms');
  assert.equal(p('Glute bridge'), 'glutes');
  assert.equal(p('Leg Raise'), 'abs');
  assert.equal(p('Seated Calf Raises'), 'calves');
  assert.equal(p('Lat pull down under arm'), 'back');
  assert.equal(p('Baysian curl'), 'biceps');
  assert.equal(guessMuscles('Shoulder Press (Smith Machine)').equipment, 'smith');
  assert.equal(guessMuscles('Dumbell Incline Bench Press').equipment, 'dumbbell');
});
