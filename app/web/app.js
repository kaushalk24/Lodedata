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
  // the line under the last node (levels through the last tap, and its port
  // output under the tap columns) is part of the Design screen only
  return S.scr.rows.filter(r => r.branch === S.branch && (!r.end || S.mode === 'design'));
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
    // the Power screen runs footage, houses, cable and level together as one
    // "ftg-hc-cab-lv" column, then the power-stop separator
    return [
      { key: 'node', head: 'Node' },
      { key: 'volt', head: 'Volt' }, { key: 'current', head: 'Current' },
      { key: 'ftg', head: 'ftg-hc-cab-lv', span: 4, cls: 'j', edit: true },
      { key: 'hc', head: '', cls: 'j', edit: true },
      { key: 'cab', head: '', cls: 'j', edit: true },
      { key: 'lv', head: '', cls: 'j', edit: true },
      { key: 'stop', head: '', cls: 'stop' },
      { key: 'amp', head: 'amp', edit: true },
      { key: 'ampname', head: 'amp ID#', cls: 'l', edit: true },
      { key: 'supply', head: 'supply', edit: true },
      { key: 'supplypct', head: '%' },
      { key: 'cplr0', head: 'cplr[branch]', cls: 'l', edit: true },
      { key: 'cplr1', head: 'cplr[branch]', cls: 'l', edit: true },
      { key: 'niu', head: 'NIU' },
    ];
  }
  return [
    { key: 'node', head: 'Node' },
    ...lvl,
    { key: 'fx', head: '', cls: 'fx' },          // "→" marks a fixed node
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
  if (r.end) {
    // the end line: levels, and the last tap's port output under the taps
    if (c.key.startsWith('lvl:')) return r.levels[+c.key.slice(4)].toFixed(2);
    if (/^tap\d$/.test(c.key)) {
      const v = (r.port_levels || [])[+c.key.slice(3)];
      return v === undefined ? '' : v.toFixed(2);
    }
    return '';
  }
  if (c.key.startsWith('lvl:')) {
    const v = r.levels[+c.key.slice(4)];      // index into the frequency order
    return v === undefined ? '' : v.toFixed(2);
  }
  switch (c.key) {
    case 'branch': return r.branch;
    case 'node': return r.node;
    case 'ftg': return (r.ftg || (r.ftg === 0 ? '0' : '')) + (S.mode === 'power' ? '|' : '');
    case 'hc': return (r.hc || '') + (S.mode === 'power' ? '|' : '');
    case 'cab': return (r.cab || (r.cab_name ? r.cab : '')) + (S.mode === 'power' ? '|' : '');
    case 'lv': return (r.lv || '') + (S.mode === 'power' ? '|' : '');
    case 'tsg': return r.tsg || '';
    case 'amp': return r.amp || '';
    case 'ampname': return r.amp_label ? `[${r.amp_label}]` : (r.amp_name || '');
    case 'map': return r.map || '';
    case 'loc': return r.loc || '';
    // "A" then the supply type and its load, as "\03  57%", run across
    case 'supply': return r.supply
      ? `${(r.supply_label || '').padEnd(12)}\\${String(r.supply_type || 0).padStart(2, '0')}` +
        (r.supply_pct != null ? `  ${r.supply_pct}%` : '')
      : '';
    case 'supplypct': return '';
    case 'niu': return r.volts === null ? '' : 'Y';
    case 'fx': return r.fixed ? '\u2192' : '';
    case 'stop': return S.mode === 'power' ? (r.power_stop ? '=' : '|') : '';
    case 'volt': return r.volts === null ? '' : r.volts.toFixed(2);
    case 'current': return r.current ? r.current.toFixed(2) : '0.00';
    case 'tap0': case 'tap1': case 'tap2': case 'tap3': {
      // in Design mode an amplifier's name runs on from the tap1 column
      const k = +c.key.slice(3);
      if (k === 0 && S.mode === 'design' && r.amp_label && !r.taps.length) return r.amp_label;
      return r.taps[k] || '';
    }
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
  let skip = 0;
  thead.innerHTML = '<tr><th class="gutter"></th>' +
    cols.map(c => {
      if (skip) { skip--; return ''; }
      if (c.span) { skip = c.span - 1; return `<th class="${c.cls || ''}" colspan="${c.span}">${esc(c.head)}</th>`; }
      return `<th class="${c.cls || ''}">${esc(c.head)}</th>`;
    }).join('') +
    '<th class="l"></th></tr>';

  if (!S.net) { tbody.innerHTML = ''; return; }
  if (!hasSpecs()) {
    tbody.innerHTML = `<tr><td class="gutter"></td><td class="l" colspan="${cols.length + 1}"
      style="color:var(--yellow);padding:18px 10px;white-space:normal;line-height:1.6">
      No spec file attached.<br><br>
      Nothing is loaded when a network is opened and nothing carries over from
      another network: every level, loss, part number and powering figure comes
      from the spec files.<br><br>
      <span style="color:var(--green)">File &rarr; Project Settings &rarr; Set All Files</span>
      &nbsp;to select a <b>.par .atv .tap .cpr .cbl</b> set (the sample specs are
      offered there too), or
      <span style="color:var(--green)">File &rarr; Open &rarr; Lode Data network (.ntw)</span>
      to bring in a design with its spec set.</td></tr>`;
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
      if (c.key === 'tap0' && S.mode === 'design' && r.amp_label && !r.taps.length) extra = ' amp spill';
      if (c.key === 'supply' && r.supply) extra = ' spill';
      if (/^tap\d$/.test(c.key)) {
        const k = +c.key.slice(3);
        const sev = r.end ? (r.port_severity || [])[k] : (r.tap_severity || [])[k];
        extra += r.end ? ' port' : ' tap';
        if (sev) extra += ' ' + sev;
      }
      if (r.end && c.key.startsWith('lvl:')) extra += ' endlv';
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

// The info box follows the cursor's column, as the program's does: a tap
// shows its port levels, a coupler previews the branch it feeds, an
// amplifier its definition, a power supply its type.
const PREVIEW_TAP = { 2: '()', 4: '[]', 6: '<>', 8: '{}' };
const f2 = v => (v === undefined || v === null) ? '' : Number(v).toFixed(2);
const pad = (v, n) => String(v).padStart(n);

function infoTap(r, k) {
  const part = (r.tap_parts || [])[k] || '';
  const lv = r.tap_levels ? r.tap_levels[k] : null;
  const fq = (S.scr && S.scr.frequencies) || [];
  if (!lv) return `${r.branch}.${r.node}\nTap Type:  ${part}`;
  return `${r.branch}.${r.node}\nTap Type:            ${part.replace(/ \(.*$/, '')}\n\n` +
    `Frequency\n  Forward\n` +
    `${pad(fq[0], 8)}: ${pad(f2(lv[0]), 7)}\n${pad(fq[1], 8)}: ${pad(f2(lv[1]), 7)}\n\n` +
    `  Return\n${pad(fq[2], 8)}: ${pad(f2(lv[2]), 7)}\n${pad(fq[3], 8)}: ${pad(f2(lv[3]), 7)}\n\n` +
    `<double-click or [.][ENTER] to edit branches>`;
}

function infoBranch(r, k) {
  const text = (r.couplers || [])[k] || '';
  const nums = [...text.matchAll(/[\[<({](\d+)[\]>)}]/g)].map(m => +m[1]);
  if (!nums.length) return null;
  const fq = (S.scr && S.scr.frequencies) || [];
  const out = [];
  for (const b of nums) {
    const m = branchMeta(b) || {};
    const rows = S.scr.rows.filter(x => x.branch === b);
    out.push(`${r.branch}.${r.node}\n${m.coupler || ''}\nFeeds Branch: ${b}\n` +
      `Start   ${fq.map(f => pad(f, 7)).join(' ')}\n` +
      `Levels  ${(m.start || []).map(v => pad(f2(v), 7)).join(' ')}\n` + '-'.repeat(96) + '\n' +
      `Node ${fq.map(f => pad(f, 7)).join(' ')}   ftg  hc cab lv amp  tap1 tap2 tap3 tap4   cplr[Br]   cplr[Br]\n` +
      rows.map(x => {
        const lv = x.levels.map(v => pad(f2(v), 7)).join(' ');
        if (x.end) return `     ${lv}`;
        const taps = [0, 1, 2, 3].map(i => {
          const t = (x.taps || [])[i];
          if (!t) return '     ';
          const br = PREVIEW_TAP[(x.tap_ports || [])[i]] || '[]';
          return pad(br[0] + t.replace(/[\/\[\]<>{}()]/g, '').trim() + br[1], 5);
        }).join('');
        return `${pad(x.node, 4)} ${lv} ${pad(x.ftg, 5)} ${pad(x.hc, 3)} ${pad(x.cab, 3)} ${pad(x.lv, 2)} ` +
          `${pad(x.amp || '', 4)} ${taps} ${pad((x.couplers || [])[0] || '', 10)} ${pad((x.couplers || [])[1] || '', 10)}`;
      }).join('\n') + '\n<double-click or [.][LT] or [.][RT] to enter branch>');
  }
  return out.join('\n\n');
}

function infoSupply(r) {
  return `${r.branch}.${r.node}\n\n\nPower Supply Information\n` +
    `Power Supply:${' '.repeat(30)}${r.supply_label || ''}\n` +
    `PS Type:${' '.repeat(35)}${r.supply_name || ''}`;
}

function infoAmp(r) {
  const a = r.amp_info || {};
  const line = (label, v) => `${label.padEnd(36)}${v === undefined || v === null ? '' : v}\n`;
  return `${r.branch}.${r.node}\n` +
    line('Amp Name:', a.name) + line('Amp Type:', a.type || r.amp_name) +
    line('Forward Pad:', a.fwd_pad) + line('Forward Eq:', a.fwd_eq === undefined ? '' : '#' + a.fwd_eq) +
    line('Return Pad:', a.ret_pad) + line('Return Eq:', a.ret_eq === undefined ? '' : '#' + a.ret_eq) +
    line('Aerial Dist to Previous Active:', a.aerial_prev) +
    line('Aerial Dist to Start of Network:', a.aerial_start) +
    line('Tot Dist to Previous Act-split:', a.total_split) +
    line('Total Dist to Previous Active:', a.total_prev) +
    line('Total Dist to Start of Network:', a.total_start) +
    line('Cascade Position:', a.cascade) + line('Power Supply:', a.supply) +
    line('Housecounts downstream:', a.homes_down);
}

function infoNode(r) {
  const t = (S.scr && S.scr.totals) || {};
  return `${r.branch}.${r.node}\n` +
    `${r.address || 'No Address'}\n` +
    `${r.cab_name || 'no cable'}\n` +
    `Distance from previous node:   ${r.ftg}\n` +
    `Total distance to start:       ${r.cumulative_ft}\n` +
    `Housecounts this node:         ${r.hc}\n` +
    (r.volts === null ? '' : `Voltage / current:             ${r.volts.toFixed(2)} V  ${r.current.toFixed(2)} A\n`) +
    (r.flags.length ? r.flags.map(f => `! ${f.message}`).join('\n') + '\n' : '') +
    `\n<double-click or [.][ENTER] to edit address>` +
    `\n\nnodes ${t.nodes || 0}  taps ${t.taps || 0}  actives ${t.actives || 0}  ` +
    `homes ${t.homes || 0}  ${t.footage || 0} ft`;
}

function renderInfo() {
  const r = pageRows()[S.row] || null;
  const box = $('#info');
  if (!r || r.end) { box.textContent = ''; }
  else {
    const c = curCol() || { key: '' };
    let text = null;
    if (/^tap\d$/.test(c.key) && (r.taps || [])[+c.key.slice(3)]) text = infoTap(r, +c.key.slice(3));
    else if (/^cplr\d$/.test(c.key)) text = r.supply ? infoSupply(r) : infoBranch(r, +c.key.slice(4));
    else if ((c.key === 'amp' || c.key === 'ampname' || c.key === 'tsg') && r.amp_info && r.amp_info.type) text = infoAmp(r);
    else if (c.key === 'supply' && r.supply) text = infoSupply(r);
    box.textContent = text || infoNode(r);
  }
  const total = (S.scr && S.scr.branches.length) || 1;
  $('#stBranch').textContent = `Branch ${S.branch} of ${total}`;
  $('#stFeeder').textContent = 'Feeder 1.1';
  const m = branchMeta(S.branch);
  const starting = m && m.parent_branch ? ` Starting ${m.parent_branch}.${m.parent_node}` : '';
  const mode = { design: 'Design', entry: 'Entry', power: 'Power' }[S.mode];
  $('#title').textContent = `Design Assistant - ${mode} - ${S.net ? S.net.name : ''}${starting}`;
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
  $$('.tbset').forEach(t => { t.hidden = !t.dataset.modes.split(' ').includes(S.mode); });
  $('#app').className = 'mode-' + S.mode;
}

// ---------------------------------------------------------------- editing
const EDIT_ORDER = ['ftg', 'hc', 'cab', 'lv'];

// Keying is faster than the round trip, so every edit is queued and the saves
// run strictly in order.  The cursor moves at once, on the keystroke, and a
// single refresh follows once the queue drains -- otherwise "300 . 4 . 2"
// races itself and lands the wrong values in the wrong columns.
let saveChain = Promise.resolve();
let pendingSaves = 0;

function queueSave(work) {
  pendingSaves += 1;
  saveChain = saveChain.then(work).catch(err => {
    let detail = err.message;
    try { detail = JSON.parse(detail).detail || detail; } catch (_) {}
    msg(detail);
  }).then(() => {
    pendingSaves -= 1;
    if (pendingSaves === 0) return doRefresh();
  });
  return saveChain;
}

function curCol() { return columns()[S.col]; }
function curRow() { return pageRows()[S.row]; }

function commitBuffer(advance) {
  const c = curCol(), r = curRow();
  if (!c || !r || S.buffer === null) return;
  const val = S.buffer.trim();
  const at = { branch: r.branch, node: r.node };
  S.buffer = null;
  const body = {};
  if (['ftg', 'hc', 'cab', 'lv', 'tsg', 'supply'].includes(c.key)) {
    const n = val === '' ? 0 : Number(val);
    if (Number.isNaN(n)) { msg('not a number'); renderGrid(); return; }
    if (c.key === 'supply') body.supply_volts = n;
    else if (c.key === 'cab') {
      body.cab = n;
      const part = pickCableById(n);
      body.cab_part = part ? part.id : null;
      if (!part && n) msg(`cable ${n} is not in the spec set`);
    } else body[c.key] = n;
  } else if (['map', 'loc', 'ampname'].includes(c.key)) {
    body[c.key === 'ampname' ? 'amp_label' : c.key] = val;
  } else { renderGrid(); return; }

  // move first, so the next keystroke lands in the right column
  if (advance) moveToNextField(); else renderGrid();
  queueSave(() => api(`/api/networks/${S.nid}/nodes/${at.branch}/${at.node}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body) }));
}

// Taps, couplers and actives are typed at the cell: "4.23" is a 4-port 23 tap,
// "8" a DC-8, "-8" the same DC with its legs swapped.  The server resolves the
// code against the attached spec set and says what it could not find.
const TYPED_COLUMNS = /^(tap\d|cplr\d|amp)$/;

function commitCode() {
  const c = curCol(), r = curRow();
  if (!c || !r) return;
  const code = (S.buffer || '').trim();
  const at = { branch: r.branch, node: r.node };
  S.buffer = null;
  renderGrid();

  if (c.key.startsWith('tap')) {
    const slot = +c.key.slice(3);
    queueSave(async () => {
      const out = await api(`/api/networks/${S.nid}/nodes/${at.branch}/${at.node}/tap`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot, code }) });
      msg(out.placed
        ? `${out.placed.name} — ${out.placed.ports} port, ${out.placed.value_db} dB,`
          + ` shown as the tap ID ${out.placed.tap_id}`
        : 'tap cleared');
    });
  } else if (c.key.startsWith('cplr')) {
    const slot = +c.key.slice(4);
    queueSave(async () => {
      const out = await api(`/api/networks/${S.nid}/nodes/${at.branch}/${at.node}/coupler`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot, code }) });
      if (!out.placed) { msg('coupler and its branch removed'); return; }
      const p = out.placed;
      const where = p.through_leg === 0 ? 'through leg downstream'
                  : p.through_leg === 1 ? 'through leg to this branch, tap leg downstream'
                  : 'through leg to the right-most branch';
      msg(`${p.name} — branch ${p.branch}, legs ${p.legs.join(' / ')} dB, ${where}`);
    });
  } else {
    queueSave(async () => {
      await api(`/api/networks/${S.nid}/nodes/${at.branch}/${at.node}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amp_code: code }) });
      msg(code === '0' || code === '' ? 'active cleared' : 'active placed');
    });
  }
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
    ev.preventDefault();
    // in a tap column the "." separates ports from value: 4.23
    if (S.buffer !== null && cols[S.col].key.startsWith('tap')) {
      S.buffer += '.'; renderGrid(); return;
    }
    // typing elsewhere: the field separator. Otherwise a branch-move prefix.
    if (S.buffer !== null) { commitBuffer(true); return; }
    S.dot = true; msg('. — press an arrow or Page key for a branch move');
    return;
  }
  else if (k === 'Enter') {
    ev.preventDefault();
    if (S.buffer !== null) {
      if (TYPED_COLUMNS.test(cols[S.col].key)) commitCode();
      else commitBuffer(false);
    } else await openCell();
    return;
  }
  else if (/^[0-9]$/.test(k)) {
    const c = cols[S.col];
    // the end line is a readout, not a node
    if (c && c.edit && !(curRow() || {}).end) { S.buffer = (S.buffer || '') + k; }
  }
  else if ((k === '-' || k === '=') && TYPED_COLUMNS.test(cols[S.col].key)) {
    // "-8" and "--8" (or "=8") choose which leg is the through leg
    S.buffer = (S.buffer || '') + k;
  }
  else if (k === '-' && S.buffer === null && cols[S.col].edit) {
    S.buffer = '-';
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
  if ((curRow() || {}).end) return;
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
  const items = libTable('actives').map(a => ({ id: a.id,
    label: (a.active_id ? a.active_id + '  ' : '') + a.name, aid: a.active_id,
    detail: `${a.kind} · in ${a.in_forward_high}/${a.in_forward_low} · out ${a.out_forward_high}/${a.out_forward_low}` }));
  chooser(`Active for node ${r.branch}.${r.node}`, items, async pick => {
    await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pick ? { amp_code: pick.aid || '' } : { clear_amp: true }) });
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
function clearCell() {
  const c = curCol(), r = curRow(); if (!c || !r) return;
  S.buffer = '0';
  if (TYPED_COLUMNS.test(c.key)) commitCode(); else commitBuffer(false);
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
// The menu bar, item for item as Lode Data 12.11 shows it.  An entry is
// [label, action] or [label, [submenu...]]; '-' is a separator.  Items this
// program does not do yet are listed all the same, and say so when picked.
const NYI = label => () => msg(`${label} is not implemented yet`);
const MENU_ACTIONS = {
  file: [
    ['New', [['Network', newNetwork]]],
    ['Open', [['Network...', openNetwork], ['Lode Data network (.ntw)...', importNtw]]],
    ['Unload', [['Specs', NYI('Unload specs')]]],
    ['Save Specs', [['All', NYI('Save Specs')]]],
    ['Save Network', () => msg('saved — every change is saved as it is made')],
    ['Save Network As...', NYI('Save Network As')],
    '-',
    ['Project Settings...', projectSettings],
    '-',
    ['Print', [['Level sheet', () => openReport('levels')],
               ['Bill of Materials', () => openReport('bom')],
               ['Powering', () => openReport('powering')]]],
    '-',
    ['Exit', () => msg('close the browser tab to exit')],
  ],
  edit: [
    ['Mark / Unmark', NYI('Mark')], ['Mark to End of Line', NYI('Mark to End of Line')],
    ['Unmark to End of Line', NYI('Unmark to End of Line')], ['Swap Mark', NYI('Swap Mark')],
    ['Copy Marked Area', NYI('Copy Marked Area')], ['Delete Marked Area', NYI('Delete Marked Area')],
    '-',
    ['Copy...\tCtrl+C', NYI('Copy')], ['Paste...\tCtrl+V', NYI('Paste')],
    '-',
    ['Find/Replace/Mark...\tCtrl+H', NYI('Find/Replace/Mark')],
    ['Rename Devices...', NYI('Rename Devices')],
    '-',
    ['Edit Node Address...', NYI('Edit Node Address')],
  ],
  mode: [
    ['Entry', () => setMode('entry')], ['Design', () => setMode('design')],
    ['Active Entry', NYI('Active Entry mode')], ['Powering', () => setMode('power')],
    '-',
    ['Select Modes...', NYI('Select Modes')],
  ],
  tools: [
    ['Network Init', netInit], ['Clear Branch Labels', NYI('Clear Branch Labels')],
    ['Clear Amp Name', NYI('Clear Amp Name')], ['Append', NYI('Append')],
    ['Convert', NYI('Convert')], ['Connect', NYI('Connect')],
    ['Move Origin', NYI('Move Origin')], ['Force Signals', NYI('Force Signals')],
    ['Plugins', NYI('Plugins')],
    '-',
    ['dB Req', NYI('dB Req')], ['Extended dB Req', NYI('Extended dB Req')],
    '-',
    ['Toggle No BOM', NYI('Toggle No BOM')], ['Delete No BOM', NYI('Delete No BOM')],
    '-',
    ['Macro Options...', NYI('Macro Options')], ['Run Batch Macro...', NYI('Run Batch Macro')],
  ],
  global: [['Cables', NYI('Global Change Cables')], ['Levels', NYI('Global Change Levels')],
           ['Maps', NYI('Global Change Maps')], ['Map Grid', NYI('Global Change Map Grid')],
           ['TSG', NYI('Global Change TSG')]],
  spec: [
    ['Parameters...', NYI('Parameters editor')], ['Actives...', viewLibrary],
    ['Taps...', viewLibrary], ['Couplers...', viewLibrary], ['Cables...', viewLibrary],
    ['Pricing...', NYI('Pricing editor')], ['Performance...', NYI('Performance editor')],
    ['Control...', NYI('Control editor')],
  ],
  test: [['Network', test], ['Powering', test], ['Global Test', NYI('Global Test')],
         '-', ['Preferences...', NYI('Test preferences')]],
  misc: [['PCD Cleanup', NYI('PCD Cleanup')], ['Override Current Passing', NYI('Override Current Passing')],
         ['Enable Dialog Warnings', NYI('Enable Dialog Warnings')], ['Set Import', NYI('Set Import')],
         ['Update All', NYI('Update All')], ['Project Load Setting', NYI('Project Load Setting')]],
  reports: [['Multi-Net Downstream Summary...', dsummary],
            ['Multi-Net PCD List...', NYI('Multi-Net PCD List')],
            ['Network Tap Report...', NYI('Network Tap Report')],
            ['Network Tilt Report...', NYI('Network Tilt Report')],
            ['Multi-Net Network Spec Report', NYI('Multi-Net Network Spec Report')]],
  view: [['Show Grid', () => { document.body.classList.toggle('nogrid'); }],
         ['Show Tips', NYI('Show Tips')]],
  help: [['Contents and Index', showHelp], ["What's New...", NYI("What's New")],
         ['About Windows...', NYI('About Windows')], ['Key Info...', showHelp],
         ['About Design Assistant/Viewer...', () => msg('Design Assistant — web replica')]],
};

function closeMenus() { $$('.dropdown').forEach(d => d.remove()); }
function dropdown(items, x, y) {
  const box = document.createElement('div');
  box.className = 'dropdown';
  box.style.left = x + 'px'; box.style.top = y + 'px';
  box.innerHTML = items.map((it, i) => it === '-' ? '<div class="sepr"></div>' : (() => {
    const [label, act] = it;
    const [text, key] = label.split('\t');
    return `<div class="di${Array.isArray(act) ? ' sub' : ''}" data-i="${i}">` +
      `<span>${esc(text)}</span><span class="k">${esc(key || '')}` +
      `${Array.isArray(act) ? ' ›' : ''}</span></div>`;
  })()).join('');
  document.body.appendChild(box);
  box.querySelectorAll('.di').forEach(el => {
    const act = items[+el.dataset.i][1];
    el.onmouseenter = () => {
      box.querySelectorAll('.dropdown').forEach(d => d.remove());
      $$('.dropdown').forEach(d => { if (+d.dataset.level > +(box.dataset.level || 0)) d.remove(); });
      if (Array.isArray(act)) {
        const r = el.getBoundingClientRect();
        const sub = dropdown(act, r.right - 2, r.top);
        sub.dataset.level = (+(box.dataset.level || 0) + 1);
      }
    };
    el.onclick = e => {
      e.stopPropagation();
      if (Array.isArray(act)) return;
      closeMenus(); act();
    };
  });
  return box;
}
$$('.menubar .mi').forEach(mi => mi.onclick = e => {
  e.stopPropagation();
  const open = $$('.dropdown').length && $('.dropdown').dataset.menu === mi.dataset.menu;
  closeMenus();
  if (open) return;
  const r = mi.getBoundingClientRect();
  const box = dropdown(MENU_ACTIONS[mi.dataset.menu] || [], r.left, r.bottom);
  box.dataset.menu = mi.dataset.menu; box.dataset.level = 0;
});
document.addEventListener('click', closeMenus);

// File > Project Settings: where a network's spec files are chosen.
function projectSettings() {
  const lib = (S.net && S.net.library) || {};
  const loaded = lib.name || '';
  const row = (label, file) => `<div class="ps-row"><span>${label}</span>` +
    `<input type="text" readonly value="${esc(file)}"><button disabled>Browse...</button></div>`;
  modal(`<h2>Project Settings</h2>
    <div class="ps">
      ${row('Network Folder', '')}${row('PCD Folder', '')}
      <fieldset><legend>Spec Files</legend>
        <button id="psSetAll">Set All Files</button>
        <input type="file" id="psFiles" multiple hidden accept=".par,.atv,.tap,.cpr,.cbl,.prc,.per">
        ${row('Parameters File', loaded && loaded + '.par')}
        ${row('Actives File', loaded && loaded + '.atv')}
        ${row('Taps File', loaded && loaded + '.tap')}
        ${row('Couplers File', loaded && loaded + '.cpr')}
        ${row('Cables File', loaded && loaded + '.cbl')}
        ${row('Pricing File', '')}${row('Performance File', '')}${row('Map Grid File', '')}
      </fieldset>
      <fieldset><legend>Misc Folders</legend>
        <button disabled>Set All Folders</button>
        ${row('Control File Folder', '')}${row('Report File Folder', '')}
      </fieldset>
      <p class="ps-note">Set All Files takes one spec set: the .par .atv .tap .cpr .cbl
      files that share a base name. Or <a href="#" id="psSample">use the sample specs</a>
      (not for real design).</p>
    </div>
    <div class="row"><button class="primary" id="mClose">OK</button>
      <button id="psCancel">Cancel</button></div>`);
  $('#psCancel').onclick = closeModal;
  $('#psSetAll').onclick = () => $('#psFiles').click();
  $('#psSample').onclick = async e => { e.preventDefault(); closeModal(); await sampleSpecs(); };
  $('#psFiles').onchange = async () => {
    const files = $('#psFiles').files;
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

function branchList() {
  const items = S.scr.branches.map(b => ({ n: b.number,
    label: `Branch ${b.number}${b.label ? ' — ' + b.label : ''}`,
    detail: b.parent_branch ? `${b.nodes} nodes · from ${b.parent_branch}.${b.parent_node} · ${b.style}`
                            : `${b.nodes} nodes · feeder` }));
  chooser('Branches', items, pick => { if (pick) gotoBranch(pick.n); });
}

function showHelp() {
  modal(`<h2>Keys</h2>
   <p><b>Taps</b> are typed at the cell: <code>2.23</code> a 2-port 23,
   <code>4.23</code> a 4-port 23, <code>8.20</code> an 8-port 20. A bare
   <code>23</code> picks the port count from the house count. <code>0</code>
   clears.</p>
   <p><b>Couplers</b> are typed as their Coupler ID: <code>2</code> a 2-way
   splitter, <code>3</code> a 3-way, <code>8</code> a DC-8. A leading
   <code>-</code> swaps the legs, so <code>-8</code> sends the through
   (low loss) leg to the branch and the tap (high loss) leg downstream;
   <code>--3</code> or <code>=3</code> sends it to the right-most branch.
   <code>0</code> removes the coupler and its branch.</p>
   <p><b>Actives</b> are typed as their Active ID.</p>
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
    <p>A .ntw refers to its equipment by position in the spec files, so pick the
    spec set it was saved with as well (.par .atv .tap .cpr .cbl). Pick just the
    .ntw first to see which set it needs.</p>
    <label>Network file <input type="file" id="ntwFile" accept=".ntw"></label>
    <label>Spec set <input type="file" id="ntwSpecs" multiple
      accept=".par,.atv,.tap,.cpr,.cbl,.prc,.per"></label>
    <div class="row"><button class="primary" id="ntwGo">Import</button>
      <button id="mClose">Cancel</button></div><pre id="ntwOut"></pre>`);
  $('#ntwGo').onclick = async () => {
    const f = $('#ntwFile').files[0]; if (!f) return;
    const fd = new FormData(); fd.append('file', f);
    for (const s of $('#ntwSpecs').files) fd.append('specs', s);
    const out = await api('/api/import/ntw', { method: 'POST', body: fd });
    if (!out.imported) {
      $('#ntwOut').textContent = `${out.network || f.name}: ${out.branches} branches, ` +
        `${out.nodes} nodes.\nIt was saved with spec set ${out.spec_set_needed} — ` +
        `pick those five files and import again.`;
      return;
    }
    const r = out.report;
    closeModal();
    await open(out.id);
    msg(`${r.network}: ${r.branches} branches, ${r.nodes} nodes read against ${r.spec_set}` +
        (r.unresolved.length ? ` — ${r.unresolved.length} unresolved: ${r.unresolved[0]}` : ''));
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
  if (pendingSaves > 0) return;      // the queue will refresh when it drains
  return doRefresh();
}

async function doRefresh() {
  S.scr = await api(`/api/networks/${S.nid}/screen`);
  if (!branchMeta(S.branch)) S.branch = S.scr.branches.length ? S.scr.branches[0].number : 1;
  S.row = Math.max(0, Math.min(S.row, pageRows().length - 1));
  renderGrid();
}
async function reload() {
  S.net = await api(`/api/networks/${S.nid}`);
  const sn = S.net.library.name;
  $('#stSpecs').textContent = sn ? `${sn} : ${sn} : ${sn} : ${sn} : ${sn} : Untitled` : 'no spec file attached';
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
