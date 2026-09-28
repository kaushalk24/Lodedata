/* The set entry sheet. Prefilled from your last working set, so repeating a set is one tap.
 * Fields follow the exercise type (reps, time, distance; weight, added weight or assistance).
 * Extras stay one tap away: label, left/right, warm-up ramp, plates, type, unit, backdating,
 * an optional RPE row, a typo guard on save, and a "type or say it" mode. */
import { html, fmtNum, fmtTime, fmtShortDate, daysBetween, toDisplay, fromDisplay, round, dayKey, uid } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { openSheet, toast, celebrate, confirmDialog } from '../ui.js';
import { wouldBePR, suggestTarget, platesPerSide, groupByDay, weeklyStreak, isRepKind } from '../stats.js';
import { KINDS, unilateralOf } from '../library.js';
import { typoCheck, warmupRamp } from '../smart.js';
import { parseLog } from '../parse.js';
import { LABELS, setText, freshSets, kindFor } from './common.js';
import { afterLog } from './flow.js';

const trim = v => String(round(v, 2));
const num = s => parseFloat(s);
const PLATE_COLORS = { 25: '#e5484d', 20: '#3e7bfa', 15: '#f5c518', 10: '#30a46c', 5: '#e8e8ea', 2.5: '#e5484d', 1.25: '#a0a0a8', 50: '#3e7bfa', 45: '#3e7bfa', 35: '#f5c518' };
const PLATE_LOADED = new Set(['barbell', 'smith', 'machine', 'other']);
export const RPE = [6, 7, 7.5, 8, 8.5, 9, 9.5, 10];
export const RPE_HINT = { 6: '4+ left', 7: '3 left', 7.5: '2–3 left', 8: '2 left', 8.5: '1–2 left', 9: '1 left', 9.5: 'maybe 1', 10: 'max' };

/* ---------- time field: typed like a timer, "130" means 1:30 ---------- */
const secFromDigits = d => (d.length <= 2 ? +d || 0 : +d.slice(0, -2) * 60 + +d.slice(-2));
const digitsFromSec = s => (s < 60 ? String(s) : `${Math.floor(s / 60)}${String(s % 60).padStart(2, '0')}`);

/** The number shown in the left field for a set, per exercise type. */
function metricText(s, kind) {
  if (!s) return '';
  if (kind === 'time') return s.sec ? digitsFromSec(s.sec) : '';
  if (kind === 'distance') return s.dist ? trim(s.dist) : '';
  return s.reps ? trim(s.reps) : '';
}
/** The number shown in the right field: assistance is shown as a positive number. */
const weightText = (s, kind, u) => (s ? trim(round(toDisplay(kind === 'assisted' ? Math.abs(s.weight) : s.weight, u), 2)) : '');

export function openSetEntry({ exId = null, setId = null }) {
  const st = store.settings();
  const editing = setId ? store.getState().sets.find(s => s.id === setId) : null;
  exId = editing?.exId || exId;
  const ex = store.exercise(exId);
  const kind = kindFor(ex);
  const all = store.setsFor(exId);
  // Prefill from the last working set: after warm-ups you want the working weight back.
  const ref = editing || [...all].reverse().find(s => s.label !== 'warmup') || all[all.length - 1] || null;
  const p = {
    exId, setId, unit: st.unit, kind,
    reps: metricText(ref, kind), weight: weightText(ref, kind, st.unit),
    label: editing ? editing.label : null,
    note: editing ? editing.note || '' : '',
    rpe: editing?.rpe ?? null,
    side: editing ? editing.side || null : nextSide(exId),
    ts: editing ? editing.ts : null,
    field: 'reps', fresh: true, panel: null, warmDone: new Set(),
  };
  openSheet(SHEET, p);
}

/** Alternate sides: after a left set, the next one is right. */
function nextSide(exId) {
  if (!unilateralOf(store.exercise(exId))) return null;
  const last = store.lastSet(exId);
  return last && last.side === 'L' && daysBetween(last.ts, Date.now()) === 0 ? 'R' : 'L';
}

function target(p) {
  if (p.setId || !store.settings().showTargets || !isRepKind(p.kind)) return null;
  const sets = store.setsFor(p.exId);
  const prevDay = groupByDay(sets.filter(s => daysBetween(s.ts, Date.now()) > 0))[0];
  if (!prevDay) return null;
  const today = sets.filter(s => daysBetween(s.ts, Date.now()) === 0 && s.label !== 'warmup');
  // One-sided exercises compare left with left and right with right.
  const prev = p.side ? prevDay.sets.filter(s => s.side === p.side) : prevDay.sets;
  const done = p.side ? today.filter(s => s.side === p.side).length : today.length;
  const st = store.settings();
  return suggestTarget(prev.length ? prev : prevDay.sets, done, { step: st.stepKg, low: st.repLow, high: st.repHigh });
}
const WHY = { weight: '(+weight)', rep: '(+1 rep)', easy: '(felt easy: +weight)', hard: '(all-out last time: match it)' };

const weightKg = p => fromDisplay(num(p.weight) || 0, p.unit);

/** The set as it would be saved from the fields. */
function candidate(p) {
  const kg = round(weightKg(p), 4);
  const set = { reps: 0, weight: kg, bw: false };
  if (p.kind === 'time') set.sec = secFromDigits(p.reps);
  else if (p.kind === 'distance') set.dist = round(num(p.reps) || 0, 1);
  else set.reps = num(p.reps) || 0;
  if (p.kind === 'bodyweight') set.bw = true;
  if (p.kind === 'assisted') { set.bw = true; set.weight = -kg; }
  return set;
}

const others = p => store.setsFor(p.exId).filter(s => s.id !== p.setId && (p.ts == null || s.ts < p.ts));
const isPR = (p, set = candidate(p)) => wouldBePR(others(p), set, store.bodyKg(), p.kind);

function fieldView(p, key) {
  const on = p.field === key;
  const val = p[key];
  let shown = val, unitLabel;
  if (key === 'reps') {
    if (p.kind === 'time') { shown = val.length > 2 ? `${val.slice(0, -2)}:${val.slice(-2)}` : val; unitLabel = val.length > 2 ? 'min' : 's'; }
    else unitLabel = p.kind === 'distance' ? 'm' : 'rep';
  } else unitLabel = p.kind === 'bodyweight' ? `+${p.unit}` : p.kind === 'assisted' ? `${p.unit} help` : p.unit;
  const len = Math.min(6, String(shown).length);
  return html`<button class="num-field ${key} len-${len} ${on ? 'on' : ''} ${on && p.fresh && val !== '' ? 'fresh' : ''}" data-a="field" data-f="${key}">
    <span class="nv">${val === '' ? html`<span class="ph">0</span>` : shown}</span><span class="nu">${unitLabel}</span></button>`;
}

function keypad() {
  const k = (v, label = v, cls = '') => html`<button class="key ${cls}" data-a="key" data-k="${v}">${label}</button>`;
  return html`<div class="keypad">
    ${['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(d => k(d))}
    ${k('.', '.', 'flat')}${k('0')}${k('del', icon('backspace'), 'flat')}
  </div>
  <div class="keypad-foot"><button class="text-btn" data-a="text-mode">${icon('keyboard')}<span>Type or say it</span></button>
    <button class="icon-btn" data-a="next-field" aria-label="Next field">${icon('forward')}</button></div>`;
}

function textMode(p) {
  const res = parsed(p);
  return html`<div class="text-entry">
    <input id="set-text" class="field text-input" value="${p.text || ''}" placeholder="8 at 60 · 3x10 25 · same again" data-in="text" autocomplete="off" autocorrect="off" autocapitalize="off" enterkeyhint="done">
    ${res.error ? html`<p class="text-err">${res.error}</p>` : res.sets.length ? html`<div class="text-preview">
      <span class="muted small">${res.sets.length === 1 ? 'Will log' : `Will log ${res.sets.length} sets`}</span>
      <div class="chips">${res.sets.map(s => html`<span class="chip static small">${setText(toStored(p, s))}${s.label ? ` · ${LABELS[s.label].name}` : ''}</span>`)}</div></div>`
      : html`<p class="hint">Write it the way you'd say it: <b>8 at 60</b>, <b>3x10 25</b>, <b>10, 9, 8 at 25</b>, <b>same again</b>. Tap the mic on your keyboard to dictate.</p>`}
    <button class="text-btn back" data-a="keypad-mode">${icon('grid')}<span>Number pad</span></button>
  </div>`;
}

function parsed(p) {
  if (!p.text?.trim()) return { sets: [], error: null };
  const last = [...others(p)].reverse().find(s => s.label !== 'warmup');
  const fallbackReps = isRepKind(p.kind) ? num(p.reps) || null : null;
  const lastForParse = last && p.kind === 'assisted' ? { ...last, weight: Math.abs(last.weight) } : last;
  return parseLog(p.text, { kind: p.kind, unit: p.unit, last: lastForParse, fallbackKg: weightKg(p), fallbackReps });
}

/** Parsed sets carry a positive weight; store it the way this exercise type does. */
function toStored(p, s) {
  const out = { reps: s.reps, weight: s.weight, bw: false };
  if (s.sec) out.sec = s.sec;
  if (s.dist) out.dist = s.dist;
  if (p.kind === 'bodyweight') out.bw = true;
  if (p.kind === 'assisted') { out.bw = true; out.weight = -Math.abs(s.weight); }
  const side = s.side || p.side;
  if (side) out.side = side;
  const rpe = s.rpe ?? p.rpe;
  if (rpe && isRepKind(p.kind)) out.rpe = rpe;
  out.label = s.label ?? p.label ?? null;
  return out;
}

function labelsPanel(p) {
  return html`<div class="panel"><div class="panel-title">Labels</div><div class="card list">
    ${[...Object.entries(LABELS), [null, { name: 'None', color: 'var(--text-3)' }]].map(([k, l]) => html`
      <button class="row" data-a="pick-label" data-l="${k ?? ''}"><span class="dot" style="background:${l.color}"></span><span class="row-main">${l.name}</span>
      ${(p.label ?? null) === k ? html`<span class="check on">${icon('check')}</span>` : ''}</button>`)}
  </div></div>`;
}

function kindPanel(p) {
  const ex = store.exercise(p.exId);
  return html`<div class="panel"><div class="panel-title">How is ${ex?.name} logged?</div><div class="card list">
    ${Object.entries(KINDS).map(([k, d]) => html`<button class="row" data-a="pick-kind" data-k="${k}">
      <span class="row-main"><span class="row-title">${d.name}</span><span class="row-sub">${d.hint}</span></span>
      ${p.kind === k ? html`<span class="check on">${icon('check')}</span>` : ''}</button>`)}
    <div class="row static"><span class="row-main"><span class="row-title">Left and right separately</span><span class="row-sub">For one-arm or one-leg exercises</span></span>
      <button type="button" class="switch ${unilateralOf(ex) ? 'on' : ''}" role="switch" aria-checked="${unilateralOf(ex)}" data-a="toggle-sides"><i></i></button></div>
  </div></div>`;
}

function warmupPanel(p) {
  const gym = store.currentGym(), ex = store.exercise(p.exId);
  const work = num(p.weight) || 0;
  const barbell = ex?.equipment === 'barbell';
  const plates = Object.keys(gym.plates).map(Number).filter(x => gym.plates[x] >= 2);
  const rows = warmupRamp(work, barbell
    ? { bar: gym.bar, smallestPlate: plates.length ? Math.min(...plates) : 1.25 }
    : { step: p.unit === 'lb' ? 5 : 2.5 });
  const perSide = kg => {
    if (!barbell || kg <= gym.bar) return '';
    const r = platesPerSide(kg, gym.bar, gym.plates);
    return r.side.length ? `${r.side.map(x => fmtNum(x)).join(' + ')} per side` : '';
  };
  return html`<div class="panel warm-panel">
    <div class="panel-title">Warm-up for ${fmtNum(work)} ${p.unit}</div>
    ${rows.length ? html`<div class="card list">${rows.map(r => { const done = p.warmDone.has(r.kg); return html`
      <div class="row static warm-row ${done ? 'done' : ''}"><span class="warm-pct">${r.pct ? `${r.pct}%` : 'Bar'}</span>
        <span class="row-main"><span class="row-title">${r.reps} × ${fmtNum(r.kg)} ${p.unit}</span>${perSide(r.kg) ? html`<span class="row-sub">${perSide(r.kg)}</span>` : ''}</span>
        <button class="warm-log ${done ? 'on' : ''}" data-a="log-warm" data-kg="${r.kg}" data-r="${r.reps}" aria-label="Log warm-up ${r.reps} × ${r.kg}" ${done ? 'disabled' : ''}>${icon('check')}</button></div>`; })}</div>
      <p class="hint">Tap ✓ after each warm-up set. They're labelled Warm-Up and don't start the rest timer.</p>`
      : html`<p class="hint">Set your working weight first. Warm-ups are worked out from it (40%, 60% and 80%).</p>`}
    <button class="btn block" data-a="close-panel">Done</button>
  </div>`;
}

function platesPanel(p) {
  const gym = store.currentGym();
  p.bar ??= gym.bar;
  if (!p.plates) {
    const total = num(p.weight) || 0;
    p.plates = total > p.bar ? platesPerSide(total, p.bar, gym.plates).side : [];
  }
  const sizes = Object.keys(gym.plates).map(Number).filter(x => gym.plates[x] > 0).sort((a, b) => b - a);
  const total = p.bar + 2 * p.plates.reduce((a, b) => a + b, 0);
  const max = Math.max(...sizes, 1);
  const plate = (w, i) => html`<button class="plate" data-a="remove-plate" data-i="${i}" style="--h:${40 + 60 * (w / max)}%;--c:${PLATE_COLORS[w] || '#8e8e93'}" aria-label="Remove ${w}"><span>${fmtNum(w)}</span></button>`;
  return html`<div class="panel plates-panel">
    <div class="panel-title">Plates <span class="muted">· ${gym.name}</span></div>
    <div class="barbell"><span class="sleeve">${p.plates.map(plate)}</span><span class="shaft">${p.bar ? `${fmtNum(p.bar)} bar` : 'no bar'}</span><span class="sleeve mirror">${[...p.plates].reverse().map((w, i) => plate(w, p.plates.length - 1 - i))}</span></div>
    <div class="plates-total"><b>${fmtNum(total)}</b> ${p.unit} <span class="muted">· ${p.plates.length ? `${p.plates.map(x => fmtNum(x)).join(' + ')} per side` : 'tap plates to load'}</span></div>
    <div class="plate-keys">${sizes.map(w => html`<button class="plate-key" data-a="add-plate" data-w="${w}" style="--c:${PLATE_COLORS[w] || '#8e8e93'}">${fmtNum(w)}</button>`)}</div>
    <div class="chips">${[...new Set([gym.bar, 20, 15, 10, 0])].map(b => html`<button class="chip ${p.bar === b ? 'on' : ''}" data-a="bar" data-b="${b}">${b ? `Bar ${fmtNum(b)}` : 'No bar'}</button>`)}
      <button class="chip" data-a="clear-plates">Clear</button></div>
    <button class="btn block" data-a="close-panel">Done</button>
  </div>`;
}

function timePanel(p) {
  const d = new Date(p.ts ?? Date.now());
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  return html`<div class="panel"><div class="panel-title">When</div>
    <input id="set-time" class="field" type="datetime-local" value="${local}" data-in="time">
    <div class="btn-row"><button class="btn" data-a="time-now">Now</button><button class="btn accent" data-a="close-panel">Done</button></div>
    <p class="hint">Backdate a set you forgot to log. It lands on the right day in your history.</p></div>`;
}

function timeLabel(p) {
  if (p.ts == null) return 'Now';
  const days = daysBetween(p.ts, Date.now());
  return days === 0 ? fmtTime(p.ts) : `${fmtShortDate(p.ts)} ${fmtTime(p.ts)}`;
}

function recentNotes(exId) {
  const seen = new Set(), out = [];
  for (const s of [...store.setsFor(exId)].reverse()) {
    const n = (s.note || '').trim();
    if (n && !seen.has(n.toLowerCase())) { seen.add(n.toLowerCase()); out.push(n); }
    if (out.length >= 6) break;
  }
  return out;
}

function typoRow(p) {
  const t = p.typo, u = p.unit;
  const val = t.field === 'weight' ? `${fmtNum(round(toDisplay(t.value, u), 2))} ${u}` : `${fmtNum(t.value)} reps`;
  const usual = t.field === 'weight' ? `${fmtNum(round(toDisplay(t.usual, u), 1))} ${u}` : `${fmtNum(t.usual)}`;
  const sugg = t.suggest == null ? null : t.field === 'weight' ? fmtNum(round(toDisplay(t.suggest, u), 2)) : fmtNum(t.suggest);
  return html`<div class="typo" role="alert">${icon('warning')}<span><b>${val}?</b> ${t.heavier ? 'Much more' : 'Much less'} than your usual ${usual}.${sugg ? ` Did you mean ${sugg}?` : ''}</span>
    <span class="typo-btns">${sugg ? html`<button class="btn accent small" data-a="typo-fix">Use ${sugg}</button>` : ''}<button class="btn small" data-a="typo-keep">Keep</button></span></div>`;
}

const SHEET = {
  cls: 'entry',
  render(p) {
    const ex = store.exercise(p.exId);
    const st = store.settings();
    const t = p.textMode ? null : target(p);
    const pr = !p.textMode && isPR(p);
    const wsteps = p.unit === 'lb' ? [2.5, 5] : [1, 5];
    const mstep = p.kind === 'time' || p.kind === 'distance' ? 5 : 1;
    const lbl = p.label ? LABELS[p.label] : null;
    const notes = p.noteFocus || !p.note ? recentNotes(p.exId).filter(n => n !== p.note).slice(0, 4) : [];
    const ss = store.supersetFor(p.exId);
    const showRpe = st.rpeOn && isRepKind(p.kind) && p.label !== 'warmup' && !p.textMode;
    const panel = p.panel === 'labels' ? labelsPanel(p) : p.panel === 'plates' ? platesPanel(p) : p.panel === 'time' ? timePanel(p)
      : p.panel === 'kind' ? kindPanel(p) : p.panel === 'warmup' ? warmupPanel(p) : p.textMode ? '' : keypad(p);
    return html`<div class="sheet-grab"></div>
      <div class="entry-title"><span>${ex?.name}</span>
        ${ss ? html`<span class="ss-tag">${ss.ids.length > 2 ? 'Circuit' : 'Superset'} ${ss.ids.indexOf(p.exId) + 1}/${ss.ids.length}</span>` : ''}
        ${p.setId ? html`<button class="link danger" data-a="delete">Delete</button>` : ''}${pr ? html`<span class="pr-pill">${icon('trophy')} Record</span>` : ''}</div>
      ${p.textMode ? textMode(p) : html`<div class="entry-fields">
        <div class="ef">${fieldView(p, 'reps')}<span class="steppers one"><button data-a="step" data-f="reps" data-d="${-mstep}" aria-label="Less">${icon('minus')}</button><button data-a="step" data-f="reps" data-d="${mstep}" aria-label="More">${icon('plus')}</button></span></div>
        <div class="ef">${fieldView(p, 'weight')}<span class="steppers two">
          ${wsteps.map(s => html`<span class="st-row"><button data-a="step" data-f="weight" data-d="${-s}" aria-label="Minus ${s}">${icon('minus')}</button><small>${fmtNum(s)}</small><button data-a="step" data-f="weight" data-d="${s}" aria-label="Plus ${s}">${icon('plus')}</button></span>`)}</span></div>
      </div>`}
      ${p.typo ? typoRow(p) : t ? html`<button class="target" data-a="apply-target"><span class="muted">Last time ${setText(t.ref)}</span><span>Try <b>${fmtNum(t.reps, 1)} × ${t.ref.bw && !t.weight ? 'BW' : fmtNum(round(toDisplay(p.kind === 'assisted' ? Math.abs(t.weight) : t.weight, p.unit), 1))}</b> ${WHY[t.why]}</span></button>` : ''}
      ${showRpe ? html`<div class="rpe-row"><span class="rpe-label">${p.rpe ? html`<b>${p.rpe}</b> · ${RPE_HINT[p.rpe]}` : 'RPE'}</span>
        <div class="rpe-opts">${RPE.map(v => html`<button class="${p.rpe === v ? 'on' : ''}" data-a="rpe" data-v="${v}" aria-label="RPE ${v}: ${RPE_HINT[v]} in reserve">${v}</button>`)}</div></div>` : ''}
      <div class="chips scroll-x entry-chips">
        <button class="chip ${lbl ? 'on' : ''}" data-a="panel" data-p="labels" style="${lbl ? `--chip:${lbl.color}` : ''}">${icon('tag')}${lbl ? lbl.name : 'Label'}</button>
        ${p.side ? html`<button class="chip on" data-a="side">${icon('updown')}${p.side === 'L' ? 'Left' : 'Right'}</button>` : ''}
        ${p.kind === 'weight' && !p.setId && !p.textMode ? html`<button class="chip ${p.panel === 'warmup' ? 'on' : ''}" data-a="panel" data-p="warmup">${icon('flame')}Warm-up</button>` : ''}
        ${p.kind === 'weight' && PLATE_LOADED.has(ex?.equipment) && !p.textMode ? html`<button class="chip ${p.panel === 'plates' ? 'on' : ''}" data-a="panel" data-p="plates">${icon('plate')}Plates</button>` : ''}
        <button class="chip ${p.panel === 'kind' ? 'on' : ''}" data-a="panel" data-p="kind">${icon('person')}${KINDS[p.kind].short}</button>
        <button class="chip" data-a="unit">${icon('scale')}${p.unit.toUpperCase()}</button>
        <button class="chip ${p.ts != null ? 'on' : ''}" data-a="panel" data-p="time">${icon('calendar')}${timeLabel(p)}</button>
      </div>
      <div class="entry-note">
        <input id="set-note" class="note-input" placeholder="Add note" value="${p.note}" data-in="note" autocomplete="off" enterkeyhint="done">
        <button class="save" data-a="save" aria-label="Save set">${icon('check')}</button>
      </div>
      ${notes.length ? html`<div class="chips scroll-x note-chips">${notes.map(n => html`<button class="chip small" data-a="note-chip" data-n="${n}">${n}</button>`)}</div>` : ''}
      ${panel}`;
  },
  mount(el, p, inst) {
    const note = el.querySelector('#set-note');
    note.addEventListener('focus', () => { p.noteFocus = true; el.classList.add('typing'); });
    note.addEventListener('blur', () => { p.noteFocus = false; setTimeout(() => el.classList.remove('typing'), 50); });
    note.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); note.blur(); } });
    const text = el.querySelector('#set-text');
    if (text) {
      text.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); save(p, inst); } });
      if (p.focusText) { p.focusText = false; setTimeout(() => { text.focus(); const n = text.value.length; text.setSelectionRange?.(n, n); }, 60); }
    }
    if (!inst._keys) {
      inst._keys = true;
      // Hardware keyboard support (desktop / iPad).
      const onKey = e => {
        if (!inst.el.classList.contains('open') || !document.body.contains(inst.el)) { if (!document.body.contains(inst.el)) document.removeEventListener('keydown', onKey); return; }
        if (e.target.matches('input,textarea,select') || p.textMode) return;
        if (/^[0-9.]$/.test(e.key)) press(p, e.key);
        else if (e.key === 'Backspace') press(p, 'del');
        else if (e.key === 'Tab') { e.preventDefault(); p.field = p.field === 'reps' ? 'weight' : 'reps'; p.fresh = true; }
        else if (e.key === 'Enter') { save(p, inst); return; }
        else return;
        inst.rerender();
      };
      document.addEventListener('keydown', onKey);
    }
  },
  inputs: {
    note: (el, ev, p) => { p.note = el.value; },
    time: (el, ev, p) => { const t = new Date(el.value).getTime(); if (Number.isFinite(t)) p.ts = Math.min(t, Date.now()); },
    text: (el, ev, p, inst) => {
      p.text = el.value; p.typo = null;
      // Update the preview without re-rendering the input, so the keyboard stays up.
      const res = parsed(p);
      const box = inst.panel.querySelector('.text-entry');
      const fresh = document.createElement('div');
      fresh.innerHTML = String(textMode(p));
      box.querySelectorAll('.text-preview, .text-err, .hint').forEach(n => n.remove());
      const next = fresh.querySelector('.text-preview, .text-err, .hint');
      if (next) el.insertAdjacentElement('afterend', next);
      inst.panel.querySelector('.save')?.classList.toggle('warn', !!res.error);
    },
  },
  actions: {
    field: (el, ev, p, inst) => { p.field = el.dataset.f; p.fresh = true; p.panel = null; inst.rerender(); },
    key: (el, ev, p, inst) => { press(p, el.dataset.k); navigator.vibrate?.(8); inst.rerender(); },
    'next-field': (el, ev, p, inst) => { p.field = p.field === 'reps' ? 'weight' : 'reps'; p.fresh = true; inst.rerender(); },
    'text-mode': (el, ev, p, inst) => { p.textMode = true; p.panel = null; p.typo = null; p.focusText = true; inst.rerender(); },
    'keypad-mode': (el, ev, p, inst) => { p.textMode = false; inst.rerender(); },
    step: (el, ev, p, inst) => {
      const f = el.dataset.f, d = +el.dataset.d;
      if (f === 'reps' && p.kind === 'time') p.reps = digitsFromSec(Math.max(0, secFromDigits(p.reps) + d));
      else p[f] = trim(Math.max(0, (num(p[f]) || 0) + d));
      p.fresh = true; p.field = f; p.typo = null;
      if (f === 'weight') p.plates = null;
      inst.rerender();
    },
    'apply-target': (el, ev, p, inst) => {
      const t = target(p); if (!t) return;
      p.reps = trim(t.reps); p.weight = trim(round(toDisplay(p.kind === 'assisted' ? Math.abs(t.weight) : t.weight, p.unit), 2));
      p.fresh = true; p.plates = null; p.typo = null; inst.rerender();
    },
    rpe: (el, ev, p, inst) => { const v = +el.dataset.v; p.rpe = p.rpe === v ? null : v; inst.rerender(); },
    side: (el, ev, p, inst) => { p.side = p.side === 'L' ? 'R' : 'L'; inst.rerender(); },
    panel: (el, ev, p, inst) => { const w = el.dataset.p; p.panel = p.panel === w ? null : w; if (w === 'plates') p.plates = null; inst.rerender(); },
    'close-panel': (el, ev, p, inst) => { p.panel = null; inst.rerender(); },
    'pick-label': (el, ev, p, inst) => { p.label = el.dataset.l || null; p.panel = null; inst.rerender(); },
    'pick-kind': (el, ev, p, inst) => {
      const k = el.dataset.k;
      if (k !== p.kind) {
        store.updateExercise(p.exId, { kind: k });
        p.kind = k;
        const ref = [...store.setsFor(p.exId)].reverse().find(s => metricText(s, k));
        p.reps = metricText(ref, k); p.weight = ref ? weightText(ref, k, p.unit) : (k === 'weight' ? p.weight : '0');
        p.rpe = null; p.fresh = true; p.field = 'reps'; p.typo = null;
      }
      p.panel = null; inst.rerender();
    },
    'toggle-sides': (el, ev, p, inst) => {
      const on = !unilateralOf(store.exercise(p.exId));
      store.updateExercise(p.exId, { unilateral: on });
      p.side = on ? nextSide(p.exId) : null; inst.rerender();
    },
    unit: (el, ev, p, inst) => {
      const kg = weightKg(p);
      p.unit = p.unit === 'kg' ? 'lb' : 'kg';
      p.weight = p.weight === '' ? '' : trim(round(toDisplay(kg, p.unit), 1)); p.plates = null; p.typo = null; inst.rerender();
    },
    'time-now': (el, ev, p, inst) => { p.ts = null; p.panel = null; inst.rerender(); },
    'add-plate': (el, ev, p, inst) => { p.plates.push(+el.dataset.w); p.plates.sort((a, b) => b - a); syncPlates(p); inst.rerender(); },
    'remove-plate': (el, ev, p, inst) => { p.plates.splice(+el.dataset.i, 1); syncPlates(p); inst.rerender(); },
    'clear-plates': (el, ev, p, inst) => { p.plates = []; syncPlates(p); inst.rerender(); },
    bar: (el, ev, p, inst) => { p.bar = +el.dataset.b; syncPlates(p); inst.rerender(); },
    'log-warm': (el, ev, p, inst) => {
      const kg = +el.dataset.kg;
      const id = uid(); freshSets.add(id);
      store.addSet({ id, exId: p.exId, reps: +el.dataset.r, weight: round(fromDisplay(kg, p.unit), 4), label: 'warmup', ts: p.ts ?? Date.now() });
      p.warmDone.add(kg); navigator.vibrate?.(10);
      inst.rerender();
      toast(`Warm-up ${el.dataset.r} × ${fmtNum(kg)} ${p.unit}`, { iconName: 'flame', action: 'Undo', onAction: () => { store.deleteSet(id); p.warmDone.delete(kg); inst.rerender(); }, ms: 2200 });
    },
    'note-chip': (el, ev, p, inst) => { p.note = el.dataset.n; inst.rerender(); },
    'typo-fix': (el, ev, p, inst) => {
      const t = p.typo;
      if (t.field === 'weight') p.weight = trim(round(toDisplay(t.suggest, p.unit), 2)); else p.reps = trim(t.suggest);
      p.typo = null; p.fresh = true; inst.rerender();
    },
    'typo-keep': (el, ev, p, inst) => { p.typoOk = true; save(p, inst); },
    save: (el, ev, p, inst) => save(p, inst),
    delete: async (el, ev, p, inst) => {
      if (!(await confirmDialog({ title: 'Delete this set?', confirm: 'Delete Set' }))) return;
      const undo = store.deleteSet(p.setId); inst.close(); toast('Set deleted', { action: 'Undo', onAction: undo });
    },
  },
};

function syncPlates(p) { p.weight = trim(p.bar + 2 * p.plates.reduce((a, b) => a + b, 0)); p.fresh = true; p.typo = null; }

function press(p, k) {
  const f = p.field;
  const timeField = f === 'reps' && p.kind === 'time';
  let v = p[f];
  if (k === 'del') v = p.fresh ? '' : v.slice(0, -1);
  else if (k === '.') { if (timeField) return; v = p.fresh || v === '' ? '0.' : v.includes('.') ? v : v + '.'; }
  else {
    if (p.fresh) v = k;
    else if (v === '0') v = k;
    else if (timeField ? v.length < 4 : !(v.includes('.') && v.split('.')[1].length >= 2) && v.replace('.', '').length < 6) v += k;
  }
  p[f] = v; p.fresh = false; p.typo = null;
  if (f === 'weight') p.plates = null;
}

function shake(p, inst, field = 'reps') {
  p.field = field; p.fresh = true; p.panel = null; p.focusText = !!p.textMode; inst.rerender();
  inst.panel.querySelector(`.num-field.${field}, .text-input`)?.classList.add('shake');
}

function save(p, inst) {
  if (p.textMode) return saveParsed(p, inst);
  const set = candidate(p);
  const metric = p.kind === 'time' ? set.sec : p.kind === 'distance' ? set.dist : set.reps;
  if (!(metric > 0)) return shake(p, inst);
  // Typo guard: check once on save; a second tap (or Keep) saves anyway.
  if (!p.typoOk && !p.typo && p.label !== 'warmup' && p.label !== 'drop' && isRepKind(p.kind)) {
    const hist = others(p).filter(s => (p.side ? s.side === p.side : true));
    const t = typoCheck(hist, { reps: set.reps, weight: p.kind === 'weight' ? set.weight : 0 });
    if (t) { p.typo = t; p.panel = null; inst.rerender(); return; }
  }
  const pr = isPR(p, set);
  const data = { ...set, label: p.label, note: p.note.trim(), side: p.side || undefined, rpe: isRepKind(p.kind) && p.label !== 'warmup' ? p.rpe || undefined : undefined };
  if (p.setId) {
    store.updateSet(p.setId, { ...data, ts: p.ts, sec: data.sec, dist: data.dist });
    inst.close();
    toast('Set updated', { iconName: 'check' });
    return;
  }
  const before = store.allSets().filter(s => dayKey(s.ts) === dayKey(Date.now())).length;
  const id = uid(); freshSets.add(id);
  const s = store.addSet({ id, exId: p.exId, ...clean(data), ts: p.ts ?? Date.now() });
  navigator.vibrate?.(15);
  inst.close();
  const next = afterLog(p.exId, { backdated: p.ts != null });
  announce([s], pr, before === 0 && p.ts == null, next);
}

function saveParsed(p, inst) {
  const res = parsed(p);
  if (res.error || !res.sets.length) { shake(p, inst); return; }
  const before = store.allSets().filter(s => dayKey(s.ts) === dayKey(Date.now())).length;
  const ts = p.ts ?? Date.now();
  let pr = false;
  const saved = res.sets.map((raw, i) => {
    const data = toStored(p, raw);
    if (!pr && wouldBePR(others(p), data, store.bodyKg(), p.kind)) pr = true;
    const id = uid(); freshSets.add(id);
    return store.addSet({ id, exId: p.exId, ...clean(data), note: i === res.sets.length - 1 ? p.note.trim() : '', ts });
  });
  navigator.vibrate?.(15);
  inst.close();
  const last = saved[saved.length - 1];
  const next = last.label === 'warmup' ? '' : afterLog(p.exId, { backdated: p.ts != null });
  announce(saved, pr, before === 0 && p.ts == null, next);
}

const clean = o => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined));

function announce(saved, pr, firstToday, next) {
  const st = store.settings();
  const undo = () => saved.forEach(s => store.deleteSet(s.id));
  const what = saved.length > 1 ? `${saved.length} sets · ${setText(saved[0])}` : setText(saved[0]);
  const tail = next ? ` · ${next}` : '';
  if (pr && st.celebrations) {
    celebrate();
    toast(`New record: ${what}${tail}`, { kind: 'gold', iconName: 'trophy', action: 'Undo', onAction: undo });
  } else if (firstToday && st.dailyCongrats) {
    const w = weeklyStreak(store.allSets(), st.weeklyGoal);
    toast(`First set today · ${w.thisWeek}/${w.goal} this week${w.streak ? ` · ${w.streak} week streak` : ''}${tail}`, { iconName: 'flame', action: 'Undo', onAction: undo });
  } else {
    toast(`Logged ${what}${tail}`, { iconName: 'check', action: 'Undo', onAction: undo, ms: next ? 3400 : 2600 });
  }
}

