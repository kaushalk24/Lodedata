'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = async (url, opts) => {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error((await r.text()).slice(0, 400));
  const t = r.headers.get('content-type') || '';
  return t.includes('json') ? r.json() : r.text();
};
const esc = s => String(s ?? '').replace(/[&<>"]/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const msg = m => { $('#stMsg').textContent = m; if (m) setTimeout(() => {
  if ($('#stMsg').textContent === m) $('#stMsg').textContent = ''; }, 4000); };

const S = {
  nid: null, net: null, scr: null, mode: 'design',
  branch: 1,          // the branch page on screen -- one at a time, as in the program
  row: 0, col: 0, buffer: null,
  dot: false,         // the "." prefix that turns a nav key into a branch move
};

// rows of the branch currently on screen
function pageRows() {
  if (!S.scr) return [];
  return S.scr.rows.filter(r => r.branch === S.branch);
}
function branchMeta(n) {
  return (S.scr && S.scr.branches.find(b => b.number === n)) || null;
}

// ---------------------------------------------------------------- columns
// Each mode shows the same node lines with a different set of columns, as the
// Design, Entry and Power screens do.
function columns() {
  const f = (S.scr && S.scr.frequencies) || [];
  const lvl = f.map((mhz, i) => ({ key: 'lvl:' + i, head: String(mhz).replace('.0', ''),
                                   cls: '', edit: false }));
  const common = [
    { key: 'ftg', head: 'ftg', edit: true },
    { key: 'hc', head: 'hc', edit: true },
    { key: 'cab', head: 'cab', edit: true },
    { key: 'lv', head: 'lv', edit: true },
  ];
  if (S.mode === 'entry') {
    return [
      { key: 'branch', head: 'Branch' }, { key: 'node', head: 'Node' },
      ...common,
      { key: 'tsg', head: 'TSG', edit: true },
      { key: 'map', head: 'Map', cls: 'l', edit: true },
      { key: 'loc', head: 'Loc', cls: 'l', edit: true },
      { key: 'cplr0', head: '[Branch1]', cls: 'l', edit: true },
      { key: 'cplr1', head: '[Branch2]', cls: 'l', edit: true },
      { key: 'ampname', head: 'Amp Name', cls: 'l', edit: true },
    ];
  }
  if (S.mode === 'power') {
    return [
      { key: 'node', head: 'Node' },
      { key: 'volt', head: 'Volt' }, { key: 'current', head: 'Current' },
      ...common,
      { key: 'amp', head: 'amp', edit: true },
      { key: 'ampname', head: 'amp ID#', cls: 'l', edit: true },
      { key: 'supply', head: 'supply', edit: true },
      { key: 'cplr0', head: 'cplr[branch]', cls: 'l', edit: true },
      { key: 'cplr1', head: 'cplr[branch]', cls: 'l', edit: true },
    ];
  }
  return [
    { key: 'node', head: 'Node' },
    ...lvl,
    ...common,
    { key: 'amp', head: 'amp', edit: true },
    { key: 'tsg', head: 'TSG', edit: true },
    { key: 'tap0', head: 'tap1', edit: true }, { key: 'tap1', head: 'tap2', edit: true },
    { key: 'tap2', head: 'tap3', edit: true }, { key: 'tap3', head: 'tap4', edit: true },
    { key: 'cplr0', head: 'cplr[branch]', cls: 'l', edit: true },
    { key: 'cplr1', head: 'cplr[branch]', cls: 'l', edit: true },
  ];
}

function cellText(r, c) {
  if (c.key.startsWith('lvl:')) {
    const v = r.levels[+c.key.slice(4)];      // index into the frequency order
    return v === undefined ? '' : v.toFixed(2);
  }
  switch (c.key) {
    case 'branch': return r.branch;
    case 'node': return r.node;
    case 'ftg': return r.ftg || (r.ftg === 0 ? '0' : '');
    case 'hc': return r.hc || '';
    case 'cab': return r.cab || (r.cab_name ? r.cab : '');
    case 'lv': return r.lv || '';
    case 'tsg': return r.tsg || '';
    case 'amp': return r.amp || '';
    case 'ampname': return r.amp_label ? `[${r.amp_label}]` : (r.amp_name || '');
    case 'map': return r.map || '';
    case 'loc': return r.loc || '';
    case 'supply': return r.supply || '';
    case 'volt': return r.volts === null ? '' : r.volts.toFixed(2);
    case 'current': return r.current ? r.current.toFixed(2) : '0.00';
    case 'tap0': case 'tap1': case 'tap2': case 'tap3':
      return r.taps[+c.key.slice(3)] || '';
    case 'cplr0': case 'cplr1':
      return r.couplers[+c.key.slice(4)] || '';
  }
  return '';
}

// ---------------------------------------------------------------- render
function renderGrid() {
  const cols = columns();
  const rows = pageRows();
  const thead = $('#grid thead'), tbody = $('#grid tbody');
  thead.innerHTML = '<tr><th class="gutter"></th>' +
    cols.map(c => `<th class="${c.cls || ''}">${esc(c.head)}</th>`).join('') +
    '<th class="l"></th></tr>';

  if (!S.net) { tbody.innerHTML = ''; return; }
  if (!hasSpecs()) {
    tbody.innerHTML = `<tr><td class="gutter"></td><td class="l" colspan="${cols.length + 1}"
      style="color:var(--yellow);padding:18px 10px;white-space:normal;line-height:1.6">
      No spec file attached.<br><br>
      Nothing is loaded when a network is opened and nothing carries over from
      another network: every level, loss, part number and powering figure comes
      from the spec files.<br><br>
      <span style="color:var(--green)">Spec Edit &rarr; Attach spec set</span>
      &nbsp;to select a <b>.par .atv .tap .cpr .cbl</b> set,
      or <span style="color:var(--green)">Spec Edit &rarr; Sample specs</span>
      to try the program out.</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map((r, i) => {
    const cls = [r.severity, i === S.row ? 'onrow' : ''].filter(Boolean).join(' ');
    const tds = cols.map((c, j) => {
      const cur = (i === S.row && j === S.col) ? ' cur' : '';
      let text = cellText(r, c);
      if (i === S.row && j === S.col && S.buffer !== null) text = S.buffer + '_';
      let extra = '';
      if (c.key === 'cab' && r.cab >= 100) extra = ' series1';
      if (c.key === 'ampname') extra = ' amp';
      return `<td class="${c.cls || ''}${cur}${extra}" data-r="${i}" data-c="${j}">${esc(text)}</td>`;
    }).join('');
    return `<tr class="${cls}"><td class="gutter">${esc(r.gutter)}</td>${tds}<td></td></tr>`;
  }).join('');

  $$('#grid tbody td[data-r]').forEach(td => td.onclick = () => {
    S.row = +td.dataset.r; S.col = +td.dataset.c; S.buffer = null;
    renderGrid(); renderInfo();
  });
  renderInfo();
}

function renderInfo() {
  const r = pageRows()[S.row] || null;
  const box = $('#info');
  if (!r) { box.textContent = ''; return; }
  const t = (S.scr && S.scr.totals) || {};
  box.textContent =
    `${r.branch}.${r.node}\n` +
    `${r.address || 'No Address'}\n` +
    `${r.cab_name || 'no cable'}\n` +
    `Distance from previous node:   ${r.ftg}\n` +
    `Total distance to start:       ${r.cumulative_ft}\n` +
    `Housecounts this node:         ${r.hc}\n` +
    `Voltage / current:             ${r.volts === null ? '-' : r.volts.toFixed(1)} V  ${r.current.toFixed(2)} A\n` +
    (r.flags.length ? r.flags.map(f => `! ${f.message}`).join('\n') + '\n' : '') +
    `\nnodes ${t.nodes || 0}  taps ${t.taps || 0}  actives ${t.actives || 0}  ` +
    `homes ${t.homes || 0}  ${t.footage || 0} ft`;
  const m = branchMeta(S.branch);
  $('#stBranch').textContent =
    `Branch ${m ? m.position : 1} of ${(S.scr && S.scr.branches.length) || 1}`;
  $('#stFeeder').textContent = `Feeder ${r.branch}.${r.node}`;
}

// ---------------------------------------------------------------- screen menu
const MENUS = {
  design: [
    [['0', 'Alter', alter], ['1', 'Jump', jump], ['2', 'Forward', null],
     ['3', 'Carry', carry], ['4', 'Fwd2A', null], ['5', 'Test', test],
     ['6', 'WillWrk', null], ['7', 'AutoCpl', null], ['8', 'Recalc', recalc],
     ['9', 'Toggle', null], ['/', 'Distance', distance]],
    [['.0', 'Break', null], ['.1', 'Join', null], ['.2', 'BkFeed', null],
     ['.3', 'UnBkFd', null], ['.4', 'XFd2A', null], ['.5', 'MoveCpl', null],
     ['.6', 'XWillWk', null], ['.7', 'SetMDU', null], ['.8', 'RotTap', null],
     ['.9', 'Copy', null], ['.+', 'Name', nameAmp]],
    [['..0', 'SpcVvv', null], ['..1', 'Xspec', null], ['..2', 'FwdFd', null],
     ['..3', 'UnFFd', null], ['..4', 'BrLabel', null], ['..5', 'Dsmry', dsummary],
     ['..6', 'Clear', clearCell], ['..7', 'CAwBF', null], ['..8', 'XCAmp', null],
     ['..9', 'LckDStr', null], ['..+', 'Notes', notes]],
  ],
  entry: [
    [['-0', 'Fd/Rev', null], ['-1', 'Jump', jump], ['-2', 'Ins/Ex', insertNode],
     ['-3', 'Return', null], ['-4', 'NetInit', netInit], ['-5', 'ChBrSt', null],
     ['-6', 'CrAfTh', null], ['-7', 'CrAfLst', null], ['-8', 'DelBr', delBranch],
     ['-9', 'SetMDU', null]],
    [['-.4', 'Label', null], ['-.6', 'New', insertNode], ['-.9', 'DpMDU', null],
     ['-.+', 'Name', nameAmp], ['-..+', 'Notes', notes]],
    [],
  ],
  power: [
    [['0', 'Alter', alter], ['1', 'Jump', jump], ['2', 'Clear', clearCell],
     ['3', 'CarryPS', null], ['4', 'Recalc', recalc], ['5', 'Test', test],
     ['6', 'Locate', null], ['7', 'BOM', () => openReport('bom')],
     ['8', 'Calc', recalc], ['9', 'NodeNIU', null], ['/', 'Distance', distance]],
    [['.0', 'Break', null], ['.1', 'Join', null], ['.2', 'ApArea', null],
     ['.3', 'CarryLE', null], ['.4', 'Report', () => openReport('powering')],
     ['.5', 'CarCplr', null], ['.6', 'TstArea', null], ['.7', 'Loc Mnu', null],
     ['.8', 'NIUtest', null], ['.9', 'Br NIU', null], ['.+', 'Name', nameAmp]],
    [['..0', 'SpcVvv', null], ['..1', 'Xspec', null], ['..2', 'Append', null],
     ['..3', 'Unapnd', null], ['..4', 'Trans', null], ['..7', 'SetMDU', null],
     ['..+', 'Notes', notes], ['..9', 'DS NIU', null]],
  ],
};

function renderMenu() {
  const rows = MENUS[S.mode];
  $('#screenmenu').innerHTML = rows.map((row, i) =>
    `<div class="smrow r${i + 1}">` + (row.length
      ? row.map(([k, label], j) =>
          `<span class="smkey" data-m="${i}" data-i="${j}">${esc(k)} ${esc(label)}</span>`).join('')
      : '<span class="smkey empty">&nbsp;</span>') + '</div>').join('');
  $$('.smkey[data-m]').forEach(el => el.onclick = () => {
    const fn = MENUS[S.mode][+el.dataset.m][+el.dataset.i][2];
    if (fn) fn(); else msg(`${el.textContent.trim()} is not implemented yet`);
  });
  document.body.className = 'mode-' + S.mode;
  $('#app').className = 'mode-' + S.mode;
}

// ---------------------------------------------------------------- editing
const EDIT_ORDER = ['ftg', 'hc', 'cab', 'lv'];

function curCol() { return columns()[S.col]; }
function curRow() { return pageRows()[S.row]; }

async function commitBuffer(advance) {
  const c = curCol(), r = curRow();
  if (!c || !r || S.buffer === null) return;
  const val = S.buffer.trim();
  S.buffer = null;
  const body = {};
  if (['ftg', 'hc', 'cab', 'lv', 'tsg', 'amp', 'supply'].includes(c.key)) {
    const n = val === '' ? 0 : Number(val);
    if (Number.isNaN(n)) { msg('not a number'); renderGrid(); return; }
    if (c.key === 'supply') body.supply_volts = n;
    else if (c.key === 'amp') {
      if (!n) { body.clear_amp = true; }
      else {
        const part = pickActiveById(n);
        if (!part) { msg(`no active with ID ${n} in the spec set`); renderGrid(); return; }
        body.amp = n; body.amp_part = part.id;
      }
    } else if (c.key === 'cab') {
      body.cab = n;
      const part = pickCableById(n);
      body.cab_part = part ? part.id : null;
      if (!part && n) msg(`cable ${n} is not in the spec set`);
    } else body[c.key] = n;
  } else if (['map', 'loc', 'ampname'].includes(c.key)) {
    body[c.key === 'ampname' ? 'amp_label' : c.key] = val;
  } else { renderGrid(); return; }

  await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body) });
  await refresh();
  if (advance) moveToNextField();
}

function moveToNextField() {
  const cols = columns();
  const c = cols[S.col];
  const i = EDIT_ORDER.indexOf(c && c.key);
  if (i >= 0 && i < EDIT_ORDER.length - 1) {
    const next = cols.findIndex(x => x.key === EDIT_ORDER[i + 1]);
    if (next >= 0) { S.col = next; renderGrid(); return; }
  }
  // past the last field: drop to the next node line, as Entry does
  S.row = Math.min(S.row + 1, pageRows().length - 1);
  S.col = cols.findIndex(x => x.key === 'ftg');
  renderGrid();
}

// ---------------------------------------------------------------- keyboard
document.addEventListener('keydown', async ev => {
  if (!$('#modal').hidden) return;
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
  const cols = columns();
  const k = ev.key;

  const n = pageRows().length;
  if (k === 'ArrowUp') {
    if (S.dot) S.row = 0; else S.row = Math.max(0, S.row - 1);
    S.buffer = null; S.dot = false;
  }
  else if (k === 'ArrowDown') {
    if (S.dot) S.row = n - 1; else S.row = Math.min(n - 1, S.row + 1);
    S.buffer = null; S.dot = false;
  }
  else if (k === 'ArrowRight') {
    // ". →" moves to the branch beginning on the highlighted node
    if (S.dot) { S.dot = false; ev.preventDefault(); enterBranch(); return; }
    S.col = Math.min(cols.length - 1, S.col + 1); S.buffer = null;
  }
  else if (k === 'ArrowLeft') {
    if (S.dot) { S.dot = false; ev.preventDefault(); returnToParent(); return; }
    S.col = Math.max(0, S.col - 1); S.buffer = null;
  }
  else if (k === 'PageUp') {
    ev.preventDefault();
    if (S.dot) { S.dot = false; gotoBranch(S.scr.branches[0].number); }
    else stepBranch(-1);
    return;
  }
  else if (k === 'PageDown') {
    ev.preventDefault();
    if (S.dot) { S.dot = false; gotoBranch(S.scr.branches.at(-1).number); }
    else stepBranch(1);
    return;
  }
  else if (k === 'Home') { S.row = 0; }
  else if (k === 'End') { S.row = n - 1; }
  else if (k === '.') {
    // typing: the field separator. Otherwise the prefix for a branch move.
    if (S.buffer !== null) { ev.preventDefault(); await commitBuffer(true); return; }
    S.dot = true; msg('. — press an arrow or Page key for a branch move');
    ev.preventDefault(); return;
  }
  else if (k === 'Enter') {
    ev.preventDefault();
    if (S.buffer !== null) { await commitBuffer(false); }
    else await openCell();
    return;
  }
  else if (/^[0-9]$/.test(k) || (k === '-' && S.buffer === null)) {
    const c = cols[S.col];
    if (c && c.edit) { S.buffer = (S.buffer || '') + k; }
  }
  else if (k === 'Backspace') {
    ev.preventDefault();
    if (S.buffer) S.buffer = S.buffer.slice(0, -1);
    else if (S.buffer === '') S.buffer = null;
  }
  else if (k === 'Escape') { S.buffer = null; S.dot = false; }
  else if (k === 'Insert') { ev.preventDefault(); await insertNode(); return; }
  else if (k === 'Delete') { ev.preventDefault(); await deleteNode(); return; }
  else return;
  ev.preventDefault();
  renderGrid();
});

// opening a cell: taps, couplers and actives get a picker
async function openCell() {
  const c = curCol(), r = curRow();
  if (!c || !r) return;
  if (c.key.startsWith('tap')) return pickTap(+c.key.slice(3));
  if (c.key.startsWith('cplr')) return pickCoupler(+c.key.slice(4));
  if (c.key === 'amp') return pickActive();
  if (c.key === 'cab') return pickCable();
  if (c.key === 'ampname') return nameAmp();
  msg('nothing to open on this column');
}

function gotoBranch(n, node) {
  if (!branchMeta(n)) return;
  S.branch = n; S.buffer = null;
  const rows = pageRows();
  S.row = node ? Math.max(0, rows.findIndex(r => r.node === node)) : 0;
  const cols = columns();
  S.col = Math.max(1, cols.findIndex(c => c.key === 'ftg'));
  renderGrid();
  const m = branchMeta(n);
  msg(`branch ${n}${m && m.parent_branch ? ` — from ${m.parent_branch}.${m.parent_node}` : ' — the feeder'}`);
}
function stepBranch(delta) {
  const list = S.scr.branches.map(b => b.number);
  const i = list.indexOf(S.branch);
  const next = list[Math.min(list.length - 1, Math.max(0, i + delta))];
  if (next === S.branch) { msg(delta < 0 ? 'first branch' : 'last branch'); return; }
  gotoBranch(next);
}
function enterBranch() {
  const r = curRow();
  if (!r || !r.couplers.length) { msg('no branch begins on this node'); return; }
  // the branch number is what sits inside the brackets
  const m = /[[({<](\d+)[\])}>]/.exec(r.couplers[0]);
  if (!m) { msg('no branch on this node'); return; }
  gotoBranch(+m[1]);
}
function returnToParent() {
  const m = branchMeta(S.branch);
  if (!m || !m.parent_branch) { msg('already on the feeder'); return; }
  gotoBranch(m.parent_branch, m.parent_node);
}

// ---------------------------------------------------------------- pickers
function hasSpecs() {
  const l = (S.net && S.net.library) || {};
  return Object.keys(l.cables || {}).length + Object.keys(l.taps || {}).length
       + Object.keys(l.actives || {}).length + Object.keys(l.passives || {}).length > 0;
}
const libTable = t => Object.values((S.net && S.net.library[t]) || {});
const pickCableById = n => libTable('cables')[n] || null;
const pickActiveById = n => libTable('actives')[n % libTable('actives').length] || null;

function modal(html) {
  $('#modalbox').innerHTML = html;
  $('#modal').hidden = false;
  const c = $('#mClose'); if (c) c.onclick = closeModal;
}
function closeModal() { $('#modal').hidden = true; }
$('#modal').onclick = e => { if (e.target.id === 'modal') closeModal(); };

function chooser(title, items, onPick, note) {
  modal(`<h2>${esc(title)}</h2>${note ? `<p class="hint">${esc(note)}</p>` : ''}
    <table><tbody>${items.map((it, i) =>
      `<tr data-i="${i}"><td>${esc(it.label)}</td><td>${esc(it.detail || '')}</td></tr>`).join('')}
    </tbody></table>
    <div class="row"><button id="mClose">Cancel</button>
      <button id="mNone">Clear this cell</button></div>`);
  $$('#modalbox tr[data-i]').forEach(tr => tr.onclick = async () => {
    closeModal(); await onPick(items[+tr.dataset.i]);
  });
  $('#mNone').onclick = async () => { closeModal(); await onPick(null); };
}

async function pickTap(slot) {
  const r = curRow();
  const taps = libTable('taps').sort((a, b) =>
    b.tap_value_db - a.tap_value_db || a.ports - b.ports);
  chooser(`Tap for node ${r.branch}.${r.node}, slot ${slot + 1}`,
    taps.map(t => ({ id: t.id, label: `${t.name}`,
      detail: `${t.ports} port · ${t.tap_value_db} dB · insertion ${t.through_loss.length ? t.through_loss.at(-1)[1] : '?'} dB` })),
    async pick => {
      await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}/tap`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot, part_id: pick ? pick.id : null }) });
      await refresh();
    }, 'Tap values are drawn in the bracket style of their port count: /2/ [4] {6} <8>');
}

async function pickCoupler(slot) {
  const r = curRow();
  const items = libTable('passives').map(p => ({ id: p.id, label: p.name,
    detail: `legs ${p.port_losses.map(v => v + ' dB').join(' / ')}` }));
  chooser(`Coupler for node ${r.branch}.${r.node}`, items, async pick => {
    await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}/coupler`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot, part_id: pick ? pick.id : null }) });
    await refresh();
    msg(pick ? 'coupler placed — it starts a new branch; press . → to go into it'
             : 'coupler and its branch removed');
  }, 'Placing a coupler creates the branch it feeds.');
}

async function pickActive() {
  const r = curRow();
  const items = libTable('actives').map(a => ({ id: a.id, label: a.name,
    detail: `${a.kind} · in ${a.in_forward_high}/${a.in_forward_low} · out ${a.out_forward_high}/${a.out_forward_low}` }));
  chooser(`Active for node ${r.branch}.${r.node}`, items, async pick => {
    await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pick ? { amp: 11, amp_part: pick.id } : { clear_amp: true }) });
    await refresh();
  });
}

async function pickCable() {
  const r = curRow();
  const items = libTable('cables').map((c, i) => ({ id: c.id, idx: i, label: c.name,
    detail: `${c.attenuation.length ? c.attenuation.at(-1)[1] + ' dB/100ft' : ''} · loop ${c.loop_resistance_ohm_per_1000ft} Ω/1000ft` }));
  chooser(`Cable for node ${r.branch}.${r.node}`, items, async pick => {
    await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pick ? { cab: pick.idx, cab_part: pick.id } : { cab: 0, cab_part: null }) });
    await refresh();
  }, 'Even cable IDs are aerial, odd are underground.');
}

// ---------------------------------------------------------------- commands
async function insertNode() {
  const r = curRow();
  await api(`/api/networks/${S.nid}/branches/${r ? r.branch : 1}/nodes`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ after: r ? r.node : 0 }) });
  await refresh(); S.row = Math.min(S.row + 1, pageRows().length - 1); renderGrid();
  msg('node inserted');
}
async function deleteNode() {
  const r = curRow(); if (!r) return;
  await api(`/api/networks/${S.nid}/branches/${r.branch}/nodes/${r.node}`,
    { method: 'DELETE' });
  await refresh(); msg('node deleted');
}
async function delBranch() {
  const r = curRow(); if (!r || r.branch === 1) { msg('the feeder cannot be deleted'); return; }
  if (!confirm(`Delete branch ${r.branch} and everything on it?`)) return;
  const parent = branchMeta(r.branch);
  await api(`/api/networks/${S.nid}/branches/${r.branch}`, { method: 'DELETE' });
  await refresh();
  gotoBranch(parent && parent.parent_branch ? parent.parent_branch : 1);
  msg('branch deleted');
}
function alter() { openCell(); }
function jump() {
  const v = prompt('Jump to node (branch.node)', `${S.branch}.1`); if (!v) return;
  const [b, n] = v.split('.').map(Number);
  if (!branchMeta(b)) { msg('no such branch'); return; }
  gotoBranch(b, n || 1);
}
function carry() {
  const r = curRow(), c = curCol(); if (!r || !c) return;
  msg(`Carry: hold ${c.head} down the branch — not implemented yet`);
}
function distance() {
  const r = curRow(); if (!r) return;
  msg(`${r.branch}.${r.node}: ${r.cumulative_ft} ft from the start of the network`);
}
function test() {
  const bad = S.scr.rows.filter(r => r.severity);
  if (!bad.length) { msg('Test: no errors'); return; }
  modal(`<h2>Test — ${bad.length} node(s) flagged</h2>
    <table><tbody>${bad.map(r => `<tr><td>${r.branch}.${r.node}</td>
      <td style="color:${r.severity === 'red' ? '#b00' : '#a70'}">${esc(r.flags.map(f => f.message).join('; '))}</td></tr>`).join('')}</tbody></table>
    <div class="row"><button id="mClose" class="primary">Close</button></div>`);
}
function dsummary() {
  const t = S.scr.totals;
  modal(`<h2>Downstream summary</h2><table><tbody>${
    Object.entries(t).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')
  }</tbody></table><div class="row"><button id="mClose" class="primary">Close</button></div>`);
}
async function recalc() { await refresh(); msg('recalculated'); }
async function clearCell() {
  const c = curCol(), r = curRow(); if (!c || !r) return;
  if (c.key.startsWith('tap')) return pickTap(+c.key.slice(3));
  S.buffer = ''; await commitBuffer(false);
}
async function nameAmp() {
  const r = curRow(); if (!r) return;
  const v = prompt('Amplifier / power supply name (Amplifier Definition)', r.amp_label || '');
  if (v === null) return;
  await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amp_label: v }) });
  await refresh();
}
async function notes() {
  const r = curRow(); if (!r) return;
  const v = prompt('Note at this node', '');
  if (v === null) return;
  await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note: v }) });
  await refresh(); msg('note saved');
}
function netInit() {
  const n = S.net;
  modal(`<h2>Network Initialization</h2>
    <p>The levels and characteristics the network starts from.</p>
    <label>Launch level at the forward high frequency (dBmV)</label>
    <input id="niLevel" type="number" step="0.1" value="${n.source_dbmv}">
    <label>Launch tilt (dB)</label>
    <input id="niTilt" type="number" step="0.1" value="${n.source_tilt_db}">
    <label>Forward high / low (MHz)</label>
    <div style="display:flex;gap:6px">
      <input id="niFh" type="number" value="${n.parameters.forward_high_mhz}">
      <input id="niFl" type="number" value="${n.parameters.forward_low_mhz}"></div>
    <label>Return high / low (MHz)</label>
    <div style="display:flex;gap:6px">
      <input id="niRh" type="number" value="${n.parameters.return_high_mhz}">
      <input id="niRl" type="number" value="${n.parameters.return_low_mhz}"></div>
    <label>Power supply voltage</label>
    <input id="niPs" type="number" value="${n.supply_volts}">
    <div class="row"><button class="primary" id="niOk">OK</button>
      <button id="mClose">Cancel</button></div>`);
  $('#niOk').onclick = async () => {
    await api(`/api/networks/${S.nid}`, { method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_dbmv: +$('#niLevel').value, source_tilt_db: +$('#niTilt').value,
        supply_volts: +$('#niPs').value,
        parameters: { forward_high_mhz: +$('#niFh').value, forward_low_mhz: +$('#niFl').value,
                      return_high_mhz: +$('#niRh').value, return_low_mhz: +$('#niRl').value } }) });
    closeModal(); await reload(); msg('network initialised');
  };
}

async function openReport(kind) {
  const rows = await api(`/api/networks/${S.nid}/reports/${kind}`);
  const cols = rows.length ? Object.keys(rows[0]) : [];
  modal(`<h2>${kind === 'bom' ? 'Bill of Materials' : kind === 'powering' ? 'Powering report' : 'Level sheet'}</h2>
    <table><thead><tr>${cols.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
    <tbody>${rows.map(r => `<tr>${cols.map(c => `<td>${esc(r[c])}</td>`).join('')}</tr>`).join('')}</tbody></table>
    <div class="row"><a class="button" href="/api/networks/${S.nid}/reports/${kind}?format=csv"
       download><button>Download CSV</button></a>
      <button id="mClose" class="primary">Close</button></div>`);
}

// ---------------------------------------------------------------- menus
const MENU_ACTIONS = {
  file: [['New network', newNetwork], ['Open network', openNetwork],
         ['Import .ntw', importNtw]],
  mode: [['Design', () => setMode('design')], ['Entry', () => setMode('entry')],
         ['Power', () => setMode('power')]],
  branch: [['Next branch  (Page Down)', () => stepBranch(1)],
           ['Previous branch  (Page Up)', () => stepBranch(-1)],
           ['Into the branch on this node  (. \u2192)', enterBranch],
           ['Back to the parent branch  (. \u2190)', returnToParent],
           ['Branch list', branchList]],
  spec: [['Attach spec set', attachSpec], ['Sample specs', sampleSpecs],
         ['View library', viewLibrary]],
  reports: [['Level sheet', () => openReport('levels')],
            ['Bill of Materials', () => openReport('bom')],
            ['Powering', () => openReport('powering')]],
  test: [['Test network', test], ['Downstream summary', dsummary]],
  edit: [['Insert node', insertNode], ['Delete node', deleteNode],
         ['Delete branch', delBranch]],
  tools: [['Network Initialization', netInit]],
  view: [['Recalculate', recalc]],
  misc: [['Name amplifier', nameAmp], ['Note', notes]],
  global: [['Network Initialization', netInit]],
  help: [['Keys', showHelp]],
};
$$('.menubar .mi').forEach(mi => mi.onclick = () => {
  const items = MENU_ACTIONS[mi.dataset.menu];
  if (!items) { msg('not implemented'); return; }
  modal(`<h2>${esc(mi.textContent)}</h2><table><tbody>${
    items.map((it, i) => `<tr data-i="${i}"><td>${esc(it[0])}</td></tr>`).join('')
  }</tbody></table><div class="row"><button id="mClose">Close</button></div>`);
  $$('#modalbox tr[data-i]').forEach(tr => tr.onclick = () => {
    closeModal(); items[+tr.dataset.i][1]();
  });
});

function branchList() {
  const items = S.scr.branches.map(b => ({ n: b.number,
    label: `Branch ${b.number}${b.label ? ' — ' + b.label : ''}`,
    detail: b.parent_branch ? `${b.nodes} nodes · from ${b.parent_branch}.${b.parent_node} · ${b.style}`
                            : `${b.nodes} nodes · feeder` }));
  chooser('Branches', items, pick => { if (pick) gotoBranch(pick.n); });
}

function showHelp() {
  modal(`<h2>Keys</h2>
   <p>Arrow keys move the cursor. Type digits to enter a value.
   <b>.</b> commits and steps to the next field, as it does in Entry mode:
   <code>107 . 2 . 0</code> enters 107 feet, 2 houses, cable 0.
   <b>Enter</b> commits, or opens a picker on the tap, coupler, amp and cable
   columns. <b>Insert</b> adds a node, <b>Delete</b> removes one,
   <b>Esc</b> abandons what you were typing.</p>
   <p>One branch is on screen at a time, as in the program.
   <b>Page Down</b> / <b>Page Up</b> move between branches,
   <b>. Page Down</b> / <b>. Page Up</b> jump to the last or first.
   <b>. &rarr;</b> goes into the branch beginning on the highlighted node and
   <b>. &larr;</b> comes back to the parent. <b>. &uarr;</b> / <b>. &darr;</b>
   go to the top and bottom of the branch.</p>
   <p>The numbered bars are the screen menu — click them or use the menu bar.</p>
   <div class="row"><button id="mClose" class="primary">Close</button></div>`);
}

// ---------------------------------------------------------------- files
async function newNetwork() {
  const name = prompt('Name for the new network', 'lode-1'); if (!name) return;
  const d = await api('/api/networks', { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, sample_specs: false }) });
  await loadList(d.id); await open(d.id);
}
async function openNetwork() {
  const list = await api('/api/networks');
  chooser('Open network', list.map(n => ({ id: n.id, label: n.name, detail: n.updated })),
    async pick => { if (pick) { await open(pick.id); } });
}
function attachSpec() {
  modal(`<h2>Attach a spec set</h2>
    <p>Select all files of one Lode Data spec set — the
    <b>.par .atv .tap .cpr .cbl</b> files that share a base name. Nothing is
    loaded until you do: every level, loss and part number comes from them.</p>
    <input type="file" id="specFiles" multiple accept=".par,.atv,.tap,.cpr,.cbl,.prc,.per">
    <div class="row"><button class="primary" id="specGo">Attach</button>
      <button id="mClose">Cancel</button></div><pre id="specOut" style="display:none"></pre>`);
  $('#specGo').onclick = async () => {
    const files = $('#specFiles').files;
    if (!files.length) return;
    const fd = new FormData(); [...files].forEach(f => fd.append('files', f));
    const out = await api(`/api/networks/${S.nid}/library/spec`, { method: 'POST', body: fd });
    closeModal(); await reload();
    msg(`${out.library.name}: ${Object.keys(out.library.cables).length} cables, ` +
        `${Object.keys(out.library.taps).length} taps, ` +
        `${Object.keys(out.library.passives).length} couplers, ` +
        `${Object.keys(out.library.actives).length} actives`);
  };
}
async function sampleSpecs() {
  await api(`/api/networks/${S.nid}/library/sample`, { method: 'POST' });
  await reload(); msg('sample specs attached — samples only, not for real design');
}
function viewLibrary() {
  const lib = S.net.library;
  const sect = (t, cols) => `<h2 style="margin-top:14px">${t}</h2><table><thead><tr>${
    cols.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${
    Object.values(lib[t.toLowerCase()] || {}).map(p => `<tr>${
      cols.map(c => `<td>${esc(fmtLib(p, c))}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  modal(`<h2>${esc(lib.name || 'no spec set')}</h2>` +
    sect('Cables', ['name', 'loop', 'attenuation']) +
    sect('Taps', ['name', 'ports', 'value', 'insertion']) +
    sect('Passives', ['name', 'kind', 'legs']) +
    sect('Actives', ['name', 'kind', 'in', 'out', 'power']) +
    `<div class="row"><button id="mClose" class="primary">Close</button></div>`);
}
function fmtLib(p, c) {
  switch (c) {
    case 'name': return p.name;
    case 'loop': return p.loop_resistance_ohm_per_1000ft;
    case 'attenuation': return (p.attenuation || []).map(a => `${a[0]}:${a[1]}`).join('  ');
    case 'ports': return p.ports;
    case 'value': return p.tap_value_db;
    case 'insertion': return (p.through_loss || []).map(a => `${a[0]}:${a[1]}`).join('  ');
    case 'kind': return p.kind;
    case 'legs': return (p.port_losses || []).join(' / ');
    case 'in': return [p.in_forward_high, p.in_forward_low, p.in_return_high, p.in_return_low].join('/');
    case 'out': return [p.out_forward_high, p.out_forward_low, p.out_return_high, p.out_return_low].join('/');
    case 'power': return (p.power_draw || []).map(a => `${a[0]}V:${a[1]}A`).join(' ');
  }
  return '';
}
function importNtw() {
  modal(`<h2>Import a .ntw network file</h2>
    <p>The payload obfuscation is solved so the file can be read, but the record
    layout is not mapped yet — .ntw files hold no text, only indices into the
    spec files. This reports what the file is.</p>
    <input type="file" id="ntwFile" accept=".ntw">
    <div class="row"><button class="primary" id="ntwGo">Read</button>
      <button id="mClose">Cancel</button></div><pre id="ntwOut"></pre>`);
  $('#ntwGo').onclick = async () => {
    const f = $('#ntwFile').files[0]; if (!f) return;
    const fd = new FormData(); fd.append('file', f);
    const out = await api('/api/import/ntw', { method: 'POST', body: fd });
    $('#ntwOut').textContent = JSON.stringify(out, null, 2);
  };
}

// ---------------------------------------------------------------- lifecycle
function setMode(m) {
  S.mode = m; S.buffer = null;
  S.col = Math.max(1, columns().findIndex(c => c.key === 'ftg'));
  $('#selMode').value = m;
  $('#title').textContent =
    `Design Assistant - ${m === 'design' ? 'Design' : m === 'entry' ? 'Entry' : 'Power'} - ${S.net ? S.net.name : ''}`;
  renderMenu(); renderGrid();
}
async function refresh() {
  S.scr = await api(`/api/networks/${S.nid}/screen`);
  if (!branchMeta(S.branch)) S.branch = S.scr.branches.length ? S.scr.branches[0].number : 1;
  S.row = Math.max(0, Math.min(S.row, pageRows().length - 1));
  renderGrid();
}
async function reload() {
  S.net = await api(`/api/networks/${S.nid}`);
  $('#stSpecs').textContent = S.net.library.name || 'no spec file attached';
  await refresh();
}
async function open(id) {
  S.nid = id; S.row = 0; S.branch = 1;
  await reload(); setMode(S.mode);
  $('#selNet').value = id;
}
async function loadList(sel) {
  const list = await api('/api/networks');
  $('#selNet').innerHTML = list.map(n =>
    `<option value="${n.id}">${esc(n.name)}</option>`).join('');
  if (!list.length) return null;
  const id = sel && list.some(n => n.id === sel) ? sel : list[0].id;
  $('#selNet').value = id;
  return id;
}
$('#selNet').onchange = e => open(e.target.value);
$('#selMode').onchange = e => setMode(e.target.value);
$('#tbNew').onclick = newNetwork;
$('#tbOpen').onclick = openNetwork;
$('#tbSave').onclick = () => msg('saved');
$('#tbInsert').onclick = insertNode;
$('#tbDelete').onclick = deleteNode;

(async () => {
  let id = await loadList();
  if (!id) {
    const d = await api('/api/networks', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'lode-1', sample_specs: false }) });
    id = await loadList(d.id);
  }
  await open(id);
})();
