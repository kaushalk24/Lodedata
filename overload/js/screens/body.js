/* Body tab: recovery map, weekly sets per muscle, bodyweight log, muscle assignment. */
import { html, relTime, fmtNum, fmtShortDate, fmtW, round } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { MUSCLES, EQUIPMENT } from '../library.js';
import { muscleReport, recoveryState } from '../stats.js';
import { bodyMap } from '../bodymap.js';
import { lineChart } from '../chart.js';
import { registerScreen, renderScreen, push, openSheet, toast, choose, promptDialog, header, backBtn, circle, emptyState } from '../ui.js';
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
        <button class="card row weight-row" data-a="bodyweight"><span class="row-icon purple">${icon('tabBody')}</span><span class="row-main"><span class="row-title">Weight</span></span>
          <span class="row-meta">${bw ? `${fmtW(bw.kg, u)} ${u}` : 'Add'}</span><span class="chev">${icon('chevronRight')}</span></button>
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
  actions: {
    refresh: (el, ev, p, inst) => { renderScreen(inst); toast('Updated'); },
    'add-weight': () => addWeight(),
    bodyweight: () => push('bodyweight'),
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
          : emptyState('No weigh-ins yet', 'Tap + to log your bodyweight. It also counts toward pull-ups, dips and other bodyweight sets.')}
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
