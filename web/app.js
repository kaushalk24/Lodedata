/* HFC Plant Designer UI: a node-line grid editor modeled on Lode's Design mode.
 * State lives in `state`; every edit goes through mutate() -> Engine.calc() -> render(). */

(() => {
  'use strict';
  const STORE = 'hfc-plant-designer:v1';
  const $ = sel => document.querySelector(sel);
  const pd = e => e.preventDefault(); // keep focus in the grid when clicking chrome buttons
  const clone = x => JSON.parse(JSON.stringify(x));
  const f1 = v => (v == null || !isFinite(v) ? '' : v.toFixed(1));
  const f2 = v => (v == null || !isFinite(v) ? '' : v.toFixed(2));
  const yes = v => v === true || v === 'true' || v === 'Y' || v === 'y' || v === 1 || v === '1';

  function el(tag, attrs = {}, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') e.className = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (v === true) e.setAttribute(k, '');
      else if (v !== false && v != null) e.setAttribute(k, v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) e.append(kid instanceof Node ? kid : String(kid));
    return e;
  }
  const btn = (label, fn, cls = '') => el('button', { type: 'button', class: `btn ${cls}`, onclick: fn }, label);

  const state = {
    network: null, specs: null, mode: 'design', branch: '1', row: 0,
    result: null, carry: null, esc: false, flash: null, undo: [],
  };

  // ---------- persistence (per-browser draft) ----------
  function load() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORE) || 'null');
      if (saved && saved.network && saved.network.branches && saved.specs && saved.specs.cables) {
        Object.assign(state, { network: saved.network, specs: normalizeSpecs(saved.specs), mode: saved.mode || 'design', branch: saved.branch || '1' });
        if (!state.network.branches[state.branch]) state.branch = '1';
        return false;
      }
    } catch (e) { /* storage unavailable: start from the sample */ }
    state.network = clone(SAMPLE_NETWORK);
    state.specs = clone(SAMPLE_SPECS);
    return true;
  }
  let saveTimer;
  function persist() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try {
        localStorage.setItem(STORE, JSON.stringify({ network: state.network, specs: state.specs, mode: state.mode, branch: state.branch }));
      } catch (e) { /* draft not kept in this browser */ }
    }, 300);
  }
  function normalizeSpecs(s) {
    const out = { name: s.name || 'SPECS', parameters: { ...SAMPLE_SPECS.parameters, ...(s.parameters || {}) } };
    for (const k of ['cables', 'actives', 'taps', 'couplers']) out[k] = Array.isArray(s[k]) ? s[k] : [];
    return out;
  }

  // ---------- model helpers ----------
  const rows = () => state.network.branches[state.branch] || [];
  const nodeId = i => `${state.branch}.${i + 1}`;
  const nodeRes = i => state.result && state.result.nodes.get(nodeId(i));
  const pw = R => state.result && state.result.power && state.result.power.nodes.get(R.id);
  const cableOf = id => state.specs.cables.find(c => String(c.id) === String(id));
  const blankRow = cbl => ({ cbl: cbl != null ? cbl : String((state.specs.cables[0] || {}).id || ''), ft: 0, hc: 0, tsg: 0, eq: '' });
  const clampRow = () => { state.row = Math.max(0, Math.min(state.row, rows().length - 1)); };
  const tokens = eq => String(eq || '').split(/\s+/).filter(Boolean);

  // Couplers may name a branch that does not exist yet: create it (Lode opens a new branch the same way).
  function ensureBranches() {
    const br = state.network.branches;
    for (const list of Object.values(br)) {
      for (const row of list) {
        for (const c of Engine.parseEquip(row.eq).couplers) {
          if (c.branch !== '1' && !br[c.branch]) br[c.branch] = [blankRow(row.cbl)];
        }
      }
    }
  }
  function feedOf(b) {
    for (const [bb, list] of Object.entries(state.network.branches)) {
      const i = list.findIndex(r => Engine.parseEquip(r.eq).couplers.some(c => c.branch === b));
      if (i >= 0) return { branch: bb, row: i };
    }
    return null;
  }

  function mutate(fn) {
    state.undo.push(JSON.stringify(state.network));
    if (state.undo.length > 60) state.undo.shift();
    fn();
    ensureBranches();
    if (!state.network.branches[state.branch]) state.branch = '1';
    clampRow();
    recalc();
  }
  function undo() {
    const s = state.undo.pop();
    if (!s) return flash('Nothing to undo');
    state.network = JSON.parse(s);
    if (!state.network.branches[state.branch]) state.branch = '1';
    clampRow();
    recalc();
    flash('Undone');
  }
  function recalc() {
    try {
      state.result = Engine.calc(state.network, state.specs);
    } catch (e) {
      state.result = null;
      flash(`Calculation stopped: ${e.message}`);
    }
    render();
    persist();
  }

  // ---------- grid columns ----------
  const P = () => state.specs.parameters;
  const COLS = {
    design: ['node', 'cbl', 'ft', 'hc', 'tsg', 'eq', 'sel', 'inHi', 'inLo', 'tapHi', 'tapLo', 'rh', 'rl', 'padeq', 'err'],
    entry: ['node', 'cbl', 'ft', 'hc', 'tsg', 'eq', 'err'],
    powering: ['node', 'cbl', 'ft', 'ohm', 'eq', 'volts', 'load', 'thru', 'zone', 'err'],
  };
  const COL = {
    node: { label: 'Node', cls: 'node l' },
    cbl: { label: 'Cbl', edit: 'text', size: 3, fields: ['cable'], tip: 'Cable ID from the Cables spec' },
    ft: { label: 'Feet', edit: 'num', size: 5, tip: 'Span length arriving at this node' },
    hc: { label: 'HC', edit: 'num', size: 3, tip: 'House count at this node' },
    tsg: { label: 'TSG', edit: 'num', size: 2, tip: 'Tap selection group (0 = default from Parameters)' },
    eq: { label: 'Equipment', edit: 'text', size: 18, cls: 'l', fields: ['equip', 'coupler', 'cascade'], tip: 'Active, taps, couplers, PS. See Help for notation' },
    sel: { label: 'Selected', cls: 'l', fields: ['coupler'], tip: 'Tap and coupler values in use (green = auto-selected)' },
    inHi: { label: () => `Hi ${P().fHi}`, val: R => f1(R.in.hi), fields: ['active'], tip: 'Level after the span, before equipment (dBmV)' },
    inLo: { label: () => `Lo ${P().fLo}`, val: R => f1(R.in.lo), fields: ['active'], tip: 'Level after the span, before equipment (dBmV)' },
    tapHi: { label: 'Tap Hi', val: R => R.tapMin && f1(R.tapMin.hi), fields: ['tap', 'perf'], tip: 'Lowest tap port output at this node' },
    tapLo: { label: 'Tap Lo', val: R => R.tapMin && f1(R.tapMin.lo), fields: ['tap'], tip: 'Lowest tap port output at this node' },
    rh: { label: () => `Rh ${P().fRh}`, val: R => R.retMax && f1(R.retMax.rh), fields: ['ret'], tip: 'Return level a modem needs at the tap port' },
    rl: { label: () => `Rl ${P().fRl}`, val: R => R.retMax && f1(R.retMax.rl), fields: ['ret'], tip: 'Return level a modem needs at the tap port' },
    padeq: { label: 'Pad/EQ', val: R => (R.active ? `${R.active.pad}/${R.active.eq}` : ''), fields: ['active'] },
    ohm: { label: 'Loop Ω', val: R => { const c = cableOf(R.row.cbl); return c && Number(R.row.ft) ? f2(Number(c.loop) * Number(R.row.ft) / 1000) : ''; } },
    volts: { label: 'Volts', val: R => pw(R) && f1(pw(R).volts), fields: ['power'] },
    load: { label: 'Load A', val: R => (pw(R) && pw(R).load ? f2(pw(R).load) : '') },
    thru: { label: 'Thru A', val: R => pw(R) && f2(pw(R).thru), fields: ['power'] },
    zone: { label: 'PS', val: R => (R.eq.ps ? 'PS' : pw(R) ? pw(R).ps : ''), tip: 'Power supply feeding this node' },
    err: { label: 'Err' },
  };
  const labelOf = d => (typeof d.label === 'function' ? d.label() : d.label);

  // ---------- rendering ----------
  function render() {
    const a = document.activeElement;
    const fid = a && a.id && a.closest('#app') ? a.id : null;
    renderToolbar();
    renderBranchbar();
    renderGrid();
    renderDetail();
    renderStatus();
    $('#doc-name').textContent = `${state.network.name || 'UNTITLED'}.NTW · specs ${state.specs.name || '—'}`;
    if (fid) {
      const n = document.getElementById(fid);
      if (n && n !== document.activeElement) { n.focus(); if (n.select) n.select(); }
    }
  }

  function renderGrid() {
    const cols = COLS[state.mode];
    $('#grid thead').replaceChildren(el('tr', {}, cols.map(c => el('th', { class: COL[c].cls || '', title: COL[c].tip || null }, labelOf(COL[c])))));
    $('#grid tbody').replaceChildren(...rows().map((row, i) => renderRow(row, i, cols)));
  }

  function severities(R) {
    const s = {};
    if (R) for (const e of R.errors) if (s[e.field] !== 'red') s[e.field] = e.sev;
    return s;
  }
  function renderRow(row, i, cols) {
    const R = nodeRes(i);
    const sev = severities(R);
    const tr = el('tr', { class: i === state.row ? 'sel' : null, 'data-r': i });
    for (const c of cols) {
      const d = COL[c];
      const worst = (d.fields || []).map(f => sev[f]).reduce((w, s) => (w === 'red' || s === 'red' ? 'red' : w || s), undefined);
      const cls = [d.cls, worst === 'red' ? 'bad' : worst === 'yellow' ? 'warn' : '', d.edit ? 'edit' : ''].filter(Boolean).join(' ');
      let content = '';
      if (d.edit) {
        content = el('input', {
          id: `c-${state.branch}-${i}-${c}`, 'data-r': i, 'data-k': c, value: row[c] == null ? '' : row[c], size: d.size,
          inputmode: d.edit === 'num' ? 'decimal' : 'text', autocomplete: 'off', spellcheck: 'false', 'aria-label': `${labelOf(d)} ${nodeId(i)}`,
        });
      } else if (c === 'node') content = nodeId(i);
      else if (c === 'sel') content = R ? selectedTokens(R) : '';
      else if (c === 'err') content = errBadge(R);
      else if (R && d.val) content = d.val(R) || '';
      tr.append(el('td', { class: cls || null }, content));
    }
    return tr;
  }
  const OPEN = { 2: '(', 4: '[', 8: '{' }, CLOSE = { 2: ')', 4: ']', 8: '}' };
  const tapTok = t => OPEN[t.ports] + t.value + CLOSE[t.ports];
  function selectedTokens(R) {
    const parts = [
      ...R.taps.map(t => el('span', { class: t.auto ? 'auto' : null }, tapTok(t))),
      ...R.couplers.map(c => el('span', { class: c.auto ? 'auto' : null }, `${c.neg ? '-' : ''}${c.id}[${c.branch}]`)),
    ];
    return parts.flatMap((p, k) => (k ? [' ', p] : [p]));
  }
  function errBadge(R) {
    if (!R || !R.errors.length) return '';
    const red = R.errors.filter(e => e.sev === 'red').length;
    const yel = R.errors.length - red;
    return el('span', { class: red ? 'bad' : 'warn', title: R.errors.map(e => e.msg).join('\n') }, [red ? `E${red}` : '', yel ? `W${yel}` : ''].filter(Boolean).join(' '));
  }

  function tools() {
    if (state.mode === 'powering') {
      return [[1, 'PS here', cmdTogglePS], [2, 'Optimize PS', cmdOptimize], [4, 'Delete', cmdDelete], [5, 'Branch ▸', cmdBranchIn],
        [6, 'Test', cmdTest], [7, '◂ Back', cmdBranchOut], [8, 'Add line', cmdAddLine], [9, 'Design', () => setMode('design')]];
    }
    return [[1, 'Lock', cmdLock], [2, 'Insert', cmdInsert], [3, state.carry ? 'Drop' : 'Carry', cmdCarry], [4, 'Delete', cmdDelete],
      [5, 'Branch ▸', cmdBranchIn], [6, 'Test', cmdTest], [7, '◂ Back', cmdBranchOut], [8, 'Add line', cmdAddLine],
      [9, state.mode === 'entry' ? 'Design' : 'Powering', () => setMode(state.mode === 'entry' ? 'design' : 'powering')]];
  }
  function renderToolbar() {
    $('#toolbar').replaceChildren(...tools().map(([n, label, fn]) =>
      el('button', { type: 'button', class: n === 3 && state.carry ? 'on' : null, title: `Esc ${n}`, onmousedown: pd, onclick: () => run(fn) }, el('b', {}, n), label)));
  }

  function renderBranchbar() {
    const net = state.network;
    const keys = Object.keys(net.branches).sort((a, b) => a - b);
    const fed = {};
    if (state.result) {
      for (const R of state.result.nodes.values()) for (const c of R.couplers) fed[c.branch] = { node: R.id, c };
    }
    const tabs = keys.map(b => el('button', {
      type: 'button', class: b === state.branch ? 'on' : null, onmousedown: pd, onclick: () => run(() => gotoBranch(b, 0)),
      title: fed[b] ? `Branch ${b}, fed from node ${fed[b].node}` : `Branch ${b}`,
    }, fed[b] ? `${b} ◂ ${fed[b].node}` : b));
    let info;
    if (state.branch === '1') {
      const start = net.start || (net.start = { hi: 0, lo: 0 });
      const inp = k => el('input', { id: `start-${k}`, value: start[k], inputmode: 'decimal', 'aria-label': `Start level ${k}`,
        onchange: e => { const v = Number(e.target.value); if (!isFinite(v)) return flash('Start level must be a number'); mutate(() => { start[k] = v; }); } });
      info = [el('span', { class: 'lbl' }, 'Start level'), 'Hi', inp('hi'), 'Lo', inp('lo'), 'dBmV'];
    } else if (fed[state.branch]) {
      const { node, c } = fed[state.branch];
      info = [el('span', { class: 'lbl' }, 'Fed from'), `${node} by ${c.part} at ${f1(c.branchIn.hi)} / ${f1(c.branchIn.lo)} dBmV`];
    } else info = [el('span', { class: 'warn' }, 'Not fed by any coupler')];
    const name = el('input', { id: 'net-name', value: net.name || '', 'aria-label': 'Network name', spellcheck: 'false',
      onchange: e => mutate(() => { net.name = e.target.value.trim().toUpperCase(); }) });
    $('#branchbar').replaceChildren(el('span', { class: 'lbl' }, 'Branch'), el('div', { class: 'tabs' }, tabs), el('span', { class: 'info' }, ...info),
      el('label', { class: 'net' }, el('span', { class: 'lbl' }, 'Network'), name));
  }

  function renderDetail() {
    const R = nodeRes(state.row);
    const items = [];
    if (!R) {
      items.push(['Node', `${nodeId(state.row)}: not calculated (branch ${state.branch} is not fed by a coupler)`]);
    } else {
      const p = P();
      const cab = cableOf(R.row.cbl);
      items.push(['Node', `${R.id} · cable ${R.row.cbl || '—'} ${cab ? cab.name : ''} · ${Number(R.row.ft) || 0} ft · HC ${Number(R.row.hc) || 0} · span loss ${f2(R.span.hi)} / ${f2(R.span.lo)} dB`]);
      items.push(['Input', `${f1(R.in.hi)} / ${f1(R.in.lo)} dBmV at ${p.fHi} / ${p.fLo} MHz · return path ${f1(R.retIn.rh)} / ${f1(R.retIn.rl)} dB back to the return input`]);
      if (R.active) {
        const a = R.active;
        const le = String(a.spec.type).toUpperCase() === 'LE' ? ` · LE cascade: ${a.leBefore} before, ${a.leAfter} after` : '';
        items.push(['Active', `${a.id} ${a.spec.name} (${a.spec.part}) · pad ${a.pad} · EQ ${a.eq} · out ${f1(a.out.hi)} / ${f1(a.out.lo)}${le}`]);
      }
      R.taps.forEach((t, k) => items.push([`Tap ${k + 1}`, `${tapTok(t)} ${t.part}${t.auto ? ' (auto)' : ''} · in ${f1(t.in.hi)} · port ${f1(t.port.hi)} / ${f1(t.port.lo)} · return needed ${f1(t.retReq.rh)} / ${f1(t.retReq.rl)}`]));
      R.couplers.forEach(c => items.push(['Coupler', `${c.neg ? '-' : ''}${c.id}[${c.branch}] ${c.part}${c.auto ? ' (auto)' : ''} · branch ${c.branch} starts at ${f1(c.branchIn.hi)} / ${f1(c.branchIn.lo)}`]));
      items.push(['Performance', `C/N ${f1(R.perf.cn)} · CTB ${f1(R.perf.ctb)} · CSO ${f1(R.perf.cso)} dB`]);
      const q = pw(R);
      if (q) items.push(['Power', `${f1(q.volts)} V · load ${f2(q.load)} A · through ${f2(q.thru)} A · supply at ${q.ps}`]);
      for (const e of R.errors) items.push([e.sev === 'red' ? 'Out of spec' : 'Marginal', e.msg, e.sev]);
    }
    $('#detail').replaceChildren(...items.flatMap(([k, v, sev]) => [el('dt', {}, k), el('dd', { class: sev === 'red' ? 'bad' : sev === 'yellow' ? 'warn' : null }, v)]));
  }

  function renderStatus() {
    const errs = state.result ? state.result.errors : [];
    const red = errs.filter(e => e.sev === 'red').length;
    const yel = errs.length - red;
    $('#status').replaceChildren(...[
      el('span', { class: 'mode' }, state.mode.toUpperCase()),
      el('span', {}, `Node ${nodeId(state.row)} · line ${state.row + 1} of ${rows().length}`),
      el('span', { class: red ? 'bad' : yel ? 'warn' : 'ok' }, red || yel ? `${red} out of spec · ${yel} marginal` : 'No errors'),
      state.carry && el('span', { class: 'msg' }, `Carrying active ${state.carry.id} from ${state.carry.from}: go to the new line, press 3 to drop`),
      state.esc && el('span', { class: 'msg' }, 'ESC: press 1–9'),
      state.flash && el('span', { class: 'msg' }, state.flash),
      el('span', { class: 'hint' }, 'Esc+1…9 commands · Ctrl+Z undo'),
    ].filter(Boolean));
  }
  function flash(msg) {
    state.flash = msg;
    renderStatus();
    clearTimeout(flash.t);
    flash.t = setTimeout(() => { state.flash = null; renderStatus(); }, 5000);
  }

  function selectRow(i, focusKey) {
    if (!rows().length) return;
    state.row = Math.max(0, Math.min(rows().length - 1, i));
    for (const tr of $('#grid tbody').children) tr.classList.toggle('sel', Number(tr.dataset.r) === state.row);
    renderDetail();
    renderStatus();
    const tr = $(`#grid tbody tr[data-r="${state.row}"]`);
    if (tr) tr.scrollIntoView({ block: 'nearest' });
    if (focusKey) {
      const inp = $(`#grid tbody input[data-r="${state.row}"][data-k="${focusKey}"]`);
      if (inp) { inp.focus(); inp.select(); }
    }
  }

  // ---------- editing ----------
  function commit(t) {
    const i = Number(t.dataset.r), k = t.dataset.k;
    const row = rows()[i];
    if (!row || !COL[k]) return;
    let v = t.value.trim();
    if (COL[k].edit === 'num') {
      v = v === '' ? 0 : Number(v);
      if (!isFinite(v)) { flash(`${labelOf(COL[k])} must be a number`); t.value = row[k]; return; }
    } else if (k === 'eq') v = v.replace(/\s+/g, ' ');
    if (String(row[k] == null ? '' : row[k]) === String(v)) return;
    mutate(() => { row[k] = v; });
  }

  const grid = $('#grid tbody');
  grid.addEventListener('focusin', e => {
    const r = e.target.dataset && e.target.dataset.r;
    if (r != null && Number(r) !== state.row) selectRow(Number(r));
  });
  grid.addEventListener('click', e => {
    const tr = e.target.closest('tr');
    if (tr && Number(tr.dataset.r) !== state.row) selectRow(Number(tr.dataset.r));
  });
  grid.addEventListener('change', e => { if (e.target.dataset.k) commit(e.target); });
  grid.addEventListener('keydown', e => {
    const t = e.target;
    if (!t.dataset || !t.dataset.k || state.esc) return;
    const k = t.dataset.k, i = Number(t.dataset.r);
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter') {
      e.preventDefault();
      commit(t);
      selectRow(e.key === 'ArrowUp' ? i - 1 : i + 1, k);
    }
  });

  document.addEventListener('keydown', e => {
    if (!$('#modal').hidden) { if (e.key === 'Escape') closeModal(); return; }
    if (e.key === 'Escape') { closeMenus(); state.esc = true; renderStatus(); return; }
    if (state.esc) {
      state.esc = false;
      if (/^[1-9]$/.test(e.key)) {
        e.preventDefault();
        const t = tools().find(x => x[0] === Number(e.key));
        if (t) run(t[2]);
      }
      renderStatus();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.target.matches('input, textarea')) { e.preventDefault(); undo(); }
  });

  // Run a command after committing whatever is being typed in the grid.
  function run(fn) {
    const a = document.activeElement;
    if (a && a.dataset && a.dataset.k && a.closest('#grid')) commit(a);
    fn();
  }

  // ---------- commands ----------
  function setMode(m) { state.mode = m; render(); selectRow(state.row); persist(); }
  function gotoBranch(b, row) { state.branch = b; state.row = row; render(); selectRow(row); persist(); }
  function jumpTo(id) {
    const [b, n] = String(id).split('.');
    if (state.network.branches[b]) gotoBranch(b, Number(n) - 1);
  }

  function cmdLock() {
    if (!state.result) return;
    mutate(() => Engine.lockSelections(state.network, state.result));
    flash('Auto-selected taps and couplers written into the Equipment column');
  }
  function cmdUnlock() { mutate(() => Engine.unlockTaps(state.network)); flash('Every tap set to auto [*]'); }
  function cmdInsert() {
    const cur = rows()[state.row];
    mutate(() => rows().splice(state.row, 0, blankRow(cur && cur.cbl)));
    selectRow(state.row, 'ft');
  }
  function cmdAddLine() {
    const cur = rows()[state.row];
    const at = rows().length ? state.row + 1 : 0;
    mutate(() => rows().splice(at, 0, blankRow(cur && cur.cbl)));
    selectRow(at, 'ft');
  }
  function cmdDelete() {
    if (!rows().length) return;
    const id = nodeId(state.row);
    mutate(() => {
      const list = rows();
      list.splice(state.row, 1);
      if (!list.length) {
        if (state.branch === '1') list.push(blankRow());
        else delete state.network.branches[state.branch];
      }
    });
    selectRow(state.row);
    flash(`Line ${id} deleted (Ctrl+Z to undo)`);
  }
  function cmdCarry() {
    const row = rows()[state.row];
    if (!state.carry) {
      const eq = Engine.parseEquip(row && row.eq);
      if (!eq.active) return flash('No active on this line to carry');
      state.carry = { branch: state.branch, row: state.row, id: eq.active, from: nodeId(state.row) };
      renderToolbar();
      return renderStatus();
    }
    const c = state.carry;
    state.carry = null;
    if (c.branch === state.branch && c.row === state.row) { renderToolbar(); return flash('Carry cancelled'); }
    const target = Engine.parseEquip(row.eq);
    if (target.active) { state.carry = c; return flash(`Line ${nodeId(state.row)} already has an active`); }
    const srcRow = (state.network.branches[c.branch] || [])[c.row];
    const src = srcRow && Engine.parseEquip(srcRow.eq);
    if (!src || src.active !== c.id) { renderToolbar(); return flash('The carried active is no longer on its line'); }
    mutate(() => {
      src.active = null;
      srcRow.eq = Engine.formatEquip(src);
      row.eq = [c.id, ...tokens(row.eq)].join(' ');
    });
    flash(`Active ${c.id} moved from ${c.from} to ${nodeId(state.row)}`);
  }
  function cmdBranchIn() {
    const eq = Engine.parseEquip((rows()[state.row] || {}).eq);
    const c = eq.couplers.find(x => state.network.branches[x.branch]);
    if (!c) return flash('No coupler feeding a branch on this line');
    gotoBranch(c.branch, 0);
  }
  function cmdBranchOut() {
    if (state.branch === '1') return flash('Already on branch 1');
    const feed = feedOf(state.branch);
    if (feed) gotoBranch(feed.branch, feed.row);
    else gotoBranch('1', 0);
  }
  function cmdTogglePS() {
    const row = rows()[state.row];
    if (!row) return;
    const t = tokens(row.eq);
    const has = t.some(x => /^PS$/i.test(x));
    mutate(() => { row.eq = (has ? t.filter(x => !/^PS$/i.test(x)) : [...t, 'PS']).join(' '); });
    flash(has ? `Power supply removed from ${nodeId(state.row)}` : `Power supply placed at ${nodeId(state.row)}`);
  }
  function cmdTest() { showReport('errors'); }

  function cmdOptimize() {
    const psRows = Object.values(state.network.branches).flat().filter(r => tokens(r.eq).some(x => /^PS$/i.test(x)));
    const out = el('div');
    const pick = (objective, label) => btn(label, () => {
      const best = Engine.optimizePS(state.network, state.specs, objective);
      if (!best) return out.replaceChildren(el('p', { class: 'warn' }, 'No location works for this objective. Balanced draw needs current flowing in at least two directions.'));
      out.replaceChildren(
        el('p', {}, `${label}: best location is node ${best.node}, lowest active voltage ${f1(best.low)} V.`),
        psRows.length <= 1 ? btn(`Move the power supply to ${best.node}`, () => {
          const [b, n] = best.node.split('.');
          mutate(() => {
            for (const list of Object.values(state.network.branches)) for (const r of list) r.eq = tokens(r.eq).filter(x => !/^PS$/i.test(x)).join(' ');
            const r = state.network.branches[b][Number(n) - 1];
            r.eq = [...tokens(r.eq), 'PS'].join(' ');
          });
          closeModal();
          jumpTo(best.node);
          flash(`Power supply moved to ${best.node}`);
        }, 'primary') : el('p', { class: 'warn' }, 'This network has more than one supply; move them by hand.'),
      );
    });
    openModal('Optimize power supply location', el('div', {},
      el('p', {}, 'Tries every node as the location of a single supply and keeps the best one.'),
      el('div', { class: 'spec-tabs' }, pick('maxlow', 'Maximum low voltage'), pick('sqdrop', 'Minimum square voltage drop'), pick('balanced', 'Balanced draw')),
      out), [btn('Close', closeModal)]);
  }

  // ---------- files ----------
  async function saveFile(filename, text) {
    if (window.claude && window.claude.use) {
      let dl = null;
      try { dl = await window.claude.use('downloads'); } catch (e) { dl = null; }
      if (dl) {
        try { await dl.save({ filename, data: text }); flash(`Saved ${filename}`); }
        catch (e) {
          if (e && e.code === 'declined') flash('Save cancelled');
          else if (e && e.code === 'rate_limited') flash('A save is already waiting for confirmation');
          else showText(filename, text);
        }
        return;
      }
      return showText(filename, text);
    }
    const a = el('a', { href: URL.createObjectURL(new Blob([text], { type: 'text/plain' })), download: filename });
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    flash(`Saved ${filename}`);
  }
  function showText(filename, text) {
    const ta = el('textarea', { class: 'export', id: 'export-text', readonly: true, 'aria-label': filename });
    ta.value = text;
    openModal(filename, el('div', {}, el('p', {}, 'Saving files is not available here. Copy the text and save it as this file name.'), ta), [
      btn('Copy', () => {
        navigator.clipboard.writeText(text).then(() => flash('Copied'), () => { ta.focus(); ta.select(); });
      }, 'primary'), btn('Close', closeModal)]);
  }
  const csvCell = v => { const s = String(v == null ? '' : v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const toCSV = rep => [rep.cols, ...rep.rows].map(r => r.map(csvCell).join(',')).join('\n') + '\n';

  function cmdSaveNet() { saveFile(`${state.network.name || 'NETWORK'}.ntw.json`, JSON.stringify(state.network, null, 1)); }
  function cmdSaveSpecs() { saveFile(`${state.specs.name || 'SPECS'}.specs.json`, JSON.stringify(state.specs, null, 1)); }
  $('#file-input').addEventListener('change', async e => {
    const file = e.target.files[0];
    e.target.value = '';
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      const net = data.network || (data.branches ? data : null);
      const specs = data.specs || (data.cables ? data : null);
      if (!net && !specs) throw new Error('it is not a network or specs file');
      if (net && (typeof net.branches !== 'object' || !net.branches['1'])) throw new Error('the network has no branch 1');
      state.undo.push(JSON.stringify(state.network));
      if (net) { state.network = { name: net.name || 'NETWORK', start: net.start || { hi: 0, lo: 0 }, branches: net.branches }; state.branch = '1'; state.row = 0; }
      if (specs) state.specs = normalizeSpecs(specs);
      recalc();
      selectRow(0);
      flash(`Opened ${file.name}`);
    } catch (err) {
      flash(`Could not open ${file.name}: ${err.message}`);
    }
  });
  function confirmThen(title, text, ok, fn) {
    openModal(title, el('p', {}, text), [btn('Cancel', closeModal), btn(ok, () => { closeModal(); fn(); }, 'primary')]);
  }
  function cmdNew() {
    confirmThen('New network', 'Start a new, empty network? The current network is replaced; the specs stay loaded. Save it first if you want to keep it.', 'Start new network', () => {
      state.undo.push(JSON.stringify(state.network));
      state.network = { name: 'NEW', start: { hi: 49, lo: 37 }, branches: { 1: [blankRow()] } };
      state.branch = '1'; state.row = 0;
      recalc();
      selectRow(0, 'cbl');
    });
  }
  function cmdSample() {
    confirmThen('Load sample', 'Replace the current network and specs with the sample? Save them first if you want to keep them.', 'Load sample', () => {
      state.undo.push(JSON.stringify(state.network));
      state.network = clone(SAMPLE_NETWORK);
      state.specs = clone(SAMPLE_SPECS);
      state.branch = '1'; state.row = 0;
      recalc();
      selectRow(0);
    });
  }

  // ---------- dialogs: reports, specs, help ----------
  function openModal(title, body, buttons) {
    $('#modal-title').textContent = title;
    $('#modal-body').replaceChildren(body);
    $('#modal-foot').replaceChildren(...buttons);
    $('#modal').hidden = false;
    $('#modal-close').focus();
  }
  function closeModal() { $('#modal').hidden = true; }
  $('#modal-close').addEventListener('click', closeModal);
  $('#modal').addEventListener('click', e => { if (e.target.id === 'modal') closeModal(); });

  const EMPTY = {
    errors: 'No errors. Every node meets the limits in the Parameters spec.',
    power: 'No power supply yet. In Powering mode, go to a line and press 1 (PS here).',
  };
  function showReport(key) {
    if (!state.result) return;
    const rep = Engine.reports(state.result, state.specs, state.network)[key];
    const isErr = key === 'errors';
    const body = rep.rows.length
      ? el('div', { class: 'scroll' }, el('table', { class: 'report' },
        el('thead', {}, el('tr', {}, rep.cols.map(c => el('th', {}, c)))),
        el('tbody', {}, rep.rows.map(r => el('tr', isErr ? { class: 'link', title: 'Go to node', onclick: () => { closeModal(); jumpTo(r[0]); } } : {},
          r.map((v, j) => el('td', { class: isErr && j === 1 ? (v === 'Out of spec' ? 'bad' : 'warn') : null }, v)))))))
      : el('p', {}, EMPTY[key] || 'Nothing to report.');
    openModal(rep.title, body, [
      rep.rows.length ? btn('Save CSV', () => saveFile(`${state.network.name || 'NETWORK'}-${key}.csv`, toCSV(rep))) : null,
      btn('Close', closeModal, 'primary'),
    ].filter(Boolean));
  }

  const SPEC_COLS = {
    cables: [['id', 'ID', 't', 3], ['name', 'Description', 't', 16], ['hi', 'Hi dB/100ft', 'n', 5], ['lo', 'Lo', 'n', 5], ['rh', 'Rh', 'n', 5], ['rl', 'Rl', 'n', 5], ['loop', 'Loop Ω/1000ft', 'n', 5]],
    actives: [['id', 'ID', 't', 3], ['name', 'Name', 't', 11], ['part', 'Part', 't', 7], ['type', 'LE/AMP', 't', 3], ['cascade', 'Cascade', 't', 3],
      ['gainHi', 'Gain Hi', 'n', 4], ['gainLo', 'Gain Lo', 'n', 4], ['outHi', 'Out Hi', 'n', 4], ['outLo', 'Out Lo', 'n', 4], ['minIn', 'Min in', 'n', 4],
      ['reserve', 'Reserve', 'n', 3], ['nf', 'NF', 'n', 3], ['ctb', 'CTB', 'n', 3], ['cso', 'CSO', 'n', 3], ['refOut', 'Ref out', 'n', 4],
      ['vi', 'Volts:Amps steps', 't', 18], ['maxAmps', 'Max A', 'n', 3]],
    taps: [['tsg', 'TSG', 'n', 2], ['part', 'Part', 't', 7], ['value', 'Value', 'n', 3], ['ports', 'Ports', 'n', 2], ['term', 'Term', 'b'],
      ['tapHi', 'Tap Hi', 'n', 4], ['tapLo', 'Tap Lo', 'n', 4], ['tapRh', 'Tap Rh', 'n', 4], ['tapRl', 'Tap Rl', 'n', 4],
      ['thruHi', 'Thru Hi', 'n', 4], ['thruLo', 'Thru Lo', 'n', 4], ['thruRh', 'Thru Rh', 'n', 4], ['thruRl', 'Thru Rl', 'n', 4], ['maxAmps', 'Max A', 'n', 3]],
    couplers: [['id', 'ID', 't', 3], ['part', 'Part', 't', 8], ['thruHi', 'Thru Hi', 'n', 4], ['thruLo', 'Thru Lo', 'n', 4], ['thruRh', 'Thru Rh', 'n', 4], ['thruRl', 'Thru Rl', 'n', 4],
      ['tapHi', 'Tap Hi', 'n', 4], ['tapLo', 'Tap Lo', 'n', 4], ['tapRh', 'Tap Rh', 'n', 4], ['tapRl', 'Tap Rl', 'n', 4], ['maxAmps', 'Max A', 'n', 3]],
  };
  const PARAM_GROUPS = [
    ['Frequencies (MHz)', [['fHi', 'Forward high'], ['fLo', 'Forward low'], ['fRh', 'Return high'], ['fRl', 'Return low']]],
    ['Tap outputs (dBmV)', [['minTapHi', 'Minimum at Hi'], ['minTapLo', 'Minimum at Lo'], ['tapWindow', 'Tap window (dB above min)'], ['defaultTsg', 'Default TSG']]],
    ['Return path (dBmV)', [['retInRh', 'Return amp input Rh'], ['retInRl', 'Return amp input Rl'], ['maxRetRh', 'Max return at tap Rh'], ['maxRetRl', 'Max return at tap Rl']]],
    ['Actives', [['maxLeCascade', 'Max LE cascade (1–3)'], ['padMax', 'Largest pad (dB)'], ['padStep', 'Pad step (dB)'], ['eqValues', 'EQ values (dB)', 't'], ['eqLoss', 'EQ insertion loss (dB)'], ['allowOverEq', 'Allow over-equalization', 'b']]],
    ['Performance (dB)', [['startCN', 'C/N at start'], ['startCTB', 'CTB at start'], ['startCSO', 'CSO at start'], ['minCN', 'Minimum C/N'], ['minCTB', 'Minimum CTB'], ['minCSO', 'Minimum CSO'],
      ['cnAdd', 'C/N addition factor'], ['ctbAdd', 'CTB addition factor'], ['ctbDerate', 'CTB derate (dB/dB)'], ['csoAdd', 'CSO addition factor'], ['csoDerate', 'CSO derate (dB/dB)']]],
    ['Powering', [['psVolts', 'Supply voltage (V)'], ['psMaxAmps', 'Supply capacity (A)']]],
  ];
  const specValue = (type, raw) => (type === 'n' ? (raw.trim() === '' ? '' : Number(raw)) : raw.trim());
  const specChanged = () => recalc();

  function openSpecs(tab = 'parameters') {
    const body = el('div');
    const names = { parameters: 'Parameters', cables: 'Cables', actives: 'Actives', taps: 'Taps', couplers: 'Couplers' };
    const draw = t => body.replaceChildren(
      el('div', { class: 'spec-tabs', role: 'tablist' }, Object.entries(names).map(([k, label]) =>
        el('button', { type: 'button', role: 'tab', class: k === t ? 'on' : null, 'aria-selected': String(k === t), onclick: () => draw(k) }, label))),
      t === 'parameters' ? paramForm() : specTable(t));
    draw(tab);
    openModal(`Specs: ${state.specs.name || 'untitled'}`, body, [btn('Save specs file', cmdSaveSpecs), btn('Done', closeModal, 'primary')]);
  }
  function specTable(t) {
    const cols = SPEC_COLS[t];
    const list = state.specs[t];
    const tbody = el('tbody');
    const redraw = () => tbody.replaceChildren(...list.map((item, i) => el('tr', {},
      cols.map(([k, label, type, w]) => el('td', {}, type === 'b'
        ? el('input', { type: 'checkbox', id: `s-${t}-${i}-${k}`, 'aria-label': `${label} row ${i + 1}`, checked: yes(item[k]), onchange: e => { item[k] = e.target.checked; specChanged(); } })
        : el('input', { id: `s-${t}-${i}-${k}`, 'aria-label': `${label} row ${i + 1}`, value: item[k] == null ? '' : item[k], size: w, spellcheck: 'false',
          onchange: e => { item[k] = specValue(type, e.target.value); specChanged(); } }))),
      el('td', {}, el('button', { type: 'button', class: 'x', title: 'Delete row', 'aria-label': `Delete row ${i + 1}`, onclick: () => { list.splice(i, 1); redraw(); specChanged(); } }, '×')))));
    redraw();
    return el('div', {},
      el('div', { class: 'scroll' }, el('table', { class: 'spec' }, el('thead', {}, el('tr', {}, cols.map(c => el('th', {}, c[1])), el('th', {}))), tbody)),
      el('p', {}, btn('Add row', () => { list.push(Object.fromEntries(cols.map(([k, , ty]) => [k, ty === 'b' ? false : '']))); redraw(); })));
  }
  function paramForm() {
    const p = P();
    const field = ([k, label, type]) => el('label', { class: 'field' }, el('span', {}, label), type === 'b'
      ? el('input', { type: 'checkbox', id: `p-${k}`, checked: yes(p[k]), onchange: e => { p[k] = e.target.checked; specChanged(); } })
      : el('input', { id: `p-${k}`, value: p[k] == null ? '' : p[k], spellcheck: 'false', onchange: e => { p[k] = specValue(type === 't' ? 't' : 'n', e.target.value); specChanged(); } }));
    return el('div', { class: 'params' },
      el('fieldset', {}, el('legend', {}, 'Spec set'), el('label', { class: 'field name' }, el('span', {}, 'Name'),
        el('input', { id: 'p-name', value: state.specs.name || '', spellcheck: 'false', onchange: e => { state.specs.name = e.target.value.trim().toUpperCase(); specChanged(); } }))),
      PARAM_GROUPS.map(([title, fields]) => el('fieldset', {}, el('legend', {}, title), fields.map(field))));
  }

  function cmdHelp() {
    const rowsN = [
      ['11', 'Active ID from the Actives spec (one per node). LE IDs 11 / 21 22 / 31 32 33 carry their cascade position'],
      ['[26]  (26)  {26}', '4-port, 2-port and 8-port tap of value 26 (up to 4 taps per node)'],
      ['[*]  (*)  {*}', 'Auto tap: the highest value that meets the tap window, the minimums and the max return level'],
      ['8[3]', 'Coupler ID 8 feeding branch 3 (thru leg continues, tap leg feeds the branch). Typing it creates branch 3'],
      ['-8[3]', 'Reversed coupler: tap leg continues downstream, thru leg feeds the branch'],
      ['*[3]', 'Auto coupler: the lowest thru loss that still feeds both legs'],
      ['PS', 'Power supply at this node'],
    ];
    const keys = [
      ['Esc then 1–9', 'Run the numbered toolbar command (the numbers change with the mode)'],
      ['↑ ↓ Enter Tab', 'Move between lines and cells. A line is recalculated when you leave the cell'],
      ['Ctrl+Z', 'Undo the last network change'],
    ];
    const table = list => el('table', { class: 'report notation' }, el('tbody', {}, list.map(([a, b]) => el('tr', {}, el('td', {}, a), el('td', {}, b)))));
    openModal('Notation and keys', el('div', {},
      el('p', {}, 'Each line is a node (a pole or pedestal). Cable, feet and house count describe the span arriving at the node. Levels show the signal after that span and before any equipment. Equipment at a node is applied in order: active, taps, couplers.'),
      table(rowsN), el('p', {}), table(keys), el('p', {}),
      el('p', {}, 'The sample specs are illustrative placeholders. Replace them with your manufacturers’ datasheet values under Specs before designing real plant.')),
    [btn('Close', closeModal, 'primary')]);
  }

  // ---------- menus ----------
  const MENUS = [
    ['File', [['New network', cmdNew], ['Open network or specs…', () => $('#file-input').click()], ['Save network', cmdSaveNet], ['Save specs', cmdSaveSpecs], ['Load sample', cmdSample]]],
    ['Mode', [['Design', () => setMode('design')], ['Entry', () => setMode('entry')], ['Powering', () => setMode('powering')]]],
    ['Specs', [['Parameters', () => openSpecs('parameters')], ['Cables', () => openSpecs('cables')], ['Actives', () => openSpecs('actives')], ['Taps', () => openSpecs('taps')], ['Couplers', () => openSpecs('couplers')]]],
    ['Tools', [['Lock auto selections', cmdLock, 'Esc 1'], ['Set all taps to auto', cmdUnlock], ['Carry active', cmdCarry, 'Esc 3'], ['Test network', cmdTest, 'Esc 6'], ['Optimize power supply…', cmdOptimize], ['Undo', undo, 'Ctrl+Z']]],
    ['Reports', [['Bill of materials', () => showReport('bom')], ['Active report', () => showReport('active')], ['Network tap report', () => showReport('tap')], ['Performance distribution', () => showReport('perf')], ['Power supply report', () => showReport('power')], ['Network test', cmdTest]]],
    ['Help', [['Notation and keys', cmdHelp]]],
  ];
  function closeMenus() { document.querySelectorAll('.dropdown').forEach(d => { d.hidden = true; }); }
  function renderMenus() {
    $('#menus').replaceChildren(...MENUS.map(([name, items]) => {
      const dd = el('div', { class: 'dropdown', role: 'menu', hidden: true }, items.map(([label, fn, key]) =>
        el('button', { type: 'button', role: 'menuitem', onmousedown: pd, onclick: () => { closeMenus(); run(fn); } }, el('span', {}, label), key ? el('kbd', {}, key) : null)));
      return el('div', { class: 'menu' }, el('button', { type: 'button', 'aria-haspopup': 'menu', onmousedown: pd,
        onclick: () => { const open = dd.hidden; closeMenus(); dd.hidden = !open; } }, name), dd);
    }));
  }
  document.addEventListener('click', e => { if (!e.target.closest('.menu')) closeMenus(); });

  // ---------- start ----------
  const fresh = load();
  renderMenus();
  clampRow();
  recalc();
  selectRow(state.row);
  if (fresh) flash('Sample network loaded with illustrative specs. Help explains the notation');
})();
