/* OpenLode Design Assistant -- browser front end.
 *
 * The browser owns the network being edited; every change is posted to
 * /api/analyse and the whole design re-solves, which is what gives Design
 * Mode its instant what-if behaviour.  Nothing is written to disk until Save.
 */
'use strict';

const S = {
  workspace: null, specName: '', netName: '', network: null,
  analysis: null, specs: null, sel: null, dirty: false, tab: 'design',
  specTab: 'taps', view: {x: 60, y: 60, k: 1}, pending: null,
  // design grid
  legs: [], legId: 'TRUNK', cur: {row: 0, col: 'ft'}, editing: null,
  undo: [], redo: [], gridActive: true,
};

/** Columns the designer types into, in the order the period key walks them. */
const ENTRY_COLS = ['ft', 'units', 'tap'];
const UNDO_LIMIT = 80;

const $ = (id) => document.getElementById(id);
const el = (tag, attrs, kids) => {
  const node = document.createElementNS(
    tag === 'svg' || SVG_TAGS.has(tag) ? 'http://www.w3.org/2000/svg'
                                       : 'http://www.w3.org/1999/xhtml', tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined) continue;
    if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids || []) if (kid) node.appendChild(kid);
  return node;
};
const SVG_TAGS = new Set(['g', 'line', 'rect', 'circle', 'path', 'text',
                          'polygon', 'polyline', 'title']);
const fmt = (v, d = 1) =>
  (v === null || v === undefined || Number.isNaN(v)) ? '' : Number(v).toFixed(d);
/* Columns that are counts or whole units, never levels. */
const INT_COLS = new Set(['Length', 'Units', 'Cascade', 'Count', 'Ports',
                          'Quantity', 'Value', 'Devices', 'Spare', 'Shortfall',
                          'Rating A', 'Max A', 'Volts', 'Watts', 'Load %']);
const cellText = (column, value) => {
  if (typeof value !== 'number') return value ?? '';
  if (INT_COLS.has(column)) return Number.isInteger(value) ? String(value)
                                                           : value.toFixed(1);
  return fmt(value);
};

function toast(message, kind) {
  const node = $('toast');
  node.textContent = message;
  node.className = kind || '';
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { node.textContent = ''; }, 3500);
}

async function api(path, options) {
  const response = await fetch('/api/' + path, options);
  const type = response.headers.get('content-type') || '';
  if (!type.includes('json')) {
    if (!response.ok) throw new Error(await response.text());
    return response.text();
  }
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || 'request failed');
  return data;
}
const post = (path, body) => api(path, {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(body),
});

/* ------------------------------------------------------------------ boot */
async function boot() {
  S.workspace = await api('workspace');
  fill($('spec-set'), S.workspace.spec_sets);
  fill($('network-name'), S.workspace.networks);
  S.specName = S.workspace.spec_sets[0] || '';
  S.netName = S.workspace.networks[0] || '';
  $('spec-set').value = S.specName;
  $('network-name').value = S.netName;
  await loadSpecs();
  if (S.netName) await loadNetwork(S.netName);
  else { S.network = blankNetwork(); await analyse(); }
  wire();
}

function fill(select, values) {
  select.textContent = '';
  for (const value of values) select.appendChild(el('option', {value, text: value}));
}

function blankNetwork() {
  return {kind: 'network', name: 'untitled', description: '', spec_set: S.specName,
          locations: [{id: 'L1', label: 'ND1', kind: 'source',
                       device: firstOf('actives', 'node'), units: 0, x: 0, y: 0}],
          spans: []};
}

function firstOf(kind, category) {
  const rows = (S.specs && S.specs.files[kind] && S.specs.files[kind].rows) || [];
  const hit = category ? rows.find((r) => r.category === category) : rows[0];
  return hit ? hit.id : '';
}

async function loadSpecs() {
  S.specs = await api('specs/' + encodeURIComponent(S.specName));
}

async function loadNetwork(name) {
  const data = await api('network/' + encodeURIComponent(name));
  S.network = data.network;
  S.sel = null;
  S.dirty = false;
  await analyse(true);
}

/* --------------------------------------------------------------- analysis */
function scheduleAnalyse() {
  S.dirty = true;
  clearTimeout(S.pending);
  S.pending = setTimeout(() => analyse(), 120);
}

async function analyse(fit) {
  try {
    const data = await post('analyse', {network: S.network, spec: S.specName});
    S.analysis = data.analysis;
    S.stats = data.stats;
    S.problems = data.problems;
    if (data.legs) adoptLegs(data.legs);
    render(fit);
  } catch (err) {
    toast(err.message, 'error');
  }
}

/* ------------------------------------------------------------------ legs */
function adoptLegs(legs) {
  S.legs = legs;
  if (!legs.some((l) => l.id === S.legId)) {
    // the leg we were on was merged away or renamed: fall back to the one
    // holding the selection, else the trunk
    const holding = S.sel && legs.find((l) => l.locations.includes(S.sel));
    S.legId = holding ? holding.id : (legs[0] ? legs[0].id : 'TRUNK');
    S.cur.row = 0;
  }
  const leg = currentLeg();
  if (leg) S.cur.row = Math.min(S.cur.row, Math.max(0, leg.locations.length - 1));
}

const currentLeg = () =>
  S.legs.find((l) => l.id === S.legId) || S.legs[0] || null;
const legById = (id) => S.legs.find((l) => l.id === id) || null;
const legChildren = (id) => S.legs.filter((l) => l.parent_leg === id);

/** Legs that begin at a given location -- what the > key offers. */
const legsFrom = (locId) => S.legs.filter((l) => l.origin === locId);

function legPath(id) {
  const chain = [];
  let cursor = legById(id);
  let guard = 0;
  while (cursor && guard++ < 64) {
    chain.unshift(cursor);
    cursor = cursor.parent_leg ? legById(cursor.parent_leg) : null;
  }
  return chain;
}

function goLeg(id, row) {
  S.legId = id;
  S.cur = {row: row || 0, col: S.cur.col || 'ft'};
  const leg = currentLeg();
  if (leg && leg.locations.length) S.sel = leg.locations[S.cur.row] || null;
  render();
  focusGrid();
}

/* ------------------------------------------------------------------ undo */
function snapshot() {
  S.undo.push(JSON.stringify(S.network));
  if (S.undo.length > UNDO_LIMIT) S.undo.shift();
  S.redo.length = 0;
}

function undo() {
  if (!S.undo.length) { toast('nothing to undo'); return; }
  S.redo.push(JSON.stringify(S.network));
  S.network = JSON.parse(S.undo.pop());
  S.dirty = true;
  analyse();
}

function redo() {
  if (!S.redo.length) { toast('nothing to redo'); return; }
  S.undo.push(JSON.stringify(S.network));
  S.network = JSON.parse(S.redo.pop());
  S.dirty = true;
  analyse();
}

/** Run a structural edit in the Python model, which owns those rules. */
async function edit(op, args, keepRow) {
  snapshot();
  try {
    const data = await post('edit', {network: S.network, spec: S.specName,
                                     op, args});
    S.network = data.network;
    S.analysis = data.analysis;
    S.stats = data.stats;
    S.problems = data.problems;
    S.dirty = true;
    if (data.legs) adoptLegs(data.legs);
    if (keepRow !== undefined) S.cur.row = keepRow;
    render();
    focusGrid();
    return true;
  } catch (err) {
    S.undo.pop();
    toast(err.message, 'error');
    return false;
  }
}

/* ------------------------------------------------------------- topology */
const locs = () => S.network.locations;
const byId = (id) => locs().find((l) => l.id === id);
const feedSpan = (id) => S.network.spans.find((s) => s.child === id);
const childSpans = (id) => S.network.spans.filter((s) => s.parent === id);
const order = () => (S.analysis ? S.analysis.solution.order : locs().map((l) => l.id));

function nextId(prefix) {
  let n = 1;
  const used = new Set([...locs().map((l) => l.id), ...S.network.spans.map((s) => s.id)]);
  while (used.has(prefix + n)) n += 1;
  return prefix + n;
}

function outPortsOf(loc) {
  const files = S.specs.files;
  if (loc.kind === 'source' || loc.kind === 'active') {
    const act = (files.actives.rows || []).find((r) => r.id === loc.device);
    return act && act.outputs && act.outputs.length
      ? act.outputs.map((o) => o.name) : ['OUT'];
  }
  if (loc.kind === 'coupler') {
    const cpl = (files.couplers.rows || []).find((r) => r.id === loc.device);
    const legs = cpl ? Number(cpl.tap_legs || 0) : 0;
    return ['THRU', ...Array.from({length: legs}, (_, i) => 'TAP' + (i + 1))];
  }
  return ['THRU'];
}

function freePort(loc) {
  const used = new Set(childSpans(loc.id).map((s) => s.port));
  return outPortsOf(loc).find((p) => !used.has(p)) || outPortsOf(loc)[0];
}

/* ------------------------------------------------------------- editing */
function addAfter(kind) {
  const parent = S.sel ? byId(S.sel) : locs()[locs().length - 1];
  if (!parent) return;
  const params = S.specs.files.parameters;
  const device = kind === 'tap' ? defaultTap()
    : kind === 'coupler' ? (params.default_coupler || firstOf('couplers'))
    : kind === 'active' ? (params.default_active || firstOf('actives'))
    : '';
  const id = nextId('L');
  const angle = childSpans(parent.id).length;
  const loc = {
    id, label: id.replace('L', ''), kind, device,
    units: kind === 'tap' ? 2 : 0, tsg: 0, tap_ports: 0, locked: false,
    pad: null, eq: null, rtn_pad: null, rtn_eq: null, power_block: false,
    note: '', x: (parent.x || 0) + 250, y: (parent.y || 0) + angle * 220,
  };
  locs().push(loc);
  S.network.spans.push({
    id: nextId('S'), parent: parent.id, child: id,
    cable: params.default_cable || firstOf('cables'), length: 250,
    port: freePort(parent), extra_loss: 0, connectors: 2, label: '',
  });
  select(id);
  scheduleAnalyse();
}

function insertActiveBefore() {
  if (!S.sel) return;
  const span = feedSpan(S.sel);
  if (!span) { toast('the source has no feed to insert into'); return; }
  const params = S.specs.files.parameters;
  const child = byId(S.sel);
  const parent = byId(span.parent);
  const id = nextId('L');
  const device = params.default_active || firstOf('actives', 'line_extender');
  const loc = {
    id, label: 'LE' + (locs().filter((l) => l.kind === 'active').length + 1),
    kind: 'active', device, units: 0, tsg: 0, tap_ports: 0, locked: false,
    pad: null, eq: null, rtn_pad: null, rtn_eq: null, power_block: false,
    note: '', x: ((child.x || 0) + (parent.x || 0)) / 2,
    y: ((child.y || 0) + (parent.y || 0)) / 2,
  };
  locs().push(loc);
  S.network.spans.push({
    id: nextId('S'), parent: span.parent, child: id, cable: span.cable,
    length: 0, port: span.port, extra_loss: 0, connectors: 2, label: 'jumper',
  });
  span.parent = id;
  span.port = outPortsOf(loc)[0];
  select(id);
  scheduleAnalyse();
}

function removeSelected() {
  if (!S.sel) return;
  const target = S.sel;
  if (!feedSpan(target)) { toast('cannot delete the source'); return; }
  const doomed = new Set();
  const walk = (id) => {
    doomed.add(id);
    childSpans(id).forEach((s) => walk(s.child));
  };
  walk(target);
  S.network.locations = locs().filter((l) => !doomed.has(l.id));
  S.network.spans = S.network.spans.filter(
    (s) => !doomed.has(s.child) && !doomed.has(s.parent));
  S.sel = null;
  scheduleAnalyse();
}

function defaultTap() {
  const rows = (S.specs.files.taps.rows || []).filter((r) => !r.self_terminating);
  const mid = rows.filter((r) => r.ports === 4);
  const pick = (mid.length ? mid : rows).sort((a, b) => a.value - b.value);
  return pick.length ? pick[Math.floor(pick.length / 2)].id : '';
}

/** The + / - keys: "change it to the next higher value tap and recalculate". */
function stepDevice(direction) {
  const loc = S.sel && byId(S.sel);
  if (!loc) return;
  const files = S.specs.files;
  let list = [];
  if (loc.kind === 'tap') {
    const current = (files.taps.rows || []).find((r) => r.id === loc.device);
    if (!current) return;
    list = (files.taps.rows || [])
      .filter((r) => r.ports === current.ports &&
                     r.self_terminating === current.self_terminating &&
                     r.tsg === current.tsg)
      .sort((a, b) => a.value - b.value);
  } else if (loc.kind === 'coupler') {
    list = (files.couplers.rows || []).slice();
  } else if (loc.kind === 'active' || loc.kind === 'source') {
    list = (files.actives.rows || []).slice();
  } else return;
  const index = list.findIndex((r) => r.id === loc.device);
  const next = list[Math.min(list.length - 1, Math.max(0, index + direction))];
  if (next && next.id !== loc.device) {
    snapshot();
    loc.device = next.id;
    S.dirty = true;
    scheduleAnalyse();
  }
}

function select(id) {
  S.sel = id;
  const leg = S.legs.find((l) => l.locations.includes(id));
  if (leg && (leg.id !== S.legId || S.tab === 'design')) {
    S.legId = leg.id;
    S.cur = {row: Math.max(0, leg.locations.indexOf(id)), col: S.cur.col || 'ft'};
    if (S.tab === 'design') { renderProps(); renderCanvas(); renderTable();
                              renderLegs(); return; }
  }
  renderProps();
  renderCanvas();
  highlightRow();
}

function moveSelection(delta) {
  const seq = order();
  const index = seq.indexOf(S.sel);
  const next = seq[Math.min(seq.length - 1, Math.max(0, index + delta))];
  if (next) select(next);
}

/* --------------------------------------------------------------- canvas */
function needsLayout() {
  const list = locs();
  if (list.length < 2) return false;
  const distinct = new Set(list.map((l) => `${l.x || 0},${l.y || 0}`));
  return distinct.size < list.length / 2;
}

function autoLayout() {
  const root = (locs().find((l) => l.kind === 'source') || locs()[0]);
  if (!root) return;
  let lane = 0;
  const place = (id, x) => {
    const loc = byId(id);
    loc.x = x;
    const kids = childSpans(id);
    if (!kids.length) { loc.y = lane * 200; lane += 1; return; }
    const ys = [];
    kids.forEach((span, index) => {
      if (index > 0) lane += 0;
      place(span.child, x + Math.max(120, Number(span.length) || 200));
      ys.push(byId(span.child).y);
    });
    loc.y = ys.reduce((a, b) => a + b, 0) / ys.length;
  };
  place(root.id, 0);
}

function bounds() {
  const xs = locs().map((l) => l.x || 0);
  const ys = locs().map((l) => l.y || 0);
  return {
    x0: Math.min(...xs), x1: Math.max(...xs),
    y0: Math.min(...ys), y1: Math.max(...ys),
  };
}

function fitView() {
  const svg = $('plant');
  const box = svg.getBoundingClientRect();
  const b = bounds();
  const w = Math.max(1, b.x1 - b.x0), h = Math.max(1, b.y1 - b.y0);
  const k = Math.min((box.width - 120) / w, (box.height - 90) / h, 2.5);
  S.view.k = Number.isFinite(k) && k > 0 ? k : 0.2;
  S.view.x = 60 - b.x0 * S.view.k;
  S.view.y = box.height / 2 - ((b.y0 + b.y1) / 2) * S.view.k;
  renderCanvas();
}

const statusOf = (id) => {
  const r = S.analysis && S.analysis.solution.results[id];
  return r ? r.status : 'ok';
};
const COLOR = {ok: 'var(--ok)', warn: 'var(--warn)', error: 'var(--error)'};

function renderCanvas() {
  const svg = $('plant');
  svg.textContent = '';
  if (!S.network) return;
  if (needsLayout()) autoLayout();
  const root = el('g', {transform:
    `translate(${S.view.x},${S.view.y}) scale(${S.view.k})`});
  const scale = 1 / S.view.k;

  for (const span of S.network.spans) {
    const a = byId(span.parent), b = byId(span.child);
    if (!a || !b) continue;
    const trunk = childSpans(b.id).length > 0 || b.kind === 'active';
    root.appendChild(el('line', {
      x1: a.x || 0, y1: a.y || 0, x2: b.x || 0, y2: b.y || 0,
      class: 'span-line' + (trunk ? ' trunk' : ''),
      'stroke-width': (trunk ? 3.2 : 2) * scale,
    }));
    if (S.view.k > 0.10 && Number(span.length)) {
      root.appendChild(el('text', {
        x: ((a.x || 0) + (b.x || 0)) / 2, y: ((a.y || 0) + (b.y || 0)) / 2 - 6 * scale,
        class: 'span-label', 'text-anchor': 'middle',
        'font-size': 9 * scale, text: `${Math.round(span.length)}`,
      }));
    }
  }

  for (const loc of locs()) {
    const status = statusOf(loc.id);
    const color = COLOR[status] || COLOR.ok;
    const x = loc.x || 0, y = loc.y || 0;
    const group = el('g', {class: 'pick', transform: `translate(${x},${y})`,
                          onclick: () => select(loc.id)});
    const stroke = loc.id === S.sel ? 'var(--accent)' : color;
    const width = (loc.id === S.sel ? 2.6 : 1.4) * scale;
    const s = scale;
    if (loc.kind === 'source') {
      group.appendChild(el('circle', {r: 11 * s, fill: '#1b2740', stroke,
                                      'stroke-width': width}));
      group.appendChild(el('text', {y: 3.5 * s, class: 'node-label',
        'text-anchor': 'middle', 'font-size': 10 * s, text: 'ND'}));
    } else if (loc.kind === 'active') {
      group.appendChild(el('rect', {x: -11 * s, y: -8 * s, width: 22 * s,
        height: 16 * s, rx: 3 * s, fill: '#2a1f3a', stroke, 'stroke-width': width}));
      group.appendChild(el('text', {y: 3.5 * s, class: 'node-label',
        'text-anchor': 'middle', 'font-size': 9 * s, fill: 'var(--active)',
        text: 'A'}));
    } else if (loc.kind === 'tap') {
      group.appendChild(el('rect', {x: -9 * s, y: -7 * s, width: 18 * s,
        height: 14 * s, fill: '#16273c', stroke, 'stroke-width': width}));
      const tap = (S.specs.files.taps.rows || []).find((r) => r.id === loc.device);
      const brackets = {2: ['[', ']'], 4: ['(', ')'], 8: ['{', '}']};
      const br = tap ? (brackets[tap.ports] || ['[', ']']) : ['', ''];
      group.appendChild(el('text', {y: 3 * s, class: 'node-label',
        'text-anchor': 'middle', 'font-size': 8.5 * s,
        text: tap ? `${br[0]}${tap.value}${br[1]}` : '?'}));
    } else if (loc.kind === 'coupler') {
      group.appendChild(el('polygon', {
        points: `0,${-9 * s} ${9 * s},0 0,${9 * s} ${-9 * s},0`,
        fill: '#15302e', stroke, 'stroke-width': width}));
    } else {
      group.appendChild(el('circle', {r: 4 * s, fill: '#22304a', stroke,
                                      'stroke-width': width}));
    }
    if (loc.power_supply) {
      group.appendChild(el('text', {x: 13 * s, y: -8 * s, 'font-size': 11 * s,
        class: 'node-label', fill: 'var(--warn)', text: '⚡'}));
    }
    if (loc.note) {
      group.appendChild(el('text', {x: -16 * s, y: -9 * s, 'font-size': 10 * s,
        class: 'node-label', fill: 'var(--warn)', text: '✎'}));
    }
    group.appendChild(el('text', {y: -12 * s, class: 'node-label',
      'text-anchor': 'middle', 'font-size': 10 * s, text: loc.label || loc.id}));
    const res = S.analysis && S.analysis.solution.results[loc.id];
    if (res && S.view.k > 0.16) {
      const column = S.analysis.solution.forward_columns[0];
      const value = loc.kind === 'tap' ? res.fwd_tap[column] : res.fwd_in[column];
      if (value !== undefined) {
        group.appendChild(el('text', {y: 20 * s, class: 'node-sub',
          'text-anchor': 'middle', 'font-size': 9 * s, fill: color,
          text: fmt(value)}));
      }
    }
    group.appendChild(el('title', {text:
      `${loc.label || loc.id} -- ${loc.kind}${loc.device ? ' ' + loc.device : ''}`}));
    root.appendChild(group);
  }
  svg.appendChild(root);
}

/* ------------------------------------------------------------ properties */
function field(label, control) {
  return el('div', {class: 'prop'}, [el('label', {text: label}), control]);
}

function input(value, onchange, type, step) {
  const node = el('input', {type: type || 'text', value: value ?? ''});
  if (step) node.setAttribute('step', step);
  node.addEventListener('change', () => onchange(node.value));
  return node;
}

function picker(options, value, onchange, labeller) {
  const node = el('select', {});
  for (const option of options) {
    const id = typeof option === 'string' ? option : option.id;
    node.appendChild(el('option', {
      value: id, text: labeller ? labeller(option) : id,
      selected: id === value ? 'selected' : null,
    }));
  }
  node.value = value ?? '';
  node.addEventListener('change', () => onchange(node.value));
  return node;
}

function renderProps() {
  const host = $('props');
  host.textContent = '';
  const loc = S.sel && byId(S.sel);
  $('sel-id').textContent = loc ? loc.id : '';
  if (!loc) {
    host.appendChild(el('div', {class: 'empty',
      text: 'Select a location on the plant, or press T to add a tap.'}));
    return;
  }
  const files = S.specs.files;
  const set = (key) => (value) => {
    loc[key] = value;
    scheduleAnalyse();
    renderCanvas();
  };
  const num = (key) => (value) => {
    loc[key] = value === '' ? 0 : Number(value);
    scheduleAnalyse();
  };

  host.appendChild(field('Label', input(loc.label, (v) => {
    loc.label = v; scheduleAnalyse(); renderCanvas();
  })));
  host.appendChild(field('Type', picker(
    ['source', 'active', 'tap', 'coupler', 'point', 'end'], loc.kind, (v) => {
      loc.kind = v;
      loc.device = v === 'tap' ? defaultTap()
        : v === 'coupler' ? firstOf('couplers')
        : v === 'active' || v === 'source' ? firstOf('actives') : '';
      renderProps(); scheduleAnalyse();
    })));

  if (loc.kind === 'tap') {
    const rows = (files.taps.rows || []).slice()
      .sort((a, b) => a.ports - b.ports || a.value - b.value);
    host.appendChild(field('Tap', picker(rows, loc.device, set('device'),
      (r) => `${r.id}  ${r.ports}p ${r.value}dB${r.self_terminating ? ' ST' : ''}`)));
    host.appendChild(field('Units', input(loc.units, num('units'), 'number')));
    host.appendChild(field('TSG', input(loc.tsg, num('tsg'), 'number')));
    host.appendChild(field('Ports', input(loc.tap_ports, num('tap_ports'), 'number')));
  } else if (loc.kind === 'coupler') {
    host.appendChild(field('Coupler', picker(files.couplers.rows || [],
      loc.device, set('device'), (r) => `${r.id}  ${r.description}`)));
  } else if (loc.kind === 'active' || loc.kind === 'source') {
    host.appendChild(field('Active', picker(files.actives.rows || [],
      loc.device, set('device'), (r) => `${r.id}  ${r.description}`)));
    const nullable = (key) => (value) => {
      loc[key] = value === '' ? null : Number(value);
      scheduleAnalyse();
    };
    host.appendChild(field('Pad', input(loc.pad, nullable('pad'), 'number', '0.5')));
    host.appendChild(field('EQ', input(loc.eq, nullable('eq'), 'number', '1')));
    host.appendChild(field('Rtn pad', input(loc.rtn_pad, nullable('rtn_pad'),
                                            'number', '0.5')));
  }

  const span = feedSpan(loc.id);
  if (span) {
    host.appendChild(el('div', {class: 'prop-head', text: 'Feed span'}));
    host.appendChild(field('Cable', picker(files.cables.rows || [], span.cable,
      (v) => { span.cable = v; scheduleAnalyse(); },
      (r) => `${r.id}  ${r.description}`)));
    host.appendChild(field('Length', input(span.length, (v) => {
      span.length = Number(v) || 0; scheduleAnalyse(); renderCanvas();
    }, 'number')));
    host.appendChild(field('Extra loss', input(span.extra_loss, (v) => {
      span.extra_loss = Number(v) || 0; scheduleAnalyse();
    }, 'number', '0.1')));
    const parent = byId(span.parent);
    if (parent) {
      host.appendChild(field('From port', picker(outPortsOf(parent), span.port,
        (v) => { span.port = v; scheduleAnalyse(); })));
    }
  }

  host.appendChild(el('div', {class: 'prop-head', text: 'Powering'}));
  const hasPs = !!loc.power_supply;
  const toggle = el('input', {type: 'checkbox'});
  toggle.checked = hasPs;
  toggle.addEventListener('change', () => {
    loc.power_supply = toggle.checked
      ? {id: 'PS' + (locs().filter((l) => l.power_supply).length + 1),
         volts: 90, max_amps: 15, feeds: [], description: '', price: 0}
      : null;
    renderProps(); scheduleAnalyse(); renderCanvas();
  });
  host.appendChild(field('Supply', toggle));
  if (loc.power_supply) {
    host.appendChild(field('Volts', input(loc.power_supply.volts, (v) => {
      loc.power_supply.volts = Number(v) || 0; scheduleAnalyse();
    }, 'number')));
    host.appendChild(field('Max A', input(loc.power_supply.max_amps, (v) => {
      loc.power_supply.max_amps = Number(v) || 0; scheduleAnalyse();
    }, 'number', '0.5')));
  }

  const note = el('textarea', {});
  note.value = loc.note || '';
  note.addEventListener('change', () => {
    loc.note = note.value; scheduleAnalyse(); renderCanvas();
  });
  host.appendChild(el('div', {class: 'prop-head', text: 'Sticky note'}));
  host.appendChild(note);

  const res = S.analysis && S.analysis.solution.results[loc.id];
  if (res) {
    host.appendChild(el('div', {class: 'prop-head', text: 'Levels (dBmV)'}));
    const box = el('div', {class: 'levels'}, []);
    const cols = S.analysis.solution.forward_columns;
    const rtn = S.analysis.solution.return_columns;
    const line = (k, v) => box.appendChild(el('div', {}, [
      el('span', {class: 'k', text: k}), el('span', {text: v})]));
    for (const c of cols) if (res.fwd_in[c] !== undefined)
      line('in ' + label(c), fmt(res.fwd_in[c]));
    for (const c of cols) if (res.fwd_tap[c] !== undefined)
      line('tap ' + label(c), fmt(res.fwd_tap[c]));
    for (const c of rtn) if (res.rtn_tap[c] !== undefined)
      line('rtn ' + label(c), fmt(res.rtn_tap[c]));
    if (res.pad !== null && res.pad !== undefined) line('pad', fmt(res.pad, 1));
    if (res.eq !== null && res.eq !== undefined) line('eq', fmt(res.eq, 1));
    if (res.cascade) line('cascade', res.cascade);
    host.appendChild(box);
    for (const flag of res.flags || []) {
      host.appendChild(el('div', {class: 'warnlist ' + flag.severity,
                                  text: flag.message}));
    }
  }

  host.appendChild(el('div', {class: 'prop-head', text: 'Edit'}));
  const bar = el('div', {class: 'tools'}, [
    el('button', {text: 'Tap', onclick: () => addAfter('tap')}),
    el('button', {text: 'Coupler', onclick: () => addAfter('coupler')}),
    el('button', {text: 'Amp', onclick: () => insertActiveBefore()}),
    el('button', {text: 'Delete', onclick: () => removeSelected()}),
  ]);
  host.appendChild(bar);
}

function label(column) {
  const freqs = S.specs.files.parameters.frequencies || [];
  const hit = freqs.find((f) => f.id === column);
  return hit ? (hit.label || String(hit.mhz)) : column;
}

/* ------------------------------------------------------------- tables */
const TABS = [
  ['design', 'Design'], ['actives', 'Actives'], ['taps', 'Tap Distribution'],
  ['performance', 'Performance'], ['power', 'Powering'], ['bom', 'BOM'],
  ['flags', 'Flags'], ['specs', 'Spec Files'],
];

function renderTabs() {
  const nav = $('tabs');
  nav.textContent = '';
  for (const [key, name] of TABS) {
    nav.appendChild(el('button', {
      text: name, class: key === S.tab ? 'on' : '',
      onclick: () => {
        S.tab = key;
        S.gridActive = key === 'design';
        renderTabs();
        renderTable();
        if (S.gridActive) setTimeout(focusGrid, 0);
      },
    }));
  }
}

function table(columns, rows, options) {
  const opts = options || {};
  S.rowIndex = new Map();
  const head = el('tr', {}, columns.map((c) =>
    el('th', {text: c, class: opts.text && opts.text.has(c) ? 'txt' : ''})));
  const body = el('tbody', {}, rows.map((row) => {
    const tr = el('tr', {class: row.__id === S.sel ? 'sel' : ''},
      columns.map((c) => {
        const value = row[c];
        const cls = [];
        if (opts.text && opts.text.has(c)) cls.push('txt');
        if (c === 'Status' && value) cls.push(value);
        if (opts.flagCells && opts.flagCells(row, c)) cls.push(opts.flagCells(row, c));
        return el('td', {class: cls.join(' '), text: cellText(c, value)});
      }));
    if (row.__id) {
      tr.addEventListener('click', () => select(row.__id));
      S.rowIndex.set(row.__id, tr);
    }
    return tr;
  }));
  return el('table', {}, [el('thead', {}, [head]), body]);
}

function renderTable() {
  const host = $('table');
  host.textContent = '';
  if (S.tab === 'specs') return renderSpecEditor(host);
  if (S.tab === 'design') return renderDesignPane(host);
  host.appendChild(el('div', {class: 'empty', text: 'loading...'}));
  post('report/' + S.tab + '?format=json',
       {network: S.network, spec: S.specName})
    .then((data) => {
      host.textContent = '';
      for (const report of data.reports) {
        const text = new Set(report.columns.filter((c) =>
          ['Loc', 'Type', 'Device', 'Cable', 'Message', 'Description', 'Item',
           'Category', 'Part', 'Unit', 'Supply', 'Location', 'Note', 'Tap',
           'Code', 'Severity', 'Status', 'Column'].includes(c)));
        const rows = report.rows.map((r) => Object.assign({}, r, {
          __id: idForLabel(r.Loc)}));
        host.appendChild(el('div', {class: 'grid-actions'}, [
          el('span', {text: report.title}),
          el('span', {class: 'spacer'}),
          ...report.summary.map((s) => el('span', {class: 'hint', text: s})),
          el('button', {class: 'mini', text: 'CSV', onclick: () =>
            download('report/' + S.tab + '?format=csv')}),
        ]));
        host.appendChild(table(report.columns, rows, {text}));
      }
    })
    .catch((err) => {
      host.textContent = '';
      host.appendChild(el('div', {class: 'empty error', text: err.message}));
    });
}

function idForLabel(label) {
  if (!label) return null;
  const hit = locs().find((l) => (l.label || l.id) === label);
  return hit ? hit.id : null;
}

/* =========================================================== design grid
 * The Design Assistant is a keyboard instrument: you work one leg at a
 * time, typing footage and house counts and tap values straight into a
 * grid, using the period key to step between fields and Enter to move on
 * to the next pole.  This is that grid.
 * ==================================================================== */

const gridRowIds = () => {
  const leg = currentLeg();
  return leg ? leg.locations : [];
};

function gridLoc(row) {
  const ids = gridRowIds();
  return ids[row] ? byId(ids[row]) : null;
}

function tapValueOf(loc) {
  if (!loc || loc.kind !== 'tap') return null;
  const tap = (S.specs.files.taps.rows || []).find((r) => r.id === loc.device);
  return tap ? tap.value : null;
}

function cellValue(loc, col) {
  if (!loc) return '';
  if (col === 'loc') return loc.label || loc.id;
  if (col === 'ft') {
    const span = feedSpan(loc.id);
    return span ? span.length : 0;
  }
  if (col === 'units') return loc.units || 0;
  if (col === 'tap') {
    if (loc.kind === 'tap') {
      const value = tapValueOf(loc);
      return value === null ? '?' : value;
    }
    return loc.device || '';
  }
  return '';
}

function renderDesignPane(host) {
  const leg = currentLeg();
  host.appendChild(crumbBar(leg));
  const wrap = el('div', {id: 'grid-wrap', tabindex: '0'}, []);
  if (!leg || !leg.locations.length) {
    wrap.appendChild(el('div', {class: 'gridhint',
      text: 'This leg is empty. Press Enter to add the first pole.'}));
  } else {
    wrap.appendChild(gridTable(leg));
  }
  wrap.addEventListener('mousedown', () => { S.gridActive = true; });
  host.appendChild(wrap);
  // a rebuild replaces every node, so re-seat the cursor and the focus
  applyCursor();
  if (S.gridActive) setTimeout(focusGrid, 0);
}

function crumbBar(leg) {
  const bar = el('div', {id: 'crumbs'}, []);
  const path = leg ? legPath(leg.id) : [];
  path.forEach((entry, index) => {
    const last = index === path.length - 1;
    const origin = entry.origin ? byId(entry.origin) : null;
    const name = entry.name || (origin
      ? `${origin.label || origin.id} [${entry.port}]` : 'TRUNK');
    bar.appendChild(el('span', {
      class: last ? 'here' : 'crumb', text: name,
      onclick: last ? null : () => goLeg(entry.id, 0),
    }));
    if (!last) bar.appendChild(el('span', {class: 'sep', text: '›'}));
  });
  if (leg) {
    const feet = leg.locations.reduce((total, id) => {
      const span = feedSpan(id);
      return total + (span ? Number(span.length) || 0 : 0);
    }, 0);
    const units = leg.locations.reduce(
      (total, id) => total + (byId(id).units || 0), 0);
    bar.appendChild(el('span', {class: 'meta',
      text: `— ${leg.locations.length} poles · ${Math.round(feet).toLocaleString()} ` +
            `${S.specs.files.parameters.distance_units} · ${units} units`}));
  }
  bar.appendChild(el('span', {class: 'spacer', style: 'flex:1'}));
  bar.appendChild(el('button', {class: 'mini', text: 'Up', title: 'back to the parent leg (<)',
                                onclick: ascend}));
  bar.appendChild(el('button', {class: 'mini', text: 'Into leg ›',
                                title: 'design a leg that starts here (>)',
                                onclick: descend}));
  bar.appendChild(el('button', {class: 'mini', text: 'Swap legs',
                                title: 'swap the legs on this device (S)',
                                onclick: swapLegs}));
  bar.appendChild(el('button', {class: 'mini', text: 'Name leg',
                                onclick: nameLeg}));
  return bar;
}

function gridTable(leg) {
  const solution = S.analysis.solution;
  const fwd = solution.forward_columns, rtn = solution.return_columns;
  const entry = [['loc', 'Loc'], ['ft', 'Ft'], ['units', 'Units'],
                 ['tap', 'Tap']];
  const readonly = ['Type', 'Cable',
    ...fwd.map((c) => 'In ' + label(c)),
    ...fwd.map((c) => 'Tap ' + label(c)),
    ...rtn.map((c) => 'Rtn ' + label(c)),
    'Pad', 'EQ', 'Status'];

  const head = el('tr', {}, [
    ...entry.map(([, name]) => el('th', {text: name, class: 'txt'})),
    ...readonly.map((name) => el('th', {
      text: name,
      class: ['Type', 'Cable', 'Status'].includes(name) ? 'txt' : '',
    })),
  ]);

  const body = el('tbody', {}, leg.locations.map((id, row) => {
    const loc = byId(id);
    const res = solution.results[id] || {fwd_in: {}, fwd_tap: {}, rtn_tap: {},
                                          flags: [], status: 'ok'};
    const branches = legsFrom(id).length > 0;
    const tr = el('tr', {
      class: (id === S.sel ? 'sel ' : '') + (branches ? 'branch' : ''),
    }, []);

    entry.forEach(([col]) => {
      const td = el('td', {
        class: 'cell' + (col === 'loc' ? ' txt' : ''),
        text: String(cellValue(loc, col)),
        'data-row': row, 'data-col': col,
        onmousedown: (event) => {
          event.preventDefault();
          if (S.editing) commitEdit().then(() => setCursor(row, col));
          else setCursor(row, col);
        },
      });
      tr.appendChild(td);
    });

    const flagFor = (column) => {
      for (const flag of res.flags || []) {
        if (!flag.column) continue;
        const name = label(flag.column);
        if (column === 'Tap ' + name || column === 'Rtn ' + name ||
            column === 'In ' + name) return flag.severity;
      }
      return '';
    };
    const cells = {
      Type: loc.kind, Cable: res.cable || '',
      Pad: res.pad ?? '', EQ: res.eq ?? '', Status: res.status,
    };
    fwd.forEach((c) => {
      cells['In ' + label(c)] = res.fwd_in[c];
      cells['Tap ' + label(c)] = res.fwd_tap[c];
    });
    rtn.forEach((c) => { cells['Rtn ' + label(c)] = res.rtn_tap[c]; });
    readonly.forEach((name) => {
      const classes = [];
      if (['Type', 'Cable', 'Status'].includes(name)) classes.push('txt');
      if (name === 'Status' && cells[name]) classes.push(cells[name]);
      const severity = flagFor(name);
      if (severity) classes.push(severity);
      tr.appendChild(el('td', {class: classes.join(' '),
                              text: cellText(name, cells[name])}));
    });
    tr.addEventListener('click', () => { S.sel = id; renderProps(); renderCanvas(); });
    return tr;
  }));
  return el('table', {}, [el('thead', {}, [head]), body]);
}

function focusGrid() {
  const wrap = $('grid-wrap');
  if (wrap && !S.editing) wrap.focus();
  S.gridActive = true;
}

const cellNode = (row, col) =>
  document.querySelector(`#grid-wrap td[data-row="${row}"][data-col="${col}"]`);

/** Paint the cursor by touching two cells, not by rebuilding the grid.
 *  Rebuilding mid-keystroke loses the focus and drops the next key. */
function applyCursor() {
  const previous = document.querySelector('#grid-wrap td.cell.cur');
  if (previous) previous.classList.remove('cur');
  const node = cellNode(S.cur.row, S.cur.col);
  if (node) {
    node.classList.add('cur');
    if (node.scrollIntoView) node.scrollIntoView({block: 'nearest',
                                                  inline: 'nearest'});
  }
  for (const tr of document.querySelectorAll('#grid-wrap tbody tr')) {
    tr.classList.remove('sel');
  }
  const row = document.querySelector(`#grid-wrap td[data-row="${S.cur.row}"]`);
  if (row && row.parentElement) row.parentElement.classList.add('sel');
}

function setCursor(row, col) {
  const ids = gridRowIds();
  S.cur = {row: Math.max(0, Math.min(ids.length - 1, row)), col: col || S.cur.col};
  S.sel = ids[S.cur.row] || S.sel;
  applyCursor();
  focusGrid();
  schedulePanels();
}

/** The properties panel and canvas can lag the cursor; the grid cannot. */
function schedulePanels() {
  clearTimeout(schedulePanels._t);
  schedulePanels._t = setTimeout(() => {
    renderProps();
    renderCanvas();
    renderLegs();
  }, 90);
}

/* ---------------------------------------------------------- grid editing */
function startEdit(seed) {
  const loc = gridLoc(S.cur.row);
  if (!loc || S.editing) return;
  const td = cellNode(S.cur.row, S.cur.col);
  if (!td) return;
  const current = seed === undefined ? String(cellValue(loc, S.cur.col)) : seed;
  const input = el('input', {value: current});
  if (S.cur.col === 'loc') input.style.textAlign = 'left';
  td.textContent = '';
  td.appendChild(input);
  S.editing = {node: input, td, row: S.cur.row, col: S.cur.col};
  input.focus();
  if (seed === undefined) input.select();
  else input.setSelectionRange(current.length, current.length);
}

function closeEditor() {
  if (!S.editing) return null;
  const {node, td, row, col} = S.editing;
  const value = node.value;
  S.editing = null;
  const loc = gridLoc(row);
  td.textContent = loc ? String(cellValue(loc, col)) : '';
  return {value, row, col, loc};
}

function cancelEdit() {
  closeEditor();
  focusGrid();
}

/** Write the typed value into the model. Returns false if it was rejected. */
async function commitEdit() {
  const closed = closeEditor();
  if (!closed) return true;
  const raw = String(closed.value).trim();
  const {loc, col, row} = closed;
  if (!loc) return true;

  if (col === 'loc') {
    if (raw !== (loc.label || '')) { snapshot(); loc.label = raw; markEdited(); }
    return true;
  }
  if (raw === '') return true;
  const value = Number(raw);
  if (Number.isNaN(value)) { toast(`"${raw}" is not a number`, 'error'); return false; }

  if (col === 'ft') {
    const span = feedSpan(loc.id);
    if (!span) { toast('the source has no feed footage'); return true; }
    if (Number(span.length) !== value) {
      snapshot();
      span.length = value;
      markEdited();
    }
    return true;
  }
  if (col === 'units') {
    if (loc.units !== value) { snapshot(); loc.units = value; markEdited(); }
    return true;
  }
  if (col === 'tap') {
    if (tapValueOf(loc) === value) return true;
    // sizing the tap from the house count is the Parameters file's job
    const ports = loc.tap_ports || portsForHomes(loc.units);
    return edit('set_tap_value', {location: loc.id, value, ports}, row);
  }
  return true;
}

function portsForHomes(homes) {
  const table = (S.specs.files.parameters.homes_to_ports || [])
    .slice().sort((a, b) => a.homes_max - b.homes_max);
  for (const row of table) if ((homes || 0) <= row.homes_max) return row.ports;
  return table.length ? table[table.length - 1].ports : 4;
}

function markEdited() {
  S.dirty = true;
  // repaint just this cell now; the full re-solve lands a moment later
  const loc = gridLoc(S.cur.row);
  const td = cellNode(S.cur.row, S.cur.col);
  if (loc && td && !S.editing) td.textContent = String(cellValue(loc, S.cur.col));
  scheduleAnalyse();
}

function moveCell(dCol, dRow) {
  const ids = gridRowIds();
  let col = S.cur.col;
  if (dCol) {
    const index = ENTRY_COLS.indexOf(col);
    const next = index < 0 ? 0 : index + dCol;
    if (next >= ENTRY_COLS.length) { col = ENTRY_COLS[0]; dRow = dRow || 1; }
    else if (next < 0) { col = ENTRY_COLS[ENTRY_COLS.length - 1]; dRow = dRow || -1; }
    else col = ENTRY_COLS[next];
  }
  setCursor(S.cur.row + (dRow || 0), col);
}

/** Enter at the foot of a leg adds the next pole -- entry as you walk. */
function appendPole() {
  const ids = gridRowIds();
  const tail = ids.length ? byId(ids[ids.length - 1]) : null;
  if (!tail) { toast('nothing to build from'); return; }
  if (childSpans(tail.id).length) {
    toast('this leg ends at a branch — press > to design a leg');
    return;
  }
  snapshot();
  const params = S.specs.files.parameters;
  const id = nextId('L');
  locs().push({
    id, label: String(ids.length + 1), kind: 'tap', device: defaultTap(),
    units: 0, tsg: 0, tap_ports: 0, locked: false, pad: null, eq: null,
    rtn_pad: null, rtn_eq: null, power_block: false, note: '',
    x: (tail.x || 0) + 200, y: tail.y || 0,
  });
  S.network.spans.push({
    id: nextId('S'), parent: tail.id, child: id,
    cable: feedCableOf(tail) || params.default_cable || firstOf('cables'),
    length: 0, port: freePort(tail), extra_loss: 0, connectors: 2,
    label: '', leg_name: '',
  });
  S.sel = id;
  S.cur = {row: ids.length, col: 'ft'};
  S.dirty = true;
  analyse().then(focusGrid);
}

function feedCableOf(loc) {
  const span = feedSpan(loc.id);
  return span ? span.cable : '';
}

/* ------------------------------------------------------- leg navigation */
function descend() {
  const loc = gridLoc(S.cur.row);
  if (!loc) return;
  const options = legsFrom(loc.id);
  if (!options.length) {
    toast(`${loc.label || loc.id} does not start a leg`);
    return;
  }
  if (options.length === 1) { goLeg(options[0].id, 0); return; }
  const choice = prompt(
    `Design which leg of ${loc.label || loc.id}?\n` +
    options.map((o, i) => `${i + 1}. ${o.port}${o.name ? '  ' + o.name : ''}`)
      .join('\n'), '1');
  const index = Number(choice) - 1;
  if (options[index]) goLeg(options[index].id, 0);
}

/** "The navigate command will load the trunk line to which the feeder leg
 *  is attached and place the cursor at the amplifier from which it
 *  originates." */
function ascend() {
  const leg = currentLeg();
  if (!leg || !leg.parent_leg) { toast('already on the trunk'); return; }
  const parent = legById(leg.parent_leg);
  if (!parent) return;
  const row = Math.max(0, parent.locations.indexOf(leg.origin));
  goLeg(parent.id, row);
}

async function swapLegs() {
  const loc = gridLoc(S.cur.row);
  if (!loc) return;
  const ports = childSpans(loc.id).map((s) => s.port);
  if (ports.length < 2) {
    toast(`${loc.label || loc.id} has only one leg to swap`);
    return;
  }
  let a = ports[0], b = ports[1];
  if (ports.length > 2) {
    const answer = prompt(
      `Swap which two legs of ${loc.label || loc.id}?\n` +
      `ports: ${ports.join(', ')}\nenter two, separated by a space`,
      `${ports[0]} ${ports[1]}`);
    if (!answer) return;
    const parts = answer.trim().split(/\s+/);
    if (parts.length !== 2 || !ports.includes(parts[0]) || !ports.includes(parts[1])) {
      toast('give two port names from the list', 'error');
      return;
    }
    [a, b] = parts;
  }
  if (await edit('swap_ports', {location: loc.id, port_a: a, port_b: b},
                 S.cur.row)) {
    toast(`swapped ${a} and ${b} on ${loc.label || loc.id}`);
  }
}

async function nameLeg() {
  const leg = currentLeg();
  if (!leg || !leg.first_span) { toast('the trunk cannot be renamed'); return; }
  const name = prompt('Name this leg:', leg.name || '');
  if (name === null) return;
  await edit('name_leg', {span: leg.first_span, name}, S.cur.row);
}

async function insertPole() {
  const loc = gridLoc(S.cur.row);
  if (!loc) return;
  if (!feedSpan(loc.id)) { toast('nothing to insert ahead of the source'); return; }
  await edit('insert_before', {
    location: loc.id, jumper: 0,
    fields: {kind: 'tap', device: defaultTap(), units: 0,
             label: String(S.cur.row + 1), x: loc.x - 120, y: loc.y},
  }, S.cur.row);
}

async function splicePole() {
  const loc = gridLoc(S.cur.row);
  if (!loc) return;
  const ok = await edit('splice_out', {location: loc.id},
                        Math.max(0, S.cur.row - 1));
  if (ok) toast(`removed ${loc.label || loc.id}, footage merged`);
}

/* -------------------------------------------------------- the key board */
function gridKey(event) {
  const key = event.key;
  const editing = !!S.editing;

  if (event.ctrlKey || event.metaKey) {
    if (key.toLowerCase() === 'z') {
      event.preventDefault();
      event.shiftKey ? redo() : undo();
    } else if (key.toLowerCase() === 'y') { event.preventDefault(); redo(); }
    else if (key.toLowerCase() === 's') { event.preventDefault(); save(); }
    return;
  }

  // the period key is the Design Assistant's field separator
  if (key === '.' && (editing || S.cur.col !== 'loc')) {
    event.preventDefault();
    commitEdit().then((ok) => { if (ok) moveCell(1, 0); });
    return;
  }
  if (key === 'Tab') {
    event.preventDefault();
    commitEdit().then((ok) => { if (ok) moveCell(event.shiftKey ? -1 : 1, 0); });
    return;
  }
  if (key === 'Enter') {
    event.preventDefault();
    commitEdit().then((ok) => {
      if (!ok) return;
      const last = S.cur.row >= gridRowIds().length - 1;
      if (last) appendPole();
      else { S.cur.col = ENTRY_COLS[0]; moveCell(0, 1); }
    });
    return;
  }
  if (key === 'Escape') { event.preventDefault(); cancelEdit(); return; }

  if (editing) return;   // everything below is for the resting cursor

  if (key === 'ArrowRight') { event.preventDefault(); moveCell(1, 0); return; }
  if (key === 'ArrowLeft') { event.preventDefault(); moveCell(-1, 0); return; }
  if (key === 'ArrowDown') { event.preventDefault(); moveCell(0, 1); return; }
  if (key === 'ArrowUp') { event.preventDefault(); moveCell(0, -1); return; }
  if (key === 'Insert') { event.preventDefault(); insertPole(); return; }
  if (key === 'Delete' || key === 'Backspace') {
    event.preventDefault(); splicePole(); return;
  }
  if (key === '+' || key === '=') { event.preventDefault(); stepDevice(1); return; }
  if (key === '-' || key === '_') { event.preventDefault(); stepDevice(-1); return; }
  if (key === '>' || (key === 'ArrowRight' && event.altKey)) {
    event.preventDefault(); descend(); return;
  }
  if (key === '<') { event.preventDefault(); ascend(); return; }
  if (key === 'F2') { event.preventDefault(); startEdit(); return; }

  // typing a value starts editing that cell
  if (/^[0-9]$/.test(key)) { event.preventDefault(); startEdit(key); return; }
  if (key.length === 1 && /[a-zA-Z]/.test(key)) {
    const lower = key.toLowerCase();
    if (lower === 's') { event.preventDefault(); swapLegs(); return; }
    if (lower === 'n') { event.preventDefault(); nameLeg(); return; }
    if (lower === 'd') { event.preventDefault(); runDesign('full'); return; }
    if (lower === 'u') { event.preventDefault(); ascend(); return; }
    if (S.cur.col === 'loc') { event.preventDefault(); startEdit(key); }
  }
}

function highlightRow() {
  if (!S.rowIndex) return;
  for (const [id, tr] of S.rowIndex) tr.classList.toggle('sel', id === S.sel);
  const current = S.rowIndex.get(S.sel);
  if (current && current.scrollIntoView) {
    current.scrollIntoView({block: 'nearest'});
  }
}

/* -------------------------------------------------------- spec editor */
const SPEC_KINDS = ['parameters', 'cables', 'taps', 'couplers', 'actives',
                    'performance', 'pricing'];

function renderSpecEditor(host) {
  const bar = el('div', {class: 'grid-actions'}, [
    ...SPEC_KINDS.map((kind) => el('button', {
      class: 'mini' + (kind === S.specTab ? ' primary' : ''), text: kind,
      onclick: () => { S.specTab = kind; renderTable(); },
    })),
    el('span', {class: 'spacer'}),
    el('button', {class: 'mini primary', text: 'Save spec file',
                  onclick: () => saveSpec(S.specTab)}),
  ]);
  host.appendChild(bar);
  for (const warning of S.specs.warnings || []) {
    host.appendChild(el('div', {class: 'warnlist', text: '⚠ ' + warning}));
  }
  const file = S.specs.files[S.specTab];
  if (!file) return;
  if (S.specTab === 'parameters') return host.appendChild(paramEditor(file));

  const rows = file.rows || [];
  if (!rows.length) {
    host.appendChild(el('div', {class: 'empty', text: 'no rows'}));
    return;
  }
  const columns = Object.keys(rows[0]);
  const head = el('tr', {}, columns.map((c) => el('th', {text: c, class: 'txt'})));
  const body = el('tbody', {}, rows.map((row) => el('tr', {}, columns.map((c) => {
    const value = row[c];
    const isObject = value !== null && typeof value === 'object';
    const cell = el('input', {
      class: 'cell' + (typeof value === 'number' ? '' : ' txt'),
      value: isObject ? JSON.stringify(value) : (value ?? ''),
    });
    cell.addEventListener('change', () => {
      let next = cell.value;
      if (isObject) { try { next = JSON.parse(next); } catch { toast('bad JSON', 'error'); return; } }
      else if (typeof value === 'number') next = Number(next);
      else if (typeof value === 'boolean') next = next === 'true' || next === '1';
      row[c] = next;
    });
    return el('td', {class: 'txt'}, [cell]);
  }))));
  host.appendChild(el('table', {}, [el('thead', {}, [head]), body]));
}

function paramEditor(file) {
  const wrap = el('div', {class: 'scroll'}, []);
  const simple = Object.entries(file).filter(([, v]) =>
    v === null || ['string', 'number', 'boolean'].includes(typeof v));
  const grid = el('div', {style: 'padding:10px 12px;columns:2;column-gap:18px'}, []);
  for (const [key, value] of simple) {
    const control = typeof value === 'boolean'
      ? (() => {
          const box = el('input', {type: 'checkbox'});
          box.checked = value;
          box.addEventListener('change', () => { file[key] = box.checked; });
          return box;
        })()
      : input(value, (v) => {
          file[key] = typeof value === 'number' ? Number(v) : v;
        }, typeof value === 'number' ? 'number' : 'text');
    const row = el('div', {class: 'prop'}, [el('label', {text: key}), control]);
    row.style.breakInside = 'avoid';
    grid.appendChild(row);
  }
  wrap.appendChild(grid);
  const complex = Object.entries(file).filter(([, v]) =>
    v !== null && typeof v === 'object');
  for (const [key, value] of complex) {
    wrap.appendChild(el('div', {class: 'prop-head', text: key,
                                style: 'margin:8px 12px'}));
    const area = el('textarea', {style: 'width:calc(100% - 24px);margin:0 12px;min-height:70px'});
    area.value = JSON.stringify(value, null, 1);
    area.addEventListener('change', () => {
      try { file[key] = JSON.parse(area.value); }
      catch { toast('bad JSON in ' + key, 'error'); }
    });
    wrap.appendChild(area);
  }
  return wrap;
}

async function saveSpec(kind) {
  try {
    await post('specs/' + encodeURIComponent(S.specName) + '/' + kind,
               S.specs.files[kind]);
    await loadSpecs();
    toast(kind + ' spec file saved');
    await analyse();
    renderTable();
  } catch (err) { toast(err.message, 'error'); }
}

const KEY_HELP = [
  'DESIGN GRID — entry works the way the Design Assistant does.',
  '',
  '  type a number     start typing in the cell under the cursor',
  '  .                 commit and step to the next field (Ft › Units › Tap)',
  '  Enter             commit and drop to the next pole;',
  '                    at the foot of a leg it adds the next pole',
  '  Tab / Shift+Tab   step fields without wrapping to a new pole',
  '  F2                edit the current cell',
  '  Esc               abandon the edit',
  '',
  '  + / -             step the tap (or coupler, or active) at the cursor',
  '  Insert            insert a pole ahead of the cursor',
  '  Delete            splice the pole out, merging its footage',
  '',
  '  >                 design a leg that starts at this pole',
  '  <  or  U          back up to the parent leg, at its origin',
  '  S                 swap the legs on this device',
  '  N                 name the current leg',
  '',
  '  D                 run the automatic design tools',
  '  Ctrl+Z / Ctrl+Y   undo / redo',
  '  Ctrl+S            save',
  '',
  'A 0 in the footage column applies no cable loss, so a device can sit on',
  'the same pole as the one above it.',
].join('\n');

/* ------------------------------------------------------------- actions */
async function runDesign(action) {
  try {
    const data = await post('design', {network: S.network, spec: S.specName,
                                       action: action || 'full'});
    S.network = data.network;
    S.analysis = data.analysis;
    S.stats = data.stats;
    S.dirty = true;
    render();
    toast(`${data.run.changes.length} change(s) in ${data.run.passes} pass(es)`);
  } catch (err) { toast(err.message, 'error'); }
}

async function save() {
  const name = S.netName || prompt('Save network as:', S.network.name || 'untitled');
  if (!name) return;
  S.network.name = name;
  try {
    const data = await post('network/' + encodeURIComponent(name),
                            {network: S.network, name});
    S.dirty = false;
    S.netName = name;
    fill($('network-name'), data.networks);
    $('network-name').value = name;
    toast('saved ' + data.saved);
  } catch (err) { toast(err.message, 'error'); }
}

function download(path) {
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = '/api/' + path;
  form.target = '_blank';
  document.body.appendChild(form);
  // the report endpoints accept the live network as JSON, so post it directly
  fetch('/api/' + path, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({network: S.network, spec: S.specName}),
  }).then((r) => r.blob()).then((blob) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = (S.network.name || 'design') +
      (path.includes('xlsx') ? '.xlsx' : '.csv');
    link.click();
    URL.revokeObjectURL(url);
  }).catch((err) => toast(err.message, 'error'));
  form.remove();
}

/** Load a Lode Data binary library (.par .cbl .cpr .tap .atv) straight in. */
async function importSpecs(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  const suggested = files[0].name.replace(/\.[^.]+$/, '');
  const name = prompt(
    'Name for this spec set (regions usually differ, so give it the ' +
    'system name):', suggested);
  if (!name) return;
  toast(`reading ${files.length} spec file(s)...`);
  try {
    const payload = [];
    for (const file of files) {
      const buffer = await file.arrayBuffer();
      let binary = '';
      const bytes = new Uint8Array(buffer);
      for (let i = 0; i < bytes.length; i += 0x8000) {
        binary += String.fromCharCode.apply(
          null, bytes.subarray(i, i + 0x8000));
      }
      payload.push({name: file.name, data: btoa(binary)});
    }
    const data = await post('import', {name, files: payload});
    S.workspace.spec_sets = data.spec_sets;
    fill($('spec-set'), data.spec_sets);
    $('spec-set').value = data.name;
    S.specName = data.name;
    await loadSpecs();
    await analyse(true);
    const counts = data.summary.counts;
    toast(`imported ${counts.cables} cables, ${counts.taps} taps, ` +
          `${counts.couplers} couplers, ${counts.actives} actives`);
    alert('IMPORT REPORT — check this against your Lode Data spec printout '
          + 'before designing.\n\n' + data.report);
  } catch (err) {
    toast(err.message, 'error');
    alert('Import failed: ' + err.message);
  }
}

/* --------------------------------------------------------------- render */
function render(fit) {
  renderTabs();
  if (fit || !render._once) { setTimeout(fitView, 0); render._once = true; }
  else renderCanvas();
  renderProps();
  renderTable();
  renderStatus();
  renderLegend();
  renderLegs();
}

function renderLegs() {
  const host = $('legs');
  if (!host) return;
  host.textContent = '';
  if (!S.legs.length) {
    host.appendChild(el('div', {class: 'gridhint', text: 'no legs yet'}));
    return;
  }
  const depth = (leg) => legPath(leg.id).length - 1;
  const ordered = [];
  const walk = (parent) => {
    for (const leg of S.legs.filter((l) => l.parent_leg === parent)) {
      ordered.push(leg);
      walk(leg.id);
    }
  };
  walk('');
  for (const leg of ordered) {
    const origin = leg.origin ? byId(leg.origin) : null;
    const name = leg.name || (origin
      ? `${origin.label || origin.id} [${leg.port}]` : 'TRUNK');
    const bad = leg.locations.some(
      (id) => (S.analysis.solution.results[id] || {}).status === 'error');
    const row = el('div', {
      class: 'leg' + (leg.id === S.legId ? ' on' : ''),
      onclick: () => goLeg(leg.id, 0),
    }, [
      el('span', {class: 'dp', text: '·'.repeat(Math.max(0, depth(leg))) }),
      el('span', {class: 'nm' + (bad ? ' error' : ''), text: name}),
      el('span', {class: 'ct', text: `${leg.locations.length}`}),
    ]);
    host.appendChild(row);
  }
}

function renderLegend() {
  const host = $('legend');
  host.textContent = '';
  const items = [['var(--ok)', 'in spec'], ['var(--warn)', 'inside margin'],
                 ['var(--error)', 'out of spec'], ['var(--tap)', 'tap ( ) 4-port [ ] 2-port { } 8-port'],
                 ['var(--active)', 'amplifier'], ['var(--coupler)', 'coupler']];
  for (const [color, text] of items) {
    const chip = el('span', {}, [el('i', {style: `background:${color}`}),
                                document.createTextNode(text)]);
    host.appendChild(chip);
  }
}

function renderStatus() {
  const stats = S.stats || {};
  $('stats').textContent =
    `${stats.locations || 0} locations · ${stats.taps || 0} taps · ` +
    `${stats.actives || 0} actives · ${stats.units || 0} units · ` +
    `${(stats.footage || 0).toLocaleString()} ${S.specs.files.parameters.distance_units}` +
    (S.dirty ? ' · unsaved' : '');
  const flags = (S.analysis && S.analysis.flags) || [];
  const errors = flags.filter((f) => f.severity === 'error').length;
  const warns = flags.filter((f) => f.severity === 'warn').length;
  const verdict = $('verdict');
  verdict.textContent = errors ? `${errors} error(s), ${warns} warning(s)`
    : warns ? `${warns} warning(s)` : 'design in spec';
  verdict.className = errors ? 'error' : warns ? 'warn' : 'ok';
}

/* ---------------------------------------------------------------- wiring */
function wire() {
  $('spec-set').addEventListener('change', async (event) => {
    S.specName = event.target.value;
    await loadSpecs();
    await analyse();
  });
  $('network-name').addEventListener('change', async (event) => {
    if (S.dirty && !confirm('Discard unsaved changes?')) {
      event.target.value = S.netName;
      return;
    }
    S.netName = event.target.value;
    await loadNetwork(S.netName);
  });
  $('btn-design').addEventListener('click', () => runDesign('full'));
  $('btn-taps').addEventListener('click', () => runDesign('taps'));
  $('btn-amps').addEventListener('click', () => runDesign('actives'));
  $('btn-save').addEventListener('click', save);
  $('btn-xlsx').addEventListener('click', () => download('report/all?format=xlsx'));
  $('btn-fit').addEventListener('click', fitView);
  const importBtn = $('btn-import'), importInput = $('import-files');
  if (importBtn && importInput) {
    importBtn.addEventListener('click', () => importInput.click());
    importInput.addEventListener('change', () => importSpecs(importInput.files));
  }
  const help = $('btn-help');
  if (help) help.addEventListener('click', () => alert(KEY_HELP));

  for (const selector of ['#plant', '#side', '#tabs']) {
    const node = document.querySelector(selector);
    if (node) node.addEventListener('mousedown', () => { S.gridActive = false; });
  }

  const svg = $('plant');
  let dragging = null;
  svg.addEventListener('mousedown', (event) => {
    dragging = {x: event.clientX, y: event.clientY,
                vx: S.view.x, vy: S.view.y};
    svg.classList.add('dragging');
  });
  window.addEventListener('mousemove', (event) => {
    if (!dragging) return;
    S.view.x = dragging.vx + (event.clientX - dragging.x);
    S.view.y = dragging.vy + (event.clientY - dragging.y);
    renderCanvas();
  });
  window.addEventListener('mouseup', () => {
    dragging = null;
    svg.classList.remove('dragging');
  });
  svg.addEventListener('wheel', (event) => {
    event.preventDefault();
    const box = svg.getBoundingClientRect();
    const mx = event.clientX - box.left, my = event.clientY - box.top;
    const factor = Math.exp(-event.deltaY * 0.0014);
    const k = Math.min(6, Math.max(0.01, S.view.k * factor));
    S.view.x = mx - (mx - S.view.x) * (k / S.view.k);
    S.view.y = my - (my - S.view.y) * (k / S.view.k);
    S.view.k = k;
    renderCanvas();
  }, {passive: false});

  window.addEventListener('keydown', (event) => {
    // The design grid is a keyboard instrument of its own.  It claims the
    // keyboard by state rather than by DOM focus, because re-solving the
    // network rebuilds the table and focus would be lost mid-keystroke --
    // which used to drop digits and let arrow keys jump to another leg.
    if (S.tab === 'design' && S.gridActive &&
        !(event.target.closest && event.target.closest('#side, #tabs, .bar'))) {
      gridKey(event);
      return;
    }
    const tag = (event.target.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag)) return;
    if (event.ctrlKey || event.metaKey) {
      const lower = event.key.toLowerCase();
      if (lower === 's') { event.preventDefault(); save(); }
      else if (lower === 'z') {
        event.preventDefault();
        event.shiftKey ? redo() : undo();
      } else if (lower === 'y') { event.preventDefault(); redo(); }
      return;
    }
    const key = event.key;
    if (key === '+' || key === '=') { event.preventDefault(); stepDevice(1); }
    else if (key === '-' || key === '_') { event.preventDefault(); stepDevice(-1); }
    else if (key === 'ArrowDown') { event.preventDefault(); moveSelection(1); }
    else if (key === 'ArrowUp') { event.preventDefault(); moveSelection(-1); }
    else if (key === 'Delete' || key === 'Backspace') {
      event.preventDefault(); removeSelected();
    } else if (key.toLowerCase() === 't') addAfter('tap');
    else if (key.toLowerCase() === 'c') addAfter('coupler');
    else if (key.toLowerCase() === 'e') addAfter('end');
    else if (key.toLowerCase() === 'a') insertActiveBefore();
    else if (key.toLowerCase() === 'd') runDesign('full');
    else if (key.toLowerCase() === 'f') fitView();
  });

  window.addEventListener('beforeunload', (event) => {
    if (S.dirty) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('resize', () => renderCanvas());
}

boot().catch((err) => {
  document.body.appendChild(el('div', {class: 'empty error',
    text: 'startup failed: ' + err.message}));
});
