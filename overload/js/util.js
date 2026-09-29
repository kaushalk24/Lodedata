/* Small shared helpers: safe HTML templating, ids, units and date/number formatting.
 * No DOM access here, so everything is testable with `node --test`. */

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ESC[c]);

class Raw { constructor(s) { this.s = s; } toString() { return this.s; } }
export const raw = s => new Raw(String(s ?? ''));

/** Tagged template that escapes every interpolation unless it is raw() or an array of raw. */
export function html(strings, ...vals) {
  let out = strings[0];
  for (let i = 0; i < vals.length; i++) {
    out += flat(vals[i]) + strings[i + 1];
  }
  return raw(out);
}
function flat(v) {
  if (v == null || v === false) return '';
  if (v instanceof Raw) return v.s;
  if (Array.isArray(v)) return v.map(flat).join('');
  return esc(v);
}

export const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const round = (v, dp = 2) => { const f = 10 ** dp; return Math.round(v * f) / f; };

/* ---------- units ---------- */
export const KG_PER_LB = 0.45359237;
export const toDisplay = (kg, unit) => unit === 'lb' ? kg / KG_PER_LB : kg;
export const fromDisplay = (v, unit) => unit === 'lb' ? v * KG_PER_LB : v;

/** 5080.75 -> "5,080.75"; 27.5 -> "27.5"; 25 -> "25". */
export function fmtNum(n, maxDec = 2) {
  if (n == null || Number.isNaN(n)) return '--';
  return Number(n).toLocaleString('en-US', { maximumFractionDigits: maxDec, minimumFractionDigits: 0 });
}
/** Weight in the user's unit, rounded for display (lb conversions keep one decimal). */
export const fmtW = (kg, unit) => fmtNum(round(toDisplay(kg, unit), unit === 'lb' ? 1 : 2));
export const fmtReps = r => fmtNum(r, 1);

/* ---------- time ---------- */
const DAY = 86400000;
export const startOfDay = ts => { const d = new Date(ts); d.setHours(0, 0, 0, 0); return d.getTime(); };
export const dayKey = ts => { const d = new Date(ts); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
export const dayKeyToTs = k => { const [y, m, d] = k.split('-').map(Number); return new Date(y, m - 1, d).getTime(); };
/** Calendar-day difference, DST safe. */
export const daysBetween = (a, b) => Math.round((startOfDay(b) - startOfDay(a)) / DAY);
/** Sunday-based week start, matching the S M T W T F S strip. */
export const startOfWeek = ts => { const d = new Date(startOfDay(ts)); d.setDate(d.getDate() - d.getDay()); return d.getTime(); };
export const addDays = (ts, n) => { const d = new Date(ts); d.setDate(d.getDate() + n); return d.getTime(); };

const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const WD3 = WEEKDAYS.map(w => w.slice(0, 3));
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const pad = n => String(n).padStart(2, '0');

/** "28/09/26" */
export const fmtShortDate = ts => { const d = new Date(ts); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${String(d.getFullYear()).slice(2)}`; };
/** "Sat, 19 Sep 2026" */
export const fmtLongDate = ts => { const d = new Date(ts); return `${WD3[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`; };
/** "7:04 AM" */
export function fmtTime(ts) {
  const d = new Date(ts); let h = d.getHours(); const ap = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12; return `${h}:${pad(d.getMinutes())} ${ap}`;
}
export const monthName = m => MONTHS[m];
export const weekdayLetter = i => 'SMTWTFS'[i];

/** Relative label used in exercise lists: "12 secs ago", "3h ago", "Yesterday", "2d ago", "1w ago", "11mo ago", "17/09/25". */
export function relTime(ts, now = Date.now()) {
  if (!ts) return '';
  const diff = Math.max(0, now - ts);
  const days = daysBetween(ts, now);
  if (days === 0) {
    const s = Math.floor(diff / 1000);
    if (s < 60) return `${Math.max(1, s)} sec${s <= 1 ? '' : 's'} ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m} min${m === 1 ? '' : 's'} ago`;
    return `${Math.floor(m / 60)}h ago`;
  }
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  if (days < 365) return `${Math.max(1, Math.floor(days / 30.44))}mo ago`;
  return fmtShortDate(ts);
}

/** Day group header in an exercise's history: "Today", "Yesterday", "Thursday", "Sat, 19 Sep 2026". */
export function dayHeader(ts, now = Date.now()) {
  const days = daysBetween(ts, now);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days > 1 && days < 7) return WEEKDAYS[new Date(ts).getDay()];
  return fmtLongDate(ts);
}

/** 322 -> "5m 22s", 3900 -> "1h 5m" */
export function fmtDuration(sec) {
  if (sec == null || !Number.isFinite(sec)) return '--';
  sec = Math.round(sec);
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${pad(s)}s`;
  return sec ? `${s}s` : '0m';
}
/** 89 -> "1:29", 3725 -> "1:02:05" */
export function fmtClock(sec) {
  sec = Math.max(0, Math.round(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  return h ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

/* ---------- search ---------- */
export const norm = s => String(s).toLowerCase().normalize('NFKD').replace(/[^\w\s]/g, ' ').replace(/\s+/g, ' ').trim();
/** Every query word must prefix-match some word of the name ("inc db" matches "Incline Dumbbell Press"). */
export function matches(name, query) {
  const q = norm(query); if (!q) return true;
  const words = norm(name).split(' ');
  const joined = words.join(' ');
  return q.split(' ').every(t => words.some(w => w.startsWith(t)) || joined.includes(t));
}

/* ---------- CSV ---------- */
export function parseCSV(text) {
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ',' || c === ';' && !text.slice(0, 200).includes(',')) { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += c;
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(c => c.trim() !== ''));
}
export const csvCell = v => { const s = String(v ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
