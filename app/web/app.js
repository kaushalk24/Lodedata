'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = async (url, opts) => {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error((await r.text()).slice(0, 400));
  // a line or branch changed: the network is modified (Num Lock's box)
  if (opts && opts.method && /^\/api\/networks\/[^/]+\/(nodes|branches)\//.test(url)) S.modified = true;
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
  tips: true,         // View > Show Tips: the info box
  // pad / EQ bank rows whose labels an amplifier's box has shown: the
  // program trims them in its memory, so the expanded display shows them
  // without their spaces from then on (until it is restarted)
  trimmed: new Set(),
  modified: false,    // an edit since the network was opened or saved
  modalKeys: null,    // keys a message box answers to ([3] [7] [9])
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
  const f = (S.scr && (S.scr.labels || S.scr.frequencies)) || [];
  const lvl = f.map((mhz, i) => ({ key: 'lvl:' + i, head: String(mhz).replace('.0', ''),
                                   cls: '', edit: false }));
  // the Parameters' extra forward frequencies (WVEXT862's 550; BH1GHzMid's
  // 550 and 860): Lode draws their columns after the two cplr[branch]
  // columns, headed with the Parameters' labels
  const xf = (S.scr && (S.scr.extra_labels || S.scr.extra_frequencies)) || [];
  const xlv = xf.map((mhz, i) => (
    { key: 'xlv:' + i, head: String(mhz).replace('.0', ''), cls: '', edit: false }));
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
    // a power stop shows as "=" between lv and amp (AL002 55.2, the user's
    // recording)
    { key: 'stop', head: '', cls: 'stop' },
    { key: 'amp', head: 'amp', edit: true },
    { key: 'tsg', head: 'TSG', edit: true },
    { key: 'tap0', head: 'tap1', edit: true }, { key: 'tap1', head: 'tap2', edit: true },
    { key: 'tap2', head: 'tap3', edit: true }, { key: 'tap3', head: 'tap4', edit: true },
    { key: 'cplr0', head: 'cplr[branch]', cls: 'l', edit: true },
    { key: 'cplr1', head: 'cplr[branch]', cls: 'l', edit: true },
    ...xlv,
  ];
}

function cellText(r, c) {
  if (c.key.startsWith('xlv:')) {
    const v = (r.extra_levels || [])[+c.key.slice(4)];
    return v === undefined ? '' : v.toFixed(2);
  }
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
    // cable 0 is left blank, as hc and lv are (AL004 1.2 - 1.5, recording 1)
    case 'cab': return (r.cab || '') + (S.mode === 'power' ? '|' : '');
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
    // AL002's 4.5-4.8, past the stop at 0.00 V, read Y too (37)
    case 'niu': return 'Y';
    case 'fx': return r.fixed ? '\u2192' : '';
    case 'stop': return S.mode === 'power' ? (r.power_stop ? '=' : '|') : (r.power_stop ? '=' : '');
    case 'volt': return r.volts === null ? '0.00' : r.volts.toFixed(2);
    case 'current': return r.current ? r.current.toFixed(2) : '0.00';
    case 'tap0': case 'tap1': case 'tap2': case 'tap3': {
      // in Design mode an amplifier's name runs on from the tap1 column
      const k = +c.key.slice(3);
      if (k === 0 && S.mode === 'design' && r.amp_label && !r.taps.length) return r.amp_label;
      return r.taps[k] || '';
    }
    case 'cplr0': case 'cplr1': {
      // a power supply's label sits in the first free cplr column of the
      // Design screen, cyan (SN001_MID 4.1: "1A")
      const k = +c.key.slice(4);
      if (psInCplr(r, k)) return r.supply_label;
      return r.couplers[k] || '';
    }
  }
  return '';
}

function psInCplr(r, k) {
  return S.mode === 'design' && !r.end && !!r.supply_label && k === (r.couplers || []).length;
}

// ---------------------------------------------------------------- render
// "/" in Design toggles the expanded display: under each node its four tap
// slots (port levels, or dashes), then the level it passes on, then a blank.
function toggleExpanded() { S.expanded = !S.expanded; renderGrid(); }

// The cyan block under an amplifier, a coupler or a branch's last node, as
// the program lays it out (measured on 6.9, 4.24-4.26 and 22.1-22.5).
function blockText(b) {
  const w = (v, n) => String(v).padStart(n);
  const [ap, as, ts, tp, tt] = b.distances.map(v => Math.round(v));
  const one = '[' + w(ap, 5) + w(as, 6) + w(ts, 5) + w(tp, 5) + w(tt, 6) +
    b.losses.map(v => w(v.toFixed(2), 6)).join('') + ']';
  // homes take three columns and the footage follows with no gap: 4.4 shows
  // 127 homes and 886 ft as "127886"
  const two = ' ' + b.above.join('-') + ' ' + b.below.join('-') + '   ' +
    String(b.homes).padEnd(3) + Math.round(b.same_cable);
  return [one, two];
}

function expandedLines(r, cols) {
  const cell = (c, text, cls) => `<td class="${c.cls || ''} ${cls || ''}">${esc(text)}</td>`;
  // text drawn from the lv column on, across the rest of the line
  const at = cols.findIndex(c => c.key === 'lv');
  // segs: [text, class] runs drawn from there on
  // the extra frequencies' columns keep their cells beside the text
  const xi = cols.findIndex(c => c.key.startsWith('xlv:'));
  const line = (fill, segs) => `<tr class="xline"><td class="gutter">${esc(r.gutter && r.gutter !== '└' ? '│' : '')}</td>` +
    cols.slice(0, segs ? at : cols.length).map(c => fill(c)).join('') +
    (segs ? `<td class="xtext" colspan="${(xi > at ? xi : cols.length + 1) - at}">` +
      segs.map(([t, cls]) => `<span class="${cls}">${esc(t)}</span>`).join('') + '</td>' +
      (xi > at ? cols.slice(xi).map(c => fill(c)).join('') + '<td></td>' : '') : '<td></td>') + '</tr>';
  // lines 2-3: an amplifier's name and supply, then its pad and EQ parts,
  // forward then return; lines 4-5: the cyan block, which starts six
  // characters to the right of the name (columns as 4.24, 22.3, 34.3 show).
  // The name is in square brackets, the supply and the parts in round ones
  // (told from < by their glyphs: 5.23, 9.3, 14.3, 29.5 on the 4 Oct set)
  const text = [null, null, null, null];
  const a = r.amp_info;
  if (a && a.name !== undefined) {
    // "(" then each slot's prefix right-aligned in ten, its label in four:
    // "(      SPB-  10¦  SEQ-750-   6)", CE-120- one further right (H043B
    // 1.8, n5a).  A label keeps its spaces until the active's box has shown
    // it (S.trimmed); a missing EQ reads <NO FWD EQ> / <NO RET EQ> and the
    // line's lead-in is reversed (LG001 2.11, the older AL004's 43.1)
    const cols = a.cols || [];
    const slot = c => {
      if (!c) return ' '.repeat(14);
      if (c.none) return c.none.padEnd(14);
      const lab = S.trimmed.has(c.key) ? c.label.trim() : c.label;
      return c.prefix.padStart(10) + lab.padEnd(4);
    };
    const line = (p, e) => {
      const t = '  (' + slot(p) + '\u00a6' + slot(e) + ')';
      return [[t.slice(0, 9), 'xblock' + (e && e.none ? ' xnoeq' : '')], [t.slice(9), 'xblock']];
    };
    text[0] = [['[' + (r.amp_label || '').padStart(18) + ']', 'xname'], ...line(cols[0], cols[2])];
    text[1] = [['(' + (a.supply || '').padStart(18) + ')', 'xsupply'], ...line(cols[1], cols[3])];
  }
  if (r.block && r.block.distances) {
    const [one, two] = blockText(r.block);
    text[2] = [['      ' + one, 'xblock']];
    text[3] = [['      ' + two, 'xblock']];
  }
  const lines = [];
  for (let k = 0; k < 4; k++) {
    const lv = (r.tap_levels || [])[k];
    const sev = (r.tap_port_severity || [])[k] || [];
    const xl = (r.tap_extra || [])[k], xsev = (r.tap_extra_severity || [])[k] || [];
    lines.push(line(c => {
      if (c.key.startsWith('lvl:')) {
        const i = +c.key.slice(4);
        return lv ? cell(c, lv[i].toFixed(2), 'xport ' + (sev[i] || '')) : cell(c, '-', 'xdash');
      }
      // the extra frequencies' columns the same way (H043B 2.10, n5c)
      if (c.key.startsWith('xlv:')) {
        const i = +c.key.slice(4);
        return xl && xl[i] !== undefined ? cell(c, xl[i].toFixed(2), 'xport ' + (xsev[i] || ''))
                                         : cell(c, '-', 'xdash');
      }
      // which number this is -- the tap slot or its homes -- is not yet known
      if (c.key === 'ftg' && lv) return cell(c, `(${k + 1})`, 'xcyan');
      // an underground location's housing, under the node number
      if (c.key === 'node' && k === 0 && r.housing) return cell(c, `(${r.housing})`, 'xhousing');
      return cell(c, '');
    }, text[k]));
  }
  const out = r.out_levels || [], outx = r.out_extra || [];
  lines.push(line(c => c.key.startsWith('lvl:') && out.length
    ? cell(c, out[+c.key.slice(4)].toFixed(2), 'xout')
    : c.key.startsWith('xlv:') && outx.length ? cell(c, outx[+c.key.slice(4)].toFixed(2), 'xout') : cell(c, '')));
  lines.push(line(c => cell(c, '')));
  return lines.join('');
}

// ftg, hc, cab and lv are one field to the program: with the cursor on any
// of them all four are lit, the cable number in its series' colour (the
// older AL004's 25.2 with the cursor on its red 505)
function underCursor(cols, j) {
  const line = ['ftg', 'hc', 'cab', 'lv'], at = cols[S.col];
  return j === S.col || (S.mode === 'design' && !!at && line.includes(at.key) && line.includes(cols[j].key));
}

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
  // a .ntw opened with no spec set shows its lines, levels 0.00, as the
  // program does (recording 1)
  if (!hasSpecs() && !(S.scr && S.scr.rows.length)) {
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
      const cur = (i === S.row && underCursor(cols, j)) ? ' cur' : '';
      let text = cellText(r, c);
      if (i === S.row && j === S.col && S.buffer !== null) text = S.buffer + '_';
      let extra = '';
      // a line with Notes: a yellow ♪ after the cable (SN001_MID 1.1)
      if (c.key === 'cab') extra = ' cab' + (r.note && S.mode === 'design' ? ' hasnote' : '');
      if (c.key === 'hc' && r.hc_severity) extra = ' ' + r.hc_severity;
      if (c.key === 'stop' && r.power_stop) extra = ' on';
      if (c.key === 'ampname') extra = ' amp';
      if (c.key === 'tap0' && S.mode === 'design' && r.amp_label && !r.taps.length) extra = ' amp spill';
      if (c.key === 'supply' && r.supply) extra = ' spill';
      if (/^cplr\d$/.test(c.key) && psInCplr(r, +c.key.slice(4))) extra = ' pslabel';
      // an active's own output split away from any active: red (S3's 1.2)
      else if (/^cplr\d$/.test(c.key) && (r.coupler_severity || [])[+c.key.slice(4)]) extra = ' ' + r.coupler_severity[+c.key.slice(4)];
      if (/^tap\d$/.test(c.key)) {
        const k = +c.key.slice(3);
        const sev = r.end ? (r.port_severity || [])[k] : (r.tap_severity || [])[k];
        extra += r.end ? ' port' : ' tap';
        if (sev) extra += ' ' + sev;
      }
      if (r.end && /^(lvl|xlv):/.test(c.key)) extra += ' endlv';
      // an input or output the active misses, and its ID, red (the older
      // AL004's 4.13: 10.97 and 24.90 and its 61)
      const lvsev = !r.end && /^(lvl|xlv):/.test(c.key) &&
        (r[c.key[0] === 'l' ? 'level_severity' : 'extra_severity'] || [])[+c.key.slice(4)];
      if (lvsev) extra += ' ' + lvsev;
      if (c.key === 'amp' && r.amp_severity) extra += ' ' + r.amp_severity;
      // the cable number in the colour its cable file gives its series; in
      // Powering its "|" too, even with cable 0 left blank (AL002's 4.1 and
      // 4.5 on WVEXT862's red 000 series, 37)
      const style = c.key === 'cab' && r.cab_color && S.mode !== 'entry' ? ` style="--cab:${r.cab_color}"` : '';
      return `<td class="${c.cls || ''}${cur}${extra}"${style} data-r="${i}" data-c="${j}">${esc(text)}</td>`;
    }).join('');
    const main = `<tr class="${cls}"><td class="gutter">${esc(r.gutter)}</td>${tds}<td></td></tr>`;
    return S.expanded && S.mode === 'design' && !r.end ? main + expandedLines(r, cols) : main;
  }).join('');

  $$('#grid tbody td[data-r]').forEach(td => td.onclick = () => {
    const typing = S.buffer !== null;
    S.row = +td.dataset.r; S.col = +td.dataset.c; S.buffer = null;
    if (typing) { renderGrid(); return; }
    // move the cursor in place: redrawing the grid would swallow a double-click
    $$('#grid td.cur').forEach(x => x.classList.remove('cur'));
    $$('#grid tr.onrow').forEach(x => x.classList.remove('onrow'));
    const cols = columns();
    td.parentElement.querySelectorAll('td[data-c]').forEach(x => {
      if (underCursor(cols, +x.dataset.c)) x.classList.add('cur');
    });
    td.parentElement.classList.add('onrow');
    renderInfo();
  });
  renderInfo();
}

// a coupler's tip: "<double-click or [.][LT] or [.][RT] to enter branch>".
// One splitter feeding two branches is one cell, 3-<11>{12}: double-clicking
// the second bracket goes into the second branch (the user, 4 Oct)
$('#grid tbody').ondblclick = ev => {
  const td = ev.target.closest('td[data-r]');
  const c = td && columns()[+td.dataset.c];
  const text = c && /^cplr\d$/.test(c.key) && (curRow().couplers || [])[+c.key.slice(4)];
  if (!text) return;
  let at = -1;
  const pos = document.caretPositionFromPoint ? document.caretPositionFromPoint(ev.clientX, ev.clientY)
    : document.caretRangeFromPoint && document.caretRangeFromPoint(ev.clientX, ev.clientY);
  if (pos && td.contains(pos.offsetNode || pos.startContainer)) at = pos.offset ?? pos.startOffset;
  const second = [...text.matchAll(/[\[<({](\d+)[\]>)}]/g)][1];
  if (second && at >= second.index) { gotoBranch(+second[1]); return; }
  enterBranch(+c.key.slice(4));
};

// The mouse wheel moves the cursor a line at a time within the branch on
// screen, never into another. Turned up on the branch's first line it goes
// back to the branch it was entered from, on the coupler's line.
let wheelSum = 0;
$('.grid-wrap').addEventListener('wheel', ev => {
  if (ev.ctrlKey || Math.abs(ev.deltaX) > Math.abs(ev.deltaY)) return;  // zoom, sideways
  ev.preventDefault();
  if (!$('#modal').hidden || !pageRows().length) return;
  // a mouse wheel's notch is one line; a touchpad's small moves add up to one
  wheelSum += ev.deltaMode ? Math.sign(ev.deltaY) * 50 : ev.deltaY;
  if (Math.abs(wheelSum) < 50) return;
  const down = wheelSum > 0;
  wheelSum = 0;
  S.buffer = null; S.dot = false;
  if (down) S.row = Math.min(pageRows().length - 1, S.row + 1);
  else if (S.row > 0) S.row -= 1;
  else { returnToParent(); showCursor(); return; }
  renderGrid();
  showCursor();
}, { passive: false });

// keep the cursor's line in sight, below the column heads, with the lines
// the expanded display draws under it
function showCursor() {
  const wrap = $('.grid-wrap'), tr = $('#grid tbody tr.onrow');
  if (!tr) return;
  let last = tr;
  while (last.nextElementSibling && last.nextElementSibling.classList.contains('xline')) {
    last = last.nextElementSibling;
  }
  const w = wrap.getBoundingClientRect(), r = tr.getBoundingClientRect();
  const top = w.top + $('#grid thead').offsetHeight, bottom = w.top + wrap.clientHeight;
  const end = last.getBoundingClientRect().bottom;
  if (r.top < top) wrap.scrollTop -= top - r.top;
  else if (end > bottom) wrap.scrollTop += Math.min(end - bottom, r.top - top);
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
  // a tap feeding a branch from its port names it (the old AL004's 11.16)
  const fed = (r.tap_branches || [])[k] ? `Branch:              ${r.tap_branches[k]}\n` : '';
  if (!lv) return `${r.branch}.${r.node}\nTap Type:  ${part}\n${fed}`;
  return `${r.branch}.${r.node}\nTap Type:            ${part.replace(/ \(.*$/, '')}\n${fed}\n` +
    `Frequency\n  Forward\n` +
    `${pad(fq[0], 8)}: ${pad(f2(lv[0]), 7)}\n${pad(fq[1], 8)}: ${pad(f2(lv[1]), 7)}\n\n` +
    `  Return\n${pad(fq[2], 8)}: ${pad(f2(lv[2]), 7)}\n${pad(fq[3], 8)}: ${pad(f2(lv[3]), 7)}\n\n` +
    `<double-click or [.][ENTER] to edit branches>`;
}

// One branch, the first in the cell: on 4.14's 3-[11]<12> the program's box
// reads "Feeds Branch: 11" only.
// The preview box as Lode prints it (SN001_MID 1.2, 15.10, 18.9, 24.7,
// 28.9, measured glyph by glyph): the branch's first ten lines, each field
// a fixed width -- node 4, levels 7 each, ftg 5, hc 4, cab 4, lv 3, the
// active from the 51st column, taps 5 each, couplers 12 each.  Levels are
// printed as computed (2.5's 32.055 reads 32.05 here, 32.06 on the screen),
// every branch is [n], hc and lv read 0, and an in-line device is left out
// (20.9's EQ).
function infoBranch(r, k) {
  const text = (r.couplers || [])[k] || '';
  // a PCD (H043B_MID's 1.1, the user's n3)
  const pcd = (r.coupler_pcds || [])[k];
  if (pcd) return `${r.branch}.${r.node}\nPCD branch connected to Network:  ${pcd}\n` +
    '<double-click or [.][LT] or [.][RT] to enter branch>';
  const found = /[\[<({](\d+)[\]>)}]/.exec(text);
  if (!found) return null;
  const fq = (S.scr && S.scr.frequencies) || [];
  const b = +found[1];
  const m = branchMeta(b) || {};
  const rows = S.scr.rows.filter(x => x.branch === b).slice(0, 10);
  const square = t => (t || '').replace(/[<({](\d+)[>)}]/g, '[$1]');
  const levels = x => (x.raw_levels || x.levels).map(v => pad(f2(v), 7)).join('');
  return `${r.branch}.${r.node}\n${m.coupler || ''}\nFeeds Branch: ${b}\n` +
    `${'Start'.padEnd(7)}${fq.map(f => pad(f, 7)).join('')}\n` +
    `${'Levels'.padEnd(7)}${(m.start || []).map(v => pad(f2(v), 7)).join('')}\n` + '-'.repeat(105) + '\n' +
    `Node${fq.map(f => pad(f, 7)).join('')}${pad('ftg', 5)}${pad('hc', 4)}${pad('cab', 4)}${pad('lv', 3)}` +
    `${pad('amp', 4)}${pad('tap1', 6)}${pad('tap2', 5)}${pad('tap3', 5)}${pad('tap4', 5)}` +
    `${pad('cplr[Br]', 12)}${pad('cplr[Br]', 12)}\n` +
    rows.map(x => {
      if (x.end) return `    ${levels(x)}`;
      const taps = [0, 1, 2, 3].map(i => {
        const t = (x.taps || [])[i];
        if (!t) return '     ';
        const br = PREVIEW_TAP[(x.tap_ports || [])[i]] || '[]';
        return pad(br[0] + t.replace(/[\/\[\]<>{}()]/g, '').trim() + br[1], 5);
      }).join('');
      const amp = x.inline ? '' : (x.amp || '');
      return (`${pad(x.node, 4)}${levels(x)}${pad(x.ftg, 5)}${pad(x.hc || 0, 4)}${pad(x.cab, 4)}` +
        `${pad(x.lv || 0, 3)}  ${amp.padEnd(3)}${taps}` +
        `${pad(square((x.couplers || [])[0]), 12)}${pad(square((x.couplers || [])[1]), 12)}`).trimEnd();
    }).join('\n') + '\n<double-click or [.][LT] or [.][RT] to enter branch>';
}

// an in-line device (Qn) in the amp column, as AL004 6.8 shows Q2
function infoInline(r) {
  return `${r.branch}.${r.node}\n${'Inline EQ Type:'.padEnd(33)}${r.amp_name || ''}`;
}

function infoSupply(r) {
  return `${r.branch}.${r.node}\n\n\nPower Supply Information\n` +
    `Power Supply:${' '.repeat(30)}${r.supply_label || ''}\n` +
    `PS Type:${' '.repeat(35)}${r.supply_name || ''}`;
}

function infoAmp(r) {
  const a = r.amp_info || {};
  // showing the box trims its labels for the rest of the session
  const fresh = (a.cols || []).filter(c => !S.trimmed.has(c.key));
  if (fresh.length) { fresh.forEach(c => S.trimmed.add(c.key)); if (S.expanded) setTimeout(renderGrid, 0); }
  const line = (label, v) => `${label.padEnd(36)}${v === undefined || v === null ? '' : v}\n`;
  // an active not yet named has no Amp Name line (88 on AL004 4.2)
  return `${r.branch}.${r.node}\n` +
    (a.name ? line('Amp Name:', a.name) : '') + line('Amp Type:', a.type || r.amp_name) +
    line('Forward Pad:', a.fwd_pad) + line('Forward Eq:', a.fwd_eq) +
    line('Return Pad:', a.ret_pad) + line('Return Eq:', a.ret_eq) +
    line('Aerial Dist to Previous Active:', a.aerial_prev) +
    line('Aerial Dist to Start of Network:', a.aerial_start) +
    line('Tot Dist to Previous Act-split:', a.total_split) +
    line('Total Dist to Previous Active:', a.total_prev) +
    line('Total Dist to Start of Network:', a.total_start) +
    line('Cascade Position:', a.cascade) + line('Power Supply:', a.supply) +
    line('Housecounts downstream:', a.homes_down);
}

// Address and cable; on an amplifier's node also its distances and homes.
// As AL004 shows it: 1.1 (the fibre node) and 11.1 have the short box, 6.1
// (bridger AL00415, cascade 1) the long one.
function infoNode(r) {
  let a = r.amp_info || {};
  const line = (label, v) => `${label.padEnd(33)}${v === undefined || v === null ? '' : v}\n`;
  // a line with no active has them too, from its block: where it splits
  // (SN001_MID 1.2: all 0, 227 homes), a branch's last line (28.16) or its
  // 0-ft first line, and a supply's line -- then the supply's own lines (4.1:
  // 0 7740 0 0 7740, 0 homes, 1A).  An in-line EQ is no active.
  const blockLine = (r.node_box || !!r.supply_label) && (!r.amp || !!r.inline) &&
    !!(r.block && r.block.distances);
  if (blockLine) {
    const [ap, as, ts, tp, tt] = r.block.distances;
    a = { aerial_prev: ap, aerial_start: as, total_split: ts, total_prev: tp, total_start: tt,
          homes_down: r.block.homes };
  }
  const amp = (a.cascade || blockLine) ?
    line('Aerial Dist to Previous Active:', a.aerial_prev) +
    line('Aerial Dist to Start of Network:', a.aerial_start) +
    line('Tot Dist to Previous Act-split:', a.total_split) +
    line('Total Dist to Previous Active:', a.total_prev) +
    line('Total Dist to Start of Network:', a.total_start) +
    line('Housecounts downstream:', a.homes_down) : '';
  const ps = r.supply_label ? '\n' + infoSupply(r).split('\n').slice(1).join('\n') : '';
  // the cable's series after it, from column 15: "EX P3 625 U    Dual New
  // Build" (the older AL004's 25.2), "DROP RB 700 A  Upgrade" (5.9)
  const cab = r.cab_series ? (r.cab_name || '').padEnd(14) + ' ' + r.cab_series : (r.cab_name || '');
  return `${r.branch}.${r.node}\n${r.address || 'No Address'}\n${cab}\n` + amp +
    `<double-click or [.][ENTER] to edit address>` + ps;
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
    else if (c.key === 'amp' && r.inline) text = infoInline(r);
    else if ((c.key === 'amp' || c.key === 'ampname' || c.key === 'tsg') && r.amp_info && r.amp_info.type) text = infoAmp(r);
    else if (c.key === 'supply' && r.supply) text = infoSupply(r);
    box.textContent = text || infoNode(r);
  }
  box.hidden = !S.tips || !box.textContent;
  const total = (S.scr && S.scr.branches.length) || 1;
  $('#stBranch').textContent = `Branch ${S.branch} of ${total}`;
  // none with the cursor on a PCD (LK002's 1.5, H043A_MID's 1.1); H043B_MID,
  // joined by one too, reads "Feeder 1.1" at 7.1 and 13.1
  const cc = curCol() || { key: '' };
  const onPcd = r && !r.end && /^cplr\d$/.test(cc.key) && (r.coupler_pcds || [])[+cc.key.slice(4)];
  $('#stFeeder').textContent = onPcd ? 'No Feeder' : 'Feeder 1.1';
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
     ['9', 'Toggle', null], ['./', 'Distance', distance]],
    [['.0', 'Break', null], ['.1', 'Join', null], ['.2', 'BkFeed', null],
     ['.3', 'UnBkFd', null], ['.4', 'XFd2A', null], ['.5', 'MoveCpl', null],
     ['.6', 'XWillWk', null], ['.7', 'SetMDU', null], ['.8', 'RotTap', null],
     ['.9', 'Copy', null], ['.+', 'Name', () => ampDefinition()]],
    [['..0', 'SpcVw', null], ['..1', 'Xspec', null], ['..2', 'FwdFd', null],
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
     ['8', 'Calc', recalc], ['9', 'NodeNIU', null], ['./', 'Distance', distance]],
    [['.0', 'Break', null], ['.1', 'Join', null], ['.2', 'ApArea', null],
     ['.3', 'CarryLE', null], ['.4', 'Report', () => openReport('powering')],
     ['.5', 'CarCplr', null], ['.6', 'TstArea', null], ['.7', 'Loc Mnu', null],
     ['.8', 'NIUtest', null], ['.9', 'Br NIU', null], ['.+', 'Name', nameAmp]],
    [['..0', 'SpcVw', null], ['..1', 'Xspec', null], ['..2', 'Append', null],
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
    const put = () => queueSave(async () => {
      const out = await api(`/api/networks/${S.nid}/nodes/${at.branch}/${at.node}/tap`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot, code }) });
      msg(out.placed
        ? `${out.placed.name} — ${out.placed.ports} port, ${out.placed.value_db} dB,`
          + ` shown as the tap ID ${out.placed.tap_id}`
        : 'tap cleared');
    });
    // taking off a tap whose port feeds a branch asks first (the older
    // AL004's 11.16, 28b); Yes takes the tap off and the branch stays, fed
    // by nothing (its 43 still there after), No leaves the tap
    if ((code === '' || code === '0') && (r.tap_branches || [])[slot]) {
      modal(`<div class="msgbox"><div class="mbtitle">Deleting Branch</div>
        <div class="mbbody"><span class="mbicon warn">!</span><span>Deleting this branch will delete all downstream design.<br><br>Continue?</span></div>
        <div class="row"><button id="mbYes">Yes</button><button id="mbNo">No</button></div></div>`);
      $('#mbNo').onclick = closeModal;
      $('#mbYes').onclick = () => { closeModal(); put(); };
      $('#mbYes').focus();
      return;
    }
    put();
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
  if (SW.data) {                        // a Spec Edit window has the keys
    if (ev.key === 'Escape') closeSpecWin();
    return;
  }
  if (!$('#modal').hidden) {            // Esc closes a window, as in the program
    if (ev.key === 'Escape') closeModal();
    else if (S.modalKeys && S.modalKeys[ev.key]) { ev.preventDefault(); S.modalKeys[ev.key](); }
    return;
  }
  if (ev.key === 'NumLock' && S.modified) { ev.preventDefault(); networkModified(); return; }
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
  else if (k === 'Home' && S.buffer !== null && cols[S.col].key.startsWith('tap')) {
    ev.preventDefault(); selectTap(+cols[S.col].key.slice(3)); return;
  }
  else if (k === 'Home') { S.row = 0; }
  else if (k === 'End') { S.row = n - 1; }
  else if (k === '+' && S.mode === 'power' && !S.dot && S.buffer === null
           && cols[S.col].key === 'stop') {
    ev.preventDefault(); await togglePowerStop(); return;
  }
  else if (S.mode !== 'entry' && S.buffer === null && /^[0-9+\/]$/.test(k)) {
    // Design and Power: "0 Alter", "5 Test", ".2 BkFeed", "..5 Dsmry" ...
    ev.preventDefault();
    const dots = S.dot || 0; S.dot = false;
    if (k === '/' && !dots) { if (S.mode === 'design') toggleExpanded(); return; }
    runMenuKey('.'.repeat(dots) + k);
    return;
  }
  else if (k === '.' && S.mode !== 'entry' && S.buffer === null) {
    // "." and ". ." lead the second and third screen-menu rows, and ". →"
    // style branch moves
    ev.preventDefault();
    S.dot = Math.min(2, (S.dot || 0) + 1);
    msg(S.dot === 1 ? '.' : '. .');
    return;
  }
  else if (k === '.') {
    ev.preventDefault();
    // in a tap column the "." separates ports from value: 4.23
    if (S.buffer !== null && cols[S.col].key.startsWith('tap')) {
      S.buffer += '.'; renderGrid(); return;
    }
    // Design, after 0 Alter: ftg hc cab lv are keyed as one, "." moving on to
    // the next still keying; a field left empty keeps its value
    const i = EDIT_ORDER.indexOf(cols[S.col].key);
    if (S.buffer !== null && S.mode === 'design' && i >= 0) {
      // lv is the last: "." keeps its value and goes no further
      if (S.buffer.trim() !== '') commitBuffer(false);
      else { S.buffer = null; renderGrid(); }
      if (i < EDIT_ORDER.length - 1) {
        S.col = cols.findIndex(x => x.key === EDIT_ORDER[i + 1]);
        S.buffer = ''; msg(`Alter ${cols[S.col].head}:`); renderGrid();
      }
      return;
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
  else if (k === 'Escape') { if (S.buffer !== null) msg(''); S.buffer = null; S.dot = false; }
  else if (k === 'Insert') {
    ev.preventDefault();
    // Design: Insert adds a line above the cursor's, ". Insert" one below
    if (S.mode === 'design') { const below = !!S.dot; S.dot = false; await insertRow(below); }
    else await insertNode();
    return;
  }
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
function enterBranch(k = 0) {
  const r = curRow();
  if (!r || !r.couplers[k]) { msg('no branch begins on this node'); return; }
  // the branch number is what sits inside the brackets; a PCD's cell names
  // the other network instead, its branch kept beside it
  const m = /[[({<](\d+)[\])}>]/.exec(r.couplers[k]);
  const b = m ? +m[1] : (r.coupler_branches || [])[k];
  if (!b) { msg('no branch on this node'); return; }
  gotoBranch(b);
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
// a cable ID is series * 100 + the cable file index; the index names the cable
const pickCableById = n => libTable('cables').find(c => c.cable_index === n % 100) || null;

function modal(html) {
  $('#modalbox').innerHTML = html;
  $('#modal').hidden = false;
  S.modalKeys = null;
  const c = $('#mClose'); if (c) c.onclick = closeModal;
}
function closeModal() { $('#modal').hidden = true; S.modalKeys = null; }
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

const SELECT_BRACKETS = { 2: '//', 4: '[]', 6: '{}', 8: '<>' };
async function selectTap(slot) {
  const r = curRow(); if (!r) return;
  const out = await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}/tap/${slot}/candidates`);
  const rows = new Map();
  for (const t of out.candidates) {
    if (!rows.has(t.row)) rows.set(t.row, {});
    rows.get(t.row)[t.ports] = t;
  }
  const byId = Object.fromEntries(out.candidates.map(t => [t.id, t]));
  let sel = out.current, tab = sel ? byId[sel].ports : 2;
  const label = t => SELECT_BRACKETS[t.ports][0] + String(t.tap_id).padStart(2) + SELECT_BRACKETS[t.ports][1];
  const place = async id => {
    closeModal(); S.buffer = null;
    await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}/tap`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slot, part_id: id }) });
    await refresh();
  };
  const draw = () => {
    modal(`<div class="seltap"><div class="sttitle">Select Tap</div>
      <div class="sttabs">${[2, 4, 6, 8].map(n =>
        `<span class="sttab${n === tab ? ' on' : ''}" data-n="${n}">${n} Port</span>`).join('')}</div>
      <div class="stlist">${[...rows.values()].map(parts => `<div class="stline">${[2, 4, 6, 8].map(n => {
        const t = parts[n];
        return `<span class="stcell">${t ? `<span class="stitem ${t.severity || 'green'}${t.id === sel ? ' sel' : ''}"
          data-id="${t.id}">${esc(label(t))}</span>` : ''}</span>`;
      }).join('')}</div>`).join('')}</div>
      <div class="row"><button id="stOk" class="primary">OK</button><button id="mClose">Cancel</button></div></div>`);
    $$('.sttab').forEach(el => el.onclick = () => { tab = +el.dataset.n; mark(); });
    $$('.stitem').forEach(el => {
      // a click only moves the highlight: redrawing or scrolling here would
      // put the second click of a double-click on another tap
      el.onclick = () => { sel = el.dataset.id; tab = byId[sel].ports; mark(); };
      el.ondblclick = () => place(el.dataset.id);
    });
    $('#stOk').onclick = () => sel && place(sel);
  };
  // the highlighted tap, and the tab showing its port count
  const mark = (scroll) => {
    $$('.sttab').forEach(el => el.classList.toggle('on', +el.dataset.n === tab));
    $$('.stitem').forEach(el => el.classList.toggle('sel', el.dataset.id === sel));
    const on = $('.stitem.sel'); if (scroll && on) on.scrollIntoView({ block: 'center' });
  };
  draw();
  mark(true);
  // arrows move within the chosen port count; Enter takes the highlighted tap
  const column = () => out.candidates.filter(t => t.ports === tab);
  const keys = ev => {
    if ($('#modal').hidden) { document.removeEventListener('keydown', keys, true); return; }
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
      const list = column(); if (!list.length) return;
      const i = list.findIndex(t => t.id === sel);
      const j = i < 0 ? 0 : Math.max(0, Math.min(list.length - 1, i + (ev.key === 'ArrowDown' ? 1 : -1)));
      sel = list[j].id; mark(true); ev.preventDefault(); ev.stopPropagation();
    } else if (ev.key === 'Enter' && sel) { ev.preventDefault(); ev.stopPropagation(); place(sel); }
  };
  document.addEventListener('keydown', keys, true);
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
// Design: a line with 0 footage above the cursor's (Insert) or below it
// (". Insert"); the cursor stays on its node, so each press adds another
async function insertRow(below) {
  const r = curRow(); if (!r || r.end) return;
  await api(`/api/networks/${S.nid}/branches/${r.branch}/nodes`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(Object.assign(below ? { after: r.node } : { before: r.node },
                                       { cable_from_previous: true })) });
  await refresh();
  if (!below) S.row = Math.min(S.row + 1, pageRows().length - 1);
  renderGrid();
}
// ".+ Name" with the cursor on an amplifier: the Amplifier Definition window.
// The name belongs to the amplifier: it shows in tap1 until a tap is placed
// there and stays with the amplifier either way.  An amplifier not yet named
// is offered the last name given; + and - in the field step its number
// (AL00410 -> AL00411).  Two actives cannot share a name, in any case: the
// window closes and "Amp Exists" says where the name is.
function stepName(name, by) {
  const m = /^(.*?)(\d+)(\D*)$/.exec(name);
  if (!m) return name;
  const n = Math.max(0, parseInt(m[2], 10) + by);
  return m[1] + String(n).padStart(m[2].length, '0') + m[3];
}
function ampExists(name, at) {
  modal(`<div class="msgbox"><div class="mbtitle">Amp Exists</div>
    <div class="mbbody"><span class="mbicon">\u2715</span><span>Amplifier ${esc(name)} already exists at ${esc(at)}.</span></div>
    <div class="row"><button id="mbOk">OK</button></div></div>`);
  $('#mbOk').onclick = closeModal; $('#mbOk').focus();
}
function ampDefinition() {
  const r = curRow(), c = curCol();
  if (!r || r.end || !c || c.key !== 'amp' || !r.amp_info || r.amp_info.name === undefined) return;
  modal(`<div class="ampdef"><div class="adtitle">Amplifier Definition</div>
    <div class="adrow"><span class="adlab">Power Supply:</span><span>${esc(r.amp_info.supply || '')}</span></div>
    <div class="adrow"><span class="adlab">Amp ID:</span><input id="adName"></div>
    <div class="row"><button id="adOk">OK</button></div>
    <div class="adstatus">Enter Amplifier name.</div></div>`);
  const input = $('#adName');
  input.value = r.amp_label || S.lastAmpName || '';
  input.focus(); input.select();
  const ok = async () => {
    const name = input.value;
    const other = name && S.scr.rows.find(x => !x.end && x.amp_info && x.amp_info.name !== undefined
      && (x.amp_label || '').toLowerCase() === name.toLowerCase()
      && !(x.branch === r.branch && x.node === r.node));
    if (other) { ampExists(name, `${other.branch}.${other.node}`); return; }
    closeModal();
    S.lastAmpName = name;
    await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amp_label: name }) });
    await refresh();
  };
  $('#adOk').onclick = ok;
  input.onkeydown = ev => {
    if (ev.key === 'Enter') { ev.preventDefault(); ok(); }
    else if (ev.key === '+' || ev.key === '-') {
      ev.preventDefault();
      input.value = stepName(input.value, ev.key === '+' ? 1 : -1); input.select();
    }
  };
}
// The Delete key, as the program does it (the user's recording): a line
// with a power stop is refused; a line a branch begins at asks first, and OK
// deletes the line with the branch and everything down it.
async function deleteNode() {
  const r = curRow(); if (!r || r.end) return;
  const url = `/api/networks/${S.nid}/branches/${r.branch}/nodes/${r.node}`;
  try {
    await api(url, { method: 'DELETE' });
  } catch (e) {
    let d = null;
    try { d = JSON.parse(e.message).detail; } catch (_) { throw e; }
    if (d && d.error) { errorBox(d.error); return; }
    if (d && d.branches) {
      // one branch: "Branch 54, begins ... this branch"; two: "Branches
      // 11, 12, begin ... these branches" (AL004 4.14, the user)
      const many = d.branches.length > 1;
      const which = d.branches.join(', ');
      modal(`<div class="msgbox"><div class="mbtitle">Delete Branch(es)?</div>
        <div class="mbtext">${many ? 'Branches' : 'Branch'} ${esc(which)}, ${many ? 'begin' : 'begins'} at this node.<br>` +
        `Deleting this node will delete ${many ? 'these branches' : 'this branch'}<br>` +
        `and all downstream nodes.<br>Delete this node?</div>
        <div class="row"><button id="mbOk">OK</button><button id="mbCancel">Cancel</button></div></div>`);
      $('#mbCancel').onclick = closeModal;
      $('#mbOk').onclick = async () => {
        closeModal();
        await api(url + '?confirm=true', { method: 'DELETE' });
        await refresh(); msg('node deleted');
      };
      $('#mbOk').focus();
      return;
    }
    throw e;
  }
  await refresh(); msg('node deleted');
}
// Num Lock on a network changed since it was opened or saved: the program's
// "Network Modified" box (the user's 33, the older AL004 after an ftg
// change): [3] Restore, [7] Save, [9] Switch, Close; 3, 7 and 9 pick them
function networkModified() {
  const choices = { '3': ['Restore', NYI('Restore')], '7': ['Save', () => saveNetwork(false)],
                    '9': ['Switch', NYI('Switch')] };
  modal(`<div class="msgbox nmod"><div class="mbtitle">Network Modified</div>
    ${Object.entries(choices).map(([k, [t]]) =>
      `<div><a href="#" class="nmlink" data-k="${k}">[${k}] ${t}</a></div>`).join('')}
    <div class="row nmrow"><button id="mClose">Close</button></div></div>`);
  const pick = k => { closeModal(); choices[k][1](); };
  $$('#modalbox .nmlink').forEach(a => a.onclick = e => { e.preventDefault(); pick(a.dataset.k); });
  S.modalKeys = { '3': () => pick('3'), '7': () => pick('7'), '9': () => pick('9') };
  $('#mClose').focus();
}
function errorBox(text) {
  modal(`<div class="msgbox"><div class="mbtitle">Error</div>
    <div class="mbtext">${esc(text)}</div>
    <div class="row"><button id="mbOk">OK</button></div></div>`);
  $('#mbOk').onclick = closeModal; $('#mbOk').focus();
}
// Powering: "+" on the power-stop column puts a stop there, "+" again takes
// it off (the user's recording, AL002 55.2)
async function togglePowerStop() {
  const r = curRow(); if (!r || r.end) return;
  await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ power_stop: !r.power_stop }) });
  await refresh();
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
// 0 Alter: the cell takes a typed value, Enter keeps it, Esc drops it.  On a
// tap the status line reads as the program's does, and Home lists the taps.
const ALTER_PROMPT = { tap: 'Enter desired tap {# of ports}.{ID #}:    [home] for list' };
function alter() {
  const r = curRow(), c = curCol();
  if (!r || !c || r.end || !c.edit) { msg('nothing to alter here'); return; }
  S.buffer = '';
  // only the tap prompt is known from the program; the others are placeholders
  msg(c.key.startsWith('tap') ? ALTER_PROMPT.tap : `Alter ${c.head}:`);
  renderGrid();
}
// a screen-menu key as typed: "5", ".2", "..5", "./"
function runMenuKey(key) {
  for (const row of MENUS[S.mode] || [])
    for (const [k, label, fn] of row)
      if (k === key) { if (fn) fn(); else msg(`${k} ${label} — not implemented yet`); return true; }
  return false;
}
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
// Test (screen menu 5): the "Design Assistant Test Results" window, one line
// per problem found at a tap -- red beyond the tap margin, yellow within it,
// over a tap window or crossed over.  Esc closes it.
function test() {
  if (S.mode === 'power') return testPower();
  const tests = (S.scr && S.scr.tests) || [];
  const net = (S.net && S.net.name) || '';
  modal(`<div class="testres">
    <div class="trtitle">Design Assistant Test Results - ${tests.length} Errors</div>
    <table><thead><tr><th>Number</th><th>Network</th><th>Error</th></tr></thead><tbody>${
      tests.map((t, i) => `<tr class="${t.severity}"><td>${i + 1}</td><td>${esc(net)}</td>` +
        `<td>${esc(t.message)}</td></tr>`).join('')}</tbody></table></div>
    <div class="row"><button id="mClose" class="primary">Close</button></div>`);
}
function testPower() {
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
// Lode's Edit Notes window: the line's note, a line per row.  The file
// keeps each row followed by "~0" (SN001_MID 1.1: SHIN1 - 4953 - P-003938~0
// POWERED BY PS "PS1A"~0DATE :02/20/26~0, three rows in the window).
async function notes() {
  const r = curRow(); if (!r) return;
  const rows = (r.note || '').split('~0');
  if (rows.length && rows[rows.length - 1] === '') rows.pop();
  modal(`<h2>Edit Notes</h2>
    <textarea id="noteText" rows="10" style="width:100%;font-family:inherit"
      spellcheck="false">${esc(rows.join('\n'))}</textarea>
    <p class="hint">Branch: ${r.branch} &nbsp; Node: ${r.node}</p>
    <div class="row"><button class="primary" id="noteOk">OK</button>
      <button id="mClose">Cancel</button></div>`);
  $('#noteText').focus();
  $('#noteOk').onclick = async () => {
    const lines = $('#noteText').value.replace(/\r/g, '').replace(/\n+$/, '');
    const note = lines ? lines.split('\n').map(l => l + '~0').join('') : '';
    closeModal();
    await api(`/api/networks/${S.nid}/nodes/${r.branch}/${r.node}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note }) });
    await refresh(); msg('note saved');
  };
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
    ['Save Network', () => saveNetwork(false)],
    ['Save Network As...', () => saveNetwork(true)],
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
    ['Parameters...', () => specEdit('par')], ['Actives...', () => specEdit('atv')],
    ['Taps...', () => specEdit('tap')], ['Couplers...', () => specEdit('cpr')], ['Cables...', () => specEdit('cbl')],
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
         ['Show Tips', () => { S.tips = !S.tips; renderInfo(); }, () => S.tips]],
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
    const [label, act, checked] = it;
    const [text, key] = label.split('\t');
    return `<div class="di${Array.isArray(act) ? ' sub' : ''}" data-i="${i}">` +
      (checked ? `<span class="chk">${checked() ? '\u2713' : ''}</span>` : '') +
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

// File > Project Settings: where a network's spec files are chosen.  As the
// program lays it out (the user's recordings): File and Set All menus, the
// folders, Spec Files with Set All Files and a line a file, Misc Folders, and
// Show on startup.  Set All Files takes one spec set and fills every line
// with its name; OK loads it and shows "Errors Loading Project".
const PS_FILES = [['Parameters File', '.par'], ['Actives File', '.atv'], ['Taps File', '.tap'],
  ['Couplers File', '.cpr'], ['Cables File', '.cbl'], ['Pricing File', ''],
  ['Performance File', ''], ['Map Grid File', '']];
// the spec set loaded, "" for none (the program's Untitled)
function specName(lib) {
  lib = lib || (S.net && S.net.library) || {};
  const parts = ['cables', 'taps', 'passives', 'actives'].some(t => Object.keys(lib[t] || {}).length);
  return parts ? (lib.name || '') : '';
}
function showOnStartup() {
  try { return localStorage.getItem('ps.startup') !== '0'; } catch (_) { return true; }
}
function projectSettings() {
  const loaded = specName();
  const row = (label, file, id) => `<div class="ps-row"><span>${label}:</span>` +
    `<input type="text" readonly value="${esc(file)}"${id ? ` id="${id}"` : ''}>` +
    `<button disabled>Browse...</button></div>`;
  modal(`<div class="ps"><div class="pstitle">Project Settings</div>
      <div class="psmenu"><span>File</span><span>Set All</span></div>
      <div class="pstools"><span title="New">&#128462;</span><span title="Open">&#128194;</span>` +
      `<span title="Save">&#128190;</span></div>
      <fieldset>${row('Network Folder', '')}${row('PCD Folder', '')}</fieldset>
      <fieldset><legend>Spec Files</legend>
        <button id="psSetAll">Set All Files</button>
        <input type="file" id="psFiles" multiple hidden accept=".par,.atv,.tap,.cpr,.cbl,.prc,.per">
        ${PS_FILES.map(([label, ext], k) => row(label, loaded && ext ? loaded + ext : '', 'psf' + k)).join('')}
      </fieldset>
      <fieldset><legend>Misc Folders</legend>
        <button disabled>Set All Folders</button>
        ${row('Control File Folder', '')}${row('Report File Folder', '')}
      </fieldset>
      <p class="ps-note">Set All Files takes one spec set: the .par .atv .tap .cpr .cbl
      files that share a base name. Or <a href="#" id="psSample">use the sample specs</a>
      (not for real design).</p>
      <div class="row psfoot"><label><input type="checkbox" id="psStartup"${showOnStartup() ? ' checked' : ''}>
        Show on startup</label>
        <button class="primary" id="psOk">OK</button><button id="psCancel">Cancel</button></div>
    </div>`);
  let files = null;
  $('#psCancel').onclick = closeModal;
  $('#psStartup').onchange = e => {
    try { localStorage.setItem('ps.startup', e.target.checked ? '1' : '0'); } catch (_) {}
  };
  $$('.psmenu span, .pstools span').forEach(x => x.onclick = () => msg(`${x.textContent || x.title}: not yet`));
  $('#psSetAll').onclick = () => $('#psFiles').click();
  $('#psSample').onclick = async e => { e.preventDefault(); closeModal(); await sampleSpecs(); };
  $('#psFiles').onchange = () => {
    files = [...$('#psFiles').files];
    if (!files.length) return;
    // every line takes the set's name, as the program's Set All Files does
    const base = files[0].name.replace(/\.[^.]*$/, '');
    PS_FILES.forEach(([, ext], k) => { $('#psf' + k).value = base + ext; });
  };
  $('#psOk').onclick = async () => {
    if (!files || !files.length) { closeModal(); return; }
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    const out = await api(`/api/networks/${S.nid}/library/spec`, { method: 'POST', body: fd });
    await reload();
    errorsLoading(out.errors || []);
  };
}

// The program's box after Project Settings' OK: a line a file.
function errorsLoading(lines) {
  modal(`<div class="msgbox"><div class="mbtitle">Errors Loading Project</div>
    <div class="errlines">${lines.map(l => `<div>${esc(l)}</div>`).join('')}</div>
    <div class="row errfoot"><button id="mbOk">OK</button>
      <span class="anykey">or Press any key to continue..</span></div></div>`);
  const done = () => { document.removeEventListener('keydown', key, true); closeModal(); };
  const key = e => { e.preventDefault(); e.stopPropagation(); done(); };
  document.addEventListener('keydown', key, true);
  $('#mbOk').onclick = done; $('#mbOk').focus();
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
   <p>The <b>mouse wheel</b> moves the cursor up and down the branch on
   screen. Double-click a coupler to go into its branch; turning the wheel up
   on that branch's first line comes back to the coupler's line.</p>
   <p>The numbered bars are the screen menu — click them or use the menu bar.</p>
   <div class="row"><button id="mClose" class="primary">Close</button></div>`);
}

// ---------------------------------------------------------------- files
// The last network this page opened from a .ntw: one keyed in from scratch
// here is written with that file's licence and user fields, as the program
// on the person's own PC would -- not someone else's on the server.  Held
// only while the page is open: nothing about a network is kept after it
// (the user).
let openedLast = null;
function lastOpened() { return openedLast; }
async function newNetwork() {
  const name = prompt('Name for the new network', 'lode-1'); if (!name) return;
  const d = await api('/api/networks', { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, sample_specs: false, header_from: lastOpened() }) });
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
// ---------------------------------------------------------------- Spec Edit
// Spec Edit > Parameters, Actives, Taps, Couplers, Cables: the program's own
// windows, tab for tab and column for column (the user's recordings of
// NBERN1GHz's and BH1GHzMid's Actives, BH1GHzMid's Taps and HUMB1GHzMid's
// Couplers windows, WV750's six Parameters tabs, WVEXT862's Cables), filled from
// the network's spec file itself, every record of it.  Shown as they are:
// nothing here edits a spec file, so Load and Cancel both close the window.
const SW = { data: null, tab: 0, sub: {}, note: '' };

async function specEdit(ext) {
  if (!S.nid) return;
  let w;
  try { w = await api(`/api/networks/${S.nid}/specs/${ext}`); }
  catch (e) {
    let text = e.message;
    try { text = JSON.parse(text).detail; } catch (_) {}
    msg(text); return;
  }
  SW.data = w; SW.tab = 0; SW.sub = {}; SW.note = '';
  renderSpecWin();
}
function closeSpecWin() {
  const el = $('#specwin'); if (el) el.remove();
  SW.data = null;
}
const SW_ICONS = [
  // New, Open, Save, Print, as the window's toolbar draws them
  '<svg viewBox="0 0 18 18"><path d="M4 2h7l3 3v11H4z" fill="#fff" stroke="#333"/><path d="M11 2v3h3" fill="none" stroke="#333"/><path d="M3 1l1.5 2M1 4h2.5M5.5 1l-.5 2" stroke="#e0b000"/><path d="M6 8h6M6 10h6M6 12h6" stroke="#888"/></svg>',
  '<svg viewBox="0 0 18 18"><path d="M1 5h5l1 1h8v9H1z" fill="#f2c94c" stroke="#7a5a00"/><path d="M3 15l2-6h12l-2 6z" fill="#f7dc80" stroke="#7a5a00"/></svg>',
  '<svg viewBox="0 0 18 18"><rect x="2" y="2" width="14" height="14" fill="#222"/><rect x="5" y="3" width="8" height="5" fill="#fff"/><rect x="5" y="11" width="8" height="5" fill="#666"/></svg>',
  '<svg viewBox="0 0 18 18"><rect x="5" y="2" width="8" height="5" fill="#fff" stroke="#333"/><rect x="2" y="7" width="14" height="6" fill="#ccc" stroke="#333"/><rect x="5" y="11" width="8" height="5" fill="#fff" stroke="#333"/></svg>',
];

// a tab control with more tabs than fit: rows, each filled out to the
// width, and the row holding the chosen tab drawn last, next to the page
// (NBERN1GHz's Actives window: "Actives ... EQs Bank 13" under "EQs Bank
// 14 ... Booster Powering" until a tab of that row is picked)
let swCanvas = null;
function textWidth(t) {
  swCanvas = swCanvas || document.createElement('canvas').getContext('2d');
  swCanvas.font = '11px "Microsoft Sans Serif", Tahoma, Arial, sans-serif';
  return swCanvas.measureText(t).width;
}
function tabRows(names, width, sel) {
  const rows = [[]];
  let used = 0;
  names.forEach((n, i) => {
    const w = Math.ceil(textWidth(n)) + 18;
    if (used + w > width && rows[rows.length - 1].length) { rows.push([]); used = 0; }
    rows[rows.length - 1].push(i); used += w;
  });
  const at = rows.findIndex(r => r.includes(sel));
  return rows.slice(at + 1).concat(rows.slice(0, at + 1));
}

function swGrid(g, cls, plain) {
  const cols = g.cols;
  const total = cols.reduce((a, c) => a + c.w, 0);
  return `<div class="sw-gridbox${cls ? ' ' + cls : ''}"><table class="sw-t${plain ? ' plain' : ''}" style="width:${total}px">` +
    `<colgroup>${cols.map(c => `<col style="width:${c.w}px">`).join('')}</colgroup>` +
    `<thead><tr>${cols.map(c => `<th>${esc(c.head)}</th>`).join('')}</tr></thead><tbody>` +
    // a cell's own colour: the Cables window's Series/Colors, each series'
    // name in the colour the cable file gives it
    g.rows.map((r, k) => `<tr>${r.map((v, i) => `<td${cols[i] && cols[i].cls ? ` class="${cols[i].cls}"` : ''}` +
      `${g.colors && g.colors[k] && g.colors[k][i] ? ` style="color:${g.colors[k][i]}"` : ''}>${esc(v)}</td>`).join('')}</tr>`).join('') +
    '</tbody></table></div>';
}

function renderSpecWin() {
  const w = SW.data; if (!w) return;
  let el = $('#specwin');
  if (!el) {
    el = document.createElement('div');
    el.id = 'specwin'; el.className = 'specwin';
    document.body.appendChild(el);
  }
  const tab = w.tabs[SW.tab] || w.tabs[0];
  const names = w.tabs.map(t => t.name);
  const rows = tabRows(names, Math.max(300, window.innerWidth - 8), SW.tab);
  el.innerHTML =
    `<div class="sw-title"><span class="sw-ico"></span><span class="sw-name">${esc(w.title)}</span>` +
    `<span class="sw-wb"><span>&#x2014;</span><span>&#x2610;</span><span class="x" id="swX">&#x2715;</span></span></div>` +
    `<div class="sw-menu">${w.menus.map(m => `<span>${esc(m)}</span>`).join('')}</div>` +
    `<div class="sw-tools">${SW_ICONS.map(s => `<span>${s}</span>`).join('')}</div>` +
    `<div class="sw-tabs">${rows.map(r => `<div class="sw-tabrow${rows.length === 1 ? ' single' : ''}">${r.map(i =>
      `<span class="sw-tab${i === SW.tab ? ' sel' : ''}" data-tab="${i}">${esc(names[i])}</span>`).join('')}</div>`).join('')}</div>` +
    `<div class="sw-page" id="swPage">${swPage(w, tab)}</div>` +
    `<div class="sw-bottom"><button class="def" id="swLoad">Load</button><button id="swCancel">Cancel</button></div>` +
    `<div class="sw-status" id="swStatus">${esc(SW.note)}</div>`;
  el.querySelectorAll('.sw-tabs .sw-tab').forEach(t => t.onclick = () => {
    SW.tab = +t.dataset.tab; SW.note = SW.data.tabs[SW.tab].note || ''; renderSpecWin();
  });
  el.querySelectorAll('.sw-subtabs .sw-tab').forEach(t => t.onclick = () => {
    SW.sub[SW.tab] = +t.dataset.sub; renderSpecWin();
  });
  el.querySelectorAll('.sw-menu span, .sw-tools span').forEach(m => m.onclick = () => {
    $('#swStatus').textContent = 'Shown only: editing and saving spec files is not done yet.';
  });
  $('#swX').onclick = $('#swLoad').onclick = $('#swCancel').onclick = closeSpecWin;
  // a cell clicked is the cursor's, as the program marks it
  el.querySelectorAll('table.sw-t tbody').forEach(tb => tb.onclick = e => {
    const td = e.target.closest('td'); if (!td || td.cellIndex === 0) return;
    el.querySelectorAll('td.cur').forEach(c => c.classList.remove('cur'));
    td.classList.add('cur');
  });
}

function swPage(w, tab) {
  if (tab.unseen) {
    return `<div class="sw-unseen">${esc(tab.name)}: not seen in Lode yet — a screenshot of this tab will show what it holds.</div>`;
  }
  if (w.kind === 'par') return parPage(tab.name, w.values);
  if (tab.sub) {
    const k = SW.sub[SW.tab] || 0, s = tab.sub[k];
    return `<div class="sw-subtabs">${tab.sub.map((t, i) =>
      `<span class="sw-tab${i === k ? ' sel' : ''}" data-sub="${i}">${esc(t.name)}</span>`).join('')}</div>` +
      `<div class="sw-subpage"><div class="sw-prefix">Prefix: <input readonly value="${esc(s.prefix)}"></div>` +
      swGrid(s.grid, 'prefixed') + '</div>';
  }
  if (tab.prefix !== undefined) {
    return `<div class="sw-prefix">Prefix: <input readonly value="${esc(tab.prefix)}"></div>` +
      swGrid(tab.grid, 'prefixed');
  }
  return swGrid(tab.grid, '', tab.plain);
}

// The Parameters tabs: each field where WV750's screenshots have it.  Those
// are at 125 %: x, y there, less the page's top (117), times 0.8.
function parPage(name, v) {
  const X = x => Math.round(x * 0.8), Y = y => Math.round((y - 117) * 0.8);
  // a group box's line is at its title's middle: y is that line
  const box = (x, y, x2, y2, title, inner = '') =>
    `<fieldset style="left:${X(x)}px;top:${Y(y) - 7}px;width:${X(x2 - x)}px;height:${X(y2 - y) + 7}px">` +
    `<legend>${esc(title)}</legend></fieldset>${inner}`;
  const lab = (x, y, t, right) => right
    ? `<span class="lb r" style="right:calc(100% - ${X(x)}px);top:${Y(y) - 8}px">${esc(t)}</span>`
    : `<span class="lb" style="left:${X(x)}px;top:${Y(y) - 8}px">${esc(t)}</span>`;
  const inp = (x, y, x2, val, off) =>
    `<input class="sw-in${off ? ' off' : ''}" readonly style="left:${X(x)}px;top:${Y(y) - 10}px;width:${X(x2 - x)}px" value="${esc(val)}">`;
  const ck = (x, y, t, on, kind = 'checkbox', after = true) =>
    `<label class="ck" style="left:${X(x)}px;top:${Y(y) - 8}px">${after ? '' : esc(t)}` +
    `<input type="${kind}" ${on ? 'checked' : ''} onclick="return false">${after ? esc(t) : ''}</label>`;
  const grid = (x, y, x2, y2, cols, rows) =>
    `<div style="position:absolute;left:${X(x)}px;top:${Y(y)}px;width:${X(x2 - x)}px;height:${X(y2 - y)}px">` +
    swGrid({ cols: cols.map(([head, w]) => ({ head, w: X(w) })), rows }, '', true) + '</div>';
  let h = '';
  if (name === 'General Parameters') {
    h += box(27, 143, 264, 340, 'Display Options');
    h += box(38, 177, 252, 215, 'Distance Units') + ck(55, 199, 'Ftg', v.distance_units === 'Ftg', 'radio') +
      ck(118, 199, 'm', v.distance_units === 'm', 'radio') + ck(182, 199, 'dM', v.distance_units === 'dM', 'radio');
    h += box(38, 234, 252, 272, 'Signal Display') + ck(55, 253, 'dBmv', v.signal_display === 'dBmV', 'radio') +
      ck(182, 253, 'dBuv', v.signal_display === 'dBuV', 'radio');
    h += ck(55, 308, 'Show Count Types', v.show_count_types);
    h += box(277, 143, 524, 340, 'Strand/Trench Types');
    for (let k = 0; k < 6; k++) h += ck(305, 164 + 24.4 * k, `${k}00 Series`, v.strand_series.includes(k));
    for (let k = 6; k < 10; k++) h += ck(421, 164 + 24.4 * (k - 6), `${k}00 Series`, v.strand_series.includes(k));
    h += box(537, 143, 860, 340, 'NIU Settings');
    [['System Penetration %:', 'system_penetration', 169], ['Offhook %:', 'offhook', 205],
     ['Ring %:', 'ring', 242], ['Additional Line %:', 'additional_line', 279],
     ['Offhook Limit:', 'offhook_limit', 316]].forEach(([t, k, y]) => {
      h += lab(715, y, t, true) + inp(719, y, 791, v.niu[k] ?? '0.00');
    });
    h += box(27, 368, 264, 514, 'Inline Equalization') + lab(173, 393, 'Max. Crossover:', true) +
      inp(179, 393, 252, v.max_crossover) + lab(173, 431, 'Max Return Crossover:', true) +
      inp(179, 431, 252, v.max_return_crossover);
    h += box(38, 463, 252, 501, 'Default EQ Placement') + ck(55, 485, 'EQ+', v.eq_placement === 'EQ+', 'radio') +
      ck(118, 485, 'EQ-', v.eq_placement === 'EQ-', 'radio') + ck(182, 485, 'EQe', v.eq_placement === 'EQe', 'radio');
    h += box(277, 368, 424, 514, 'Replacement Cables') + lab(357, 393, 'Backfeed:', true) +
      inp(366, 393, 408, v.replacement_cables.backfeed ?? 0) + lab(357, 431, 'Fwd. Feed:', true) +
      inp(366, 431, 408, v.replacement_cables.fwd_feed ?? 0);
    h += box(438, 368, 746, 514, 'Miscellaneous Part Numbers') + lab(551, 393, 'HTH Connectors:', true) +
      inp(555, 393, 742, v.misc_parts.hth_connectors || '') + lab(551, 431, 'Splices:', true) +
      inp(555, 431, 742, v.misc_parts.splices || '') + lab(551, 469, 'Terminators:', true) +
      inp(555, 469, 742, v.misc_parts.terminators || '');
    h += lab(873, 393, 'Lines per Form:', true) + inp(879, 393, 921, v.lines_per_form) +
      lab(873, 431, 'Max. Tap Cascade:', true) + inp(879, 431, 921, v.max_tap_cascade) +
      lab(873, 469, 'Max. LE Cascade:', true) + inp(879, 469, 921, v.max_le_cascade);
    h += ck(757, 503, 'Allow Over Equalization ', v.allow_over_equalization, 'checkbox', false);
  } else if (name === 'System Levels') {
    h += lab(18, 147, 'Tap Margin:') + inp(99, 147, 171, v.tap_margin);
    h += lab(18, 182, 'Forward Tap Window:') + grid(20, 203, 187, 950, [['Frequency', 95], ['Window', 72]], v.forward_windows);
    h += lab(215, 182, 'Return Tap Window:') + grid(230, 203, 397, 950, [['Frequency', 95], ['Window', 72]], v.return_windows);
    const w = [54, 86, 74, 80, 67, 86, 74, 74, 73, 85, 85, 128, 120, 120, 114];
    h += lab(413, 182, 'Levels:') + grid(413, 203, 1910, 950, v.level_cols.map((c, i) => [c, w[i]]), v.level_rows);
  } else if (name === 'Tap Selection') {
    h += box(18, 139, 226, 193, 'Optimization') + ck(37, 167, 'OP-', v.optimization === 'OP-', 'radio') +
      ck(100, 167, 'OP+', v.optimization === 'OP+', 'radio') + ck(163, 167, 'OFf', v.optimization === 'OFf', 'radio');
    h += ck(253, 167, 'Enforce Tap Window', v.enforce_tap_window) + ck(452, 167, 'Enforce Tap Tilt', v.enforce_tap_tilt) +
      ck(638, 167, 'Flag Hi/Lo Tilt', v.flag_hi_lo_tilt);
    h += grid(20, 210, 248, 950, [['Homes', 60], ['Number of Ports', 143]], v.ports_by_homes.map(r => r.map(String)));
    h += grid(283, 210, 511, 950, [['Ports', 45], ['Tap Type', 85]], v.tap_type_by_ports.map(r => r.map(String)));
  } else if (name === 'Powering') {
    // its screenshot was taken 5 px higher than the other five: + 5
    const P = y => y + 5;
    h += box(18, P(128), 168, P(258), 'Power Interpolation') +
      ck(37, P(163), 'Step', v.power_interpolation === 'step', 'radio') +
      ck(37, P(194), 'Linear', v.power_interpolation === 'linear', 'radio') +
      ck(37, P(225), 'Constant Wattage', v.power_interpolation === 'constant_wattage', 'radio');
    h += box(18, P(274), 168, P(371), 'Overvoltage Check') + ck(37, P(307), 'Off', !v.overvoltage_check, 'radio') +
      ck(37, P(340), 'On', v.overvoltage_check, 'radio');
    h += box(180, P(128), 375, P(371), 'Maximum Amperage Through');
    [['Power Inserter:', 'power_inserter', 162], ['Amplifier:', 'amplifier', 199], ['Bridger Port:', 'bridger_port', 236],
     ['Coupler:', 'coupler', 272], ['Line Extender:', 'line_extender', 308], ['Tap:', 'tap', 345]].forEach(([t, k, y]) => {
      h += lab(280, P(y), t, true) + inp(292, P(y), 364, v.max_amps_through[k] ?? '0.00');
    });
    h += box(18, P(393), 375, P(480), 'Pre Load/Test Attached Networks') + ck(37, P(416), 'Off', !v.pre_load, 'radio') +
      ck(37, P(448), 'On', v.pre_load, 'radio');
    h += lab(387, P(128), 'Transformers:') + grid(387, P(148), 704, 950, [['ID #', 67], ['Part Number', 190], ['Voltage', 60]],
      v.transformers.map(r => r.map(String)));
    h += lab(715, P(128), 'Power Supplies:') + grid(716, P(148), 1910, 950,
      [['ID #', 68], ['Part Number', 188], ['Voltage Rating', 131], ['Current Rating', 127], ['% Capacity', 97]],
      v.supplies.map(r => r.map(String)));
  } else if (name === 'Underground Housings') {
    h += box(18, 133, 227, 421, 'Equipment Size - Point Values');
    [['Amplifier:', 'amplifier', 166], ['Line Extender:', 'line_extender', 205], ['2, 4, 6 Port Tap:', 'tap', 242],
     ['8 Port Tap:', 'tap_8_port', 281], ['Coupler:', 'coupler', 320], ['Power Suppy:', 'power_supply', 358],
     ['Equalizer:', 'equalizer', 397]].forEach(([t, k, y]) => {
      h += lab(128, y, t, true) + inp(139, y, 211, v.points[k] ?? 0);
    });
    h += grid(243, 127, 1910, 950, [['Housing Number', 147], ['Part Number', 189], ['Minimum Size (Points)', 191]],
      v.housings.map(r => r.map(String)));
  } else if (name === 'Frequencies') {
    h += box(18, 141, 204, 380, 'Forward Frequencies') + lab(107, 172, 'High:', true) + inp(117, 172, 189, v.forward[0][0]) +
      lab(107, 208, 'Low:', true) + inp(117, 208, 189, v.forward[1][0]);
    v.forward.slice(2).forEach(([t, on], i) => {
      const y = 243 + 37 * i;
      h += ck(34, y, `Freq. ${i + 3}:`, on) + inp(117, y, 189, t, !on);
    });
    h += box(217, 141, 403, 380, 'Return Frequencies') + lab(306, 172, 'High:', true) + inp(316, 172, 388, v.return[0][0]) +
      lab(306, 208, 'Low:', true) + inp(316, 208, 388, v.return[1][0]);
    v.return.slice(2).forEach(([t, on], i) => {
      const y = 243 + 37 * i;
      h += ck(233, y, `Freq. ${i + 3}:`, on) + inp(316, y, 388, t, !on);
    });
    h += box(418, 141, 617, 380, 'Freqs. for Active EQ Selection');
    [['Fwd High:', 'fwd_high', 170], ['Fwd. Low:', 'fwd_low', 206], ['Ret. High:', 'ret_high', 242],
     ['Ret. Low:', 'ret_low', 278]].forEach(([t, k, y]) => {
      h += lab(505, y, t, true) +
        `<select class="sw-in" tabindex="-1" onmousedown="return false" style="left:${X(516)}px;top:${Y(y) - 10}px;width:${X(85)}px">` +
        `<option>${esc(v.eq_selection[k] || '')}</option></select>`;
    });
  }
  return `<div class="sw-form">${h}</div>`;
}

function importNtw() {
  modal(`<h2>Import a .ntw network file</h2>
    <p>A .ntw refers to its equipment by position in the spec files. Pick the
    spec set it was saved with as well (.par .atv .tap .cpr .cbl), or open the
    .ntw alone, as the program does, and attach the set afterwards through
    File &rarr; Project Settings &rarr; Set All Files.</p>
    <label>Network file <input type="file" id="ntwFile" accept=".ntw"></label>
    <label>Spec set <input type="file" id="ntwSpecs" multiple
      accept=".par,.atv,.tap,.cpr,.cbl,.prc,.per"></label>
    <div class="row"><button class="primary" id="ntwGo">Import</button>
      <button id="mClose">Cancel</button></div><pre id="ntwOut"></pre>`);
  // picked through the browser's file access where it has it, so that
  // Save Network can write straight back into this file
  let picked = null;
  if (window.showOpenFilePicker) $('#ntwFile').onclick = async e => {
    e.preventDefault();
    try {
      const [h] = await window.showOpenFilePicker({ types: NTW_TYPES });
      const dt = new DataTransfer();
      dt.items.add(await h.getFile());
      $('#ntwFile').files = dt.files;
      picked = h;
    } catch (_) {}
  };
  $('#ntwGo').onclick = async () => {
    const f = $('#ntwFile').files[0]; if (!f) return;
    const fd = new FormData(); fd.append('file', f);
    for (const s of $('#ntwSpecs').files) fd.append('specs', s);
    const out = await api('/api/import/ntw', { method: 'POST', body: fd });
    if (!out.imported) {
      $('#ntwOut').textContent = `${out.network || f.name}: ${out.branches} branches, ` +
        `${out.nodes} nodes.\nIt was saved with spec set ${out.spec_set_needed} — ` +
        `pick those five files and import again.` +
        (out.mismatch && out.mismatch.length ? '\n\nSpec File Mismatch\n' +
          out.mismatch.map(([what, text]) => `${(what + ':').padStart(13)}  ${text}`).join('\n') : '');
      return;
    }
    const r = out.report;
    openedLast = out.id;
    if (picked && picked.name === f.name) await keepFile(out.id, picked);
    closeModal();
    await loadList(out.id);
    await open(out.id);
    msg(`${r.network}: ${r.branches} branches, ${r.nodes} nodes, spec files ${r.spec_set}` +
        (r.unresolved.length ? ` — ${r.unresolved.length} unresolved: ${r.unresolved[0]}` : ''));
    if (r.mismatch && r.mismatch.length) specMismatch(r.mismatch);
  };
}

// The program's warning on opening a network with other spec files than it
// was saved with (the user: it tells the designer which spec set the
// network was saved with; it does not stop another set being used, as for
// a node upgrade).
function specMismatch(lines) {
  modal(`<div class="msgbox"><div class="mbtitle">Spec File Mismatch</div>
    <div class="mbbody"><span class="mbicon warn">!</span><table class="mismatch">${
      lines.map(([what, text]) => `<tr><td>${esc(what)}:</td><td>${esc(text)}</td></tr>`).join('')
    }</table></div><div class="row"><button id="mbOk">OK</button></div></div>`);
  $('#mbOk').onclick = closeModal; $('#mbOk').focus();
}

// ---------------------------------------------------------------- saving
// File > Save Network writes the network back into the .ntw it was opened
// from, as the program's Save does: opening a .ntw keeps hold of that file
// (the browser asks once for leave to save to it).  Save Network As... asks
// for a file, and the network then carries that file's name and saves there.
// A network with no file yet asks too; a browser with no file access
// (Firefox) downloads the file instead.  The file is held only while the
// page is open: nothing about a network is kept after it (the user).
const NTW_TYPES = [{ description: 'Lode Data network', accept: { 'application/octet-stream': ['.ntw'] } }];
const saveTo = {};                       // network id -> the file it saves to

async function keepFile(nid, handle) { saveTo[nid] = handle; }
async function fileFor(nid) { return saveTo[nid] || null; }

// earlier versions kept the last network opened and each network's file in
// the browser (the Windows program's window too): take them away
try { localStorage.removeItem('ntw.lastOpened'); } catch (_) {}
try { indexedDB.deleteDatabase('design-assistant'); } catch (_) {}

// The Windows program (LodeData.exe, desktop/lodedata_desktop.py) shows this
// page in its own window. There Open and Save go through Windows' own
// dialogs, a file is kept by its path, and Save writes straight back into it.
function desktopFile(path) {
  const name = path.split(/[\\/]/).pop();
  return {
    name, path,
    getFile: async () => {
      const b = atob(await window.pywebview.api.read_file(path));
      return new File([Uint8Array.from(b, c => c.charCodeAt(0))], name);
    },
    createWritable: async () => {
      const parts = [];
      return {
        write: async blob => { parts.push(blob); },
        close: async () => {
          const bytes = new Uint8Array(await new Blob(parts).arrayBuffer());
          let s = '';
          for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
          await window.pywebview.api.write_file(path, btoa(s));
        },
      };
    },
  };
}
function desktopDialogs() {
  const none = () => new DOMException('no file chosen', 'AbortError');
  window.showOpenFilePicker = async () => {
    const p = await window.pywebview.api.open_ntw();
    if (!p) throw none();
    return [desktopFile(p)];
  };
  window.showSaveFilePicker = async o => {
    const p = await window.pywebview.api.save_ntw((o && o.suggestedName) || 'network.ntw');
    if (!p) throw none();
    return desktopFile(p);
  };
}
window.addEventListener('pywebviewready', desktopDialogs);

async function saveNetwork(as) {
  if (!S.nid || !S.net) return;
  const nid = S.nid;
  let handle = as ? null : await fileFor(nid);
  try {
    if (!handle && window.showSaveFilePicker) {
      // asked for first, while the menu click still counts as the user's
      handle = await window.showSaveFilePicker({ suggestedName: `${S.net.name || 'network'}.ntw`, types: NTW_TYPES });
    }
    if (handle && handle.queryPermission &&
        await handle.queryPermission({ mode: 'readwrite' }) !== 'granted' &&
        await handle.requestPermission({ mode: 'readwrite' }) !== 'granted') {
      msg('not saved: leave to write the file was not given'); return;
    }
    const name = handle ? handle.name : `${S.net.name || 'network'}.ntw`;
    await saveChain;                     // every edit keyed so far goes in
    const r = await fetch(`/api/networks/${nid}/ntw?filename=${encodeURIComponent(name)}`, { method: 'POST' });
    if (!r.ok) {
      let t = await r.text();
      try { t = JSON.parse(t).detail || t; } catch (_) {}
      msg(t); return;
    }
    const blob = await r.blob();
    let skipped = [];
    try { skipped = JSON.parse(r.headers.get('X-Not-Written') || '[]'); } catch (_) {}
    if (handle) {
      const w = await handle.createWritable();
      await w.write(blob); await w.close();
      await keepFile(nid, handle);
    } else {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = name;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    }
    const stem = name.replace(/\.ntw$/i, '');
    if (S.nid === nid && S.net.name !== stem) {     // Save As under a new name
      S.net.name = stem;
      renderInfo();                      // the title bar carries the name
      await loadList(nid);
    }
    if (S.nid === nid) S.modified = false;
    msg(`saved ${name}` + (skipped.length ? ` — ${skipped.length} not written: ${skipped[0]}` : ''));
  } catch (e) {
    if (e.name !== 'AbortError') msg(e.message);
  }
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
  const s = specName(S.net.library) || 'Untitled';
  $('#stSpecs').textContent = `${s} : ${s} : ${s} : ${s} : ${s} : Untitled`;
  await refresh();
}
async function open(id) {
  S.nid = id; S.row = 0; S.branch = 1; S.modified = false;
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
$('#tbSave').onclick = () => saveNetwork(false);
$('#tbInsert').onclick = insertNode;
$('#tbDelete').onclick = deleteNode;

(async () => {
  let id = await loadList();
  if (!id) {
    const d = await api('/api/networks', { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'lode-1', sample_specs: false, header_from: lastOpened() }) });
    id = await loadList(d.id);
  }
  await open(id);
  // the program opens Project Settings on startup unless Show on startup
  // was unticked there
  if (showOnStartup()) projectSettings();
})();
