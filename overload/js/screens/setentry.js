/* The set entry sheet: reps/weight with a custom keypad, steppers, label, plates, bodyweight,
 * unit, time and note. Prefilled from the last set so repeating a set is one tap. */
import { html, fmtNum, fmtTime, fmtShortDate, daysBetween, toDisplay, fromDisplay, round, dayKey } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { openSheet, toast, celebrate, confirmDialog } from '../ui.js';
import { wouldBePR, suggestTarget, platesPerSide, groupByDay, weeklyStreak } from '../stats.js';
import { LABELS, setText } from './common.js';
import { startRest } from '../timer.js';

const trim = v => String(round(v, 2));
const num = s => parseFloat(s);
const PLATE_COLORS = { 25: '#e5484d', 20: '#3e7bfa', 15: '#f5c518', 10: '#30a46c', 5: '#e8e8ea', 2.5: '#e5484d', 1.25: '#a0a0a8', 50: '#3e7bfa', 45: '#3e7bfa', 35: '#f5c518' };

export function openSetEntry({ exId = null, setId = null }) {
  const st = store.settings();
  const editing = setId ? store.getState().sets.find(s => s.id === setId) : null;
  exId = editing?.exId || exId;
  const last = editing || store.lastSet(exId);
  const u = st.unit;
  const p = {
    exId, setId, unit: u,
    reps: last ? trim(last.reps) : '',
    weight: last ? trim(toDisplay(last.weight, u)) : '',
    label: editing ? editing.label : null,
    note: editing ? editing.note || '' : '',
    bw: last ? !!last.bw : store.exercise(exId)?.equipment === 'bodyweight',
    ts: editing ? editing.ts : null,
    field: 'reps', fresh: true, panel: null,
  };
  openSheet(SHEET, p);
}

function target(p) {
  if (p.setId || !store.settings().showTargets) return null;
  const sets = store.setsFor(p.exId);
  const prevDay = groupByDay(sets.filter(s => daysBetween(s.ts, Date.now()) > 0))[0];
  if (!prevDay) return null;
  const todayWorking = sets.filter(s => daysBetween(s.ts, Date.now()) === 0 && s.label !== 'warmup').length;
  const st = store.settings();
  return suggestTarget(prevDay.sets, todayWorking, { step: st.stepKg, low: st.repLow, high: st.repHigh });
}

function weightKg(p) { return fromDisplay(num(p.weight) || 0, p.unit); }

function isPR(p) {
  const reps = num(p.reps);
  if (!(reps >= 1)) return false;
  const others = store.setsFor(p.exId).filter(s => s.id !== p.setId && (p.ts == null || s.ts < p.ts));
  return wouldBePR(others, reps, weightKg(p), store.bodyKg(), p.bw);
}

function fieldView(p, key) {
  const on = p.field === key;
  const val = p[key];
  const unitLabel = key === 'reps' ? 'rep' : p.bw ? (num(p.weight) ? `+${p.unit}` : `BW`) : p.unit;
  return html`<button class="num-field ${key} ${on ? 'on' : ''} ${on && p.fresh && val !== '' ? 'fresh' : ''}" data-a="field" data-f="${key}">
    <span class="nv">${val === '' ? html`<span class="ph">0</span>` : val}</span><span class="nu">${unitLabel}</span></button>`;
}

function keypad(p) {
  const k = (v, label = v, cls = '') => html`<button class="key ${cls}" data-a="key" data-k="${v}">${label}</button>`;
  return html`<div class="keypad">
    ${['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(d => k(d))}
    ${k('.', '.', 'flat')}${k('0')}${k('del', icon('backspace'), 'flat')}
  </div>
  <div class="keypad-foot"><button class="icon-btn" data-a="hide-keypad" aria-label="Hide keypad">${icon('keyboard')}</button>
    <button class="icon-btn" data-a="next-field" aria-label="Next field">${icon('forward')}</button></div>`;
}

function labelsPanel(p) {
  return html`<div class="panel"><div class="panel-title">Labels</div><div class="card list">
    ${[...Object.entries(LABELS), [null, { name: 'None', color: 'var(--text-3)' }]].map(([k, l]) => html`
      <button class="row" data-a="pick-label" data-l="${k ?? ''}"><span class="dot" style="background:${l.color}"></span><span class="row-main">${l.name}</span>
      ${(p.label ?? null) === k ? html`<span class="check on">${icon('check')}</span>` : ''}</button>`)}
  </div></div>`;
}

function platesPanel(p) {
  const gym = store.currentGym();
  p.bar ??= gym.bar;
  if (!p.side) {
    const total = num(p.weight) || 0;
    p.side = total > p.bar ? platesPerSide(total, p.bar, gym.plates).side : [];
  }
  const sizes = Object.keys(gym.plates).map(Number).filter(x => gym.plates[x] > 0).sort((a, b) => b - a);
  const total = p.bar + 2 * p.side.reduce((a, b) => a + b, 0);
  const max = Math.max(...sizes, 1);
  const plate = (w, i) => html`<button class="plate" data-a="remove-plate" data-i="${i}" style="--h:${40 + 60 * (w / max)}%;--c:${PLATE_COLORS[w] || '#8e8e93'}" aria-label="Remove ${w}"><span>${fmtNum(w)}</span></button>`;
  return html`<div class="panel plates-panel">
    <div class="panel-title">Plates <span class="muted">· ${gym.name}</span></div>
    <div class="barbell"><span class="sleeve">${p.side.map(plate)}</span><span class="shaft">${p.bar ? `${fmtNum(p.bar)} bar` : 'no bar'}</span><span class="sleeve mirror">${[...p.side].reverse().map((w, i) => plate(w, p.side.length - 1 - i))}</span></div>
    <div class="plates-total"><b>${fmtNum(total)}</b> ${p.unit} <span class="muted">· ${p.side.length ? `${p.side.map(x => fmtNum(x)).join(' + ')} per side` : 'tap plates to load'}</span></div>
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

const SHEET = {
  cls: 'entry',
  render(p) {
    const ex = store.exercise(p.exId);
    const t = target(p);
    const pr = isPR(p);
    const steps = p.unit === 'lb' ? [2.5, 5] : [1, 5];
    const lbl = p.label ? LABELS[p.label] : null;
    const notes = p.noteFocus || !p.note ? recentNotes(p.exId).filter(n => n !== p.note).slice(0, 4) : [];
    const panel = p.panel === 'labels' ? labelsPanel(p) : p.panel === 'plates' ? platesPanel(p) : p.panel === 'time' ? timePanel(p) : p.hideKeys ? '' : keypad(p);
    return html`<div class="sheet-grab"></div>
      <div class="entry-title"><span>${ex?.name}</span>${p.setId ? html`<button class="link danger" data-a="delete">Delete</button>` : ''}${pr ? html`<span class="pr-pill">${icon('trophy')} Record</span>` : ''}</div>
      <div class="entry-fields">
        <div class="ef">${fieldView(p, 'reps')}<span class="steppers one"><button data-a="step" data-f="reps" data-d="-1" aria-label="One rep less">${icon('minus')}</button><button data-a="step" data-f="reps" data-d="1" aria-label="One rep more">${icon('plus')}</button></span></div>
        <div class="ef">${fieldView(p, 'weight')}<span class="steppers two">
          ${steps.map(s => html`<span class="st-row"><button data-a="step" data-f="weight" data-d="${-s}" aria-label="Minus ${s}">${icon('minus')}</button><small>${fmtNum(s)}</small><button data-a="step" data-f="weight" data-d="${s}" aria-label="Plus ${s}">${icon('plus')}</button></span>`)}</span></div>
      </div>
      ${t ? html`<button class="target" data-a="apply-target"><span class="muted">Last time ${setText(t.ref)}</span><span>Try <b>${fmtNum(t.reps, 1)} × ${fmtNum(round(toDisplay(t.weight, p.unit), 1))}</b> ${t.why === 'weight' ? '(+weight)' : '(+1 rep)'}</span></button>` : ''}
      <div class="chips scroll-x entry-chips">
        <button class="chip ${lbl ? 'on' : ''}" data-a="panel" data-p="labels" style="${lbl ? `--chip:${lbl.color}` : ''}">${icon('tag')}${lbl ? lbl.name : 'Label'}</button>
        <button class="chip ${p.panel === 'plates' ? 'on' : ''}" data-a="panel" data-p="plates">${icon('plate')}Plates</button>
        <button class="chip ${p.bw ? 'on' : ''}" data-a="bw">${icon('person')}${p.bw ? 'Bodyweight +' : 'Weight'}</button>
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
    if (!inst._keys) {
      inst._keys = true;
      // Hardware keyboard support (desktop / iPad).
      const onKey = e => {
        if (!document.body.contains(inst.el)) { document.removeEventListener('keydown', onKey); return; }
        if (e.target.matches('input,textarea')) return;
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
    time: (el, ev, p, inst) => { const t = new Date(el.value).getTime(); if (Number.isFinite(t)) { p.ts = Math.min(t, Date.now()); } },
  },
  actions: {
    field: (el, ev, p, inst) => { p.field = el.dataset.f; p.fresh = true; p.panel = null; p.hideKeys = false; inst.rerender(); },
    key: (el, ev, p, inst) => { press(p, el.dataset.k); navigator.vibrate?.(8); inst.rerender(); },
    'next-field': (el, ev, p, inst) => { p.field = p.field === 'reps' ? 'weight' : 'reps'; p.fresh = true; inst.rerender(); },
    'hide-keypad': (el, ev, p, inst) => { p.hideKeys = true; inst.rerender(); },
    step: (el, ev, p, inst) => {
      const f = el.dataset.f, d = +el.dataset.d;
      p[f] = trim(Math.max(0, (num(p[f]) || 0) + d)); p.fresh = true; p.field = f;
      if (f === 'weight') p.side = null;
      inst.rerender();
    },
    'apply-target': (el, ev, p, inst) => {
      const t = target(p); if (!t) return;
      p.reps = trim(t.reps); p.weight = trim(round(toDisplay(t.weight, p.unit), 2)); p.fresh = true; p.side = null; inst.rerender();
    },
    panel: (el, ev, p, inst) => { const w = el.dataset.p; p.panel = p.panel === w ? null : w; if (w === 'plates') p.side = null; inst.rerender(); },
    'close-panel': (el, ev, p, inst) => { p.panel = null; p.hideKeys = false; inst.rerender(); },
    'pick-label': (el, ev, p, inst) => { p.label = el.dataset.l || null; p.panel = null; inst.rerender(); },
    bw: (el, ev, p, inst) => { p.bw = !p.bw; if (p.bw && p.fresh && num(p.weight) && store.setsFor(p.exId).every(s => !s.bw)) p.weight = '0'; inst.rerender(); },
    unit: (el, ev, p, inst) => {
      const kg = weightKg(p);
      p.unit = p.unit === 'kg' ? 'lb' : 'kg';
      p.weight = p.weight === '' ? '' : trim(round(toDisplay(kg, p.unit), 1)); p.side = null; inst.rerender();
    },
    'time-now': (el, ev, p, inst) => { p.ts = null; p.panel = null; inst.rerender(); },
    'add-plate': (el, ev, p, inst) => { p.side.push(+el.dataset.w); p.side.sort((a, b) => b - a); syncPlates(p); inst.rerender(); },
    'remove-plate': (el, ev, p, inst) => { p.side.splice(+el.dataset.i, 1); syncPlates(p); inst.rerender(); },
    'clear-plates': (el, ev, p, inst) => { p.side = []; syncPlates(p); inst.rerender(); },
    bar: (el, ev, p, inst) => { p.bar = +el.dataset.b; syncPlates(p); inst.rerender(); },
    'note-chip': (el, ev, p, inst) => { p.note = el.dataset.n; inst.rerender(); },
    save: (el, ev, p, inst) => save(p, inst),
    delete: async (el, ev, p, inst) => {
      if (!(await confirmDialog({ title: 'Delete this set?', confirm: 'Delete Set' }))) return;
      const undo = store.deleteSet(p.setId); inst.close(); toast('Set deleted', { action: 'Undo', onAction: undo });
    },
  },
};

function syncPlates(p) { p.weight = trim(p.bar + 2 * p.side.reduce((a, b) => a + b, 0)); p.fresh = true; }

function press(p, k) {
  const f = p.field;
  let v = p[f];
  if (k === 'del') v = p.fresh ? '' : v.slice(0, -1);
  else if (k === '.') v = p.fresh || v === '' ? '0.' : v.includes('.') ? v : v + '.';
  else {
    if (p.fresh) v = k;
    else if (v === '0') v = k;
    else if (!(v.includes('.') && v.split('.')[1].length >= 2) && v.replace('.', '').length < 6) v += k;
  }
  p[f] = v; p.fresh = false;
  if (f === 'weight') p.side = null;
}

function save(p, inst) {
  const reps = num(p.reps);
  if (!(reps > 0)) {
    p.field = 'reps'; p.fresh = true; p.panel = null; inst.rerender();
    inst.panel.querySelector('.num-field.reps')?.classList.add('shake');
    return;
  }
  const weight = round(weightKg(p), 4);
  const pr = isPR(p);
  const data = { reps, weight, label: p.label, note: p.note.trim(), bw: p.bw };
  if (p.setId) {
    store.updateSet(p.setId, { ...data, ts: p.ts });
    inst.close();
    toast('Set updated', { iconName: 'check' });
    return;
  }
  const before = store.allSets().filter(s => dayKey(s.ts) === dayKey(Date.now())).length;
  const s = store.addSet({ exId: p.exId, ...data, ts: p.ts ?? Date.now() });
  inst.close();
  if (p.ts == null) startRest(p.exId);
  const st = store.settings();
  if (pr && st.celebrations) {
    celebrate();
    toast(`New record: ${setText(s)}`, { kind: 'gold', iconName: 'trophy', action: 'Undo', onAction: () => store.deleteSet(s.id) });
  } else if (before === 0 && p.ts == null && st.dailyCongrats) {
    const w = weeklyStreak(store.allSets(), st.weeklyGoal);
    toast(`First set today · ${w.thisWeek}/${w.goal} this week${w.streak ? ` · ${w.streak} week streak` : ''}`, { iconName: 'flame', action: 'Undo', onAction: () => store.deleteSet(s.id) });
  } else {
    toast(`Logged ${setText(s)}`, { iconName: 'check', action: 'Undo', onAction: () => store.deleteSet(s.id), ms: 2600 });
  }
}
