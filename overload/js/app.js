/* Boot: load data, build the tab bar, wire global actions, theme, wake lock and offline cache. */
import { html } from './util.js';
import { icon } from './icons.js';
import * as store from './store.js';
import { demoState } from './dataio.js';
import { initNav, wireEvents, setGlobalActions, showTab, push, back, refreshAll, currentTab, topScreen, toast } from './ui.js';
import { startRest, stopRest, addRest, restExId, restoreRest, unlockAudio } from './timer.js';
import { openSettings } from './screens/settings.js';
import './screens/home.js';
import './screens/exercises.js';
import './screens/exercise.js';
import './screens/sessions.js';
import './screens/body.js';
import './screens/today.js';

const TABS = [['sets', 'Sets', 'tabSets'], ['sessions', 'Sessions', 'tabSessions'], ['body', 'Body', 'tabBody'], ['today', 'Today', 'tabToday']];

function applyTheme() {
  const t = store.settings().theme;
  const root = document.documentElement;
  // "Match Device" leaves any theme a host page stamped on <html> alone; only undo our own choice.
  if (t === 'system') { if (root.dataset.themeOwner) { root.removeAttribute('data-theme'); delete root.dataset.themeOwner; } }
  else { root.setAttribute('data-theme', t); root.dataset.themeOwner = 'app'; }
  const eff = root.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const dark = eff === 'dark';
  document.querySelector('meta[name=theme-color]')?.setAttribute('content', dark ? '#000000' : '#f2f2f7');
}

let wakeLock = null;
async function syncWakeLock() {
  const want = store.settings().keepAwake && document.visibilityState === 'visible';
  try {
    if (want && !wakeLock && 'wakeLock' in navigator) {
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release', () => { wakeLock = null; });
    } else if (!want && wakeLock) { await wakeLock.release(); wakeLock = null; }
  } catch { wakeLock = null; }
}

/** Keep bottom docks above the on-screen keyboard (iOS resizes the visual viewport only). */
function trackKeyboard() {
  const vv = window.visualViewport;
  if (!vv) return;
  const update = () => {
    const kb = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
    document.documentElement.style.setProperty('--kb', `${kb}px`);
    document.body.classList.toggle('kb-open', kb > 80);
  };
  vv.addEventListener('resize', update); vv.addEventListener('scroll', update); update();
}

async function boot() {
  const had = await store.load();
  if (!had && window.OVERLOAD_DEMO) store.replaceState(demoState(store.getState()));
  applyTheme();
  document.querySelector('.tabbar').innerHTML = String(html`${TABS.map(([k, label, ic]) => html`<button data-a="tab" data-tab="${k}">${icon(ic)}<span>${label}</span></button>`)}`);
  wireEvents();
  initNav();
  setGlobalActions({
    back: () => back(),
    tab: el => showTab(el.dataset.tab),
    settings: () => openSettings(),
    'open-import': () => openSettings('data'),
    'open-exercise': el => push('exercise', { id: el.dataset.id }),
    'load-demo': () => { store.replaceState(demoState(store.getState())); toast('Demo data loaded. Erase it any time in Settings › Import & Export.'); },
    'timer-open': () => {
      const id = restExId();
      if (!id) return;
      const top = topScreen();
      if (top?.name === 'exercise' && top.p.id === id) return;
      if (currentTab() !== 'sets') showTab('sets');
      push('exercise', { id });
    },
    'timer-add': () => addRest(30),
    'timer-stop': () => stopRest(),
  });
  store.subscribe(() => { applyTheme(); refreshAll(); syncWakeLock(); });
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', applyTheme);
  document.addEventListener('visibilitychange', () => { syncWakeLock(); if (document.visibilityState === 'hidden') store.save(); else refreshAll(); });
  window.addEventListener('pagehide', () => store.save());
  document.addEventListener('pointerdown', unlockAudio, { once: true });
  trackKeyboard();
  syncWakeLock();
  restoreRest();
  document.body.classList.add('ready');
  if ('serviceWorker' in navigator && location.protocol.startsWith('http') && !window.OVERLOAD_DEMO) {
    navigator.serviceWorker.register('sw.js').catch(() => { /* offline cache is optional */ });
  }
}

boot();
export { startRest };
