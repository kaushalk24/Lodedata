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
};

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
    render(fit);
  } catch (err) {
    toast(err.message, 'error');
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
    loc.device = next.id;
    scheduleAnalyse();
  }
}

function select(id) {
  S.sel = id;
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
      onclick: () => { S.tab = key; renderTabs(); renderTable(); },
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
  if (S.tab === 'design') return host.appendChild(designTable());
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

function designTable() {
  const solution = S.analysis.solution;
  const fwd = solution.forward_columns, rtn = solution.return_columns;
  const columns = ['Loc', 'Type', 'Device', 'Cable', 'Length', 'Units',
    ...fwd.map((c) => 'In ' + label(c)),
    ...fwd.map((c) => 'Tap ' + label(c)),
    ...rtn.map((c) => 'Rtn ' + label(c)),
    'Pad', 'EQ', 'Status'];
  const rows = solution.order.map((id) => {
    const r = solution.results[id];
    const row = {
      __id: id, Loc: r.label, Type: r.kind, Device: r.device, Cable: r.cable,
      Length: r.length || '', Units: r.units || '',
      Pad: r.pad ?? '', EQ: r.eq ?? '', Status: r.status,
    };
    fwd.forEach((c) => {
      row['In ' + label(c)] = r.fwd_in[c];
      row['Tap ' + label(c)] = r.fwd_tap[c];
    });
    rtn.forEach((c) => { row['Rtn ' + label(c)] = r.rtn_tap[c]; });
    return row;
  });
  const flagCells = (row, column) => {
    if (!row.__id) return '';
    const res = S.analysis.solution.results[row.__id];
    for (const flag of res.flags || []) {
      if (!flag.column) continue;
      const name = label(flag.column);
      if (column === 'Tap ' + name || column === 'Rtn ' + name ||
          column === 'In ' + name) return flag.severity;
    }
    return '';
  };
  return table(columns, rows, {
    text: new Set(['Loc', 'Type', 'Device', 'Cable', 'Status']), flagCells});
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

/* --------------------------------------------------------------- render */
function render(fit) {
  renderTabs();
  if (fit || !render._once) { setTimeout(fitView, 0); render._once = true; }
  else renderCanvas();
  renderProps();
  renderTable();
  renderStatus();
  renderLegend();
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
    const tag = (event.target.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag)) return;
    if (event.ctrlKey || event.metaKey) {
      if (event.key.toLowerCase() === 's') { event.preventDefault(); save(); }
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
