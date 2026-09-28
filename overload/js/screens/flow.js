/* What happens right after a set is logged: the rest timer, and moving through a superset.
 * Supersets follow Hevy: no rest between exercises in a round, the timer runs after the last one,
 * and the screen moves on to the next exercise by itself. */
import * as store from '../store.js';
import { startRest, stopRest } from '../timer.js';
import { topScreen, replace } from '../ui.js';

/** Returns a short note for the toast ("Next: Hammer Curl"), or '' outside a superset. */
export function afterLog(exId, { backdated = false } = {}) {
  if (backdated) return '';
  const ss = store.supersetFor(exId);
  if (!ss) { startRest(exId); return ''; }
  const i = ss.ids.indexOf(exId);
  const last = i === ss.ids.length - 1;
  const nextId = ss.ids[last ? 0 : i + 1];
  if (last) startRest(exId); else stopRest();
  const top = topScreen();
  if (top?.name === 'exercise' && top.p.id === exId) replace('exercise', { id: nextId });
  const name = store.exercise(nextId)?.name || '';
  return last ? `Round done. Rest, then ${name}` : `Next: ${name}`;
}
