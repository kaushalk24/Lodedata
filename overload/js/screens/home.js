/* Sets tab root: My Workouts, templates, plan designer, streak. */
import { html, dayKey, fmtLongDate, weekdayLetter } from '../util.js';
import { icon } from '../icons.js';
import * as store from '../store.js';
import { registerScreen, renderScreen, push, openSheet, toast, confirmDialog, header, circle, toggle } from '../ui.js';
import { TEMPLATES, libByName, MUSCLES } from '../library.js';
import { generatePlan, planDayText, GOALS } from '../planner.js';
import { weeklyStreak, heatmap, daysSinceLast } from '../stats.js';
import { COLORS } from './common.js';

const TIPS = [
  { title: 'Organize by Workout', body: 'One folder per training day, like Push, Pull and Legs. Open the folder at the gym and work down the list.', folders: ['Push', 'Pull', 'Legs'] },
  { title: 'Organize by Muscle Group', body: 'One folder per body part. Handy when your days change but the muscles you train stay the same.', folders: ['Chest', 'Back', 'Legs', 'Shoulders', 'Arms'] },
  { title: 'Organize by Program', body: 'Follow a set plan with named days, such as Upper A and Lower A, and repeat the cycle.', folders: ['Upper A', 'Lower A', 'Upper B', 'Lower B'] },
];

registerScreen('home', {
  render(p) {
    const st = store.getState();
    const streak = weeklyStreak(store.allSets(), st.settings.weeklyGoal);
    const since = daysSinceLast(store.allSets());
    const showReminder = since != null && since >= st.settings.remindDays && st.ui.reminderDismissed !== dayKey(Date.now());
    const groups = [...new Set(st.workouts.map(w => w.group).filter(Boolean))];
    const wRow = (w, i) => html`<div class="row-wrap">
      ${p.edit ? html`<button class="row-del" data-a="delete-workout" data-id="${w.id}" aria-label="Delete ${w.name}">${icon('minus')}</button>` : ''}
      <button class="row" data-a="${p.edit ? 'edit-workout' : 'open-workout'}" data-id="${w.id}">
        <span class="row-icon c-${w.color}">${icon('book')}</span>
        <span class="row-main"><span class="row-title">${w.name}</span></span>
        ${p.edit ? html`<span class="reorder"><span data-a="move-workout" data-dir="-1" data-id="${w.id}" ${i === 0 ? 'hidden' : ''}>${icon('up')}</span><span data-a="move-workout" data-dir="1" data-id="${w.id}">${icon('down')}</span></span>`
        : html`<span class="row-meta">${w.exIds.length}</span><span class="chev">${icon('chevronRight')}</span>`}
      </button></div>`;
    const tip = TIPS[st.ui.tipIndex % TIPS.length];
    return html`
      ${header({
        left: circle('settings', 'gear', 'Settings'),
        right: html`<button class="circle ${streak.streak ? 'lit' : ''}" data-a="streak" aria-label="Streak">${icon('flame')}${streak.streak ? html`<small>${streak.streak}</small>` : ''}</button>
                    <button class="pill-btn" data-a="edit-toggle">${p.edit ? 'Done' : 'Edit'}</button>`,
      })}
      <div class="scroll"><div class="content">
        <h2 class="large-title">My Workouts</h2>
        ${showReminder ? html`<div class="banner">
          <span class="banner-icon">${icon('bell')}</span>
          <div><b>${since} days since your last workout</b><p>Everything has recovered, so today is a good day to train.</p></div>
          <button class="circle small" data-a="dismiss-reminder" aria-label="Dismiss">${icon('x')}</button></div>` : ''}
        <div class="card list">
          <button class="row accent" data-a="new-workout"><span class="row-icon">${icon('plus')}</span><span class="row-main">New Workout…</span></button>
          <button class="row accent" data-a="planner"><span class="row-icon">${icon('wand')}</span><span class="row-main">New Custom Plan…</span></button>
          <button class="row" data-a="my-exercises"><span class="row-icon c-green">${icon('books')}</span><span class="row-main"><span class="row-title">My Exercises</span></span>
            <span class="row-meta">${st.exercises.length}</span><span class="chev">${icon('chevronRight')}</span></button>
          ${st.workouts.filter(w => !w.group).map(wRow)}
          ${groups.map(g => html`<div class="list-caption">${g}</div>${st.workouts.filter(w => w.group === g).map(wRow)}`)}
        </div>
        ${!st.sets.length ? html`<div class="card onboarding">
          <h3>Welcome to Overload</h3>
          <p>Log a set in three taps: pick an exercise, check the numbers, hit the green button. Your data stays on this phone.</p>
          <div class="btn-row"><button class="btn accent" data-a="my-exercises">Log first set</button>
          <button class="btn" data-a="load-demo">Try demo data</button><button class="btn" data-a="open-import">Import history</button></div>
        </div>` : ''}
        <button class="section-head" data-a="toggle-templates"><h3>Workout Templates</h3><span class="${st.ui.templatesCollapsed ? '' : 'flip'}">${icon('chevronDown')}</span></button>
        ${st.ui.templatesCollapsed ? '' : html`<div class="tpl-grid">${TEMPLATES.map(t => html`
          <button class="tpl" data-a="template" data-id="${t.id}"><b>${t.name}</b><span>${t.exercises.join(', ')}</span></button>`)}</div>`}
        <button class="card tip" data-a="tips">
          <span class="eyebrow">Building your workouts</span>
          <span class="tip-row">${icon('note')}<span><b>${tip.title}</b><span>Explore common workout structures to build your personalized tracking setup.</span></span></span>
        </button>
      </div></div>`;
  },
  actions: {
    'edit-toggle': (el, ev, p, inst) => { p.edit = !p.edit; renderScreen(inst); },
    'my-exercises': () => push('exercises'),
    'open-workout': el => push('workout', { id: el.dataset.id }),
    'edit-workout': el => workoutEditor(el.dataset.id),
    'new-workout': () => workoutEditor(),
    'move-workout': (el, ev) => { ev.stopPropagation(); store.moveWorkout(el.dataset.id, +el.dataset.dir); },
    'delete-workout': async el => {
      const w = store.workout(el.dataset.id);
      if (!(await confirmDialog({ title: `Delete “${w.name}”?`, message: 'The exercises and their history stay in My Exercises.', confirm: 'Delete Workout' }))) return;
      const undo = store.deleteWorkout(w.id);
      toast(`Deleted ${w.name}`, { action: 'Undo', onAction: undo });
    },
    'toggle-templates': () => store.setUi('templatesCollapsed', !store.getState().ui.templatesCollapsed),
    template: el => templateSheet(TEMPLATES.find(t => t.id === el.dataset.id)),
    tips: () => tipsSheet(),
    planner: () => plannerSheet(),
    streak: () => streakSheet(),
    'dismiss-reminder': () => store.setUi('reminderDismissed', dayKey(Date.now())),
  },
});

/* ---------- workout editor ---------- */
export function workoutEditor(id = null) {
  const w = id ? store.workout(id) : null;
  const groups = [...new Set(store.getState().workouts.map(x => x.group).filter(Boolean))];
  openSheet({
    cls: 'tall',
    render: p => html`<div class="sheet-grab"></div>
      <form data-form="save" class="editor">
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Cancel')}<h2>${w ? 'Edit Workout' : 'New Workout'}</h2>
          <button type="submit" class="circle accent" aria-label="Save">${icon('check')}</button></div>
        <div class="scroll"><div class="big-icon c-${p.color}">${icon('bookFill')}</div>
        <label class="field-label" for="w-name">Name</label>
        <input id="w-name" class="field" value="${p.name}" placeholder="Lower Body, Monday, Triceps…" autocomplete="off" data-in="name">
        <p class="hint"><span class="accent-text">Organize</span> by workout, muscle group, day of the week, etc.</p>
        <label class="field-label" for="w-desc">Description</label>
        <textarea id="w-desc" class="field" rows="3" placeholder="Set a description or plan" data-in="desc">${p.desc}</textarea>
        <div class="swatches">${COLORS.map(c => html`<button type="button" class="swatch c-${c} ${p.color === c ? 'on' : ''}" data-a="color" data-c="${c}" aria-label="${c}"></button>`)}</div>
        <label class="field-label" for="w-group">Group</label>
        <input id="w-group" class="field" value="${p.group}" placeholder="No Group" list="w-groups" autocomplete="off" data-in="group">
        <datalist id="w-groups">${groups.map(g => html`<option value="${g}"></option>`)}</datalist>
        <p class="hint">Optional: organize this workout into a group.</p></div>
      </form>`,
    mount: el => { if (!w) setTimeout(() => el.querySelector('#w-name')?.focus(), 80); },
    inputs: { name: (el, ev, p) => { p.name = el.value; }, desc: (el, ev, p) => { p.desc = el.value; }, group: (el, ev, p) => { p.group = el.value; } },
    actions: { color: (el, ev, p, inst) => { p.color = el.dataset.c; inst.panel.querySelectorAll('.swatches .swatch').forEach(s => s.classList.toggle('on', s.dataset.c === p.color)); inst.panel.querySelector('.big-icon').className = `big-icon c-${p.color}`; } },
    forms: {
      save: (f, ev, p, inst) => {
        if (!p.name.trim()) { f.querySelector('#w-name').focus(); return; }
        const data = { name: p.name.trim(), desc: p.desc, color: p.color, group: p.group.trim() };
        if (w) store.updateWorkout(w.id, data); else { const nw = store.addWorkout(data); inst.close(); push('workout', { id: nw.id }); return; }
        inst.close();
      },
    },
  }, { name: w?.name || '', desc: w?.desc || '', color: w?.color || 'green', group: w?.group || '' });
}

/* ---------- templates ---------- */
function templateSheet(t) {
  openSheet({
    cls: 'tall',
    render: () => html`<div class="sheet-grab"></div>
      <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>Template</h2><span class="circle ghost"></span></div>
      <div class="scroll"><h2 class="sheet-title">${t.name}</h2><p class="muted">${t.desc}</p>
      <div class="card list">${t.exercises.map(n => { const lib = libByName(n); return html`<div class="row static">
        <span class="row-main"><span class="row-title">${n}</span><span class="row-sub">${lib ? lib.primary.map(m => MUSCLES[m]).join(', ') : ''}</span></span></div>`; })}</div>
      <button class="btn accent block" data-a="add">Add to My Workouts</button></div>`,
    actions: {
      add: (el, ev, p, inst) => {
        const w = store.workoutFromNames(t.name, t.exercises, { color: t.color, desc: t.desc });
        inst.close(); toast(`Added ${t.name}`); push('workout', { id: w.id });
      },
    },
  });
}

function tipsSheet() {
  store.setUi('tipIndex', store.getState().ui.tipIndex + 1);
  openSheet({
    cls: 'tall',
    render: () => html`<div class="sheet-grab"></div>
      <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>Building Your Workouts</h2><span class="circle ghost"></span></div>
      <div class="scroll"><p class="muted">A workout here is a folder of exercises. Each exercise keeps its own history, so the same exercise can sit in several folders.</p>
      ${TIPS.map((t, i) => html`<div class="card pad"><h3>${t.title}</h3><p class="muted">${t.body}</p>
        <div class="chips">${t.folders.map(f => html`<span class="chip static">${f}</span>`)}</div>
        <button class="btn block" data-a="create" data-i="${i}">Create these folders</button></div>`)}</div>`,
    actions: {
      create: (el, ev, p, inst) => {
        const t = TIPS[+el.dataset.i];
        const colors = ['red', 'blue', 'green', 'orange', 'purple'];
        t.folders.forEach((f, i) => store.addWorkout({ name: f, color: colors[i % colors.length] }));
        inst.close(); toast(`Created ${t.folders.length} folders`);
      },
    },
  });
}

/* ---------- plan designer (offline) ---------- */
function plannerSheet() {
  const seg = (key, opts, p) => html`<div class="seg">${opts.map(([v, label]) => html`<button type="button" class="${p[key] === v ? 'on' : ''}" data-a="set" data-k="${key}" data-v="${v}">${label}</button>`)}</div>`;
  openSheet({
    cls: 'tall planner',
    render: p => {
      if (p.plan) {
        return html`<div class="sheet-grab"></div>
          <div class="sheet-head">${circle('edit-plan', 'chevronLeft', 'Back')}<h2>Your Plan</h2><span class="circle ghost"></span></div>
          <div class="scroll"><h2 class="sheet-title">${p.plan.name}</h2><p class="muted">${p.plan.progression}</p>
          ${p.plan.days.map((d, i) => html`<div class="card pad plan-day"><h3><span class="day-num">${i + 1}</span>${d.name}</h3>
            ${d.exercises.map(e => html`<div class="plan-ex"><span>${e.name}</span><span class="muted">${e.sets} × ${e.reps}</span></div>`)}</div>`)}
          <button class="btn accent block" data-a="save-plan">Add ${p.plan.days.length} workouts</button></div>`;
      }
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<span></span><span class="tag">Offline · Free</span></div>
        <div class="scroll"><div class="plan-hero">${icon('sparkle')}<h2>Design Your Plan</h2><p class="muted">Built from proven splits. Runs on your phone, no account needed.</p></div>
        <div class="card pad"><h3 class="center">Training Goal</h3><p class="muted center">Start by selecting your priority.</p>
          ${Object.entries(GOALS).map(([k, g]) => html`<button type="button" class="goal ${p.goal === k ? 'on' : ''}" data-a="set" data-k="goal" data-v="${k}">
            <span class="goal-icon">${icon({ physique: 'heart', strength: 'trophy', athletic: 'bolt', general: 'target' }[k])}</span>
            <span><b>${g.name}</b><span class="muted">${g.blurb}</span></span></button>`)}</div>
        <label class="field-label">Days per week</label>${seg('days', [[2, '2'], [3, '3'], [4, '4'], [5, '5'], [6, '6']], p)}
        <label class="field-label">Equipment</label>${seg('equipment', [['gym', 'Full gym'], ['dumbbells', 'Dumbbells'], ['bodyweight', 'Bodyweight']], p)}
        <label class="field-label">Experience</label>${seg('level', [['beginner', 'Beginner'], ['intermediate', 'Intermediate']], p)}
        <button class="btn accent block" data-a="generate">Generate Plan</button></div>`;
    },
    actions: {
      set: (el, ev, p, inst) => { const v = el.dataset.v; p[el.dataset.k] = el.dataset.k === 'days' ? +v : v; inst.rerender(); },
      generate: (el, ev, p, inst) => { p.plan = generatePlan(p); inst.rerender(); },
      'edit-plan': (el, ev, p, inst) => { p.plan = null; inst.rerender(); },
      'save-plan': (el, ev, p, inst) => {
        const colors = ['red', 'blue', 'orange', 'green', 'purple', 'pink'];
        const ws = p.plan.days.map((d, i) => store.workoutFromNames(d.name, d.exercises.map(e => e.name),
          { color: colors[i % colors.length], desc: planDayText(d, i === 0 ? p.plan.progression : '') }));
        for (const w of ws) store.updateWorkout(w.id, { group: p.plan.name });
        inst.close(); toast(`Added ${ws.length} workouts`);
      },
    },
  }, { goal: 'physique', days: 3, equipment: 'gym', level: 'beginner', plan: null });
}

/* ---------- streak ---------- */
function streakSheet() {
  openSheet({
    cls: 'tall', live: true,
    render: () => {
      const st = store.getState();
      const s = weeklyStreak(store.allSets(), st.settings.weeklyGoal);
      const grid = heatmap(store.allSets(), 17);
      const days = grid.flat().filter(d => d.count).length;
      return html`<div class="sheet-grab"></div>
        <div class="sheet-head">${circle('sheet-dismiss', 'x', 'Close')}<h2>Streak</h2><span class="circle ghost"></span></div>
        <div class="scroll"><div class="streak-hero ${s.streak ? 'lit' : ''}">${icon('flame')}<b>${s.streak}</b><span>week${s.streak === 1 ? '' : 's'} in a row</span></div>
        <div class="card pad"><div class="week-dots">${Array.from({ length: s.goal }, (_, i) => html`<i class="${i < s.thisWeek ? 'on' : ''}"></i>`)}</div>
          <p class="center muted">${s.thisWeek >= s.goal ? 'Goal met this week.' : `${s.goal - s.thisWeek} more workout${s.goal - s.thisWeek === 1 ? '' : 's'} this week to keep the streak.`}</p></div>
        <div class="card pad"><div class="heat">
          <div class="heat-days">${[0, 1, 2, 3, 4, 5, 6].map(d => html`<span>${d % 2 ? weekdayLetter(d) : ''}</span>`)}</div>
          ${grid.map(col => html`<div class="heat-col">${col.map(c => html`<i class="${c.count == null ? 'future' : c.count ? (c.count > 20 ? 'l3' : c.count > 10 ? 'l2' : 'l1') : ''}" title="${fmtLongDate(c.ts)}"></i>`)}</div>`)}
        </div><p class="muted small">${days} training days in the last 17 weeks</p></div>
        <div class="card list">
          <div class="row static"><span class="row-main">Workout goal</span>
            <span class="stepper"><button data-a="goal" data-d="-1" aria-label="Fewer">${icon('minus')}</button><b>${st.settings.weeklyGoal} / week</b><button data-a="goal" data-d="1" aria-label="More">${icon('plus')}</button></span></div>
          <div class="row static"><span class="row-main">Daily congratulations</span>${toggle('congrats', st.settings.dailyCongrats)}</div>
        </div><p class="hint">A week counts when you train on at least ${st.settings.weeklyGoal} different days.</p></div>`;
    },
    actions: {
      goal: el => store.setSetting('weeklyGoal', Math.min(7, Math.max(1, store.settings().weeklyGoal + +el.dataset.d))),
      congrats: () => store.setSetting('dailyCongrats', !store.settings().dailyCongrats),
    },
  });
}

export { streakSheet };
