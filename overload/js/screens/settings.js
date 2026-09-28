/* Settings sheet with its own page stack. */
import { html, raw, fmtNum, fmtClock, dayKey } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { openSheet, toast, choose, confirmDialog, promptDialog, circle, toggle } from '../ui.js';
import { setsToCSV, buildImport, detectMapping, demoState } from '../dataio.js';
import { parseCSV } from '../util.js';
import { streakSheet } from './home.js';
import { erasePhotos } from './body.js';
import { learnedRest } from '../smart.js';

export const VERSION = '1.1.0';

const row = (a, ic, label, meta = '', extra = '') => html`<button class="row" data-a="${a}" ${raw(extra)}><span class="row-icon">${icon(ic)}</span><span class="row-main">${label}</span>${meta ? html`<span class="row-meta">${meta}</span>` : ''}<span class="chev">${icon('chevronRight')}</span></button>`;
const swRow = (a, ic, label, on) => html`<div class="row static"><span class="row-icon">${icon(ic)}</span><span class="row-main">${label}</span>${toggle(a, on)}</div>`;
/** "Learned from your sets": real median rest per exercise, where it differs from the timer by 30 s or more. */
function learnedSection(s) {
  const { byEx, overall } = learnedRest(store.allSets());
  if (!overall) return '';
  const rows = [...byEx].map(([id, r]) => ({ ex: store.exercise(id), r })).filter(x => x.ex)
    .map(x => ({ ...x, timer: x.ex.restSec ?? s.restSec })).filter(x => Math.abs(x.timer - x.r.sec) >= 30)
    .sort((a, b) => Math.abs(b.timer - b.r.sec) - Math.abs(a.timer - a.r.sec)).slice(0, 8);
  return html`<div class="section-label">Learned from your sets</div>
    <div class="card list"><div class="row static"><span class="row-main"><span class="row-title">Your typical rest</span><span class="row-sub">Median gap between sets of the same exercise</span></span>
      <b class="learned">${fmtClock(overall)}</b>${overall !== s.restSec ? html`<button class="pill-btn small" data-a="use-typical" data-s="${overall}">Use</button>` : ''}</div>
    ${rows.map(x => html`<div class="row static"><span class="row-main"><span class="row-title">${x.ex.name}</span><span class="row-sub">You rest ${fmtClock(x.r.sec)} · timer ${fmtClock(x.timer)}</span></span>
      <button class="pill-btn small" data-a="apply-rest" data-id="${x.ex.id}" data-s="${x.r.sec}">Apply</button></div>`)}
    ${rows.length > 1 ? html`<button class="row accent" data-a="apply-all-rest"><span class="row-main">Apply to all exercises</span></button>` : ''}</div>`;
}

const THEMES = { system: 'Match Device', dark: 'Dark', light: 'Light' };

const PAGES = {
  main: {
    title: 'Settings',
    render() {
      const st = store.getState(), s = st.settings;
      return html`
        <div class="card data-card"><span class="row-icon">${icon('database')}</span><div><b>Your data stays on this phone</b>
          <p class="muted small">${st.sets.length.toLocaleString()} sets · ${st.exercises.length} exercises. No account, no subscription. Back up now and then.</p></div>
          <button class="pill-btn" data-a="page" data-p="data">Backup</button></div>
        <div class="card list">
          ${row('page', 'plate', 'Gyms & Plates', store.currentGym().name, 'data-p="gyms"')}
          ${row('unit', 'scale', 'Unit', s.unit === 'kg' ? 'Metric (kg)' : 'Imperial (lb)')}
          ${row('page', 'download', 'Import & Export', '', 'data-p="data"')}
          ${row('page', 'palette', 'Display', THEMES[s.theme], 'data-p="display"')}
          ${row('streaks', 'flame', 'Streaks', `${s.weeklyGoal} / week`)}
          ${swRow('celebrations', 'trophy', 'Record Celebrations', s.celebrations)}
        </div>
        <div class="card list">
          ${row('page', 'bell', 'Workout Reminders', `${s.remindDays} days`, 'data-p="reminders"')}
          ${row('page', 'timer', 'Default Interset Rest', s.restOn ? fmtClock(s.restSec) : 'Off', 'data-p="rest"')}
          ${row('page', 'target', 'Progression Targets', s.showTargets ? `${s.repLow}–${s.repHigh} reps` : 'Off', 'data-p="targets"')}
        </div>
        <div class="card list">
          ${row('page', 'info', 'Help & Install', '', 'data-p="help"')}
          <div class="row static"><span class="row-icon">${icon('sparkle')}</span><span class="row-main">Version</span><span class="row-meta">${VERSION}</span></div>
        </div>
        <p class="hint center">Every feature is free. There is no Pro tier.</p>`;
    },
  },
  gyms: {
    title: 'Gyms & Plates',
    render() {
      const st = store.getState();
      return html`<p class="hint">Each gym keeps its own bar and plates for the plate calculator, and sets remember where they were done. Pick the gym you're training at now.</p>
        <div class="card list">${st.gyms.map(g => html`<div class="row-wrap"><button class="row" data-a="use-gym" data-id="${g.id}">
          <span class="row-icon ${g.id === st.settings.gymId ? 'accent-bg' : ''}">${icon('pin')}</span><span class="row-main"><span class="row-title">${g.name}</span>
          <span class="row-sub">Bar ${fmtNum(g.bar)} · ${Object.keys(g.plates).filter(k => g.plates[k] > 0).map(Number).sort((a, b) => b - a).map(x => fmtNum(x)).join(', ')}</span></span>
          ${g.id === st.settings.gymId ? html`<span class="check on">${icon('check')}</span>` : ''}</button>
          <button class="circle small" data-a="page" data-p="gym" data-id="${g.id}" aria-label="Edit ${g.name}">${icon('edit')}</button></div>`)}
          <button class="row accent" data-a="add-gym"><span class="row-icon">${icon('plus')}</span><span class="row-main">Add gym…</span></button></div>`;
    },
  },
  gym: {
    title: 'Plates',
    render(p) {
      const g = store.gym(p.gymId);
      const sizes = Object.keys(g.plates).map(Number).sort((a, b) => b - a);
      return html`<div class="card list"><button class="row" data-a="rename-gym"><span class="row-main">Name</span><span class="row-meta">${g.name}</span><span class="chev">${icon('edit')}</span></button>
          <div class="row static"><span class="row-main">Barbell</span><span class="stepper"><button data-a="bar" data-d="-2.5" aria-label="Lighter bar">${icon('minus')}</button><b>${fmtNum(g.bar)}</b><button data-a="bar" data-d="2.5" aria-label="Heavier bar">${icon('plus')}</button></span></div></div>
        <div class="section-label">Plates available (total count)</div>
        <div class="plate-setup">${sizes.map(w => html`<div class="pcol ${g.plates[w] ? '' : 'off'}"><button data-a="pc" data-w="${w}" data-d="2" aria-label="More ${w}">${icon('plus')}</button>
          <b class="pcount">${g.plates[w]}</b><span class="pw">${fmtNum(w)}</span><button data-a="pc" data-w="${w}" data-d="-2" aria-label="Fewer ${w}">${icon('minus')}</button></div>`)}</div>
        <div class="card list"><button class="row accent" data-a="add-plate-size"><span class="row-icon">${icon('plus')}</span><span class="row-main">New plate size…</span></button>
        ${store.getState().gyms.length > 1 ? html`<button class="row danger" data-a="delete-gym"><span class="row-icon">${icon('trash')}</span><span class="row-main">Delete gym</span></button>` : ''}</div>
        <p class="hint">By adding your own setup, the plates keyboard takes into account the plates available at your location. Counts are total plates, so 2 makes one pair.</p>`;
    },
  },
  display: {
    title: 'Display',
    render() {
      const s = store.settings();
      return html`<div class="card list">${Object.entries(THEMES).map(([k, n]) => html`<button class="row" data-a="theme" data-v="${k}"><span class="row-main">${n}</span>${s.theme === k ? html`<span class="check on">${icon('check')}</span>` : ''}</button>`)}</div>
        <div class="card list">${swRow('keep-awake', 'moon', 'Notepad Mode', s.keepAwake)}</div>
        <p class="hint">Notepad Mode keeps the screen awake while the app is open, for faster logging. Battery impact may vary.</p>
        <div class="card list">${swRow('sound', 'bell', 'Timer sound', s.sound)}</div>`;
    },
  },
  reminders: {
    title: 'Workout Reminders',
    render() {
      const s = store.settings();
      return html`<div class="big-icon c-green">${icon('calendar')}</div>
        <p class="center">Muscle grows during recovery, and consistent weekly training helps support progress over time.</p>
        <p class="center muted">When it has been a while since your last workout, a reminder appears at the top of My Workouts.</p>
        <div class="card list"><div class="row static"><span class="row-main">Remind after</span>
          <span class="stepper"><button data-a="remind" data-d="-1" aria-label="Sooner">${icon('minus')}</button><b>${s.remindDays} days inactive</b><button data-a="remind" data-d="1" aria-label="Later">${icon('plus')}</button></span></div></div>`;
    },
  },
  rest: {
    title: 'Default Interset Rest',
    render(p) {
      const s = store.settings();
      const recs = [['Time Efficient', 'More sets, less joint stress', 60, 'var(--green)'], ['Build Muscle', 'Get toned or bigger', 120, 'var(--blue)'], ['Increase Strength', 'Maximize muscular power', 300, 'var(--orange)']];
      return html`<div class="card list">${swRow('rest-on', 'timer', 'Timer', s.restOn)}</div>
        <div class="card list">
          <div class="row static"><span class="row-main">Minutes</span><span class="stepper"><button data-a="rest" data-d="-60" aria-label="Minus a minute">${icon('minus')}</button><b>${Math.floor(s.restSec / 60)}</b><button data-a="rest" data-d="60" aria-label="Plus a minute">${icon('plus')}</button></span></div>
          <div class="row static"><span class="row-main">Seconds</span><span class="stepper"><button data-a="rest" data-d="-15" aria-label="Minus 15 seconds">${icon('minus')}</button><b>${s.restSec % 60}</b><button data-a="rest" data-d="15" aria-label="Plus 15 seconds">${icon('plus')}</button></span></div>
        </div>
        <p class="hint">Select the interset rest duration you'd like to use the majority of the time. Individual exercises can override it from their ••• menu.</p>
        ${learnedSection(s)}
        <div class="section-label">Default Recommendations</div>
        <div class="card list">${recs.map(([t, sub, sec, c]) => html`<button class="row" data-a="rest-set" data-s="${sec}"><span class="row-main"><span class="row-title">${t}</span><span class="row-sub">${sub}</span></span>
          <span class="rec" style="--c:${c}">${sec / 60} minute${sec > 60 ? 's' : ''}</span></button>`)}</div>
        <button class="card article ${p.open ? 'open' : ''}" data-a="article"><b>Understanding Interset Rest</b><span class="muted">How it affects your muscles and performance</span>
          <span class="article-body">Short rests (about 1 minute) keep sessions quick and joints happy, but fatigue builds and reps drop on later sets. For muscle growth, 2 to 3 minutes lets you keep reps and load high enough to count. For heavy strength work, 3 to 5 minutes restores the energy your muscles need to lift near your max. When in doubt, rest until your breathing settles and you feel ready to give the next set your best effort.</span></button>`;
    },
  },
  targets: {
    title: 'Progression Targets',
    render() {
      const s = store.settings(), u = s.unit;
      return html`<div class="card list">${swRow('targets-on', 'target', 'Show “beat last time” target', s.showTargets)}</div>
        <p class="hint">When you log a set, the app shows what you did in the same set last session and suggests one step more: another rep, or more weight once you reach the top of your rep range. Tap it to fill the numbers in.</p>
        <div class="card list">${swRow('rpe-on', 'bolt', 'Rate effort (RPE)', s.rpeOn)}</div>
        <p class="hint">Adds a one-tap effort row to the set sheet. RPE 10 means nothing left in the tank, 9 means one more rep was possible, 8 means two. Sets that felt easy (7 or less) get a weight jump next time; all-out sets (9.5 or 10) are matched before trying to beat them.</p>
        <div class="card list">
          <div class="row static"><span class="row-main">Rep range, bottom</span><span class="stepper"><button data-a="rep" data-k="repLow" data-d="-1" aria-label="Lower">${icon('minus')}</button><b>${s.repLow}</b><button data-a="rep" data-k="repLow" data-d="1" aria-label="Higher">${icon('plus')}</button></span></div>
          <div class="row static"><span class="row-main">Rep range, top</span><span class="stepper"><button data-a="rep" data-k="repHigh" data-d="-1" aria-label="Lower">${icon('minus')}</button><b>${s.repHigh}</b><button data-a="rep" data-k="repHigh" data-d="1" aria-label="Higher">${icon('plus')}</button></span></div>
          <button class="row" data-a="step-kg"><span class="row-main">Weight step</span><span class="row-meta">${fmtNum(u === 'lb' ? s.stepKg / 0.45359237 : s.stepKg, 1)} ${u}</span><span class="chev">${icon('chevronRight')}</span></button>
        </div>`;
    },
  },
  data: {
    title: 'Import & Export',
    render() {
      return html`<div class="section-label">Backup</div>
        <div class="card list">
          ${row('backup', 'download', 'Save backup file (.json)')}
          <label class="row"><span class="row-icon">${icon('upload')}</span><span class="row-main">Restore from backup…</span><input type="file" accept=".json,application/json" data-in="restore" hidden><span class="chev">${icon('chevronRight')}</span></label>
        </div>
        <p class="hint">A backup holds everything: exercises, sets, workouts, gyms and settings. Save one to Files or iCloud Drive every few weeks.</p>
        <div class="section-label">Spreadsheet</div>
        <div class="card list">
          ${row('export-csv', 'download', 'Export sets as CSV')}
          <label class="row"><span class="row-icon">${icon('upload')}</span><span class="row-main">Import CSV from another app…</span><input type="file" accept=".csv,text/csv,text/plain" data-in="csv" hidden><span class="chev">${icon('chevronRight')}</span></label>
        </div>
        <p class="hint">Works with exports from Setgraph, Strong, Hevy and most spreadsheets. Columns are detected automatically and you can adjust them before importing. Importing the same file twice doesn't duplicate sets.</p>
        <div class="section-label">Start over</div>
        <div class="card list">
          ${row('demo', 'sparkle', 'Load demo data')}
          <button class="row danger" data-a="erase"><span class="row-icon">${icon('trash')}</span><span class="row-main">Erase all data</span></button>
        </div>`;
    },
  },
  help: {
    title: 'Help & Install',
    render() {
      return html`<div class="card pad prose">
        <h3>Install on iPhone</h3><p>Open this page in Safari, tap Share, then <b>Add to Home Screen</b>. It opens full screen and works offline, including in a basement gym with no signal.</p>
        <h3>Install on Android</h3><p>In Chrome, open the menu and tap <b>Install app</b>.</p>
        <h3>Logging fast</h3><p>The set sheet opens with your last set filled in. If nothing changed, tap the green check. The stack button next to + logs a copy of the last set in one tap.</p>
        <h3>Machine settings</h3><p>Use an exercise's pinned note for seat and pin positions so they're always at the top.</p>
        <h3>Several gyms</h3><p>Add each gym under Gyms &amp; Plates. Sets remember the gym, and the filter on an exercise compares like with like.</p>
        <h3>Records</h3><p>A trophy marks a set that beat every earlier set with at least as many reps. The Records view lists your best weight for each rep count.</p>
        <h3>Type or say a set</h3><p>In the set sheet, tap <b>Type or say it</b> and write it the way you'd say it: <b>8 at 60</b>, <b>3x10 25</b>, <b>10, 9, 8 at 25</b>, <b>60 for 8</b> or <b>same again</b>. Tap the microphone on the iPhone keyboard to dictate. You see what will be logged before it's saved.</p>
        <h3>Planks, carries and assisted machines</h3><p>Tap the type chip in the set sheet (it says <b>Weight</b> by default) to switch an exercise to Timed, Distance, Bodyweight or Assisted. One-arm and one-leg exercises can log left and right separately; the sheet alternates sides for you.</p>
        <h3>Supersets</h3><p>In a workout, tap ••• › Create superset. After each set the next exercise opens, and the rest timer only runs after the last one.</p>
        <h3>Warm-ups</h3><p>With your working weight in the sheet, tap <b>Warm-up</b> for a 40% / 60% / 80% ramp with plates per side. Tap ✓ on each one as you do it.</p>
        <h3>Smart checks</h3><p>The app flags a weight that looks like a typo, exercises that look like duplicates, lifts that have stalled, and your real rest times. All of it runs on your phone.</p>
      </div>`;
    },
  },
};

export function openSettings(page = 'main') {
  openSheet({
    cls: 'tall settings', live: true,
    render(p) {
      const page = PAGES[p.stack[p.stack.length - 1]];
      const isRoot = p.stack.length === 1;
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${isRoot ? html`<span class="circle ghost"></span>` : circle('page-back', 'chevronLeft', 'Back')}<h2>${page.title}</h2>
          ${isRoot ? html`<button class="circle accent" data-a="sheet-dismiss" aria-label="Done">${icon('check')}</button>` : html`<span class="circle ghost"></span>`}</div>
        <div class="scroll">${page.render(p)}</div>`;
    },
    actions: ACTIONS,
    inputs: INPUTS,
  }, { stack: page === 'main' ? ['main'] : ['main', page] });
}

const go = (p, inst, page) => { p.stack.push(page); inst.rerender(); inst.panel.querySelector('.scroll').scrollTop = 0; };

const ACTIONS = {
  page: (el, ev, p, inst) => { if (el.dataset.id) p.gymId = el.dataset.id; go(p, inst, el.dataset.p); },
  'page-back': (el, ev, p, inst) => { p.stack.pop(); inst.rerender(); },
  unit: async () => {
    const v = await choose({ title: 'Unit', options: [{ label: 'Metric (kg)', value: 'kg' }, { label: 'Imperial (lb)', value: 'lb' }] });
    if (v) store.setSetting('unit', v);
  },
  streaks: () => streakSheet(),
  celebrations: () => store.setSetting('celebrations', !store.settings().celebrations),
  'use-gym': el => { store.setSetting('gymId', el.dataset.id); toast(`Training at ${store.gym(el.dataset.id).name}`, { iconName: 'pin' }); },
  'add-gym': async (el, ev, p, inst) => {
    const name = await promptDialog({ title: 'New gym', placeholder: 'Cult Rajajinagar, Home…', confirm: 'Add' });
    if (name) { const g = store.addGym(name); store.setSetting('gymId', g.id); p.gymId = g.id; go(p, inst, 'gym'); }
  },
  'rename-gym': async (el, ev, p) => { const g = store.gym(p.gymId); const n = await promptDialog({ title: 'Gym name', value: g.name }); if (n) store.updateGym(g.id, { name: n }); },
  bar: (el, ev, p) => { const g = store.gym(p.gymId); store.updateGym(g.id, { bar: Math.max(0, g.bar + +el.dataset.d) }); },
  pc: (el, ev, p) => { const g = store.gym(p.gymId); const w = el.dataset.w; store.updateGym(g.id, { plates: { ...g.plates, [w]: Math.max(0, (g.plates[w] || 0) + +el.dataset.d) } }); },
  'add-plate-size': async (el, ev, p) => {
    const v = parseFloat(await promptDialog({ title: 'Plate size', type: 'number', placeholder: '0.5', confirm: 'Add' }));
    if (v > 0) { const g = store.gym(p.gymId); store.updateGym(g.id, { plates: { ...g.plates, [v]: 2 } }); }
  },
  'delete-gym': async (el, ev, p, inst) => {
    if (!(await confirmDialog({ title: `Delete ${store.gym(p.gymId).name}?`, message: 'Sets logged there are kept.', confirm: 'Delete Gym' }))) return;
    store.deleteGym(p.gymId); p.stack.pop(); inst.rerender();
  },
  theme: el => store.setSetting('theme', el.dataset.v),
  'keep-awake': () => store.setSetting('keepAwake', !store.settings().keepAwake),
  sound: () => store.setSetting('sound', !store.settings().sound),
  remind: el => store.setSetting('remindDays', Math.min(30, Math.max(1, store.settings().remindDays + +el.dataset.d))),
  'rest-on': () => store.setSetting('restOn', !store.settings().restOn),
  'rpe-on': () => store.setSetting('rpeOn', !store.settings().rpeOn),
  'apply-rest': el => { store.updateExercise(el.dataset.id, { restSec: +el.dataset.s }); toast(`Rest set to ${fmtClock(+el.dataset.s)}`, { iconName: 'timer' }); },
  'apply-all-rest': () => {
    const { byEx } = learnedRest(store.allSets());
    const changes = {};
    for (const [id, r] of byEx) { const ex = store.exercise(id); if (ex && (ex.restSec ?? store.settings().restSec) !== r.sec) changes[id] = r.sec; }
    const n = store.setRestTimes(changes);
    toast(n ? `Updated ${n} exercise timer${n === 1 ? '' : 's'}` : 'Timers already match', { iconName: 'timer' });
  },
  'use-typical': el => store.setSetting('restSec', +el.dataset.s),
  rest: el => store.setSetting('restSec', Math.min(900, Math.max(15, store.settings().restSec + +el.dataset.d))),
  'rest-set': el => { store.setSetting('restSec', +el.dataset.s); toast(`Rest set to ${fmtClock(+el.dataset.s)}`, { iconName: 'timer' }); },
  article: (el, ev, p, inst) => { p.open = !p.open; inst.rerender(); },
  'targets-on': () => store.setSetting('showTargets', !store.settings().showTargets),
  rep: el => {
    const s = store.settings(), k = el.dataset.k, v = s[k] + +el.dataset.d;
    if (k === 'repLow' && (v < 1 || v >= s.repHigh)) return;
    if (k === 'repHigh' && (v <= s.repLow || v > 30)) return;
    store.setSetting(k, v);
  },
  'step-kg': async () => {
    const lb = store.settings().unit === 'lb';
    const opts = lb ? [2.5, 5, 10] : [1, 1.25, 2.5, 5];
    const v = await choose({ title: 'Smallest weight jump', options: opts.map(o => ({ label: `${o} ${lb ? 'lb' : 'kg'}`, value: o })) });
    if (v) store.setSetting('stepKg', lb ? v * 0.45359237 : v);
  },
  backup: () => downloadFile(`overload-backup-${dayKey(Date.now())}.json`, JSON.stringify(store.exportState()), 'application/json'),
  'export-csv': () => downloadFile(`overload-sets-${dayKey(Date.now())}.csv`, setsToCSV(store.getState()), 'text/csv'),
  demo: async () => {
    if (store.getState().sets.length && !(await confirmDialog({ title: 'Replace your data with demo data?', message: 'Save a backup first if you want to keep what you have.', confirm: 'Load Demo Data' }))) return;
    store.replaceState(demoState(store.getState())); toast('Demo data loaded');
  },
  erase: async () => {
    if (!(await confirmDialog({ title: 'Erase everything?', message: 'All exercises, sets, workouts, photos and settings on this device will be deleted.', confirm: 'Erase All Data' }))) return;
    await erasePhotos();
    store.replaceState(store.defaultState()); toast('All data erased');
  },
};

const INPUTS = {
  restore: async el => {
    const f = el.files?.[0]; el.value = ''; if (!f) return;
    try {
      const data = JSON.parse(await f.text());
      if (!Array.isArray(data.sets) || !Array.isArray(data.exercises)) throw new Error('not a backup');
      if (!(await confirmDialog({ title: 'Restore this backup?', message: `${data.sets.length} sets and ${data.exercises.length} exercises will replace what's on this device.`, confirm: 'Restore', destructive: false }))) return;
      store.replaceState(data); toast('Backup restored', { iconName: 'check' });
    } catch { toast('That file is not an Overload backup'); }
  },
  csv: async el => { const f = el.files?.[0]; el.value = ''; if (f) importSheet(await f.text(), f.name); },
};

/** Save a file: share sheet on phones (Save to Files), download link elsewhere. */
export async function downloadFile(name, text, type) {
  const blob = new Blob([text], { type });
  try {
    const file = new File([blob], name, { type });
    if (navigator.canShare?.({ files: [file] }) && /iPhone|iPad|Android/i.test(navigator.userAgent)) { await navigator.share({ files: [file] }); return; }
  } catch (e) { if (e?.name === 'AbortError') return; }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  toast(`Saved ${name}`, { iconName: 'download' });
}

const FIELD_NAMES = { exercise: 'Exercise *', date: 'Date *', time: 'Time', reps: 'Reps *', weight: 'Weight', note: 'Note', label: 'Set type / label', unit: 'Unit column' };

export function importSheet(text, filename = 'file.csv') {
  const rows = parseCSV(text);
  if (rows.length < 2) { toast('That file has no rows to import'); return; }
  const header = rows[0];
  openSheet({
    cls: 'tall',
    render: p => {
      const st = store.getState();
      const preview = buildImport(text, p.m, { exercises: st.exercises, sets: st.sets }, { gymId: st.settings.gymId });
      p.preview = preview;
      const ok = p.m.exercise >= 0 && p.m.date >= 0 && p.m.reps >= 0;
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Cancel')}<h2>Import CSV</h2><span class="circle ghost"></span></div>
        <div class="scroll"><p class="muted">${filename} · ${rows.length - 1} rows</p>
        <div class="card list">${Object.entries(FIELD_NAMES).map(([f, n]) => html`<label class="row static"><span class="row-main">${n}</span>
          <select data-in="map" data-f="${f}"><option value="-1">—</option>${header.map((h, i) => html`<option value="${i}" ${p.m[f] === i ? 'selected' : ''}>${h || `Column ${i + 1}`}</option>`)}</select></label>`)}</div>
        <div class="card list">
          <label class="row static"><span class="row-main">Weights are in</span><select data-in="unitdef"><option value="kg" ${p.m.unitDefault === 'kg' ? 'selected' : ''}>kg</option><option value="lb" ${p.m.unitDefault === 'lb' ? 'selected' : ''}>lb</option></select></label>
          <label class="row static"><span class="row-main">Dates look like</span><select data-in="dayfirst"><option value="1" ${p.m.dayFirst ? 'selected' : ''}>28/09 (day first)</option><option value="0" ${p.m.dayFirst ? '' : 'selected'}>09/28 (month first)</option></select></label>
        </div>
        <div class="card pad"><p><b>${preview.newSets.length.toLocaleString()} sets</b> will be added across ${new Set(preview.newSets.map(s => s.exId)).size} exercises${preview.newExercises.length ? `, including ${preview.newExercises.length} new` : ''}.</p>
          ${preview.skipped ? html`<p class="muted small">${preview.skipped} already in your log and skipped.</p>` : ''}
          ${preview.bad ? html`<p class="muted small">${preview.bad} rows are missing an exercise, date or reps and will be skipped.</p>` : ''}</div>
        <button class="btn accent block" data-a="do-import" ${ok && preview.newSets.length ? '' : 'disabled'}>Import</button></div>`;
    },
    inputs: {
      map: (el, ev, p, inst) => { p.m = { ...p.m, [el.dataset.f]: +el.value }; inst.rerender(); },
      unitdef: (el, ev, p, inst) => { p.m = { ...p.m, unitDefault: el.value }; inst.rerender(); },
      dayfirst: (el, ev, p, inst) => { p.m = { ...p.m, dayFirst: el.value === '1' }; inst.rerender(); },
    },
    actions: {
      'do-import': (el, ev, p, inst) => {
        const st = store.getState();
        const { newExercises, newSets } = p.preview;
        store.replaceState({ ...st, exercises: [...st.exercises, ...newExercises], sets: [...st.sets, ...newSets] });
        inst.close(); toast(`Imported ${newSets.length.toLocaleString()} sets`, { iconName: 'check' });
      },
    },
  }, { m: detectMapping(header) });
}
