/* Today tab (or any day): week strip, day stats, set details, calendar and share card. */
import { html, dayKey, startOfDay, startOfWeek, addDays, daysBetween, fmtNum, fmtW, fmtDuration, fmtClock, fmtLongDate, weekdayLetter, monthName, fmtReps } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { daySummary, prSetIds, collapseSets, summarize } from '../stats.js';
import { registerScreen, renderScreen, push, openSheet, toast, header, backBtn, circle, emptyState, showTab } from '../ui.js';
import { unit, setText } from './common.js';

function dayData(ts) {
  const k = dayKey(ts);
  const sets = store.allSets().filter(s => dayKey(s.ts) === k);
  const bodyKg = store.bodyKg();
  const prIds = new Set();
  for (const exId of new Set(sets.map(s => s.exId))) for (const id of prSetIds(store.setsFor(exId), bodyKg)) prIds.add(id);
  const sum = daySummary(sets, prIds, bodyKg);
  const sessions = store.getState().sessions.filter(s => dayKey(s.start) === k);
  const sessionSec = sessions.reduce((a, s) => a + ((s.end || Date.now()) - s.start) / 1000, 0);
  const strength = sessions.find(s => s.activity === 'Strength Training');
  const order = [...new Set(sets.map(s => s.exId))];
  return { k, sets, sum, prIds, sessionSec, strength, order, bodyKg };
}

registerScreen('today', {
  render(p, inst) {
    const root = !p.pushed;
    const ts = startOfDay(p.date || Date.now());
    const d = dayData(ts), u = unit(), st = store.getState();
    const isToday = daysBetween(ts, Date.now()) === 0;
    const weekStart = startOfWeek(ts);
    const trained = new Set(store.allSets().map(s => dayKey(s.ts)));
    const dur = d.strength ? ((d.strength.end || Date.now()) - d.strength.start) / 1000 : d.sum.duration;
    const stat = (label, value, color, key) => html`<button class="stat" data-a="stat" data-k="${key}"><span>${label} ${icon('chevronRight')}</span><b style="color:${color}">${value}</b></button>`;
    return html`${header({
      left: root ? (isToday ? '' : html`<button class="pill-btn" data-a="go-today">Today</button>`) : backBtn(), title: isToday ? 'Today' : fmtLongDate(ts),
      right: html`<span class="btn-pair">${circle('calendar', 'calendar', 'Calendar')}${circle('share-day', 'share', 'Share workout')}</span>`,
    })}
      <div class="scroll"><div class="content">
        ${!st.ui.shareTipDismissed && d.sets.length ? html`<div class="banner share-tip"><span class="banner-icon">${icon('share')}</span>
          <div><b>Share your workout</b><p>Turn this session into an image card or caption-ready text for stories and chats.</p></div>
          <button class="circle small" data-a="dismiss-share" aria-label="Dismiss">${icon('x')}</button></div>` : ''}
        <div class="week-strip">${[0, 1, 2, 3, 4, 5, 6].map(i => { const day = addDays(weekStart, i); const k = dayKey(day); return html`
          <button class="wd ${trained.has(k) ? 'trained' : ''} ${k === d.k ? 'sel' : ''} ${day > Date.now() ? 'future' : ''}" data-a="pick-day" data-ts="${day}">
            <small>${weekdayLetter(i)}</small><b>${new Date(day).getDate()}</b></button>`; })}</div>
        <div class="card stats">
          ${stat('Sets', d.sum.sets, 'var(--sets)', 'sets')}${stat('Repetitions', fmtReps(d.sum.reps), 'var(--reps)', 'reps')}
          ${stat('Exercises', d.sum.exercises, 'var(--ex)', 'sets')}${stat('Volume', d.sum.volume ? `${fmtW(d.sum.volume, u)} ${u}` : '0', 'var(--vol)', 'volume')}
          ${stat('Duration', dur ? html`${fmtDuration(dur)}${d.strength ? '' : html`<small class="auto">auto</small>`}` : '--', 'var(--text)', 'sets')}
          ${stat('Avg Rest', d.sum.avgRest ? fmtDuration(d.sum.avgRest) : '--', 'var(--orange)', 'sets')}
          ${stat('Session Time', fmtClock(d.sessionSec), 'var(--text-2)', 'sessions')}
          ${stat('PRs', html`${icon('trophy')} ${d.sum.prs}`, 'var(--gold)', 'prs')}
        </div>
        ${d.sets.length ? html`<h3 class="section-title">Set Details</h3>
          <div class="card set-details">${d.order.map(exId => { const ex = store.exercise(exId); const sets = d.sets.filter(s => s.exId === exId); return html`
            <button class="sd" data-a="open-exercise" data-id="${exId}"><b>${ex?.name || 'Deleted exercise'}</b>
            ${collapseSets(sets).map(g => html`<span>${g.count > 1 ? `${g.count} sets: ` : ''}${fmtReps(g.reps)} rep ${g.bw ? `BW${g.weight ? ` +${fmtW(g.weight, u)}` : ''}` : `${fmtW(g.weight, u)} ${u}`}</span>`)}
            ${sets.some(s => d.prIds.has(s.id)) ? html`<span class="gold">${icon('trophy')} Record</span>` : ''}</button>`; })}</div>`
        : emptyState(isToday ? 'Nothing logged yet today' : 'Rest day', isToday ? 'Open a workout and log your first set. Stats fill in as you go.' : 'No sets were logged on this day.',
          isToday ? html`<button class="btn accent" data-a="go-sets">Open My Workouts</button>` : '')}
      </div></div>`;
  },
  actions: {
    'pick-day': (el, ev, p, inst) => { const t = +el.dataset.ts; if (t > Date.now()) return; p.date = daysBetween(t, Date.now()) === 0 ? null : t; renderScreen(inst); },
    calendar: (el, ev, p, inst) => calendarSheet(p, inst),
    'share-day': (el, ev, p) => shareSheet(startOfDay(p.date || Date.now())),
    'dismiss-share': () => store.setUi('shareTipDismissed', true),
    'open-exercise': el => push('exercise', { id: el.dataset.id }),
    'go-sets': () => showTab('sets'),
    'go-today': (el, ev, p, inst) => { p.date = null; renderScreen(inst); },
    stat: (el, ev, p) => el.dataset.k === 'sessions' ? showTab('sessions') : breakdown(startOfDay(p.date || Date.now())),
  },
});

function breakdown(ts) {
  const d = dayData(ts), u = unit();
  openSheet({
    render: () => html`<div class="sheet-grab"></div>
      <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>By exercise</h2><span class="circle ghost"></span></div>
      <div class="scroll"><div class="card list">
        <div class="row static bd head"><span class="row-main">Exercise</span><span>Sets</span><span>Reps</span><span>Volume</span></div>
        ${d.order.map(id => { const s = summarize(d.sets.filter(x => x.exId === id), d.bodyKg); const prs = d.sets.filter(x => x.exId === id && d.prIds.has(x.id)).length; return html`
        <button class="row bd" data-a="open" data-id="${id}"><span class="row-main">${store.exercise(id)?.name}${prs ? html` <span class="gold">${icon('trophy')}</span>` : ''}</span><span style="color:var(--sets)">${s.sets}</span><span style="color:var(--reps)">${fmtReps(s.reps)}</span><span style="color:var(--vol)">${fmtW(s.volume, u)}</span></button>`; })}
      </div></div>`,
    actions: { open: (el, ev, p, inst) => { inst.close(); push('exercise', { id: el.dataset.id }); } },
  });
}

function calendarSheet(sp, screen) {
  const sel = startOfDay(sp.date || Date.now());
  openSheet({
    render: p => {
      const first = new Date(p.y, p.m, 1), startPad = first.getDay(), days = new Date(p.y, p.m + 1, 0).getDate();
      const counts = new Map();
      for (const s of store.allSets()) { const k = dayKey(s.ts); counts.set(k, (counts.get(k) || 0) + 1); }
      const monthDays = [...Array(days)].map((_, i) => new Date(p.y, p.m, i + 1).getTime());
      const trainedCount = monthDays.filter(t => counts.has(dayKey(t))).length;
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${circle('prev', 'chevronLeft', 'Previous month')}<h2>${monthName(p.m)} ${p.y}</h2>${circle('next', 'chevronRight', 'Next month')}</div>
        <div class="cal">${[0, 1, 2, 3, 4, 5, 6].map(i => html`<small>${weekdayLetter(i)}</small>`)}
          ${[...Array(startPad)].map(() => html`<span></span>`)}
          ${monthDays.map(t => { const c = counts.get(dayKey(t)) || 0; return html`<button class="cd ${c ? 'trained' : ''} ${t === sel ? 'sel' : ''} ${t > Date.now() ? 'future' : ''}" data-a="pick" data-ts="${t}">${new Date(t).getDate()}</button>`; })}
        </div><p class="muted center small">${trainedCount} training day${trainedCount === 1 ? '' : 's'} in ${monthName(p.m)}</p>`;
    },
    actions: {
      prev: (el, ev, p, inst) => { p.m--; if (p.m < 0) { p.m = 11; p.y--; } inst.rerender(); },
      next: (el, ev, p, inst) => { p.m++; if (p.m > 11) { p.m = 0; p.y++; } inst.rerender(); },
      pick: (el, ev, p, inst) => { const t = +el.dataset.ts; if (t > Date.now()) return; sp.date = daysBetween(t, Date.now()) === 0 ? null : t; inst.close(); renderScreen(screen); },
    },
  }, { y: new Date(sel).getFullYear(), m: new Date(sel).getMonth() });
}

/* ---------- share card ---------- */
function shareTextFor(ts) {
  const d = dayData(ts), u = unit();
  const lines = [`${fmtLongDate(ts)} · ${d.sum.sets} sets · ${fmtW(d.sum.volume, u)} ${u}${d.sum.prs ? ` · ${d.sum.prs} PR${d.sum.prs > 1 ? 's' : ''}` : ''}`, ''];
  for (const id of d.order) {
    const sets = d.sets.filter(s => s.exId === id);
    lines.push(`${store.exercise(id)?.name}`);
    for (const g of collapseSets(sets)) lines.push(`  ${g.count > 1 ? `${g.count} × ` : ''}${setText(g)}`);
  }
  lines.push('', 'Logged with Overload');
  return lines.join('\n');
}

export function drawShareCard(ts) {
  const d = dayData(ts), u = unit();
  const c = document.createElement('canvas');
  c.width = 1080; c.height = 1350;
  const g = c.getContext('2d');
  const grad = g.createLinearGradient(0, 0, 0, 1350);
  grad.addColorStop(0, '#0f1511'); grad.addColorStop(1, '#050505');
  g.fillStyle = grad; g.fillRect(0, 0, 1080, 1350);
  g.fillStyle = 'rgba(48,209,88,0.12)'; g.beginPath(); g.arc(980, 120, 260, 0, Math.PI * 2); g.fill();
  const font = (w, s) => `${w} ${s}px -apple-system, "SF Pro Display", "Helvetica Neue", Arial, sans-serif`;
  g.fillStyle = '#30d158'; g.font = font(800, 34); g.fillText('OVERLOAD', 80, 120);
  g.fillStyle = '#ffffff'; g.font = font(800, 76); g.fillText(fmtLongDate(ts), 80, 215);
  const stats = [['Sets', String(d.sum.sets), '#ff375f'], ['Reps', fmtReps(d.sum.reps), '#30d158'], [`Volume ${u}`, fmtW(d.sum.volume, u), '#64d2ff'], ['PRs', String(d.sum.prs), '#ffd60a']];
  stats.forEach(([label, v, col], i) => {
    const x = 80 + i * 240;
    g.fillStyle = col; g.font = font(800, 64); g.fillText(v, x, 340);
    g.fillStyle = '#8e8e93'; g.font = font(600, 28); g.fillText(label, x, 385);
  });
  g.fillStyle = 'rgba(255,255,255,0.08)'; g.fillRect(80, 430, 920, 2);
  let y = 510;
  const shown = d.order.slice(0, 7);
  for (const id of shown) {
    const sets = d.sets.filter(s => s.exId === id);
    const best = sets.reduce((a, s) => (!a || s.weight > a.weight ? s : a), null);
    g.fillStyle = '#ffffff'; g.font = font(700, 40); g.fillText(truncate(g, store.exercise(id)?.name || '', 600), 80, y);
    g.fillStyle = '#ff9f0a'; g.font = font(700, 38); g.textAlign = 'right'; g.fillText(best ? setText(best) : '', 1000, y); g.textAlign = 'left';
    g.fillStyle = '#8e8e93'; g.font = font(500, 28); g.fillText(`${sets.length} set${sets.length === 1 ? '' : 's'}${sets.some(s => d.prIds.has(s.id)) ? '  ·  new record' : ''}`, 80, y + 42);
    y += 112;
  }
  if (d.order.length > shown.length) { g.fillStyle = '#8e8e93'; g.font = font(600, 30); g.fillText(`+ ${d.order.length - shown.length} more`, 80, y); }
  g.fillStyle = '#48484a'; g.font = font(600, 26); g.fillText('Logged with Overload · free and offline', 80, 1290);
  return c;
}
function truncate(g, s, w) { if (g.measureText(s).width <= w) return s; while (s && g.measureText(s + '…').width > w) s = s.slice(0, -1); return s + '…'; }

function shareSheet(ts) {
  if (!dayData(ts).sets.length) { toast('Nothing to share on this day'); return; }
  const canvas = drawShareCard(ts);
  const url = canvas.toDataURL('image/png');
  openSheet({
    cls: 'tall',
    render: () => html`<div class="sheet-grab"></div>
      <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>Share</h2><span class="circle ghost"></span></div>
      <div class="scroll"><img class="share-img" src="${url}" alt="Workout summary card">
      <p class="hint center">Press and hold the image to save it to Photos.</p>
      <div class="btn-row"><button class="btn accent" data-a="share-img">${icon('share')} Share image</button><button class="btn" data-a="copy">${icon('copy')} Copy text</button></div></div>`,
    actions: {
      'share-img': async () => {
        try {
          const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
          const file = new File([blob], `overload-${dayKey(ts)}.png`, { type: 'image/png' });
          if (navigator.canShare?.({ files: [file] })) { await navigator.share({ files: [file], text: shareTextFor(ts) }); return; }
          const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = file.name; a.click();
        } catch (e) { if (e?.name !== 'AbortError') toast('Press and hold the image to save it'); }
      },
      copy: async () => {
        try { await navigator.clipboard.writeText(shareTextFor(ts)); toast('Caption copied', { iconName: 'copy' }); }
        catch { toast('Copy is not available here'); }
      },
    },
  });
}
export { fmtNum };
