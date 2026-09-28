/* Sessions tab: timed activities (strength training, tennis, a run...). */
import { html, fmtClock, fmtDuration, dayHeader, startOfWeek, fmtTime } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { registerScreen, renderScreen, choose, confirmDialog, toast, header, emptyState } from '../ui.js';

export const ACTIVITIES = {
  'Strength Training': ['tabSets', 'var(--accent)'], Running: ['bolt', 'var(--orange)'], Walking: ['person', 'var(--teal)'],
  Cycling: ['target', 'var(--blue)'], Tennis: ['sparkle', 'var(--purple)'], Badminton: ['sparkle', 'var(--pink)'],
  Cricket: ['target', 'var(--yellow)'], Football: ['target', 'var(--green)'], Swimming: ['heart', 'var(--vol)'],
  Yoga: ['heart', 'var(--pink)'], HIIT: ['flame', 'var(--red)'], 'Stair Climbing': ['up', 'var(--orange)'], Other: ['timer', 'var(--text-2)'],
};
const RANGES = { week: 'This week', month: 'This month', all: 'All time' };
const actIcon = a => html`<span class="act-icon" style="--c:${(ACTIVITIES[a] || ACTIVITIES.Other)[1]}">${icon((ACTIVITIES[a] || ACTIVITIES.Other)[0])}</span>`;

function rangeStart(r) {
  const now = new Date();
  if (r === 'week') return startOfWeek(Date.now());
  if (r === 'month') return new Date(now.getFullYear(), now.getMonth(), 1).getTime();
  return 0;
}

registerScreen('sessions', {
  render(p) {
    const st = store.getState();
    p.activity ??= 'Strength Training'; p.filter ??= 'All';
    const range = st.ui.sessionRange, style = st.ui.sessionStyle;
    const running = store.runningSession();
    const done = st.sessions.filter(s => s.end).sort((a, b) => b.start - a.start);
    const acts = [...new Set(done.map(s => s.activity))];
    const shown = done.filter(s => p.filter === 'All' || s.activity === p.filter);
    const inRange = shown.filter(s => s.start >= rangeStart(range));
    const total = inRange.reduce((a, s) => a + (s.end - s.start) / 1000, 0);
    const days = [];
    for (const s of shown) { const k = new Date(s.start).toDateString(); const last = days[days.length - 1]; if (last?.k === k) last.items.push(s); else days.push({ k, ts: s.start, items: [s] }); }
    const card = s => html`<button class="${style === 'cards' ? 'sess-card' : 'row'}" data-a="session" data-id="${s.id}">
      ${actIcon(s.activity)}<span class="row-main"><span class="row-title">${s.activity}</span><span class="row-sub">${fmtTime(s.start)} – ${fmtTime(s.end)}</span></span>
      <b class="sess-time" style="color:${(ACTIVITIES[s.activity] || ACTIVITIES.Other)[1]}">${fmtClock((s.end - s.start) / 1000)}</b></button>`;
    return html`${header({
      left: html`<button class="pill-btn range-btn" data-a="range" aria-label="Change period">${RANGES[range]}${icon('updown')}</button>`, title: 'Sessions',
      right: html`<button type="button" class="circle" data-a="style" aria-label="${style === 'cards' ? 'Show as list' : 'Show as cards'}">${icon(style === 'cards' ? 'list' : 'grid')}</button>`,
    })}
      <div class="scroll"><div class="content">
        <div class="chips scroll-x">${['All', ...acts].map(a => html`<button class="chip ${p.filter === a ? 'on accent' : ''}" data-a="filter" data-v="${a}">${a}</button>`)}</div>
        ${running ? html`<div class="card running">${actIcon(running.activity)}<div><span class="muted">In progress</span><b>${running.activity}</b></div>
          <b class="live-time" data-start="${running.start}">${fmtClock((Date.now() - running.start) / 1000)}</b></div>` : ''}
        ${done.length ? html`<div class="total-line"><span class="muted">${RANGES[range]}</span><b>${fmtDuration(total)}</b><span class="muted">${inRange.length} session${inRange.length === 1 ? '' : 's'}</span></div>
          ${days.map(d => html`<div class="day-head static">${dayHeader(d.ts)}</div><div class="${style === 'cards' ? 'sess-grid' : 'card list'}">${d.items.map(card)}</div>`)}`
        : running ? '' : html`<div class="ghost-cards">${['Strength Training', 'Tennis', 'Stair Climbing'].map((a, i) => html`<div class="sess-card ghost">${actIcon(a)}<span class="row-main"><span class="row-title">${a}</span></span><b class="sess-time" style="color:${ACTIVITIES[a][1]}">${['00:29', '01:31', '00:10'][i]}</b></div>`)}</div>
          ${emptyState('No Sessions', 'Add sessions to track the duration of your activities. Starting one while you lift also fills in Duration on the Today tab.', '', 'timer')}`}
      </div></div>
      <div class="dock sessions-dock">
        <button class="act-pick" data-a="pick-activity">${icon((ACTIVITIES[p.activity] || ACTIVITIES.Other)[0])}<span>${running ? running.activity : p.activity}</span>${icon('updown')}</button>
        ${running ? html`<button class="btn danger" data-a="stop">${icon('stop')} Stop</button>` : html`<button class="btn accent" data-a="start">New Session</button>`}
      </div>`;
  },
  mount(el, p, inst) {
    clearInterval(inst._tick);
    const live = el.querySelector('.live-time');
    if (live) inst._tick = setInterval(() => { if (!document.body.contains(live)) return clearInterval(inst._tick); live.textContent = fmtClock((Date.now() - +live.dataset.start) / 1000); }, 1000);
  },
  actions: {
    range: () => { const r = store.getState().ui.sessionRange; store.setUi('sessionRange', r === 'week' ? 'month' : r === 'month' ? 'all' : 'week'); },
    style: () => store.setUi('sessionStyle', store.getState().ui.sessionStyle === 'cards' ? 'list' : 'cards'),
    filter: (el, ev, p, inst) => { p.filter = el.dataset.v; renderScreen(inst); },
    'pick-activity': async (el, ev, p, inst) => {
      if (store.runningSession()) return;
      const v = await choose({ title: 'Activity', options: Object.keys(ACTIVITIES).map(a => ({ label: a, value: a, icon: ACTIVITIES[a][0] === 'tabSets' ? 'dumbbell' : ACTIVITIES[a][0] })) });
      if (v) { p.activity = v; renderScreen(inst); }
    },
    start: (el, ev, p) => { store.startSession(p.activity); toast(`${p.activity} started`, { iconName: 'timer' }); },
    stop: () => { const s = store.stopSession(); if (s) toast(`${s.activity}: ${fmtDuration((s.end - s.start) / 1000)}`, { iconName: 'check' }); },
    session: async el => {
      const s = store.getState().sessions.find(x => x.id === el.dataset.id);
      const v = await choose({ title: `${s.activity} · ${fmtDuration((s.end - s.start) / 1000)}`, options: [{ label: 'Delete session', value: 'del', icon: 'trash', destructive: true }] });
      if (v === 'del' && await confirmDialog({ title: 'Delete this session?', confirm: 'Delete Session' })) {
        const undo = store.deleteSession(s.id); toast('Session deleted', { action: 'Undo', onAction: undo });
      }
    },
  },
});
