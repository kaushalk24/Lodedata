/* Body tab: recovery map, weekly sets per muscle, bodyweight, measurements, progress photos,
 * muscle assignment. Photos live only in this device's IndexedDB. */
import { html, relTime, fmtNum, fmtShortDate, fmtLongDate, fmtW, round } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { MUSCLES, EQUIPMENT } from '../library.js';
import { muscleReport, recoveryState } from '../stats.js';
import { bodyMap } from '../bodymap.js';
import { lineChart } from '../chart.js';
import { registerScreen, renderScreen, push, openSheet, toast, choose, confirmDialog, promptDialog, header, backBtn, circle, emptyState, topScreen } from '../ui.js';
import { exRow, unit } from './common.js';

const STATE_NAME = { fresh: 'Just trained', recovering: 'Recovering', rested: 'Rested', none: 'Not trained' };
const report = () => muscleReport(store.allSets(), store.muscleMap);

function weekSetsNote(n) {
  if (n >= 20) return 'high';
  if (n >= 10) return 'good';
  return n > 0 ? 'low' : '';
}

registerScreen('body', {
  render() {
    const rep = report(), now = Date.now(), u = unit();
    const bw = [...store.getState().body].sort((a, b) => b.ts - a.ts)[0];
    const unassigned = store.getState().exercises.filter(e => !e.primary?.length).length;
    const muscles = Object.keys(MUSCLES).map(m => ({ m, last: rep[m]?.last || 0, week: rep[m]?.weekSets || 0 }))
      .sort((a, b) => (b.last - a.last) || a.m.localeCompare(b.m));
    return html`${header({ left: circle('refresh', 'refresh', 'Refresh'), title: 'Body', right: circle('add-weight', 'plus', 'Log bodyweight') })}
      <div class="scroll"><div class="content">
        <div class="card list">
          <button class="row" data-a="bodyweight"><span class="row-icon purple">${icon('tabBody')}</span><span class="row-main"><span class="row-title">Weight</span></span>
            <span class="row-meta">${bw ? `${fmtW(bw.kg, u)} ${u}` : 'Add'}</span><span class="chev">${icon('chevronRight')}</span></button>
          <button class="row" data-a="measurements"><span class="row-icon purple">${icon('target')}</span><span class="row-main"><span class="row-title">Measurements</span></span>
            <span class="row-meta">${measureSummary()}</span><span class="chev">${icon('chevronRight')}</span></button>
          <button class="row" data-a="photos"><span class="row-icon purple">${icon('camera')}</span><span class="row-main"><span class="row-title">Progress photos</span></span>
            <span class="row-meta">${photoCache.list ? photoCache.list.length || 'Add' : ''}</span><span class="chev">${icon('chevronRight')}</span></button>
        </div>
        <div class="legend"><span><i class="dot fresh"></i>Just Trained</span><span><i class="dot recovering"></i>Recovering</span><span><i class="dot rested"></i>Rested</span></div>
        ${bodyMap({ interactive: true, cls: m => recoveryState(rep[m]?.last, now) })}
        ${unassigned ? html`<button class="card row warn" data-a="unassigned"><span class="row-icon">${icon('warning')}</span><span class="row-main">Unassigned Exercises</span><span class="row-meta">${unassigned}</span><span class="chev">${icon('chevronRight')}</span></button>` : ''}
        <div class="card list">${muscles.map(x => html`<button class="row" data-a="muscle" data-m="${x.m}">
          <i class="dot ${recoveryState(x.last, now)}"></i><span class="row-main"><span class="row-title">${MUSCLES[x.m]}</span>
          ${x.week ? html`<span class="row-sub"><span class="wk ${weekSetsNote(x.week)}">${fmtNum(x.week, 1)} sets</span> this week</span>` : ''}</span>
          <span class="row-meta">${x.last ? relTime(x.last, now) : '–'}</span><span class="chev">${icon('chevronRight')}</span></button>`)}</div>
        <p class="hint">Sets count hard sets in the last 7 days: 1 for a muscle an exercise targets, 0.5 for one it assists. Around 10–20 a week suits most muscle-building goals.</p>
      </div></div>`;
  },
  mount: (el, p, inst) => { if (!photoCache.list) loadPhotos().then(() => renderScreen(inst)); },
  actions: {
    refresh: (el, ev, p, inst) => { renderScreen(inst); toast('Updated'); },
    'add-weight': () => addWeight(),
    bodyweight: () => push('bodyweight'),
    measurements: () => push('measurements'),
    photos: () => push('photos'),
    unassigned: () => push('unassigned'),
    muscle: el => push('muscle', { m: el.dataset.m }),
  },
});

async function addWeight() {
  const u = unit();
  const last = [...store.getState().body].sort((a, b) => b.ts - a.ts)[0];
  const v = await promptDialog({ title: `Bodyweight (${u})`, type: 'number', value: last ? fmtW(last.kg, u).replace(/,/g, '') : '', confirm: 'Save', hint: 'Used for bodyweight exercises like pull-ups and dips.' });
  const n = parseFloat(v);
  if (n > 0) { store.addBodyWeight(u === 'lb' ? n * 0.45359237 : n); toast('Bodyweight saved', { iconName: 'check' }); }
}

registerScreen('muscle', {
  render(p) {
    const rep = report()[p.m] || { last: 0, weekSets: 0 };
    const exs = store.sortedExercises().filter(e => e.primary?.includes(p.m) || e.secondary?.includes(p.m));
    const primary = exs.filter(e => e.primary.includes(p.m)), secondary = exs.filter(e => !e.primary.includes(p.m));
    const state = recoveryState(rep.last);
    return html`${header({ left: backBtn(), title: MUSCLES[p.m] })}
      <div class="scroll"><div class="content">
        <div class="info-map">${bodyMap({ small: true, cls: m => m === p.m ? state === 'none' ? 'primary' : state : 'none' })}</div>
        <div class="tiles three">
          <div class="tile"><span>Status</span><b class="st-${state}">${STATE_NAME[state]}</b></div>
          <div class="tile"><span>Last trained</span><b>${rep.last ? relTime(rep.last) : '–'}</b></div>
          <div class="tile"><span>Sets this week</span><b>${fmtNum(rep.weekSets, 1)}</b></div>
        </div>
        ${primary.length ? html`<div class="section-label">Targets ${MUSCLES[p.m].toLowerCase()}</div><div class="card list">${primary.map(e => exRow(e, { detail: true }))}</div>` : ''}
        ${secondary.length ? html`<div class="section-label">Also works it</div><div class="card list">${secondary.map(e => exRow(e, { detail: true }))}</div>` : ''}
        ${!exs.length ? emptyState('No exercises yet', 'Exercises you add that work this muscle show up here.') : ''}
      </div></div>`;
  },
  actions: { 'open-exercise': el => push('exercise', { id: el.dataset.id }) },
});

registerScreen('bodyweight', {
  render() {
    const u = unit();
    const list = [...store.getState().body].sort((a, b) => a.ts - b.ts);
    const recent = list.slice(-30);
    return html`${header({ left: backBtn(), title: 'Weight', right: circle('add-weight', 'plus', 'Log bodyweight') })}
      <div class="scroll"><div class="content">
        ${list.length ? html`
          <div class="chart-head"><div class="big-set"><span class="wt">${fmtW(list[list.length - 1].kg, u)} <small>${u}</small></span></div>
            ${list.length > 1 ? html`<span class="muted small">${fmtW(list[list.length - 1].kg - list[0].kg, u)} ${u} since ${fmtShortDate(list[0].ts)}</span>` : ''}</div>
          ${lineChart([{ name: 'Weight', color: 'var(--purple)', values: recent.map(b => round(b.kg, 2)), fmt: v => `${fmtW(v, u)} ${u}` }], recent.map(b => fmtShortDate(b.ts)))}
          <div class="card list">${[...list].reverse().map((b, i, a) => { const prev = a[i + 1]; const d = prev ? b.kg - prev.kg : 0; return html`
            <button class="row" data-a="entry" data-id="${b.id}"><span class="row-main">${fmtShortDate(b.ts)}</span>
            ${prev ? html`<span class="row-sub ${d > 0 ? 'up' : d < 0 ? 'down' : ''}">${d > 0 ? '+' : ''}${fmtW(d, u)}</span>` : ''}<span class="row-meta strong">${fmtW(b.kg, u)} ${u}</span></button>`; })}</div>`
          : emptyState('No weigh-ins yet', 'Tap + to log your bodyweight. It also counts toward pull-ups, dips and other bodyweight sets.', '', 'scale')}
      </div></div>`;
  },
  actions: {
    'add-weight': () => addWeight(),
    entry: async el => {
      const v = await choose({ options: [{ label: 'Delete entry', value: 'del', icon: 'trash', destructive: true }] });
      if (v === 'del') { const undo = store.deleteBodyWeight(el.dataset.id); toast('Entry deleted', { action: 'Undo', onAction: undo }); }
    },
  },
});

/* ---------- measurements ---------- */
export const MEASURES = [
  ['bodyfat', 'Body fat', '%'], ['neck', 'Neck'], ['shoulders', 'Shoulders'], ['chest', 'Chest'], ['arms', 'Arms'],
  ['forearms', 'Forearms'], ['waist', 'Waist'], ['hips', 'Hips'], ['thighs', 'Thighs'], ['calves', 'Calves'],
];
const MEASURE = Object.fromEntries(MEASURES.map(([k, name, u]) => [k, { name, pct: u === '%' }]));
/** Tape measurements are stored in cm and shown in inches for lb users. */
const lenUnit = () => (unit() === 'lb' ? 'in' : 'cm');
const showLen = (key, v) => (MEASURE[key].pct ? v : unit() === 'lb' ? v / 2.54 : v);
const fromLen = (key, v) => (MEASURE[key].pct ? v : unit() === 'lb' ? v * 2.54 : v);
const mUnit = key => (MEASURE[key].pct ? '%' : lenUnit());
const fmtM = (key, v) => `${fmtNum(round(showLen(key, v), 1), 1)} ${mUnit(key)}`;
const byKey = key => store.getState().measures.filter(m => m.key === key).sort((a, b) => a.ts - b.ts);

function measureSummary() {
  const all = store.getState().measures;
  if (!all.length) return 'Add';
  const waist = byKey('waist');
  return waist.length ? `Waist ${fmtM('waist', waist[waist.length - 1].value)}` : `${new Set(all.map(m => m.key)).size} tracked`;
}

registerScreen('measurements', {
  render() {
    const rows = MEASURES.map(([key]) => ({ key, list: byKey(key) })).filter(r => r.list.length);
    return html`${header({ left: backBtn(), title: 'Measurements', right: circle('log', 'plus', 'Log measurements') })}
      <div class="scroll"><div class="content">
        ${rows.length ? html`<div class="card list">${rows.map(({ key, list }) => { const last = list[list.length - 1], first = list[0], d = last.value - first.value; return html`
          <button class="row" data-a="open" data-k="${key}"><span class="row-main"><span class="row-title">${MEASURE[key].name}</span>
            <span class="row-sub">${list.length > 1 ? `${d > 0 ? '+' : d < 0 ? '−' : '±'}${fmtNum(round(Math.abs(showLen(key, d)), 1), 1)} ${mUnit(key)} since ${fmtShortDate(first.ts)}` : fmtShortDate(last.ts)}</span></span>
            <span class="row-meta strong">${fmtM(key, last.value)}</span><span class="chev">${icon('chevronRight')}</span></button>`; })}</div>
          <p class="hint">Measure at the same time of day, relaxed, at the widest point (waist at the navel). Arms and thighs: pick one side and stick with it.</p>`
        : emptyState('No measurements yet', 'Track waist, chest, arms and more to see changes the scale misses.', html`<button class="btn accent" data-a="log">Log measurements</button>`, 'target')}
      </div></div>`;
  },
  actions: { log: () => logMeasures(), open: el => push('measure', { key: el.dataset.k }) },
});

function logMeasures() {
  openSheet({
    cls: 'tall',
    render: () => html`<div class="sheet-grab"></div>
      <form data-form="save" class="editor">
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Cancel')}<h2>Measurements</h2><button type="submit" class="circle accent" aria-label="Save">${icon('check')}</button></div>
        <div class="scroll"><p class="hint">Fill in the ones you measured today. Empty fields are skipped.</p>
          <div class="card list">${MEASURES.map(([key]) => { const last = byKey(key).pop(); return html`<label class="row static m-row"><span class="row-main">${MEASURE[key].name}</span>
            <input id="m-${key}" class="m-input" type="number" inputmode="decimal" step="any" min="0" name="${key}" placeholder="${last ? fmtNum(round(showLen(key, last.value), 1), 1) : ''}"><span class="m-unit">${mUnit(key)}</span></label>`; })}</div></div>
      </form>`,
    forms: {
      save: (form, ev, p, inst) => {
        const vals = {};
        for (const [key] of MEASURES) {
          const v = parseFloat(form.querySelector(`#m-${key}`).value);
          if (v > 0 && (MEASURE[key].pct ? v < 80 : v < 400)) vals[key] = round(fromLen(key, v), 2);
        }
        if (!Object.keys(vals).length) { toast('Enter at least one measurement'); return; }
        store.addMeasures(vals);
        inst.close(); toast(`Saved ${Object.keys(vals).length} measurement${Object.keys(vals).length === 1 ? '' : 's'}`, { iconName: 'check' });
      },
    },
  });
}

registerScreen('measure', {
  render(p) {
    const list = byKey(p.key), name = MEASURE[p.key].name;
    const recent = list.slice(-30);
    return html`${header({ left: backBtn(), title: name, right: circle('add', 'plus', `Log ${name}`) })}
      <div class="scroll"><div class="content">
        ${list.length ? html`<div class="chart-head"><div class="big-set"><span class="wt">${fmtNum(round(showLen(p.key, list[list.length - 1].value), 1), 1)} <small>${mUnit(p.key)}</small></span></div></div>
          ${lineChart([{ name, color: 'var(--purple)', values: recent.map(m => round(showLen(p.key, m.value), 2)), fmt: v => `${fmtNum(v, 1)} ${mUnit(p.key)}` }], recent.map(m => fmtShortDate(m.ts)))}
          <div class="card list">${[...list].reverse().map(m => html`<button class="row" data-a="entry" data-id="${m.id}"><span class="row-main">${fmtShortDate(m.ts)}</span><span class="row-meta strong">${fmtM(p.key, m.value)}</span></button>`)}</div>`
        : emptyState(`No ${name.toLowerCase()} entries`, 'Tap + to add one.', '', 'target')}
      </div></div>`;
  },
  actions: {
    add: async (el, ev, p) => {
      const v = parseFloat(await promptDialog({ title: `${MEASURE[p.key].name} (${mUnit(p.key)})`, type: 'number', confirm: 'Save' }));
      if (v > 0) store.addMeasures({ [p.key]: round(fromLen(p.key, v), 2) });
    },
    entry: async el => {
      const v = await choose({ options: [{ label: 'Delete entry', value: 'del', icon: 'trash', destructive: true }] });
      if (v === 'del') { const undo = store.deleteMeasure(el.dataset.id); toast('Entry deleted', { action: 'Undo', onAction: undo }); }
    },
  },
});

/* ---------- progress photos ---------- */
const photoCache = { list: null, urls: new Map() };
async function loadPhotos() {
  try { photoCache.list = await store.listPhotos(); } catch { photoCache.list = []; }
  return photoCache.list;
}
const urlOf = ph => {
  if (!photoCache.urls.has(ph.id)) photoCache.urls.set(ph.id, URL.createObjectURL(ph.blob));
  return photoCache.urls.get(ph.id);
};
/** Shrink to 1600 px on the long side as JPEG so photos don't fill the phone. */
async function shrink(file) {
  const src = URL.createObjectURL(file);
  try {
    const img = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; });
    const scale = Math.min(1, 1600 / Math.max(img.naturalWidth, img.naturalHeight));
    const c = document.createElement('canvas');
    c.width = Math.round(img.naturalWidth * scale); c.height = Math.round(img.naturalHeight * scale);
    c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
    return await new Promise(res => c.toBlob(b => res(b || file), 'image/jpeg', 0.85));
  } catch { return file; } finally { URL.revokeObjectURL(src); }
}
export async function erasePhotos() {
  await store.clearPhotos().catch(() => {});
  for (const u of photoCache.urls.values()) URL.revokeObjectURL(u);
  photoCache.urls.clear(); photoCache.list = [];
}

registerScreen('photos', {
  render() {
    const list = photoCache.list;
    return html`${header({ left: backBtn(), title: 'Progress Photos', right: html`<label class="circle" aria-label="Add photos">${icon('plus')}<input type="file" accept="image/*" multiple data-in="photo" hidden></label>` })}
      <div class="scroll"><div class="content">
        ${!list ? html`<p class="muted center">Loading…</p>` : list.length ? html`
          <div class="photo-grid">${list.map(ph => html`<button class="photo" data-a="view" data-id="${ph.id}"><img src="${urlOf(ph)}" alt="Progress photo, ${fmtShortDate(ph.ts)}" loading="lazy"><span>${fmtShortDate(ph.ts)}</span></button>`)}</div>
          <p class="hint">Photos stay on this phone. They aren't included in backups or exports.</p>`
        : emptyState('No photos yet', 'Take one every few weeks in the same spot and light. Photos stay on this phone and are never uploaded.',
          html`<label class="btn accent">${icon('camera')} Add photo<input type="file" accept="image/*" multiple data-in="photo" hidden></label>`, 'camera')}
      </div></div>`;
  },
  mount: (el, p, inst) => { if (!photoCache.list) loadPhotos().then(() => renderScreen(inst)); },
  inputs: {
    photo: async (el, ev, p, inst) => {
      const files = [...(el.files || [])]; el.value = '';
      if (!files.length) return;
      try {
        for (const f of files) {
          const ts = f.lastModified && f.lastModified < Date.now() && f.lastModified > 946684800000 ? f.lastModified : Date.now();
          await store.addPhoto(await shrink(f), ts);
        }
        await loadPhotos();
        renderScreen(inst);
        toast(`Added ${files.length} photo${files.length === 1 ? '' : 's'}`, { iconName: 'check' });
      } catch { toast("Couldn't save the photo. Your browser may be out of storage."); }
    },
  },
  actions: { view: el => viewPhoto(el.dataset.id) },
});

function viewPhoto(id) {
  const list = photoCache.list || [];
  openSheet({
    cls: 'tall photo-sheet',
    render: p => {
      const ph = list.find(x => x.id === id);
      if (!ph) return '';
      const first = list[list.length - 1];
      const compare = p.compare && first && first.id !== ph.id;
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>${fmtLongDate(ph.ts)}</h2>${circle('delete', 'trash', 'Delete photo')}</div>
        <div class="scroll">${compare ? html`<div class="compare-pair">
            <figure><img src="${urlOf(first)}" alt="First photo"><figcaption>${fmtShortDate(first.ts)}</figcaption></figure>
            <figure><img src="${urlOf(ph)}" alt="This photo"><figcaption>${fmtShortDate(ph.ts)}</figcaption></figure></div>`
          : html`<img class="photo-full" src="${urlOf(ph)}" alt="Progress photo">`}
          ${first && first.id !== ph.id ? html`<button class="btn block" data-a="toggle">${icon('layers')} ${compare ? 'Show this photo only' : `Compare with first (${fmtShortDate(first.ts)})`}</button>` : ''}</div>`;
    },
    actions: {
      toggle: (el, ev, p, inst) => { p.compare = !p.compare; inst.rerender(); },
      delete: async (el, ev, p, inst) => {
        if (!(await confirmDialog({ title: 'Delete this photo?', message: "It isn't backed up anywhere, so this can't be undone.", confirm: 'Delete Photo' }))) return;
        await store.deletePhoto(id);
        const u = photoCache.urls.get(id); if (u) URL.revokeObjectURL(u); photoCache.urls.delete(id);
        await loadPhotos();
        inst.close();
        const top = topScreen(); if (top?.name === 'photos') renderScreen(top);
        toast('Photo deleted');
      },
    },
  }, { compare: false });
}

registerScreen('unassigned', {
  render() {
    const list = store.sortedExercises().filter(e => !e.primary?.length);
    return html`${header({ left: backBtn(), title: 'Assign Muscles' })}
      <div class="scroll"><div class="content">
        ${list.length ? html`<p class="hint">These exercises don't count toward the body map yet. Tap one to pick its muscles.</p>
          <div class="card list">${list.map(e => exRow(e, { action: 'assign' }))}</div>` : emptyState('All assigned', 'Every exercise counts toward the body map.')}
      </div></div>`;
  },
  actions: { assign: el => muscleEditor(el.dataset.id) },
});

/** Tap a muscle to cycle: off → primary → secondary → off. */
export function muscleEditor(exId) {
  const ex = store.exercise(exId);
  openSheet({
    cls: 'tall', live: true,
    render: () => {
      const e = store.exercise(exId);
      const state = m => e.primary.includes(m) ? 'primary' : e.secondary.includes(m) ? 'secondary' : '';
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>${e.name}</h2><button class="circle accent" data-a="sheet-dismiss" aria-label="Done">${icon('check')}</button></div>
        <div class="scroll">
        <div class="info-map">${bodyMap({ small: true, cls: m => state(m) || 'none' })}</div>
        <div class="legend"><span><i class="dot primary"></i>Targets</span><span><i class="dot secondary"></i>Assists</span></div>
        <p class="hint center">Tap once for a target muscle, twice for an assisting one.</p>
        <div class="chips wrap">${Object.entries(MUSCLES).map(([m, n]) => html`<button class="chip ${state(m)}" data-a="cycle" data-m="${m}">${n}</button>`)}</div>
        <div class="section-label">Equipment</div>
        <div class="chips wrap">${Object.entries(EQUIPMENT).map(([k, n]) => html`<button class="chip ${e.equipment === k ? 'on' : ''}" data-a="eq" data-k="${k}">${n}</button>`)}</div></div>`;
    },
    actions: {
      cycle: el => {
        const e = store.exercise(exId), m = el.dataset.m;
        let primary = e.primary.filter(x => x !== m), secondary = e.secondary.filter(x => x !== m);
        if (e.primary.includes(m)) secondary.push(m); else if (!e.secondary.includes(m)) primary.push(m);
        store.updateExercise(exId, { primary, secondary });
      },
      eq: el => store.updateExercise(exId, { equipment: el.dataset.k }),
    },
  });
  return ex;
}
