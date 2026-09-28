/* Rest timer bar ("2:44 Next Set"). Counts to an end timestamp, so it stays correct after the
 * phone locks. Beeps and vibrates when rest is over, then counts overtime. */
import { html, fmtClock } from './util.js';
import { icon } from './icons.js';
import * as store from './store.js';

const KEY = 'overload-timer';
let t = null; // { end, total, exId, alerted }
let tick = null;
let audio = null;

export function unlockAudio() {
  if (audio) return;
  try { audio = new (window.AudioContext || window.webkitAudioContext)(); } catch { audio = null; }
}
function beep() {
  if (!audio || !store.settings().sound) return;
  try {
    audio.resume?.();
    [0, 0.22, 0.44].forEach((d, i) => {
      const o = audio.createOscillator(), g = audio.createGain();
      o.frequency.value = i === 2 ? 1320 : 880; o.type = 'sine';
      g.gain.setValueAtTime(0.0001, audio.currentTime + d);
      g.gain.exponentialRampToValueAtTime(0.25, audio.currentTime + d + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + d + 0.18);
      o.connect(g).connect(audio.destination); o.start(audio.currentTime + d); o.stop(audio.currentTime + d + 0.2);
    });
  } catch { /* audio unavailable */ }
}

export function startRest(exId) {
  const st = store.settings();
  if (!st.restOn) return;
  const sec = store.exercise(exId)?.restSec ?? st.restSec;
  t = { end: Date.now() + sec * 1000, total: sec, exId, alerted: false };
  persist(); loop();
}
export function stopRest() { t = null; persist(); render(); }
export function addRest(sec) { if (!t) return; t.end = Math.max(Date.now(), t.end) + sec * 1000; t.total += sec; t.alerted = false; persist(); render(); }
export const restExId = () => t?.exId || null;

function persist() { try { t ? localStorage.setItem(KEY, JSON.stringify(t)) : localStorage.removeItem(KEY); } catch { /* ignore */ } }
export function restoreRest() {
  try { const v = JSON.parse(localStorage.getItem(KEY)); if (v && Date.now() - v.end < 60000) { t = v; loop(); } } catch { /* ignore */ }
}

function loop() {
  clearTimeout(tick);
  const step = () => { render(); if (t) tick = setTimeout(step, 250); };
  step();
}

function render() {
  const bar = document.getElementById('timerbar');
  document.body.classList.toggle('has-timer', !!t);
  if (!t) { bar.innerHTML = ''; return; }
  const left = (t.end - Date.now()) / 1000;
  if (left <= 0 && !t.alerted) {
    t.alerted = true; persist(); beep();
    try { navigator.vibrate?.([220, 120, 220]); } catch { /* unsupported */ }
  }
  if (left < -45) { stopRest(); return; }
  const over = left <= 0;
  const frac = over ? 1 : 1 - left / t.total;
  const C = 2 * Math.PI * 9;
  bar.className = `timerbar ${over ? 'over' : ''}`;
  bar.innerHTML = String(html`<button class="tb-main" data-a="timer-open" aria-label="Open exercise">
      <svg class="ring" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle class="prog" cx="12" cy="12" r="9" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - frac)}"/></svg>
      <b>${over ? `+${fmtClock(-left)}` : fmtClock(left)}</b><span>${over ? 'Go! Next set' : 'Next Set'}</span></button>
    <button class="tb-btn" data-a="timer-add" aria-label="Add 30 seconds">+30s</button>
    <button class="tb-btn x" data-a="timer-stop" aria-label="Stop timer">${icon('x')}</button>`);
}
