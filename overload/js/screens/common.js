/* Markup shared by several screens: exercise rows, set rows, labels, colours. */
import { html, fmtW, fmtReps, fmtTime, relTime, daysBetween, fmtNum } from '../util.js';
import { icon, EQUIP_ICON } from '../icons.js';
import * as store from '../store.js';
import { kindOf } from '../library.js';

/**
 * The set type for an exercise. Until the user picks one, the name-based guess yields to history:
 * a "bodyweight" exercise always logged with a plain weight stays a weight exercise, and one logged
 * with the old Bodyweight toggle stays bodyweight.
 */
export function kindFor(ex) {
  if (!ex) return 'weight';
  if (ex.kind) return ex.kind;
  const guess = kindOf(ex);
  const last = store.lastSet(ex.id);
  if (!last || guess === 'time' || guess === 'distance' || guess === 'assisted') return guess;
  if (last.bw) return last.weight < 0 ? 'assisted' : 'bodyweight';
  return last.weight > 0 ? 'weight' : guess;
}
import { plateauInfo } from '../smart.js';

export const LABELS = {
  warmup: { name: 'Warm-Up', color: 'var(--orange)', badge: 'W' },
  amrap: { name: 'AMRAP', color: 'var(--green)', badge: 'A' },
  failure: { name: 'Failure', color: 'var(--red)', badge: 'F' },
  drop: { name: 'Drop Set', color: 'var(--purple)', badge: 'D' },
  pr: { name: 'PR Attempt', color: 'var(--gold)', badge: 'PR' },
};

/** Set ids just logged; the exercise screen highlights them once. */
export const freshSets = new Set();

export const COLORS = ['red', 'orange', 'yellow', 'green', 'pink', 'blue', 'purple', 'gray', 'multi'];

export const unit = () => store.settings().unit;
export const W = kg => fmtW(kg, unit());

/** 45 -> "45 s", 90 -> "1:30" */
export const fmtSec = sec => (sec < 60 ? `${sec} s` : `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`);
const signed = (kg, u) => `${kg > 0 ? '+' : '−'}${fmtW(Math.abs(kg), u)} ${u}`;

/** "8 × 25 kg", "10 × BW", "8 × BW +10 kg", "8 × BW −20 kg", "1:30", "40 m × 32 kg", with " (L)" for one side. */
export function setText(s) {
  const u = unit();
  const side = s.side ? ` (${s.side})` : '';
  const load = s.weight ? ` × ${fmtW(s.weight, u)} ${u}` : '';
  if (s.sec) return `${fmtSec(s.sec)}${load}${side}`;
  if (s.dist) return `${fmtNum(s.dist, 1)} m${load}${side}`;
  if (s.bw) return `${fmtReps(s.reps)} × BW${s.weight ? ` ${signed(s.weight, u)}` : ''}${side}`;
  return `${fmtReps(s.reps)} × ${fmtW(s.weight, u)} ${u}${side}`;
}

export const labelBadge = l => l && LABELS[l] ? html`<span class="badge" style="--c:${LABELS[l].color}">${LABELS[l].badge}</span>` : '';

/** One logged set, as in the exercise history list. */
export function setRow(s, i, { pr = false, gymName = '' } = {}) {
  const u = unit();
  const metric = s.sec ? html`<b>${fmtSec(s.sec).replace(' s', '')}</b>${s.sec < 60 ? ' s' : ''}` : s.dist ? html`<b>${fmtNum(s.dist, 1)}</b> m` : html`<b>${fmtReps(s.reps)}</b> rep`;
  const wt = s.bw
    ? (s.weight ? html`<b>${s.weight > 0 ? '+' : '−'}${fmtW(Math.abs(s.weight), u)}</b> ${u}` : html`<b>BW</b>`)
    : (s.sec || s.dist) && !s.weight ? '' : html`<b>${fmtW(s.weight, u)}</b> ${u}`;
  return html`<button class="set-row" data-a="edit-set" data-id="${s.id}" id="set-${s.id}">
    <span class="idx">${i}</span><span class="time">${fmtTime(s.ts)}</span>
    <span class="badges">${labelBadge(s.label)}${s.side ? html`<span class="badge side">${s.side}</span>` : ''}${pr ? html`<span class="trophy" title="Personal record">${icon('trophy')}</span>` : ''}</span>
    <span class="reps">${metric}${s.rpe ? html`<small class="rpe">@${s.rpe}</small>` : ''}</span>
    <span class="wt">${wt}</span>
    <span class="chev">${icon('chevronRight')}</span>
    ${s.note || gymName ? html`<span class="note">${s.note}${s.note && gymName ? ' · ' : ''}${gymName ? html`<em>${gymName}</em>` : ''}</span>` : ''}
  </button>`;
}

/**
 * The plateau for an exercise, unless the user dismissed it. After a dismissal it only comes back
 * once three more sessions pass without a new best.
 */
export function stallFor(ex) {
  const pl = plateauInfo(store.setsFor(ex.id), { kind: kindFor(ex), bodyKg: store.bodyKg(), formula: store.settings().formula });
  return pl && !(ex.plateauAck >= pl.total - 2) ? pl : null;
}

/** Exercise list row with last-trained time. In workouts it also shows the last top set and a done-today tick. */
export function exRow(ex, { detail = false, action = 'open-exercise', trailing = null, now = Date.now() } = {}) {
  const last = store.lastSet(ex.id);
  const doneToday = last && daysBetween(last.ts, now) === 0;
  let sub = '';
  let stalled = false;
  if (detail && last) {
    const sets = store.setsFor(ex.id);
    const day = sets.filter(s => daysBetween(s.ts, last.ts) === 0 && s.label !== 'warmup');
    const score = s => [s.weight, s.sec || s.dist || s.reps];
    const top = day.reduce((a, s) => { if (!a) return s; const [aw, am] = score(a), [sw, sm] = score(s); return sw > aw || (sw === aw && sm > am) ? s : a; }, null);
    if (top) sub = `Last: ${setText({ ...top, side: null })}${day.length > 1 ? ` · ${day.length} sets` : ''}`;
    stalled = !!stallFor(ex);
  }
  return html`<button class="row" data-a="${action}" data-id="${ex.id}">
    ${detail ? html`<span class="row-lead ${doneToday ? 'done' : ''}">${doneToday ? icon('check') : icon(EQUIP_ICON[ex.equipment] || 'dumbbell')}</span>` : ''}
    <span class="row-main"><span class="row-title">${ex.name}</span>${sub ? html`<span class="row-sub">${sub}${stalled ? html` · <span class="stalled">Stalled</span>` : ''}</span>` : ''}</span>
    ${trailing ?? html`<span class="row-meta">${relTime(last?.ts, now)}</span><span class="chev">${icon('chevronRight')}</span>`}
  </button>`;
}

export const colorDot = c => html`<span class="swatch c-${c}"></span>`;
