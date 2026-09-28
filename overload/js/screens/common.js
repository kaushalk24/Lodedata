/* Markup shared by several screens: exercise rows, set rows, labels, colours. */
import { html, fmtW, fmtReps, fmtTime, relTime, daysBetween } from '../util.js';
import { icon, EQUIP_ICON } from '../icons.js';
import * as store from '../store.js';

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

/** "8 × 25 kg", "10 × BW", "8 × BW +10 kg" */
export function setText(s) {
  const u = unit();
  if (s.bw) return `${fmtReps(s.reps)} × BW${s.weight ? ` +${fmtW(s.weight, u)} ${u}` : ''}`;
  return `${fmtReps(s.reps)} × ${fmtW(s.weight, u)} ${u}`;
}

export const labelBadge = l => l && LABELS[l] ? html`<span class="badge" style="--c:${LABELS[l].color}">${LABELS[l].badge}</span>` : '';

/** One logged set, as in the exercise history list. */
export function setRow(s, i, { pr = false, gymName = '' } = {}) {
  const u = unit();
  return html`<button class="set-row" data-a="edit-set" data-id="${s.id}" id="set-${s.id}">
    <span class="idx">${i}</span><span class="time">${fmtTime(s.ts)}</span>
    <span class="badges">${labelBadge(s.label)}${pr ? html`<span class="trophy" title="Personal record">${icon('trophy')}</span>` : ''}</span>
    <span class="reps"><b>${fmtReps(s.reps)}</b> rep</span>
    <span class="wt">${s.bw ? html`<b>${s.weight ? `+${fmtW(s.weight, u)}` : 'BW'}</b>${s.weight ? ` ${u}` : ''}` : html`<b>${fmtW(s.weight, u)}</b> ${u}`}</span>
    <span class="chev">${icon('chevronRight')}</span>
    ${s.note || gymName ? html`<span class="note">${s.note}${s.note && gymName ? ' · ' : ''}${gymName ? html`<em>${gymName}</em>` : ''}</span>` : ''}
  </button>`;
}

/** Exercise list row with last-trained time. In workouts it also shows the last top set and a done-today tick. */
export function exRow(ex, { detail = false, action = 'open-exercise', trailing = null, now = Date.now() } = {}) {
  const last = store.lastSet(ex.id);
  const doneToday = last && daysBetween(last.ts, now) === 0;
  let sub = '';
  if (detail && last) {
    const sets = store.setsFor(ex.id);
    const day = sets.filter(s => daysBetween(s.ts, last.ts) === 0 && s.label !== 'warmup');
    const top = day.reduce((a, s) => (!a || s.weight > a.weight || (s.weight === a.weight && s.reps > a.reps) ? s : a), null);
    if (top) sub = `Last: ${setText(top)}${day.length > 1 ? ` · ${day.length} sets` : ''}`;
  }
  return html`<button class="row" data-a="${action}" data-id="${ex.id}">
    ${detail ? html`<span class="row-lead ${doneToday ? 'done' : ''}">${doneToday ? icon('check') : icon(EQUIP_ICON[ex.equipment] || 'dumbbell')}</span>` : ''}
    <span class="row-main"><span class="row-title">${ex.name}</span>${sub ? html`<span class="row-sub">${sub}</span>` : ''}</span>
    ${trailing ?? html`<span class="row-meta">${relTime(last?.ts, now)}</span><span class="chev">${icon('chevronRight')}</span>`}
  </button>`;
}

export const colorDot = c => html`<span class="swatch c-${c}"></span>`;
