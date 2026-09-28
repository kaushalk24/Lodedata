/* Exercise detail: Sets history, Chart, 1RM and Records. */
import { html, fmtW, fmtReps, fmtNum, fmtShortDate, fmtTime, dayHeader, dayKeyToTs, round, toDisplay, fromDisplay, uid, monthName } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import {
  groupByDay, compareToPrevious, prSetIds, recordRanges, bestEfforts, bestE1rm, percentTable, FORMULAS, e1rm, summarize, isRepKind,
} from '../stats.js';
import { KINDS, unilateralOf } from '../library.js';
import { learnedRest, projectGoal } from '../smart.js';
import { lineChart } from '../chart.js';
import { registerScreen, renderScreen, push, pop, replace, openSheet, toast, choose, confirmDialog, promptDialog, header, backBtn, circle, toggle, emptyState } from '../ui.js';
import { setRow, labelBadge, unit, setText, freshSets, fmtSec, stallFor, kindFor } from './common.js';
import { openSetEntry } from './setentry.js';
import { afterLog } from './flow.js';
import { muscleEditor } from './body.js';

const VIEWS = [
  ['sets', 'Sets', 'layers'], ['chart', 'Chart', 'chart'], ['onerm', '1RM', 'sun'], ['records', 'Records', 'trophy'],
];

function visibleSets(p) {
  let sets = store.setsFor(p.id);
  if (p.hideWarmups) sets = sets.filter(s => s.label !== 'warmup');
  if (p.gym) sets = sets.filter(s => s.gymId === p.gym);
  return sets;
}

function deltaCell(label, value, d, color, fmt = v => fmtNum(v)) {
  const up = d.diff > 0, down = d.diff < 0;
  return html`<div class="cmp" style="--c:${color}"><i></i><div><b>${value}</b> ${label}
    <span class="cmp-d ${up ? 'up' : down ? 'down' : ''}">${up ? '▲' : down ? '▼' : '▲'} ${fmt(Math.abs(d.diff))} (${fmtNum(Math.abs(d.pct ?? 0), 1)}%)</span></div></div>`;
}

function setsView(p, ex) {
  const sets = visibleSets(p);
  if (!sets.length) {
    return html`${ex.note ? pinned(ex) : ''}${p.gym || p.hideWarmups
      ? emptyState('No sets match the filter', 'Change the filter to see the rest of your history.', '', 'filter')
      : emptyState('No sets yet', 'Tap the green + to log your first set. Your last set is remembered, so the next one is usually a single tap.', '', 'tabSets')}`;
  }
  const bodyKg = store.bodyKg(), u = unit(), kind = kindFor(ex);
  const prs = prSetIds(store.setsFor(p.id), bodyKg, kind);
  const days = groupByDay(sets);
  const cmp = compareToPrevious(sets, bodyKg);
  const gyms = store.getState().gyms;
  const multiGym = new Set(sets.map(s => s.gymId)).size > 1;
  const gymName = id => gyms.find(g => g.id === id)?.name || '';
  // With several gyms, the day header names the gym once; a set only repeats it if it differs.
  const dayGym = d => {
    const n = {}; for (const s of d.sets) n[s.gymId] = (n[s.gymId] || 0) + 1;
    return Object.entries(n).sort((a, b) => b[1] - a[1])[0]?.[0];
  };
  const limit = p.limit || 40;
  const total = sum => kind === 'time' ? `${fmtSec(sum.sec)} total` : kind === 'distance' ? `${fmtNum(sum.dist, 1)} m` : sum.volume ? `${fmtW(sum.volume, u)} ${u}` : `${fmtReps(sum.reps)} reps`;
  return html`
    ${ex.note ? pinned(ex) : ''}
    ${stallCard(ex)}
    ${days.slice(0, limit).map((d, di) => { const g = multiGym ? dayGym(d) : null; const sum = summarize(d.sets, bodyKg); return html`
      <button class="day-head" data-a="open-day" data-day="${d.key}"><span class="dh-title">${dayHeader(d.ts)}${icon('chevronRight')}</span>
        <span class="dh-meta">${sum.sets} set${sum.sets === 1 ? '' : 's'} · ${total(sum)}${g ? html` · <em>${gymName(g)}</em>` : ''}</span></button>
      <div class="card list sets">
        ${di === 0 && cmp ? html`<div class="compare">
          <div class="eyebrow">${icon('updown')} Compared to previous</div>
          <div class="cmp-grid">
            ${deltaCell(cmp.cur.sets === 1 ? 'Set' : 'Sets', cmp.cur.sets, cmp.sets, 'var(--sets)')}
            ${kind === 'time' ? deltaCell('Total time', fmtSec(cmp.cur.sec), cmp.sec, 'var(--reps)', v => fmtSec(v))
              : kind === 'distance' ? deltaCell('Distance (m)', fmtNum(cmp.cur.dist, 1), cmp.dist, 'var(--reps)', v => fmtNum(v, 1))
              : html`${deltaCell('Reps', fmtReps(cmp.cur.reps), cmp.reps, 'var(--reps)', v => fmtReps(v))}
                ${cmp.cur.volume || cmp.prev.volume ? html`${deltaCell(`Volume (${u})`, fmtW(cmp.cur.volume, u), cmp.volume, 'var(--vol)', v => fmtW(v, u))}
                ${deltaCell(`${u}/rep`, fmtW(cmp.cur.perRep, u), cmp.perRep, 'var(--weight)', v => fmtW(v, u))}` : ''}`}
          </div></div>` : ''}
        ${d.sets.map((s, i) => setRow(s, i + 1, { pr: prs.has(s.id), gymName: g && s.gymId !== g ? gymName(s.gymId) : '' }))}
      </div>`; })}
    ${days.length > limit ? html`<button class="btn block" data-a="more">Show older sessions (${days.length - limit} more)</button>` : ''}`;
}

const pinned = ex => html`<button class="card pinned" data-a="edit-note">${icon('pin')}<span>${ex.note}</span></button>`;

/** "Stalled" card: no better estimated 1RM for 4+ sessions. Suggests the classic lighter week. */
function stallCard(ex) {
  const pl = stallFor(ex);
  if (!pl) return '';
  const u = unit(), d = new Date(pl.since);
  const lighter = pl.deloadKg
    ? html`Try a lighter week: 2–3 sets of ${fmtReps(Math.max(5, Math.floor(pl.top.reps)))} at <b>${fmtW(pl.deloadKg, u)} ${u}</b> (about 10% less), then build back up.`
    : html`Try a lighter week: 2 sets, stopping 2–3 reps short of failure, then build back up.`;
  return html`<div class="card stall"><span class="stall-icon">${icon('chart')}</span>
    <div><b>Stalled for ${pl.sessions} sessions</b><p>No new best since ${d.getDate()} ${monthName(d.getMonth())}. ${lighter}</p></div>
    <button class="circle small" data-a="ack-stall" aria-label="Dismiss">${icon('x')}</button></div>`;
}

/** Chips to step between the exercises of a superset. */
function supersetStrip(ex) {
  const ss = store.supersetFor(ex.id);
  if (!ss) return '';
  return html`<div class="ss-strip"><span class="ss-label">${icon('layers')}${ss.ids.length > 2 ? 'Circuit' : 'Superset'}</span>
    ${ss.ids.map((id, i) => html`<button class="chip small ${id === ex.id ? 'on' : ''}" data-a="ss-go" data-id="${id}">${i + 1}. ${store.exercise(id).name}</button>`)}</div>`;
}

/** The set the repeat button logs: the last one again, on the other side for one-sided exercises. */
function repeatOf(last) {
  const r = { reps: last.reps, weight: last.weight, bw: !!last.bw, label: last.label === 'warmup' || last.label === 'pr' ? null : last.label };
  if (last.sec) r.sec = last.sec;
  if (last.dist) r.dist = last.dist;
  if (last.side) r.side = last.side === 'L' ? 'R' : 'L';
  return r;
}

function chartView(p) {
  const sets = visibleSets(p);
  const u = unit();
  const last = store.lastSet(p.id);
  if (!last) return emptyState('Nothing to chart yet', 'Charts appear after your first sets.', '', 'chart');
  p.chartMode ??= 'sets'; p.chartRange ??= 'recent';
  const kind = kindFor(store.exercise(p.id));
  let chart, extra = '';
  if (kind === 'time' || kind === 'distance') {
    const days = groupByDay(sets).reverse();
    const pick = p.chartRange === 'recent' ? days.slice(-10) : days;
    const best = pick.map(d => Math.max(...d.sets.map(s => (kind === 'time' ? s.sec : s.dist) || 0)));
    const fmt = v => (kind === 'time' ? fmtSec(Math.round(v)) : `${fmtNum(v, 1)} m`);
    const series = [{ name: kind === 'time' ? 'Longest' : 'Farthest', color: 'var(--reps)', values: best, fmt }];
    const loads = pick.map(d => Math.max(...d.sets.map(s => s.weight)));
    if (loads.some(w => w > 0)) series.push({ name: 'Weight', color: 'var(--weight)', values: loads, fmt: v => `${fmtW(v, u)} ${u}` });
    chart = lineChart(series, pick.map(d => fmtShortDate(d.ts)));
  } else if (p.chartMode === 'sets') {
    const days = groupByDay(sets);
    const pick = p.chartRange === 'recent' ? days.slice(0, 2).reverse().flatMap(d => d.sets) : sets.slice(-150);
    chart = lineChart([
      { name: 'Reps', color: 'var(--reps)', values: pick.map(s => s.reps), fmt: v => `${fmtReps(round(v, 1))} rep` },
      { name: 'Weight', color: 'var(--weight)', values: pick.map(s => s.weight), fmt: v => `${fmtW(v, u)} ${u}` },
    ], pick.map(s => `${fmtShortDate(s.ts)} ${fmtTime(s.ts)}`));
  } else {
    const days = groupByDay(sets).reverse();
    const pick = p.chartRange === 'recent' ? days.slice(-10) : days;
    const f = store.settings().formula, bodyKg = store.bodyKg();
    const e1 = pick.map(d => bestE1rm(d.sets, f, bodyKg)?.value ?? null);
    const vol = pick.map(d => summarize(d.sets, bodyKg).volume);
    chart = lineChart([
      { name: 'Est. 1RM', color: 'var(--purple)', values: e1, fmt: v => `1RM ${fmtW(v, u)}` },
      { name: 'Volume', color: 'var(--vol)', values: vol, fmt: v => `Vol ${fmtW(v, u)}` },
    ], pick.map(d => fmtShortDate(d.ts)));
    const first = e1.find(v => v != null), lastV = [...e1].reverse().find(v => v != null);
    const change = first ? ((lastV - first) / first) * 100 : 0;
    extra = html`<div class="tiles three">
      <div class="tile"><span>Est. 1RM</span><b style="color:var(--purple)">${fmtW(lastV || 0, u)} ${u}</b></div>
      <div class="tile"><span>Change</span><b class="${change >= 0 ? 'up' : 'down'}">${change >= 0 ? '+' : ''}${fmtNum(change, 1)}%</b></div>
      <div class="tile"><span>Sessions</span><b>${pick.length}</b></div></div>
      <p class="hint center">${p.chartRange === 'recent' ? 'Last 10 sessions.' : 'All sessions.'} Estimated with the ${FORMULAS[f].name} formula, warm-ups excluded.</p>`;
  }
  const repKind = isRepKind(kind);
  const head = last.sec ? html`<span class="reps">${fmtSec(last.sec)}</span>` : last.dist ? html`<span class="reps">${fmtNum(last.dist, 1)} <small>m</small></span>` : html`<span class="reps">${fmtReps(last.reps)} <small>rep</small></span>`;
  const load = last.bw ? (last.weight ? `${last.weight > 0 ? '+' : '−'}${fmtW(Math.abs(last.weight), u)}` : 'BW') : last.weight || repKind ? fmtW(last.weight, u) : '';
  return html`<div class="chart-head"><div class="big-set">${head}
      ${load ? html`<span class="wt">${load} <small>${load === 'BW' ? '' : u}</small></span>` : ''}${labelBadge(last.label)}</div>
      <span class="muted small">Last Set: ${fmtShortDate(last.ts)}, ${fmtTime(last.ts)}</span></div>
    ${chart}${extra}
    <div class="seg"><button class="${p.chartRange === 'recent' ? 'on' : ''}" data-a="chart-range" data-v="recent">${p.chartMode === 'sets' && repKind ? 'Last 2 Sessions' : 'Last 10'}</button><button class="${p.chartRange === 'all' ? 'on' : ''}" data-a="chart-range" data-v="all">All</button></div>
    ${repKind ? html`<div class="seg"><button class="${p.chartMode === 'sets' ? 'on' : ''}" data-a="chart-mode" data-v="sets">Sets</button><button class="${p.chartMode === 'stats' ? 'on' : ''}" data-a="chart-mode" data-v="stats">Stats</button></div>` : ''}`;
}

function oneRmView(p) {
  const st = store.settings(), u = unit();
  const best = bestE1rm(store.setsFor(p.id), st.formula, store.bodyKg());
  return html`<div class="section-label">1RM Settings</div>
    <div class="card list">
      <div class="row static"><span class="row-icon purple">${icon('sun')}</span><span class="row-main">1 Rep Max</span>${toggle('onerm-toggle', st.oneRmOn)}</div>
      <button class="row" data-a="formula"><span class="row-icon purple">${icon('chart')}</span><span class="row-main">Formula</span><span class="row-meta">${FORMULAS[st.formula].name}</span><span class="chev">${icon('chevronRight')}</span></button>
    </div>
    <p class="hint">For some exercises, targeting a percentage of your 1RM can help you reach your workout goals, whether it is gaining muscle mass or maximizing strength.</p>
    ${st.oneRmOn ? best ? html`
      <div class="card pad onerm"><span class="muted">Estimated 1RM</span><b>${fmtW(best.value, u)} <small>${u}</small></b>
        <span class="muted small">From ${setText(best.set)} on ${fmtShortDate(best.set.ts)}</span></div>
      <div class="card list">${percentTable(best.value).map(r => html`<div class="row static pct"><span class="pct-p">${r.pct}%</span><span class="row-main">${fmtNum(round(toDisplay(r.weight, u), 1))} ${u}</span><span class="row-meta">~${r.reps} rep${r.reps === 1 ? '' : 's'}</span></div>`)}</div>`
      : emptyState('No estimate yet', 'Log a working set of 15 reps or fewer.', '', 'sun') : ''}`;
}

function goalCard(ex, sets) {
  const u = unit(), st = store.settings();
  if (!ex.goal) {
    return html`<button class="card goal-empty" data-a="set-goal">${icon('target')}<span><b>Set a strength goal</b><span class="muted">See when you'll reach it at your current rate</span></span>${icon('chevronRight')}</button>`;
  }
  const g = projectGoal(sets, ex.goal, { formula: st.formula, bodyKg: store.bodyKg() });
  const pct = Math.max(0, Math.min(100, (g.current / ex.goal) * 100));
  const when = g.eta ? new Date(g.eta) : null;
  const status = {
    reached: html`<b class="up">Goal reached.</b> Set a new one to keep going.`,
    'on-track': html`At this rate, around <b>${when && `${when.getDate()} ${monthName(when.getMonth())} ${when.getFullYear()}`}</b> (+${fmtW(g.perWeek, u)} ${u} a week).`,
    far: html`More than 2 years away at your current rate (+${fmtW(g.perWeek, u)} ${u} a week).`,
    flat: 'Not improving lately. A lighter week or a new rep range can restart progress.',
    data: 'Log a few more sessions over two weeks to project a date.',
  }[g.status];
  return html`<button class="card goal-card" data-a="set-goal">
    <span class="goal-head"><span class="muted">Goal · estimated 1RM</span><b>${fmtW(ex.goal, u)} ${u}</b></span>
    <span class="goal-bar"><i style="width:${pct}%"></i></span>
    <span class="goal-meta"><span>Now ${g.current ? `${fmtW(g.current, u)} ${u}` : '–'}</span><span>${Math.round(pct)}%</span></span>
    <span class="goal-status">${status}</span></button>`;
}

function recordsView(p) {
  const ex = store.exercise(p.id), kind = kindFor(ex);
  const sets = store.setsFor(p.id), u = unit(), bodyKg = store.bodyKg();
  if (!sets.length) return html`${kind === 'weight' ? goalCard(ex, sets) : ''}${emptyState('No records yet', 'Records fill in as you log sets.', '', 'trophy')}`;
  const row = (label, value, setId) => html`<button class="row" data-a="jump" data-id="${setId}"><span class="row-main muted">${label}</span><span class="row-meta strong">${value}</span><span class="chev">${icon('chevronRight')}</span></button>`;
  if (!isRepKind(kind)) {
    const key = kind === 'time' ? 'sec' : 'dist';
    const best = sets.reduce((a, s) => ((s[key] || 0) > (a?.[key] || 0) ? s : a), null);
    const heavy = sets.reduce((a, s) => (s.weight > (a?.weight ?? 0) ? s : a), null);
    const days = groupByDay(sets).map(d => ({ d, v: d.sets.reduce((a, s) => a + (s[key] || 0), 0) }));
    const topDay = days.reduce((a, x) => (x.v > a.v ? x : a), days[0]);
    const fmt = v => (kind === 'time' ? fmtSec(v) : `${fmtNum(v, 1)} m`);
    return html`<div class="section-label">Best Efforts</div><div class="card list">
      ${best ? row(kind === 'time' ? 'Longest' : 'Farthest', setText(best), best.id) : ''}
      ${heavy ? row('Heaviest', setText(heavy), heavy.id) : ''}
      ${row(kind === 'time' ? 'Most time in a session' : 'Most distance in a session', fmt(topDay.v), topDay.d.sets[0].id)}
    </div><p class="hint">A trophy marks each set that beat everything before it: longer or farther at the same weight, or heavier at the same length.</p>`;
  }
  const b = bestEfforts(sets, bodyKg);
  const best1 = kind === 'weight' ? bestE1rm(sets, store.settings().formula, bodyKg) : null;
  const rel = kind === 'bodyweight' || kind === 'assisted';
  const fmtRec = w => {
    if (!rel) return `${fmtW(w, u)} ${u}`;
    const d = round(w - bodyKg, 2);
    return d === 0 ? 'BW' : `BW ${d > 0 ? '+' : '−'}${fmtW(Math.abs(d), u)} ${u}`;
  };
  return html`${kind === 'weight' ? goalCard(ex, sets) : ''}
    <div class="section-label">Best Efforts</div>
    <div class="card list">
      ${b.setVolume.value ? row('Set Volume', `${fmtW(b.setVolume.value, u)} ${u}`, b.setVolume.set.id) : ''}
      ${b.sessionVolume.value ? row('Session Volume', `${fmtW(b.sessionVolume.value, u)} ${u}`, b.sessionVolume.day.sets[0].id) : ''}
      ${row(kind === 'assisted' ? 'Least assistance' : 'Heaviest Set', setText(b.maxWeight.set), b.maxWeight.set.id)}
      ${row('Most Reps', setText(b.maxReps.set), b.maxReps.set.id)}
      ${best1 ? row('Estimated 1RM', `${fmtW(best1.value, u)} ${u}`, best1.set.id) : ''}
    </div>
    <div class="card list records"><div class="rec-head"><span>Repetitions</span><span>Record</span></div>
      ${recordRanges(sets, bodyKg).map(r => html`<button class="row" data-a="jump" data-id="${r.setId}"><span class="row-main muted">${r.from === r.to ? r.from : `${r.from}–${r.to}`}</span>
        <span class="row-meta strong">${fmtRec(r.weight)}</span><span class="chev">${icon('chevronRight')}</span></button>`)}
    </div>
    <p class="hint">The heaviest weight you have lifted for at least that many reps. A trophy marks each set that set a new record.</p>`;
}

registerScreen('exercise', {
  render(p) {
    const ex = store.exercise(p.id);
    if (!ex) return html`${header({ left: backBtn() })}<div class="scroll"></div>`;
    p.view ??= 'sets';
    const filtered = p.hideWarmups || p.gym;
    const body = { sets: setsView, chart: chartView, onerm: oneRmView, records: recordsView }[p.view](p, ex);
    return html`${header({ left: backBtn(), title: ex.name, right: html`${circle('filter', 'filter', 'Filter', filtered ? 'on' : '')}${circle('menu', 'dots', 'More')}` })}
      <nav class="viewbar">${VIEWS.map(([k, label, ic]) => html`<button class="vb ${k} ${p.view === k ? 'on' : ''}" data-a="view" data-v="${k}" aria-label="${label}">${icon(ic)}<span>${label}</span></button>`)}</nav>
      <div class="scroll with-viewbar"><div class="content">${p.view === 'sets' ? supersetStrip(ex) : ''}${body}</div></div>
      ${p.view === 'sets' ? html`<div class="fab-row"><button class="fab" data-a="log" aria-label="Log set">${icon('plus')}</button>
        ${store.lastSet(p.id) ? html`<button class="repeat-pill" data-a="repeat" aria-label="Log the same set again">${icon('repeat')}<span>${setText(repeatOf(store.lastSet(p.id)))}</span></button>` : ''}</div>` : ''}`;
  },
  mount(el, p) {
    for (const id of freshSets) el.querySelector(`#set-${CSS.escape(id)}`)?.classList.add('new');
    freshSets.clear();
    if (p.flash) {
      const row = el.querySelector(`#set-${CSS.escape(p.flash)}`);
      p.flash = null;
      if (row) { row.scrollIntoView({ block: 'center' }); row.classList.add('flash'); }
    }
  },
  actions: {
    view: (el, ev, p, inst) => { p.view = el.dataset.v; renderScreen(inst); inst.el.querySelector('.scroll').scrollTop = 0; },
    log: (el, ev, p) => openSetEntry({ exId: p.id }),
    'edit-set': el => openSetEntry({ setId: el.dataset.id }),
    repeat: (el, ev, p) => {
      const last = store.lastSet(p.id);
      if (!last) return;
      const id = uid(); freshSets.add(id);
      const s = store.addSet({ id, exId: p.id, ...repeatOf(last) });
      navigator.vibrate?.(12);
      const next = afterLog(p.id);
      toast(`Logged ${setText(s)}${next ? ` · ${next}` : ''}`, { action: 'Undo', onAction: () => store.deleteSet(s.id), iconName: 'check', ms: next ? 3400 : 2600 });
    },
    'ss-go': el => replace('exercise', { id: el.dataset.id }),
    'ack-stall': (el, ev, p) => { const pl = stallFor(store.exercise(p.id)); if (pl) store.updateExercise(p.id, { plateauAck: pl.total }); },
    'set-goal': async (el, ev, p) => {
      const ex = store.exercise(p.id), u = unit();
      const v = await promptDialog({ title: `Goal for ${ex.name}`, type: 'number', value: ex.goal ? String(round(toDisplay(ex.goal, u), 1)) : '',
        placeholder: `1 rep max in ${u}`, hint: 'Your target 1 rep max. The app estimates your current max from your sets. Leave empty to remove the goal.' });
      if (v == null) return;
      const n = parseFloat(v);
      store.updateExercise(p.id, { goal: n > 0 ? round(fromDisplay(n, u), 2) : null });
    },
    more: (el, ev, p, inst) => { p.limit = (p.limit || 40) + 60; renderScreen(inst); },
    'open-day': el => push('today', { date: dayKeyToTs(el.dataset.day), pushed: true }),
    'chart-range': (el, ev, p, inst) => { p.chartRange = el.dataset.v; renderScreen(inst); },
    'chart-mode': (el, ev, p, inst) => { p.chartMode = el.dataset.v; renderScreen(inst); },
    'onerm-toggle': () => store.setSetting('oneRmOn', !store.settings().oneRmOn),
    formula: async () => {
      const v = await choose({ title: '1RM formula', message: 'Epley suits most lifters. Brzycki reads a little lower above 10 reps.', options: Object.entries(FORMULAS).map(([k, f]) => ({ label: `${f.name}${k === store.settings().formula ? '  ✓' : ''}   ·  100 × 8 → ${fmtNum(e1rm(100, 8, k), 1)}`, value: k })) });
      if (v) store.setSetting('formula', v);
    },
    jump: (el, ev, p, inst) => { p.view = 'sets'; p.flash = el.dataset.id; p.hideWarmups = false; p.gym = null; p.limit = 9999; renderScreen(inst); },
    'edit-note': (el, ev, p) => editNote(p.id),
    filter: (el, ev, p, inst) => filterSheet(p, inst),
    menu: (el, ev, p) => exerciseMenu(p.id),
  },
});

async function editNote(id) {
  const ex = store.exercise(id);
  const v = await promptDialog({ title: 'Pinned note', value: ex.note || '', placeholder: 'Seat 4, pin 3, grip width…', hint: 'Shown at the top of this exercise. Good for machine settings.' });
  if (v != null) store.updateExercise(id, { note: v });
}

function filterSheet(p, screen) {
  openSheet({
    render: () => {
      const gyms = store.getState().gyms;
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>Filter</h2><span class="circle ghost"></span></div>
        <div class="card list"><div class="row static"><span class="row-main">Show warm-ups</span>${toggle('warm', !p.hideWarmups)}</div></div>
        ${gyms.length > 1 ? html`<div class="section-label">Gym</div><div class="card list">
          ${[{ id: null, name: 'All gyms' }, ...gyms].map(g => html`<button class="row" data-a="gym" data-id="${g.id || ''}"><span class="row-main">${g.name}</span>${(p.gym || null) === g.id ? html`<span class="check on">${icon('check')}</span>` : ''}</button>`)}
        </div><p class="hint">Machines differ between gyms. Filter to compare like with like.</p>` : ''}`;
    },
    actions: {
      warm: (el, ev, x, inst) => { p.hideWarmups = !p.hideWarmups; inst.rerender(); renderScreen(screen); },
      gym: (el, ev, x, inst) => { p.gym = el.dataset.id || null; inst.rerender(); renderScreen(screen); },
    },
  });
}

async function exerciseMenu(id) {
  const ex = store.exercise(id);
  const rest = ex.restSec ?? null;
  const v = await choose({ title: ex.name, options: [
    { label: `Logged as: ${KINDS[kindFor(ex)].name}${unilateralOf(ex) ? ', left and right' : ''}`, value: 'kind', icon: 'layers' },
    { label: 'Rename', value: 'rename', icon: 'edit' },
    { label: ex.note ? 'Edit pinned note' : 'Add pinned note (machine settings)', value: 'note', icon: 'pin' },
    { label: 'Muscles and equipment', value: 'muscles', icon: 'person' },
    { label: `Rest timer: ${rest == null ? 'default' : `${Math.floor(rest / 60)}:${String(rest % 60).padStart(2, '0')}`}`, value: 'rest', icon: 'timer' },
    { label: 'Add to workout', value: 'workout', icon: 'book' },
    { label: 'Merge into another exercise', value: 'merge', icon: 'copy' },
    { label: 'Delete exercise', value: 'delete', icon: 'trash', destructive: true },
  ] });
  if (v === 'rename') {
    const name = await promptDialog({ title: 'Rename', value: ex.name });
    if (name) store.updateExercise(id, { name });
  }
  if (v === 'note') editNote(id);
  if (v === 'muscles') muscleEditor(id);
  if (v === 'kind') {
    const k = await choose({ title: 'How is it logged?', options: [
      ...Object.entries(KINDS).map(([key, d]) => ({ label: `${d.name}${kindFor(ex) === key ? '  ✓' : ''}`, value: key })),
      { label: `Left and right separately: ${unilateralOf(ex) ? 'On' : 'Off'}`, value: 'sides', icon: 'updown' },
    ] });
    if (k === 'sides') store.updateExercise(id, { unilateral: !unilateralOf(ex) });
    else if (k) store.updateExercise(id, { kind: k });
  }
  if (v === 'rest') {
    const learned = learnedRest(store.allSets()).byEx.get(id);
    const opts = [null, 60, 90, 120, 150, 180, 240, 300].filter(s => s !== learned?.sec);
    const r = await choose({ title: 'Rest after each set', options: [
      ...(learned ? [{ label: `Your usual: ${fmtRestLabel(learned.sec)} (from ${learned.n} rests)`, value: learned.sec, icon: 'sparkle' }] : []),
      ...opts.map(s => ({ label: s == null ? `Use default (${fmtRestLabel(store.settings().restSec)})` : fmtRestLabel(s), value: s == null ? 'default' : s })),
    ] });
    if (r != null) store.updateExercise(id, { restSec: r === 'default' ? null : r });
  }
  if (v === 'workout') {
    const ws = store.getState().workouts;
    if (!ws.length) { toast('Create a workout first'); return; }
    const w = await choose({ title: 'Add to workout', options: ws.map(w => ({ label: `${w.name}${w.exIds.includes(id) ? '  ✓' : ''}`, value: w.id })) });
    if (w) { store.toggleInWorkout(w, id); toast(store.workout(w).exIds.includes(id) ? `Added to ${store.workout(w).name}` : `Removed from ${store.workout(w).name}`); }
  }
  if (v === 'merge') {
    const others = store.sortedExercises().filter(e => e.id !== id);
    const into = await choose({ title: `Merge “${ex.name}” into…`, message: 'All sets move to the exercise you pick, then this one is removed.', options: others.map(e => ({ label: e.name, value: e.id })) });
    if (into && await confirmDialog({ title: `Merge into “${store.exercise(into).name}”?`, message: `${store.setsFor(id).length} sets will move. This can't be undone.`, confirm: 'Merge', destructive: false })) {
      store.mergeExercise(id, into); pop(); push('exercise', { id: into }); toast('Merged');
    }
  }
  if (v === 'delete' && await confirmDialog({ title: `Delete “${ex.name}”?`, message: `This removes ${store.setsFor(id).length} logged sets.`, confirm: 'Delete Exercise' })) {
    const undo = store.deleteExercise(id); pop(); toast(`Deleted ${ex.name}`, { action: 'Undo', onAction: undo });
  }
}
const fmtRestLabel = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
