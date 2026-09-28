/* View layer plumbing: per-tab navigation stacks, bottom sheets, dialogs, toasts, and one
 * delegated event handler. Screens and sheets are plain objects:
 *   { render(p, inst) -> html, actions?: {name(el, ev, p, inst)}, inputs?: {name(el, ev, p, inst)},
 *     mount?(el, p, inst), title? }
 * `p` is the instance's own mutable params/state object. */
import { html, esc, raw } from './util.js';
import { icon } from './icons.js';
import { hydrateCharts } from './chart.js';

const screens = {};
export const registerScreen = (name, def) => { screens[name] = def; };

export const TABS = ['sets', 'sessions', 'body', 'today'];
const ROOT_SCREEN = { sets: 'home', sessions: 'sessions', body: 'body', today: 'today' };
const nav = { tab: 'sets', stacks: {} };
const sheets = [];
let globalActions = {};
export const setGlobalActions = a => { globalActions = a; };
export const currentTab = () => nav.tab;

/* ---------- screens ---------- */
function tabRoot(tab) { return document.querySelector(`.tab-root[data-tab="${tab}"]`); }

function makeScreen(name, params, tab) {
  const el = document.createElement('section');
  el.className = 'screen';
  el.dataset.screen = name;
  const inst = { name, p: params, el, tab, def: screens[name] };
  el._inst = inst;
  renderScreen(inst);
  return inst;
}

export function renderScreen(inst) {
  const scroller = inst.el.querySelector('.scroll');
  const top = scroller ? scroller.scrollTop : 0;
  inst.el.innerHTML = String(inst.def.render(inst.p, inst));
  const sc = inst.el.querySelector('.scroll');
  if (sc && top) sc.scrollTop = top;
  hydrateCharts(inst.el);
  inst.def.mount?.(inst.el, inst.p, inst);
  inst.dirty = false;
}

export function initNav() {
  for (const tab of TABS) {
    const inst = makeScreen(ROOT_SCREEN[tab], {}, tab);
    nav.stacks[tab] = [inst];
    tabRoot(tab).appendChild(inst.el);
  }
  showTab('sets', true);
  try { history.pushState({ trap: 1 }, ''); } catch { /* sandboxed */ }
  window.addEventListener('popstate', () => {
    if (back()) { try { history.pushState({ trap: 1 }, ''); } catch { /* ignore */ } }
  });
  wireEdgeSwipe();
}

export function showTab(tab, silent = false) {
  if (!silent && tab === nav.tab) { // tapping the active tab pops to its root
    const st = nav.stacks[tab];
    while (st.length > 1) { const s = st.pop(); s.el.remove(); }
    st[0].el.classList.remove('behind');
    const sc = st[0].el.querySelector('.scroll'); sc?.scrollTo({ top: 0, behavior: 'smooth' });
    renderScreen(st[0]);
  }
  nav.tab = tab;
  for (const t of TABS) tabRoot(t).hidden = t !== tab;
  const top = topScreen();
  if (top.dirty) renderScreen(top);
  document.querySelectorAll('.tabbar [data-tab]').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
}

export const topScreen = (tab = nav.tab) => { const st = nav.stacks[tab]; return st[st.length - 1]; };

export function push(name, params = {}) {
  const st = nav.stacks[nav.tab];
  const prev = st[st.length - 1];
  const inst = makeScreen(name, params, nav.tab);
  inst.el.classList.add('enter');
  tabRoot(nav.tab).appendChild(inst.el);
  st.push(inst);
  requestAnimationFrame(() => requestAnimationFrame(() => { inst.el.classList.remove('enter'); prev.el.classList.add('behind'); }));
  return inst;
}

export function pop() {
  const st = nav.stacks[nav.tab];
  if (st.length < 2) return false;
  const inst = st.pop(), prev = st[st.length - 1];
  inst.def.unmount?.(inst.el, inst.p, inst);
  prev.el.classList.remove('behind');
  renderScreen(prev);
  inst.el.classList.add('leave');
  setTimeout(() => inst.el.remove(), 320);
  return true;
}

/** Close the top sheet, or pop the current stack. Returns false if there was nothing to close. */
export function back() {
  if (sheets.length) { closeSheet(sheets[sheets.length - 1]); return true; }
  return pop();
}

/** Re-render whatever is visible (after a store change). Hidden tabs re-render when shown. */
export function refreshAll() {
  for (const tab of TABS) for (const s of nav.stacks[tab] || []) s.dirty = true;
  const top = topScreen();
  if (top) renderScreen(top);
  for (const sh of sheets) if (sh.def.live) renderSheet(sh);
}

function wireEdgeSwipe() {
  let start = null;
  document.addEventListener('touchstart', e => {
    const t = e.touches[0];
    if (t.clientX > 22 || sheets.length || nav.stacks[nav.tab].length < 2) return;
    start = { x: t.clientX, y: t.clientY, el: topScreen().el, dx: 0 };
  }, { passive: true });
  document.addEventListener('touchmove', e => {
    if (!start) return;
    const t = e.touches[0];
    start.dx = Math.max(0, t.clientX - start.x);
    if (Math.abs(t.clientY - start.y) > 40 && start.dx < 20) { start = null; return; }
    start.el.style.transition = 'none';
    start.el.style.transform = `translateX(${start.dx}px)`;
  }, { passive: true });
  document.addEventListener('touchend', () => {
    if (!start) return;
    const { el, dx } = start; start = null;
    el.style.transition = ''; el.style.transform = '';
    if (dx > 90) pop();
  });
}

/* ---------- sheets ---------- */
/**
 * @param {object} def  { render, actions, inputs, mount, live, cls, onClose }
 * @param {object} p    sheet state
 */
export function openSheet(def, p = {}) {
  const wrap = document.createElement('div');
  wrap.className = `sheet ${def.cls || ''}`;
  wrap.innerHTML = '<div class="sheet-backdrop" data-a="sheet-dismiss"></div><div class="sheet-panel" role="dialog" aria-modal="true"></div>';
  const inst = { def, p, el: wrap, panel: wrap.querySelector('.sheet-panel') };
  inst.panel._inst = inst;
  inst.close = v => closeSheet(inst, v);
  inst.rerender = () => renderSheet(inst);
  document.getElementById('sheets').appendChild(wrap);
  sheets.push(inst);
  renderSheet(inst);
  requestAnimationFrame(() => requestAnimationFrame(() => wrap.classList.add('open')));
  wireSheetDrag(inst);
  return inst;
}
export function renderSheet(inst) {
  const sc = inst.panel.querySelector('.scroll');
  const top = sc ? sc.scrollTop : 0;
  inst.panel.innerHTML = String(inst.def.render(inst.p, inst));
  const sc2 = inst.panel.querySelector('.scroll'); if (sc2 && top) sc2.scrollTop = top;
  hydrateCharts(inst.panel);
  inst.def.mount?.(inst.panel, inst.p, inst);
}
export function closeSheet(inst, value) {
  const i = sheets.indexOf(inst);
  if (i < 0) return;
  sheets.splice(i, 1);
  inst.el.classList.remove('open');
  inst.el.classList.add('closing');
  if (document.activeElement && inst.el.contains(document.activeElement)) document.activeElement.blur();
  setTimeout(() => inst.el.remove(), 300);
  inst.def.onClose?.(inst.p, value, inst);
}
export const topSheet = () => sheets[sheets.length - 1];

function wireSheetDrag(inst) {
  let y0 = null, dy = 0;
  inst.panel.addEventListener('pointerdown', e => {
    if (!e.target.closest('.sheet-grab')) return;
    y0 = e.clientY; dy = 0; inst.panel.style.transition = 'none';
    inst.panel.setPointerCapture?.(e.pointerId);
  });
  inst.panel.addEventListener('pointermove', e => {
    if (y0 == null) return;
    dy = Math.max(0, e.clientY - y0);
    inst.panel.style.transform = `translateY(${dy}px)`;
  });
  const end = () => {
    if (y0 == null) return;
    y0 = null; inst.panel.style.transition = ''; inst.panel.style.transform = '';
    if (dy > 90 && !inst.def.noDismiss) closeSheet(inst);
  };
  inst.panel.addEventListener('pointerup', end);
  inst.panel.addEventListener('pointercancel', end);
}

/* ---------- dialogs ---------- */
/** Action list. Resolves with the chosen option's value, or null. */
export function choose({ title = '', message = '', options }) {
  return new Promise(resolve => {
    openSheet({
      cls: 'action-sheet',
      render: () => html`<div class="sheet-grab"></div>
        ${title ? html`<div class="as-title">${title}</div>` : ''}${message ? html`<p class="as-msg">${message}</p>` : ''}
        <div class="as-list">${options.map((o, i) => html`<button class="as-item ${o.destructive ? 'danger' : ''}" data-a="pick" data-i="${i}">${o.icon ? icon(o.icon) : ''}<span>${o.label}</span></button>`)}</div>
        <button class="as-cancel" data-a="sheet-dismiss">Cancel</button>`,
      actions: { pick: (el, ev, p, inst) => inst.close(options[+el.dataset.i].value) },
      onClose: (p, v) => resolve(v ?? null),
    });
  });
}
export async function confirmDialog({ title, message = '', confirm = 'Delete', destructive = true }) {
  const v = await choose({ title, message, options: [{ label: confirm, value: true, destructive }] });
  return v === true;
}
/** Single text field. Resolves with the trimmed text, or null when cancelled. */
export function promptDialog({ title, value = '', placeholder = '', confirm = 'Save', type = 'text', hint = '' }) {
  return new Promise(resolve => {
    let done = false;
    openSheet({
      cls: 'prompt-sheet',
      render: () => html`<div class="sheet-grab"></div>
        <form class="prompt" data-form="submit">
          <div class="sheet-head"><button type="button" class="circle" data-a="sheet-dismiss" aria-label="Cancel">${icon('x')}</button>
          <h2>${title}</h2><button type="submit" class="circle accent" aria-label="${confirm}">${icon('check')}</button></div>
          <input id="prompt-input" class="field" type="${type}" ${type === 'number' ? raw('inputmode="decimal" step="any"') : ''} value="${value}" placeholder="${placeholder}" autocomplete="off" enterkeyhint="done">
          ${hint ? html`<p class="hint">${hint}</p>` : ''}
        </form>`,
      mount: el => { const i = el.querySelector('input'); setTimeout(() => { i.focus(); i.select?.(); }, 60); },
      forms: { submit: (form, ev, p, inst) => { done = true; const v = form.querySelector('input').value.trim(); inst.close(); resolve(v); } },
      onClose: () => { if (!done) resolve(null); },
    });
  });
}

/* ---------- toasts ---------- */
let toastTimer = null;
export function toast(message, { action = null, onAction = null, kind = '', ms = 3800, iconName = null } = {}) {
  const el = document.getElementById('toast');
  el.className = `toast show ${kind}`;
  el.innerHTML = String(html`${iconName ? icon(iconName) : ''}<span>${message}</span>${action ? html`<button data-a="toast-action">${action}</button>` : ''}`);
  el._onAction = onAction;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.classList.remove('show'); }, ms);
}
export function celebrate() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const layer = document.getElementById('confetti');
  const colors = ['#ffd60a', '#30d158', '#ff9f0a', '#64d2ff', '#ff375f', '#bf5af2'];
  let bits = '';
  for (let i = 0; i < 36; i++) {
    const x = 50 + (Math.random() - 0.5) * 30, dx = (Math.random() - 0.5) * 90, dy = 40 + Math.random() * 50, rot = Math.random() * 720;
    bits += `<i style="left:${x}%;background:${colors[i % 6]};--dx:${dx}vw;--dy:${dy}vh;--r:${rot}deg;animation-delay:${Math.random() * 120}ms"></i>`;
  }
  layer.innerHTML = bits;
  setTimeout(() => { layer.innerHTML = ''; }, 1800);
}

/* ---------- events ---------- */
function owner(el) {
  const panel = el.closest('.sheet-panel');
  if (panel) return panel._inst;
  const sc = el.closest('.screen');
  return sc ? sc._inst : null;
}

export function wireEvents() {
  document.addEventListener('click', ev => {
    const el = ev.target.closest('[data-a]');
    if (!el || el.disabled) return;
    const a = el.dataset.a;
    if (a === 'sheet-dismiss') {
      ev.preventDefault();
      const sh = el.closest('.sheet');
      const inst = sheets.find(s => s.el === sh);
      if (inst && !(inst.def.noDismiss && el.classList.contains('sheet-backdrop'))) closeSheet(inst);
      return;
    }
    if (a === 'toast-action') { const t = document.getElementById('toast'); t.classList.remove('show'); t._onAction?.(); return; }
    const inst = owner(el);
    const fn = inst?.def.actions?.[a];
    if (fn) { ev.preventDefault(); fn(el, ev, inst.p, inst); return; }
    if (globalActions[a]) { ev.preventDefault(); globalActions[a](el, ev, inst); }
  });
  const onInput = ev => {
    if (ev.type === 'input' && ev.target.matches('select,[type=file],[type=checkbox],[type=datetime-local]')) return; // handled on change
    const el = ev.target.closest('[data-in]');
    if (!el) return;
    const inst = owner(el);
    const fn = inst?.def.inputs?.[el.dataset.in];
    if (fn) fn(el, ev, inst.p, inst);
  };
  document.addEventListener('input', onInput);
  document.addEventListener('change', ev => { if (ev.target.matches('select,[type=checkbox],[type=datetime-local],[type=date],[type=file]')) onInput(ev); });
  document.addEventListener('submit', ev => {
    const form = ev.target.closest('[data-form]');
    ev.preventDefault();
    if (!form) return;
    const inst = owner(form);
    inst?.def.forms?.[form.dataset.form]?.(form, ev, inst.p, inst);
  });
}

/* ---------- shared bits of markup ---------- */
export const header = ({ title = '', left = '', right = '', large = false } = {}) => html`
  <header class="bar ${large ? 'large' : ''}">
    <div class="bar-side">${left}</div><h1 class="bar-title">${title}</h1><div class="bar-side right">${right}</div>
  </header>`;
export const backBtn = () => html`<button type="button" class="circle" data-a="back" aria-label="Back">${icon('chevronLeft')}</button>`;
export const circle = (a, name, label, extra = '') => html`<button type="button" class="circle ${extra}" data-a="${a}" aria-label="${label}">${icon(name)}</button>`;
export const toggle = (a, on, extra = '') => html`<button type="button" class="switch ${on ? 'on' : ''}" role="switch" aria-checked="${on ? 'true' : 'false'}" data-a="${a}" ${raw(extra)}><i></i></button>`;
export const emptyState = (title, body, actions = '') => html`<div class="empty"><h3>${title}</h3><p>${body}</p>${actions}</div>`;
export { esc };
