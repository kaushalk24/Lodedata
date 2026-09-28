/* My Exercises (search / create / library) and the workout folder screen. */
import { html, matches, esc, relTime } from '../util.js';
import { icon, EQUIP_ICON } from '../icons.js';
import * as store from '../store.js';
import { LIBRARY, LIB_BY_ID, MUSCLES, EQUIPMENT } from '../library.js';
import { registerScreen, renderScreen, push, pop, openSheet, toast, choose, confirmDialog, header, backBtn, circle, emptyState } from '../ui.js';
import { exRow } from './common.js';
import { findDuplicates, pairKey } from '../smart.js';
import { bodyMap } from '../bodymap.js';
import { workoutEditor } from './home.js';

const searchDock = (p, placeholder, { left = '', right = '' } = {}) => html`
  <div class="dock ${p.searching ? 'searching' : ''}">
    <span class="when-idle">${left}</span>
    <label class="search"><span class="search-icon">${icon('search')}</span>
      <input id="search-${p.key}" type="search" placeholder="${placeholder}" value="${p.q || ''}" data-in="q" autocomplete="off" autocorrect="off" enterkeyhint="done">
      <button class="search-clear" data-a="clear-q" aria-label="Clear" ${p.q ? '' : 'hidden'}>${icon('x')}</button></label>
    <span class="when-idle">${right}</span>
    <span class="when-search">${circle('end-search', 'x', 'Close search')}</span>
  </div>`;

function libRow(e, { inWorkout = false } = {}) {
  return html`<div class="row lib">
    <button class="lib-add" data-a="add-lib" data-id="${e.id}" aria-label="Add ${e.name}">${icon('plus')}</button>
    <span class="lib-eq">${icon(EQUIP_ICON[e.equipment])}</span>
    <button class="row-main" data-a="add-lib" data-id="${e.id}"><span class="row-title">${e.name}</span>
      <span class="row-sub">${e.primary.concat(e.secondary).map(m => MUSCLES[m]).join(', ')}</span></button>
    <button class="lib-info" data-a="lib-info" data-id="${e.id}" aria-label="About ${e.name}">${icon('info')}</button>
  </div>`;
}

/** Search results: create row, matching own exercises, then library by popularity. */
function results(p, { wid = null } = {}) {
  const q = (p.q || '').trim();
  const mine = store.sortedExercises().filter(e => matches(e.name, q));
  const own = new Set(store.getState().exercises.map(e => e.libId).filter(Boolean));
  const ownNames = new Set(store.getState().exercises.map(e => e.name.toLowerCase()));
  const lib = q ? LIBRARY.filter(e => !own.has(e.id) && !ownNames.has(e.name.toLowerCase()) && matches(e.name, q)).slice(0, 40) : [];
  const w = wid ? store.workout(wid) : null;
  const exact = mine.some(e => e.name.toLowerCase() === q.toLowerCase());
  const mineRow = e => w
    ? exRow(e, { action: 'toggle-in', trailing: html`<span class="check ${w.exIds.includes(e.id) ? 'on' : ''}">${icon('check')}</span>` })
    : exRow(e);
  return html`
    ${q && !exact ? html`<div class="card list"><button class="row accent" data-a="create"><span class="row-icon">${icon('plus')}</span><span class="row-main">Create “${q}”</span></button></div>` : ''}
    ${mine.length ? html`<div class="card list">${mine.map(mineRow)}</div>` : ''}
    ${lib.length ? html`<div class="list-caption">By Popularity</div><div class="card list">${lib.map(e => libRow(e))}</div>` : ''}
    ${q && !mine.length && !lib.length ? html`<p class="muted center">No match. Create it and it will learn the muscles from the name.</p>` : ''}`;
}

/** Switch the screen into search mode without re-rendering the input (keeps the keyboard up). */
function showResults(inst) {
  const p = inst.p;
  p.searching = true;
  inst.el.querySelector('.dock')?.classList.add('searching');
  const c = inst.el.querySelector('.content');
  let r = c.querySelector('.results');
  if (!r) { c.innerHTML = '<div class="results"></div>'; r = c.querySelector('.results'); }
  r.innerHTML = String(results(p, { wid: p.id }));
  inst.el.querySelector('.search-clear')?.toggleAttribute('hidden', !p.q);
}
const searchInputs = { q: (el, ev, p, inst) => { p.q = el.value; showResults(inst); } };
const wireSearchFocus = (el, p, inst) => el.querySelector('input[type=search]')?.addEventListener('focus', () => showResults(inst));

async function addFromLibrary(libId, p) {
  const lib = LIB_BY_ID[libId];
  const ex = store.addExercise(lib.name, { libId });
  if (p.id) { const w = store.workout(p.id); if (!w.exIds.includes(ex.id)) store.toggleInWorkout(p.id, ex.id); toast(`Added ${ex.name}`); }
  else push('exercise', { id: ex.id });
}

const searchActions = {
  'clear-q': (el, ev, p, inst) => { p.q = ''; const i = inst.el.querySelector('input[type=search]'); i.value = ''; showResults(inst); i.focus(); },
  'end-search': (el, ev, p, inst) => { p.q = ''; p.searching = false; document.activeElement?.blur(); renderScreen(inst); },
  create: (el, ev, p, inst) => {
    const ex = store.addExercise(p.q.trim());
    p.q = ''; p.searching = false; document.activeElement?.blur();
    if (p.id) { store.toggleInWorkout(p.id, ex.id); renderScreen(inst); toast(`Created ${ex.name}`); }
    else push('exercise', { id: ex.id });
  },
  'add-lib': (el, ev, p) => addFromLibrary(el.dataset.id, p),
  'lib-info': (el, ev, p) => libInfo(el.dataset.id, p),
};

registerScreen('exercises', {
  render(p) {
    p.key ??= 'ex';
    let list = store.sortedExercises();
    if (p.sort === 'az') list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    return html`${header({ left: backBtn(), title: 'Exercises', right: circle('menu', 'dots', 'More') })}
      <div class="scroll"><div class="content">
        ${p.searching ? html`<div class="results">${results(p)}</div>` : list.length
          ? html`${dupRow()}<div class="card list">${list.map(e => exRow(e))}</div>`
          : emptyState('No exercises yet', 'Search below to add from the library, or type any name to create your own.', '', 'books')}
      </div></div>
      ${searchDock(p, 'Search or add')}`;
  },
  mount: wireSearchFocus,
  inputs: searchInputs,
  actions: {
    ...searchActions,
    'open-exercise': el => push('exercise', { id: el.dataset.id }),
    dups: () => push('duplicates'),
    menu: async (el, ev, p, inst) => {
      const unassigned = store.getState().exercises.filter(e => !e.primary?.length).length;
      const v = await choose({ options: [
        { label: p.sort === 'az' ? 'Sort by recent' : 'Sort A to Z', value: 'sort', icon: 'filter' },
        { label: `Assign muscles${unassigned ? ` (${unassigned})` : ''}`, value: 'unassigned', icon: 'person' },
        { label: 'Browse library', value: 'library', icon: 'books' },
      ] });
      if (v === 'sort') { p.sort = p.sort === 'az' ? 'recent' : 'az'; renderScreen(inst); }
      if (v === 'unassigned') push('unassigned');
      if (v === 'library') push('library');
    },
  },
});

/* ---------- duplicate finder ---------- */
const duplicates = () => findDuplicates(store.getState().exercises, store.setsFor, new Set(store.getState().ui.dupIgnore || []));
function dupRow() {
  const n = duplicates().length;
  return n ? html`<button class="card row warn" data-a="dups"><span class="row-icon">${icon('copy')}</span><span class="row-main">${n} possible duplicate${n === 1 ? '' : 's'}</span><span class="chev">${icon('chevronRight')}</span></button>` : '';
}
const exSummary = ex => {
  const sets = store.setsFor(ex.id);
  return sets.length ? `${sets.length} set${sets.length === 1 ? '' : 's'} · last ${relTime(sets[sets.length - 1].ts).toLowerCase()}` : 'No sets';
};

registerScreen('duplicates', {
  render() {
    const pairs = duplicates();
    return html`${header({ left: backBtn(), title: 'Duplicates' })}
      <div class="scroll"><div class="content">
        ${pairs.length ? html`<p class="hint">These look like the same exercise under two names. Merging moves every set into the one you keep, so its history and records are complete again.</p>
          ${pairs.map(({ keep, drop }) => html`<div class="card pad dup">
            <div class="dup-pair">
              <div class="dup-row"><div><b>${keep.name}</b><span class="muted small">${exSummary(keep)}</span></div>
                <button class="btn accent small" data-a="merge" data-keep="${keep.id}" data-drop="${drop.id}" aria-label="Keep ${keep.name}">Keep</button></div>
              <span class="dup-eq">${icon('updown')}</span>
              <div class="dup-row"><div><b>${drop.name}</b><span class="muted small">${exSummary(drop)}</span></div>
                <button class="btn small" data-a="merge" data-keep="${drop.id}" data-drop="${keep.id}" aria-label="Keep ${drop.name}">Keep</button></div></div>
            <button class="link center" data-a="not-dup" data-a-id="${keep.id}" data-b-id="${drop.id}">They're different exercises</button></div>`)}`
        : emptyState('No duplicates', 'Every exercise has its own name and history.', '', 'check')}
      </div></div>`;
  },
  actions: {
    merge: async el => {
      const keep = store.exercise(el.dataset.keep), drop = store.exercise(el.dataset.drop);
      const n = store.setsFor(drop.id).length;
      if (!(await confirmDialog({ title: `Merge into “${keep.name}”?`, message: `${n} set${n === 1 ? '' : 's'} from “${drop.name}” will move, then “${drop.name}” is removed. This can't be undone.`, confirm: 'Merge', destructive: false }))) return;
      store.mergeExercise(drop.id, keep.id);
      toast(`Merged into ${keep.name}`, { iconName: 'check' });
    },
    'not-dup': el => {
      const ui = store.getState().ui;
      store.setUi('dupIgnore', [...(ui.dupIgnore || []), pairKey(el.dataset.aId, el.dataset.bId)]);
    },
  },
});

/* ---------- library browser (by muscle) ---------- */
registerScreen('library', {
  render(p) {
    p.m ??= 'chest';
    const list = LIBRARY.filter(e => e.primary.includes(p.m));
    return html`${header({ left: backBtn(), title: 'Library' })}
      <div class="scroll"><div class="content">
        <div class="chips scroll-x">${Object.entries(MUSCLES).map(([k, n]) => html`<button class="chip ${p.m === k ? 'on' : ''}" data-a="m" data-m="${k}">${n}</button>`)}</div>
        <div class="card list">${list.map(e => libRow(e))}</div>
      </div></div>`;
  },
  actions: {
    m: (el, ev, p, inst) => { p.m = el.dataset.m; renderScreen(inst); },
    'add-lib': (el) => { const lib = LIB_BY_ID[el.dataset.id]; const ex = store.addExercise(lib.name, { libId: lib.id }); push('exercise', { id: ex.id }); },
    'lib-info': (el, ev, p) => libInfo(el.dataset.id, {}),
  },
});

/* ---------- library info ---------- */
function libInfo(libId, ctx) {
  const e = LIB_BY_ID[libId];
  openSheet({
    render: () => html`<div class="sheet-grab"></div>
      <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>${e.name}</h2><span class="circle ghost"></span></div>
      <div class="info-map">${bodyMap({ small: true, cls: m => e.primary.includes(m) ? 'primary' : e.secondary.includes(m) ? 'secondary' : 'none' })}</div>
      <div class="legend"><span><i class="dot primary"></i>Primary</span><span><i class="dot secondary"></i>Secondary</span></div>
      <div class="card list">
        <div class="row static"><span class="row-main">Equipment</span><span class="row-meta">${EQUIPMENT[e.equipment]}</span></div>
        <div class="row static"><span class="row-main">Primary</span><span class="row-meta">${e.primary.map(m => MUSCLES[m]).join(', ')}</span></div>
        ${e.secondary.length ? html`<div class="row static"><span class="row-main">Secondary</span><span class="row-meta">${e.secondary.map(m => MUSCLES[m]).join(', ')}</span></div>` : ''}
      </div>
      <button class="btn accent block" data-a="add">${ctx.id ? 'Add to workout' : 'Add to My Exercises'}</button>`,
    actions: { add: (el, ev, p, inst) => { inst.close(); addFromLibrary(libId, ctx); } },
  });
}

/* ---------- workout folder ---------- */
registerScreen('workout', {
  render(p) {
    p.key ??= 'w';
    const w = store.workout(p.id);
    if (!w) return html`${header({ left: backBtn() })}<div class="scroll"></div>`;
    const list = w.exIds.map(store.exercise).filter(Boolean).sort((a, b) => store.lastTs(b.id) - store.lastTs(a.id));
    const now = Date.now();
    return html`${header({ left: backBtn(), title: w.name, right: html`${circle('share-workout', 'share', 'Share')}${circle('menu', 'dots', 'More')}` })}
      <div class="scroll"><div class="content">
        ${p.searching ? html`<div class="results">${results(p, { wid: w.id })}</div>` : html`
          ${w.desc ? html`<button class="card plan-note ${p.expand ? 'open' : ''}" data-a="expand">${icon('note')}<span>${w.desc}</span></button>` : ''}
          ${list.length ? folderList(w, list, now)
            : emptyState('Empty workout', 'Tap “Add or remove” below to put exercises in this folder.', '', 'book')}`}
      </div></div>
      ${searchDock(p, 'Add or remove', { left: circle('edit-desc', 'note', 'Plan and notes'), right: circle('duplicate', 'copy', 'Duplicate workout') })}`;
  },
  mount: wireSearchFocus,
  inputs: searchInputs,
  actions: {
    ...searchActions,
    'open-exercise': el => push('exercise', { id: el.dataset.id }),
    'toggle-in': (el, ev, p, inst) => {
      store.toggleInWorkout(p.id, el.dataset.id);
      showResults(inst);
    },
    expand: (el, ev, p, inst) => { p.expand = !p.expand; renderScreen(inst); },
    ungroup: (el, ev, p) => { const undo = store.removeSuperset(p.id, +el.dataset.i); toast('Superset removed', { action: 'Undo', onAction: undo }); },
    'edit-desc': (el, ev, p) => workoutEditor(p.id),
    duplicate: (el, ev, p) => { const w = store.duplicateWorkout(p.id); toast(`Created ${w.name}`); },
    'share-workout': async (el, ev, p) => {
      const w = store.workout(p.id);
      const text = `${w.name}\n${w.exIds.map(id => `• ${store.exercise(id)?.name}`).join('\n')}${w.desc ? `\n\n${w.desc}` : ''}`;
      await shareText(text, w.name);
    },
    menu: async (el, ev, p) => {
      const w = store.workout(p.id);
      const v = await choose({ title: w.name, options: [
        { label: 'Create superset or circuit…', value: 'superset', icon: 'layers' },
        { label: 'Edit name, colour and plan', value: 'edit', icon: 'edit' },
        { label: 'Duplicate', value: 'dup', icon: 'copy' },
        { label: 'Delete workout', value: 'del', icon: 'trash', destructive: true },
      ] });
      if (v === 'superset') supersetSheet(p.id);
      if (v === 'edit') workoutEditor(p.id);
      if (v === 'dup') { const c = store.duplicateWorkout(p.id); toast(`Created ${c.name}`); }
      if (v === 'del' && await confirmDialog({ title: `Delete “${w.name}”?`, message: 'Exercises and their history are kept.', confirm: 'Delete Workout' })) {
        const undo = store.deleteWorkout(p.id); pop(); toast(`Deleted ${w.name}`, { action: 'Undo', onAction: undo });
      }
    },
  },
});

/** Exercises by recency, with each superset kept together as one block. */
function folderList(w, list, now) {
  const groups = (w.supersets || []).map((g, gi) => ({ gi, ids: g.filter(id => store.exercise(id) && w.exIds.includes(id)) })).filter(g => g.ids.length >= 2);
  const grouped = new Set(groups.flatMap(g => g.ids));
  const items = [
    ...groups.map(g => ({ g, ts: Math.max(...g.ids.map(store.lastTs)) })),
    ...list.filter(e => !grouped.has(e.id)).map(e => ({ e, ts: store.lastTs(e.id) })),
  ].sort((a, b) => b.ts - a.ts);
  const out = []; let run = [];
  const flush = () => { if (run.length) out.push(html`<div class="card list">${run}</div>`); run = []; };
  for (const it of items) {
    if (it.e) { run.push(exRow(it.e, { detail: true, now })); continue; }
    flush();
    out.push(html`<div class="card list ss-group"><div class="ss-head"><span>${icon('layers')}${it.g.ids.length > 2 ? 'Circuit' : 'Superset'}</span>
      <button class="link" data-a="ungroup" data-i="${it.g.gi}">Ungroup</button></div>
      ${it.g.ids.map(id => exRow(store.exercise(id), { detail: true, now }))}</div>`);
  }
  flush();
  return out;
}

/** Pick exercises in the order you'll do them. */
function supersetSheet(wid) {
  const w = store.workout(wid);
  const exs = w.exIds.map(store.exercise).filter(Boolean);
  if (exs.length < 2) { toast('Add at least two exercises to this workout first'); return; }
  openSheet({
    cls: 'tall',
    render: p => html`<div class="sheet-grab"></div>
      <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Cancel')}<h2>Superset</h2><span class="circle ghost"></span></div>
      <div class="scroll"><p class="hint">Tap exercises in the order you'll do them. After each set the next exercise opens, and the rest timer runs after the last one.</p>
        <div class="card list">${exs.map(e => { const n = p.order.indexOf(e.id) + 1; return html`<button class="row" data-a="pick" data-id="${e.id}">
          <span class="order ${n ? 'on' : ''}">${n || ''}</span><span class="row-main"><span class="row-title">${e.name}</span></span></button>`; })}</div>
        <button class="btn accent block" data-a="save" ${p.order.length >= 2 ? '' : 'disabled'}>${p.order.length > 2 ? `Make a circuit of ${p.order.length}` : 'Make superset'}</button></div>`,
    actions: {
      pick: (el, ev, p, inst) => { const id = el.dataset.id; p.order = p.order.includes(id) ? p.order.filter(x => x !== id) : [...p.order, id]; inst.rerender(); },
      save: (el, ev, p, inst) => { store.addSuperset(wid, p.order); inst.close(); toast(p.order.length > 2 ? 'Circuit created' : 'Superset created', { iconName: 'layers' }); },
    },
  }, { order: [] });
}

export async function shareText(text, title = 'Overload') {
  try { if (navigator.share) { await navigator.share({ title, text }); return; } } catch (e) { if (e?.name === 'AbortError') return; }
  try { await navigator.clipboard.writeText(text); toast('Copied to clipboard', { iconName: 'copy' }); }
  catch { toast('Sharing is not available here'); }
}
export { esc };
