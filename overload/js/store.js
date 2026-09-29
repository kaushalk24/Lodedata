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
    measures: [],
    gyms: [{ id: gymId, name: 'My Gym', bar: 20, plates: { ...DEFAULT_PLATES } }],
    settings: {
      unit: 'kg', theme: 'system', keepAwake: true, weeklyGoal: 3, dailyCongrats: true,
      celebrations: true, restOn: true, restSec: 165, remindDays: 4, sound: true,
      oneRmOn: false, formula: 'epley', gymId, repLow: 8, repHigh: 12, stepKg: 2.5, showTargets: true, rpeOn: false,
    },
    ui: { templatesCollapsed: false, shareTipDismissed: false, reminderDismissed: null, tipIndex: 0, sessionStyle: 'cards', sessionRange: 'week', dupIgnore: [], backupAt: 0, backupSnooze: 0 },
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
  const before = state.workouts.map(w => ({ id: w.id, exIds: [...w.exIds], supersets: (w.supersets || []).map(g => [...g]) }));
  state.exercises = state.exercises.filter(e => e.id !== id);
  state.sets = state.sets.filter(s => s.exId !== id);
  for (const w of state.workouts) { w.exIds = w.exIds.filter(x => x !== id); dropFromSupersets(w, id); }
  commit({ sets: true });
  return () => { // undo
    state.exercises.push(ex); state.sets.push(...sets);
    for (const b of before) { const w = workout(b.id); if (w) { w.exIds = b.exIds; w.supersets = b.supersets; } }
    commit({ sets: true });
  };
}
/** Set several per-exercise rest timers in one save. Returns how many changed. */
export function setRestTimes(map) {
  let n = 0;
  for (const [id, sec] of Object.entries(map)) { const ex = exercise(id); if (ex) { ex.restSec = sec; n++; } }
  if (n) commit();
  return n;
}
/** Move all history of `fromId` into `intoId` (fixes duplicates like "Forearm curls 1/2"). */
export function mergeExercise(fromId, intoId) {
  if (fromId === intoId) return;
  for (const s of state.sets) if (s.exId === fromId) s.exId = intoId;
  for (const w of state.workouts) {
    if (w.exIds.includes(fromId)) w.exIds = [...new Set(w.exIds.map(x => x === fromId ? intoId : x))];
    if (w.supersets) w.supersets = w.supersets.map(g => [...new Set(g.map(x => x === fromId ? intoId : x))]).filter(g => g.length >= 2);
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
  if (w.exIds.includes(exId)) { w.exIds = w.exIds.filter(x => x !== exId); dropFromSupersets(w, exId); }
  else w.exIds = [...w.exIds, exId];
  commit();
}

/* ---------- supersets (groups of exercises inside a workout, done back to back) ---------- */
function dropFromSupersets(w, exId) {
  if (w.supersets) w.supersets = w.supersets.map(g => g.filter(x => x !== exId)).filter(g => g.length >= 2);
}
/** The superset an exercise belongs to (first match across workouts), with only exercises that still exist. */
export function supersetFor(exId) {
  for (const w of state.workouts) {
    for (const g of w.supersets || []) {
      if (!g.includes(exId)) continue;
      const ids = g.filter(id => exercise(id) && w.exIds.includes(id));
      if (ids.length >= 2 && ids.includes(exId)) return { wid: w.id, ids };
    }
  }
  return null;
}
/** Group exercises in the order given. An exercise can only be in one group per workout. */
export function addSuperset(wid, ids) {
  const w = workout(wid);
  const keep = (w.supersets || []).map(g => g.filter(x => !ids.includes(x))).filter(g => g.length >= 2);
  w.supersets = [...keep, [...ids]];
  commit();
}
export function removeSuperset(wid, index) {
  const w = workout(wid);
  const [g] = w.supersets.splice(index, 1);
  commit();
  return () => { w.supersets.splice(index, 0, g); commit(); };
}
export function duplicateWorkout(id) {
  const w = workout(id);
  const copy = addWorkout({ ...w, name: `${w.name} copy` });
  if (w.supersets?.length) { copy.supersets = w.supersets.map(g => [...g]); commit(); }
  return copy;
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

/* ---------- measurements (stored in cm, or % for body fat) ---------- */
export function addMeasures(values, ts = Date.now()) {
  for (const [key, value] of Object.entries(values)) state.measures.push({ id: uid(), ts, key, value });
  commit();
}
export function deleteMeasure(id) {
  const m = state.measures.find(x => x.id === id);
  state.measures = state.measures.filter(x => x.id !== id); commit();
  return () => { state.measures.push(m); commit(); };
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

// One shared connection. Version 2 adds the photos store; photos never go into backups or CSV.
let dbp = null;
function idb() {
  dbp ??= new Promise((resolve, reject) => {
    const r = indexedDB.open('overload', 2);
    r.onupgradeneeded = () => {
      const db = r.result;
      if (!db.objectStoreNames.contains('kv')) db.createObjectStore('kv');
      if (!db.objectStoreNames.contains('photos')) db.createObjectStore('photos', { keyPath: 'id' });
    };
    r.onsuccess = () => {
      const db = r.result;
      db.onversionchange = () => { db.close(); dbp = null; };
      resolve(db);
    };
    r.onerror = () => { dbp = null; reject(r.error); };
    r.onblocked = () => { dbp = null; reject(new Error('Close other Overload tabs to finish updating.')); };
  });
  return dbp;
}
async function idbDo(mode, fn, storeName = 'kv') {
  const db = await idb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    const req = fn(tx.objectStore(storeName));
    tx.oncomplete = () => resolve(req?.result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

/* ---------- progress photos (IndexedDB only: they stay on this device) ---------- */
export const listPhotos = async () => ((await idbDo('readonly', s => s.getAll(), 'photos')) || []).sort((a, b) => b.ts - a.ts);
export async function addPhoto(blob, ts = Date.now()) {
  const p = { id: uid(), ts, blob };
  await idbDo('readwrite', s => s.put(p), 'photos');
  return p;
}
export const deletePhoto = id => idbDo('readwrite', s => s.delete(id), 'photos');
export const clearPhotos = () => idbDo('readwrite', s => s.clear(), 'photos');

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
