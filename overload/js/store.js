/* App state, persistence (IndexedDB with localStorage fallback) and every mutation.
 * Screens read through the query helpers and re-render when `subscribe` fires. */

import { uid, norm } from './util.js';
import { guessMuscles, libByName, LIB_BY_ID } from './library.js';

const DEFAULT_PLATES = { 25: 30, 20: 30, 15: 30, 10: 30, 5: 30, 2.5: 30, 1.25: 10 };

export function defaultState() {
  const gymId = uid();
  return {
    v: 1,
    exercises: [],
    workouts: [],
    sets: [],
    sessions: [],
    body: [],
    gyms: [{ id: gymId, name: 'My Gym', bar: 20, plates: { ...DEFAULT_PLATES } }],
    settings: {
      unit: 'kg', theme: 'system', keepAwake: true, weeklyGoal: 3, dailyCongrats: true,
      celebrations: true, restOn: true, restSec: 165, remindDays: 4, sound: true,
      oneRmOn: false, formula: 'epley', gymId, repLow: 8, repHigh: 12, stepKg: 2.5, showTargets: true,
    },
    ui: { templatesCollapsed: false, shareTipDismissed: false, reminderDismissed: null, tipIndex: 0, sessionStyle: 'cards', sessionRange: 'week' },
  };
}

let state = defaultState();
const listeners = new Set();
let exIndex = null; // exId -> sets (sorted by ts)

export const getState = () => state;
export const settings = () => state.settings;
export const subscribe = fn => { listeners.add(fn); return () => listeners.delete(fn); };

function commit({ sets = false } = {}) {
  if (sets) exIndex = null;
  scheduleSave();
  for (const fn of listeners) fn();
}

/* ---------- queries ---------- */
export const exercise = id => state.exercises.find(e => e.id === id);
export const workout = id => state.workouts.find(w => w.id === id);
export const gym = id => state.gyms.find(g => g.id === id) || state.gyms[0];
export const currentGym = () => gym(state.settings.gymId);

function buildIndex() {
  exIndex = new Map();
  state.sets.sort((a, b) => a.ts - b.ts);
  for (const s of state.sets) {
    if (!exIndex.has(s.exId)) exIndex.set(s.exId, []);
    exIndex.get(s.exId).push(s);
  }
}
export const setsFor = exId => { if (!exIndex) buildIndex(); return exIndex.get(exId) || []; };
export const allSets = () => { if (!exIndex) buildIndex(); return state.sets; };
export const lastSet = exId => { const a = setsFor(exId); return a[a.length - 1] || null; };
export const lastTs = exId => lastSet(exId)?.ts || 0;
export const muscleMap = exId => { const e = exercise(exId); return e ? { primary: e.primary || [], secondary: e.secondary || [] } : null; };
/** Most recent bodyweight entry, used to weigh bodyweight sets. */
export const bodyKg = () => state.body.length ? [...state.body].sort((a, b) => b.ts - a.ts)[0].kg : 0;
export const findExerciseByName = name => state.exercises.find(e => norm(e.name) === norm(name));
export const sortedExercises = () => [...state.exercises].sort((a, b) => (lastTs(b.id) - lastTs(a.id)) || a.name.localeCompare(b.name));

/* ---------- exercises ---------- */
export function addExercise(name, extra = {}) {
  name = name.trim();
  const existing = findExerciseByName(name);
  if (existing) return existing;
  const lib = extra.libId ? LIB_BY_ID[extra.libId] : libByName(name);
  const g = lib ? { primary: lib.primary, secondary: lib.secondary, equipment: lib.equipment } : guessMuscles(name);
  const ex = {
    id: uid(), name, libId: lib?.id || null, primary: [...g.primary], secondary: [...g.secondary], equipment: g.equipment,
    note: '', restSec: null, created: Date.now(), ...extra,
  };
  state.exercises.push(ex);
  commit();
  return ex;
}
export function updateExercise(id, patch) { Object.assign(exercise(id), patch); commit(); }
export function deleteExercise(id) {
  const ex = exercise(id);
  const sets = state.sets.filter(s => s.exId === id);
  const inWorkouts = state.workouts.filter(w => w.exIds.includes(id)).map(w => w.id);
  state.exercises = state.exercises.filter(e => e.id !== id);
  state.sets = state.sets.filter(s => s.exId !== id);
  for (const w of state.workouts) w.exIds = w.exIds.filter(x => x !== id);
  commit({ sets: true });
  return () => { // undo
    state.exercises.push(ex); state.sets.push(...sets);
    for (const wid of inWorkouts) workout(wid)?.exIds.push(id);
    commit({ sets: true });
  };
}
/** Move all history of `fromId` into `intoId` (fixes duplicates like "Forearm curls 1/2"). */
export function mergeExercise(fromId, intoId) {
  if (fromId === intoId) return;
  for (const s of state.sets) if (s.exId === fromId) s.exId = intoId;
  for (const w of state.workouts) {
    if (w.exIds.includes(fromId)) w.exIds = [...new Set(w.exIds.map(x => x === fromId ? intoId : x))];
  }
  const from = exercise(fromId), into = exercise(intoId);
  if (from?.note && !into.note) into.note = from.note;
  state.exercises = state.exercises.filter(e => e.id !== fromId);
  commit({ sets: true });
}

/* ---------- sets ---------- */
export function addSet(s) {
  const set = { id: uid(), ts: Date.now(), label: null, note: '', gymId: state.settings.gymId, bw: false, ...s };
  state.sets.push(set);
  commit({ sets: true });
  return set;
}
export function updateSet(id, patch) { Object.assign(state.sets.find(s => s.id === id), patch); commit({ sets: true }); }
export function deleteSet(id) {
  const s = state.sets.find(x => x.id === id);
  state.sets = state.sets.filter(x => x.id !== id);
  commit({ sets: true });
  return () => { state.sets.push(s); commit({ sets: true }); };
}

/* ---------- workouts (folders) ---------- */
export function addWorkout({ name, desc = '', color = 'green', group = '', exIds = [] }) {
  const w = { id: uid(), name: name.trim() || 'Workout', desc, color, group, exIds: [...exIds], created: Date.now() };
  state.workouts.push(w); commit(); return w;
}
export function updateWorkout(id, patch) { Object.assign(workout(id), patch); commit(); }
export function deleteWorkout(id) {
  const i = state.workouts.findIndex(w => w.id === id);
  const [w] = state.workouts.splice(i, 1); commit();
  return () => { state.workouts.splice(i, 0, w); commit(); };
}
export function moveWorkout(id, dir) {
  const a = state.workouts, i = a.findIndex(w => w.id === id), j = i + dir;
  if (j < 0 || j >= a.length) return;
  [a[i], a[j]] = [a[j], a[i]]; commit();
}
export function toggleInWorkout(wid, exId) {
  const w = workout(wid);
  w.exIds = w.exIds.includes(exId) ? w.exIds.filter(x => x !== exId) : [...w.exIds, exId];
  commit();
}
export function duplicateWorkout(id) {
  const w = workout(id);
  return addWorkout({ ...w, name: `${w.name} copy` });
}
/** Create a workout from exercise names, adding any exercise that doesn't exist yet. */
export function workoutFromNames(name, names, { color = 'green', desc = '' } = {}) {
  const ids = names.map(n => addExercise(n).id);
  return addWorkout({ name, color, desc, exIds: ids });
}

/* ---------- sessions (timed activities) ---------- */
export const runningSession = () => state.sessions.find(s => !s.end) || null;
export function startSession(activity) {
  if (runningSession()) return runningSession();
  const s = { id: uid(), activity, start: Date.now(), end: null };
  state.sessions.push(s); commit(); return s;
}
export function stopSession() { const s = runningSession(); if (s) { s.end = Date.now(); commit(); } return s; }
export function addSession(activity, start, end) { state.sessions.push({ id: uid(), activity, start, end }); commit(); }
export function deleteSession(id) {
  const s = state.sessions.find(x => x.id === id);
  state.sessions = state.sessions.filter(x => x.id !== id); commit();
  return () => { state.sessions.push(s); commit(); };
}

/* ---------- body ---------- */
export function addBodyWeight(kg, ts = Date.now()) { state.body.push({ id: uid(), ts, kg }); commit(); }
export function deleteBodyWeight(id) {
  const b = state.body.find(x => x.id === id);
  state.body = state.body.filter(x => x.id !== id); commit();
  return () => { state.body.push(b); commit(); };
}

/* ---------- gyms ---------- */
export function addGym(name) {
  const g = { id: uid(), name: name.trim() || 'Gym', bar: 20, plates: { ...currentGym().plates } };
  state.gyms.push(g); commit(); return g;
}
export function updateGym(id, patch) { Object.assign(gym(id), patch); commit(); }
export function deleteGym(id) {
  if (state.gyms.length < 2) return;
  state.gyms = state.gyms.filter(g => g.id !== id);
  if (state.settings.gymId === id) state.settings.gymId = state.gyms[0].id;
  commit();
}

/* ---------- settings / ui ---------- */
export function setSetting(k, v) { state.settings[k] = v; commit(); }
export function setUi(k, v) { state.ui[k] = v; commit(); }

/* ---------- whole-state operations ---------- */
export function replaceState(next) {
  const base = defaultState();
  state = {
    ...base, ...next,
    settings: { ...base.settings, ...(next.settings || {}) },
    ui: { ...base.ui, ...(next.ui || {}) },
    gyms: next.gyms?.length ? next.gyms : base.gyms,
  };
  if (!state.gyms.some(g => g.id === state.settings.gymId)) state.settings.gymId = state.gyms[0].id;
  commit({ sets: true });
}
export const exportState = () => JSON.parse(JSON.stringify(state));

/* ---------- persistence ---------- */
const KEY = 'overload-state';
let saveTimer = null;
function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(save, 250); }

function idb() {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open('overload', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('kv');
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
async function idbDo(mode, fn) {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('kv', mode);
    const req = fn(tx.objectStore('kv'));
    tx.oncomplete = () => resolve(req?.result);
    tx.onerror = () => reject(tx.error);
  });
}

export async function save() {
  clearTimeout(saveTimer);
  const json = JSON.stringify(state);
  try { await idbDo('readwrite', s => s.put(json, KEY)); return; } catch { /* fall through */ }
  try { localStorage.setItem(KEY, json); } catch { /* storage unavailable: keep running in memory */ }
}

export async function load() {
  let json = null;
  try { json = await idbDo('readonly', s => s.get(KEY)); } catch { /* fall back */ }
  if (!json) { try { json = localStorage.getItem(KEY); } catch { /* ignore */ } }
  if (json) {
    try { replaceState(JSON.parse(json)); return true; } catch { /* corrupt: start fresh */ }
  }
  try { navigator.storage?.persist?.(); } catch { /* optional */ }
  return false;
}
